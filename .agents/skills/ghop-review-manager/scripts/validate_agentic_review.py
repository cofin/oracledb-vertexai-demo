"""Static validator for GHOP AGENTIC_REVIEW and domain review skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path

__all__ = ["ValidationResult", "main", "validate_repo"]

EXPECTED_SKILLS: tuple[str, ...] = (
    ".agents/skills/review-python-backend/SKILL.md",
    ".agents/skills/review-oracle-sqlspec/SKILL.md",
    ".agents/skills/review-ai-and-mcp/SKILL.md",
    ".agents/skills/review-web-htmx/SKILL.md",
)

DISABLED_GHOP_TOOLS: tuple[str, ...] = (
    "run_command",
    "code_search",
    "invoke_subagent",
    "define_subagent",
    "manage_subagents",
    "read_url_content",
    "search_web",
    "schedule",
    "generate_image",
)

MAX_SKILL_LINES = 150


class ValidationResult:
    """Accumulates validation errors across AGENTIC_REVIEW and review skills."""

    def __init__(self) -> None:
        """Initialize an empty error list."""
        self.errors: list[str] = []

    @property
    def is_valid(self) -> bool:
        """True when zero validation errors were recorded."""
        return not self.errors

    def add_error(self, message: str) -> None:
        """Record a validation error message."""
        self.errors.append(message)


def validate_repo(repo_root: Path) -> ValidationResult:
    """Validate AGENTIC_REVIEW and all registered domain review skills under repo_root."""
    result = ValidationResult()
    skill_paths = _validate_agentic_review_file(repo_root, result)
    seen_fp_ids: dict[str, Path] = {}
    for rel_path in skill_paths:
        _validate_skill_bundle(repo_root, rel_path, seen_fp_ids, result)
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint validating the repository root."""
    args = argv if argv is not None else sys.argv[1:]
    repo_root = Path(args[0]).resolve() if args else Path.cwd().resolve()
    result = validate_repo(repo_root)
    if not result.is_valid:
        for err in result.errors:
            sys.stderr.write(f"[ERROR] {err}\n")
        return 1
    sys.stdout.write(f"Validated AGENTIC_REVIEW and {len(EXPECTED_SKILLS)} GHOP review skills in {repo_root}\n")
    return 0


def _validate_agentic_review_file(repo_root: Path, result: ValidationResult) -> list[str]:
    """Validate AGENTIC_REVIEW textproto syntax and AutoRater line-parser compatibility."""
    agentic_review_path = repo_root / "AGENTIC_REVIEW"
    if not agentic_review_path.is_file():
        result.add_error(f"Missing AGENTIC_REVIEW at {agentic_review_path}")
        return []

    lines = agentic_review_path.read_text(encoding="utf-8").splitlines()
    autorater_skills: list[str] = []
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if "review_capability_skills" in raw_line:
            if stripped.startswith("#"):
                result.add_error(
                    f"AGENTIC_REVIEW:{idx}: Comment line must not contain 'review_capability_skills' "
                    "because github_worker_main.py parses every line containing that substring."
                )
                continue
            matches = re.findall(r'["\']([^"\']+)["\']', raw_line)
            if len(matches) != 1 or not re.fullmatch(r'review_capability_skills:\s*"[^"]+"', stripped):
                result.add_error(f"AGENTIC_REVIEW:{idx}: Must be single-line 'review_capability_skills: \"<path>\"'")
            autorater_skills.extend(matches)
        elif stripped and not stripped.startswith("#"):
            result.add_error(
                f"AGENTIC_REVIEW:{idx}: Unsupported field '{stripped}' "
                "(github_skills.py only reads review_capability_skills)"
            )

    if tuple(autorater_skills) != EXPECTED_SKILLS:
        result.add_error(f"AGENTIC_REVIEW skills {autorater_skills} do not match expected {list(EXPECTED_SKILLS)}")
    return autorater_skills


def _validate_skill_bundle(
    repo_root: Path, rel_skill_path: str, seen_fp_ids: dict[str, Path], result: ValidationResult
) -> None:
    """Validate a single SKILL.md and its references/ directory."""
    skill_path = repo_root / rel_skill_path
    if not skill_path.is_file():
        result.add_error(f"Registered skill file does not exist: {rel_skill_path}")
        return

    content = skill_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if len(lines) >= MAX_SKILL_LINES:
        result.add_error(
            f"{rel_skill_path}: {len(lines)} lines exceeds progressive-disclosure limit ({MAX_SKILL_LINES})"
        )

    expected_name = skill_path.parent.name
    _validate_frontmatter(rel_skill_path, lines, expected_name, result)
    _validate_no_positive_disabled_tools(rel_skill_path, lines, result)
    _validate_referenced_repo_paths(skill_path, content, repo_root, result.errors)

    refs_dir = skill_path.parent / "references"
    if not refs_dir.is_dir():
        result.add_error(f"{rel_skill_path}: Missing references/ directory at {refs_dir}")
        return

    fp_path = refs_dir / "false-positive-suppressions.md"
    if not fp_path.is_file():
        result.add_error(f"{rel_skill_path}: Missing {fp_path.relative_to(repo_root)}")
    else:
        _validate_fp_catalog(fp_path, seen_fp_ids, result)

    ref_files = sorted(refs_dir.glob("*.md"))
    for ref_file in ref_files:
        ref_text = ref_file.read_text(encoding="utf-8")
        ref_rel = str(ref_file.relative_to(repo_root))
        _validate_no_positive_disabled_tools(ref_rel, ref_text.splitlines(), result)
        _validate_referenced_repo_paths(ref_file, ref_text, repo_root, result.errors)

    checklist_files = [p for p in ref_files if p.name != "false-positive-suppressions.md"]
    if not checklist_files:
        result.add_error(f"{rel_skill_path}: Missing domain checklist .md in {refs_dir}")


def _validate_frontmatter(rel_skill_path: str, lines: list[str], expected_name: str, result: ValidationResult) -> None:
    """Verify YAML frontmatter has matching name and non-empty description."""
    if not lines or lines[0].strip() != "---":
        result.add_error(f"{rel_skill_path}: Missing opening YAML frontmatter delimiter '---'")
        return
    closing_idx = next((i for i in range(1, min(len(lines), 30)) if lines[i].strip() == "---"), None)
    if closing_idx is None:
        result.add_error(f"{rel_skill_path}: Missing closing YAML frontmatter delimiter '---'")
        return

    frontmatter = "\n".join(lines[1:closing_idx])
    name_match = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_match or name_match.group(1).strip("\"'") != expected_name:
        result.add_error(f"{rel_skill_path}: Frontmatter name must equal '{expected_name}'")
    if not desc_match or not desc_match.group(1).strip("\"' "):
        result.add_error(f"{rel_skill_path}: Frontmatter description must be non-empty")


def _validate_no_positive_disabled_tools(rel_skill_path: str, lines: list[str], result: ValidationResult) -> None:
    """Ensure no line positively instructs the bot to call a disabled GHOP tool."""
    negation_tokens = ("disabled", "never", "do not", "don't", "cannot", "not available")
    for idx, line in enumerate(lines, start=1):
        lower = line.lower()
        for tool_name in DISABLED_GHOP_TOOLS:
            if re.search(rf"\b{re.escape(tool_name)}\b", lower) and not any(neg in lower for neg in negation_tokens):
                result.add_error(
                    f"{rel_skill_path}:{idx}: References disabled GHOP tool '{tool_name}' "
                    "without an explicit prohibition/disabled notice"
                )


def _validate_fp_catalog(fp_path: Path, seen_fp_ids: dict[str, Path], result: ValidationResult) -> None:
    """Verify FP-* suppression headings exist, are sequential starting at 01, and are globally unique."""
    text = fp_path.read_text(encoding="utf-8")
    matches = re.findall(r"^##\s+`(FP-([A-Z]+)-(\d{2}))`", text, re.MULTILINE)
    if not matches:
        result.add_error(f"{fp_path}: Contains no '## `FP-<DOMAIN>-<NN>`' suppression headings")
        return

    prefixes = {prefix for _, prefix, _ in matches}
    if len(prefixes) > 1:
        result.add_error(f"{fp_path}: Inconsistent suppression domain prefixes {sorted(prefixes)}")

    actual_numbers = [int(num_str) for _, _, num_str in matches]
    expected_numbers = list(range(1, len(matches) + 1))
    if actual_numbers != expected_numbers:
        result.add_error(
            f"{fp_path}: Suppression numbers {actual_numbers} must be sequential starting at 01 ({expected_numbers})"
        )

    for fp_id, _, _ in matches:
        if fp_id in seen_fp_ids:
            result.add_error(f"Duplicate suppression ID {fp_id} in {fp_path} and {seen_fp_ids[fp_id]}")
        seen_fp_ids[fp_id] = fp_path


def _validate_referenced_repo_paths(md_path: Path, text: str, repo_root: Path, errors: list[str]) -> None:
    """Verify concrete backticked repository file and directory paths exist under repo_root."""
    repo_prefixes = ("src/", "tools/", "Makefile", "pyproject.toml", "manage.py")
    rel_md = md_path.relative_to(repo_root) if md_path.is_relative_to(repo_root) else md_path
    for raw_token in re.findall(r"`([^`\n]+)`", text):
        candidate = raw_token.strip().split("::", 1)[0]
        if not candidate.startswith(repo_prefixes):
            continue
        if any(ch in candidate for ch in ("*", "{", "}", "<", ">", " ")):
            continue
        target = repo_root / candidate.rstrip("/")
        if not target.exists():
            errors.append(f"{rel_md}: Referenced repository path does not exist: '{candidate}'")


if __name__ == "__main__":
    raise SystemExit(main())
