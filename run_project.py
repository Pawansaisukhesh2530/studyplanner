"""Launch with local packages, including this computer's recovered environment."""

from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parent
for folder in (ROOT / ".runtime" / "packages", ROOT / ".venv" / "Lib" / "site-packages"):
    if folder.exists() and str(folder) not in sys.path:
        sys.path.append(str(folder))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "browser"
    if mode == "browser":
        sys.argv = ["streamlit", "run", str(ROOT / "app.py"), "--server.address=127.0.0.1"]
        runpy.run_module("streamlit", run_name="__main__")
    elif mode == "api":
        runpy.run_path(str(ROOT / "api.py"), run_name="__main__")
    elif mode == "desktop":
        runpy.run_path(str(ROOT / "faculty_desktop.py"), run_name="__main__")
    elif mode == "restore":
        runpy.run_path(str(ROOT / "restore_backup.py"), run_name="__main__")
    elif mode == "test":
        import unittest
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(not result.wasSuccessful())
    else:
        raise SystemExit("Choose browser, api, desktop, restore, or test.")


if __name__ == "__main__":
    main()
