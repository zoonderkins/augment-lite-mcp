import subprocess, shutil

def _run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"cmd": cmd, "error": str(e), "returncode": -1, "stdout": "", "stderr": ""}

def run_checks(repo_path: str="."):
    report = {"ruff": None, "pytest": None, "mypy": None}
    if shutil.which("ruff"):
        report["ruff"] = _run(["ruff", "check", repo_path])
    if shutil.which("pytest"):
        report["pytest"] = _run(["pytest", "-q", repo_path])
    if shutil.which("mypy"):
        report["mypy"]  = _run(["mypy", "--strict", repo_path])
    return report