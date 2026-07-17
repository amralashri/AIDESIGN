from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REQUIRED = {
    "PySide6": "PySide6>=6.7,<7",
    "numpy": "numpy>=1.26",
    "scipy": "scipy>=1.12",
    "ezdxf": "ezdxf>=1.3",
}


def missing_packages() -> list[str]:
    return [
        requirement
        for module, requirement in REQUIRED.items()
        if importlib.util.find_spec(module) is None
    ]


def install_packages(packages: list[str]) -> bool:
    if not packages:
        return True

    print("Missing packages:")
    for item in packages:
        print(f"  - {item}")

    print("\nInstalling required packages. This may take a few minutes...")
    command = [sys.executable, "-m", "pip", "install", "--upgrade", *packages]
    completed = subprocess.run(command, check=False)
    return completed.returncode == 0


def main() -> int:
    missing = missing_packages()
    if missing and not install_packages(missing):
        print("\nInstallation failed.")
        print("Run this command manually:")
        print(f'  "{sys.executable}" -m pip install -r requirements.txt')
        input("\nPress Enter to close...")
        return 1

    try:
        from main import main as launch
        return int(launch() or 0)
    except Exception as exc:
        print("\nAIDESIGN failed to start:")
        print(f"{type(exc).__name__}: {exc}")
        input("\nPress Enter to close...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
