#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28.1",
#     "rich>=13.9.4",
# ]
# ///
"""Oracle SQLcl installer tool.

This tool downloads and installs the latest version of Oracle SQLcl
to a local directory (~/.local/bin by default).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

SQLCL_DOWNLOAD_URL = "https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-latest.zip"
DEFAULT_INSTALL_DIR = Path.home() / ".local" / "bin"


def download_sqlcl(temp_dir: Path) -> Path:
    """Download SQLcl zip file to temporary directory."""
    zip_path = temp_dir / "sqlcl-latest.zip"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading SQLcl...", total=None)

        with httpx.stream("GET", SQLCL_DOWNLOAD_URL, follow_redirects=True, timeout=300) as response:
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                f.writelines(response.iter_bytes(chunk_size=8192))

        progress.update(task, completed=True)

    console.print(f"[green]✓[/green] Downloaded to {zip_path}")
    return zip_path


def extract_sqlcl(zip_path: Path, temp_dir: Path) -> Path:
    """Extract SQLcl zip file."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting SQLcl...", total=None)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        progress.update(task, completed=True)

    extracted_dir = temp_dir / "sqlcl"
    console.print(f"[green]✓[/green] Extracted to {extracted_dir}")
    return extracted_dir


def install_sqlcl(extracted_dir: Path, install_dir: Path) -> None:
    """Install SQLcl to the specified directory."""
    install_dir.mkdir(parents=True, exist_ok=True)

    bin_dir = extracted_dir / "bin"
    if not bin_dir.exists():
        console.print(f"[red]✖[/red] SQLcl bin directory not found at {bin_dir}")
        raise SystemExit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Installing SQLcl...", total=None)

        # Copy all files from sqlcl directory to install location
        sqlcl_install_dir = install_dir.parent / "sqlcl"
        if sqlcl_install_dir.exists():
            shutil.rmtree(sqlcl_install_dir)

        shutil.copytree(extracted_dir, sqlcl_install_dir)

        # Create symlinks in bin directory
        for script in ["sql", "sqlcl"]:
            script_path = sqlcl_install_dir / "bin" / script
            if script_path.exists():
                symlink_path = install_dir / script
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()
                symlink_path.symlink_to(script_path)

        progress.update(task, completed=True)

    console.print(f"[green]✓[/green] SQLcl installed to {sqlcl_install_dir}")
    console.print(f"[green]✓[/green] Symlinks created in {install_dir}")


def verify_installation(install_dir: Path) -> None:
    """Verify SQLcl installation."""
    sql_path = install_dir / "sql"
    if not sql_path.exists():
        console.print("[red]✖[/red] Installation verification failed - sql command not found")
        raise SystemExit(1)

    console.print("[green]✓[/green] Installation verified successfully")


def main() -> None:
    """Main installation workflow."""
    console.print("[bold blue]Oracle SQLcl Installer[/bold blue]\n")

    # Check if install directory is in PATH
    install_dir = DEFAULT_INSTALL_DIR
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    if str(install_dir) not in path_dirs:
        console.print(
            f"[yellow]⚠[/yellow] {install_dir} is not in your PATH. "
            "You may need to add it to your shell configuration.\n"
        )

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download
            zip_path = download_sqlcl(temp_path)

            # Extract
            extracted_dir = extract_sqlcl(zip_path, temp_path)

            # Install
            install_sqlcl(extracted_dir, install_dir)

            # Verify
            verify_installation(install_dir)

        console.print("\n[bold green]✓ SQLcl installation complete![/bold green]")
        console.print("\nRun [cyan]sql -V[/cyan] to verify the installation")

        if str(install_dir) not in path_dirs:
            console.print("\n[yellow]Add to your PATH:[/yellow]")
            console.print(f'  export PATH="$PATH:{install_dir}"')

    except httpx.HTTPError as e:
        console.print(f"[red]✖[/red] Download failed: {e}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]✖[/red] Installation failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
