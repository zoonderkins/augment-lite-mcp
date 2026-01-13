import subprocess
import shutil
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.validators import validate_project_path


def _run(cmd):
    """Run a command and capture output."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
        return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "error": "Command timed out", "returncode": -1, "stdout": "", "stderr": ""}
    except Exception as e:
        return {"cmd": cmd, "error": str(e), "returncode": -1, "stdout": "", "stderr": ""}


def run_checks(repo_path: str = "."):
    """
    Run code quality checks on a repository.

    Args:
        repo_path: Path to the repository to check

    Returns:
        Dictionary with check results
    """
    # Validate path (security: prevent command injection)
    try:
        validated_path = validate_project_path(repo_path)
        safe_path = str(validated_path)
    except ValueError as e:
        return {"error": f"Invalid repository path: {e}"}

    report = {"ruff": None, "pytest": None, "mypy": None}

    if shutil.which("ruff"):
        report["ruff"] = _run(["ruff", "check", safe_path])
    if shutil.which("pytest"):
        report["pytest"] = _run(["pytest", "-q", safe_path])
    if shutil.which("mypy"):
        report["mypy"] = _run(["mypy", "--strict", safe_path])

    return report