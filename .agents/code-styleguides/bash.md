# Bash & Shell Scripting Guide

Based on Google Shell Style Guide principles for portable, maintainable scripts.

## File Conventions

### Shebang and Encoding
```bash
#!/usr/bin/env bash
# Use env for portability across systems

# For POSIX-only scripts
#!/bin/sh
```

### File Extensions
- Executables: No extension or `.sh`
- Libraries: `.sh` extension required
- All scripts should be executable: `chmod +x script.sh`

## Script Structure

### Standard Template
```bash
#!/usr/bin/env bash
#
# Brief description of what the script does.
#
# Usage: script.sh [options] <arguments>

set -euo pipefail  # Strict mode
IFS=$'\n\t'        # Safer word splitting

# Constants
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Default values
DEBUG="${DEBUG:-false}"
VERBOSE="${VERBOSE:-false}"

main() {
    parse_args "$@"
    validate_environment
    # Main logic here
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                set -x
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                break
                ;;
        esac
    done
}

usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [options] <arguments>

Description of what this script does.

Options:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output
    -d, --debug     Enable debug mode

Examples:
    ${SCRIPT_NAME} --verbose input.txt
EOF
}

# Run main
main "$@"
```

## Strict Mode

### Always Use Strict Mode
```bash
set -euo pipefail

# -e: Exit on error
# -u: Error on undefined variables
# -o pipefail: Pipeline fails if any command fails
```

### Handling Expected Failures
```bash
# When a command might fail
if ! command_that_might_fail; then
    echo "Command failed, continuing..."
fi

# Or capture exit code
set +e  # Temporarily disable
command_that_might_fail
exit_code=$?
set -e  # Re-enable
```

## Variables

### Naming Conventions
```bash
# Constants: UPPER_SNAKE_CASE
readonly MAX_RETRIES=3
readonly CONFIG_FILE="/etc/app/config"

# Local variables: lower_snake_case
local file_count=0
local temp_dir=""

# Environment variables: UPPER_SNAKE_CASE
export DATABASE_URL="postgres://..."
```

### Variable Expansion
```bash
# Always quote variables
echo "${variable}"        # Good
echo "$variable"          # Acceptable
echo $variable            # Bad - word splitting issues

# Default values
name="${NAME:-default}"   # Use default if unset or empty
name="${NAME-default}"    # Use default only if unset

# Required variables
: "${REQUIRED_VAR:?Error: REQUIRED_VAR must be set}"
```

### Arrays
```bash
# Declare arrays
declare -a files=("file1.txt" "file2.txt")
declare -A config=(["key"]="value" ["other"]="data")

# Iterate safely
for file in "${files[@]}"; do
    echo "${file}"
done

# Array length
echo "Count: ${#files[@]}"
```

## Functions

### Function Style
```bash
# Preferred: function keyword with parentheses
function do_something() {
    local input="$1"
    local output=""

    # Function body
    output="processed: ${input}"

    echo "${output}"
}

# Alternative: just parentheses (POSIX compatible)
do_something() {
    # ...
}
```

### Return Values
```bash
# Return status codes (0 = success, non-zero = failure)
function is_valid() {
    local value="$1"
    [[ -n "${value}" ]] && return 0 || return 1
}

# Return data via stdout
function get_config() {
    echo "config_value"
}

# Capture output
result="$(get_config)"
```

### Local Variables
```bash
function process_file() {
    local file="$1"           # Always use local
    local -r constant="value" # Local readonly
    local -i counter=0        # Local integer
    local -a items=()         # Local array
}
```

## Control Flow

### Conditionals
```bash
# Test command (preferred)
if [[ -f "${file}" ]]; then
    echo "File exists"
elif [[ -d "${file}" ]]; then
    echo "Is directory"
else
    echo "Not found"
fi

# String comparisons
[[ "${str}" == "value" ]]     # Equal
[[ "${str}" != "value" ]]     # Not equal
[[ "${str}" =~ ^[0-9]+$ ]]    # Regex match
[[ -z "${str}" ]]             # Empty
[[ -n "${str}" ]]             # Not empty

# Numeric comparisons
[[ "${num}" -eq 5 ]]          # Equal
[[ "${num}" -lt 10 ]]         # Less than
(( num > 5 ))                 # Arithmetic comparison
```

### Loops
```bash
# Iterate over array
for item in "${array[@]}"; do
    echo "${item}"
done

# C-style for loop
for ((i = 0; i < 10; i++)); do
    echo "${i}"
done

# While loop with read
while IFS= read -r line; do
    echo "${line}"
done < "${input_file}"

# Process command output
while IFS= read -r file; do
    process "${file}"
done < <(find . -name "*.txt")
```

## Error Handling

### Logging Functions
```bash
readonly RED='\033[0;31m'
readonly YELLOW='\033[0;33m'
readonly GREEN='\033[0;32m'
readonly NC='\033[0m'  # No Color

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

function info() {
    echo -e "${GREEN}[INFO]${NC} $*" >&2
}

function warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

function error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    exit 1
}

function debug() {
    if [[ "${DEBUG}" == "true" ]]; then
        echo -e "[DEBUG] $*" >&2
    fi
}
```

### Trap for Cleanup
```bash
function cleanup() {
    local exit_code=$?
    # Cleanup temp files
    [[ -d "${TEMP_DIR:-}" ]] && rm -rf "${TEMP_DIR}"
    exit "${exit_code}"
}

trap cleanup EXIT ERR INT TERM

# Create temp directory
TEMP_DIR="$(mktemp -d)"
```

## Command Execution

### Subshells and Command Substitution
```bash
# Command substitution (preferred)
result="$(command)"

# Avoid backticks
result=`command`  # Bad - hard to nest, read

# Subshell for isolation
(
    cd /some/dir
    ./run_here.sh
)
# Original directory preserved
```

### Checking Command Existence
```bash
function require_command() {
    local cmd="$1"
    if ! command -v "${cmd}" &> /dev/null; then
        error "Required command not found: ${cmd}"
    fi
}

require_command "jq"
require_command "curl"
```

### Safe Command Execution
```bash
# Check before running
if [[ -x "${script}" ]]; then
    "${script}"
fi

# Capture both stdout and stderr
output="$(command 2>&1)" || {
    echo "Command failed: ${output}"
    exit 1
}
```

## File Operations

### Safe File Handling
```bash
# Check file exists and is readable
[[ -r "${file}" ]] || error "Cannot read: ${file}"

# Safe temporary files
temp_file="$(mktemp)"
trap 'rm -f "${temp_file}"' EXIT

# Atomic writes
echo "content" > "${temp_file}"
mv "${temp_file}" "${target_file}"
```

### Path Handling
```bash
# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolve symlinks
REAL_PATH="$(readlink -f "${path}")"

# Join paths safely
full_path="${dir}/${file}"
```

## Best Practices

- Use `shellcheck` for linting: `shellcheck script.sh`
- Always quote variables: `"${var}"`
- Use `[[` over `[` for tests (bash-specific but safer)
- Prefer `$(command)` over backticks
- Use `local` for function variables
- Use `readonly` for constants
- Use arrays for lists, not space-separated strings
- Redirect errors to stderr: `echo "error" >&2`
- Use meaningful exit codes (0=success, 1=general error, 2=misuse)

## Anti-Patterns

```bash
# Bad: Unquoted variables
for file in $files; do  # Word splitting issues

# Good: Quoted expansion
for file in "${files[@]}"; do

# Bad: Using ls in scripts
for file in $(ls *.txt); do  # Parsing ls is fragile

# Good: Use globbing or find
for file in *.txt; do
# Or
while IFS= read -r -d '' file; do
    process "${file}"
done < <(find . -name "*.txt" -print0)

# Bad: cd without error handling
cd /some/dir
./script.sh

# Good: Handle cd failure
cd /some/dir || error "Failed to cd to /some/dir"
./script.sh

# Bad: Eval with user input
eval "${user_input}"  # Security vulnerability

# Good: Use arrays for command building
cmd=("ls" "-la" "${dir}")
"${cmd[@]}"
```

## Cross-Platform Compatibility

For scripts that must run on diverse systems (Linux, Solaris, HP-UX, AIX, Windows via WSL/Cygwin), apply these additional patterns.

### Locale Setup

```bash
# Ensure consistent string processing across systems
export LC_ALL=C
export LANG=C
```

### OS Detection Pattern

```bash
OS_NAME=$(uname -s)
case "${OS_NAME}" in
  Linux*)     PLATFORM="Linux" ;;
  Darwin*)    PLATFORM="Mac" ;;
  SunOS*)     PLATFORM="Solaris" ;;
  CYGWIN*)    PLATFORM="Cygwin" ;;
  MINGW*)     PLATFORM="MinGW" ;;
  AIX*)       PLATFORM="AIX" ;;
  HP-UX*)     PLATFORM="HPUX" ;;
  *)          PLATFORM="UNKNOWN:${OS_NAME}" ;;
esac
```

### Command Resolution for Legacy Unix

Critical for Solaris/AIX compatibility where standard tools may be non-POSIX.

```bash
# Default to standard path
GREP="grep"
AWK="awk"
SED="sed"

if [[ "${PLATFORM}" == "Solaris" ]]; then
  # Solaris: Use xpg4 versions for POSIX compliance
  [[ -x /usr/xpg4/bin/grep ]] && GREP="/usr/xpg4/bin/grep"
  [[ -x /usr/xpg4/bin/awk ]] && AWK="/usr/xpg4/bin/awk"
  [[ -x /usr/xpg4/bin/sed ]] && SED="/usr/xpg4/bin/sed"
fi

# Validate critical tools exist
for cmd in "${GREP}" "${AWK}" "${SED}"; do
  command -v "${cmd}" &> /dev/null || {
    echo "Error: Required command '${cmd}' not found." >&2
    exit 1
  }
done
```

### Windows Path Handling (WSL & Cygwin)

```bash
normalize_path() {
  local path="$1"
  if [[ "${PLATFORM}" == "Cygwin" ]]; then
    cygpath -w "${path}"
  elif grep -q "Microsoft" /proc/version 2>/dev/null; then
    # WSL detection
    wslpath -w "${path}"
  else
    echo "${path}"
  fi
}
```
