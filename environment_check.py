from __future__ import annotations

import importlib
import platform
import sys


PACKAGES = ("PySide6", "numpy", "scipy", "ezdxf")


def main() -> None:
    print("AIDESIGN Environment Check")
    print("=" * 40)
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    print()

    failed = False
    for package in PACKAGES:
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", "installed")
            print(f"[OK] {package}: {version}")
        except Exception as exc:
            failed = True
            print(f"[MISSING] {package}: {exc}")

    print()
    if failed:
        print("Run install.bat, then run this check again.")
    else:
        print("Environment is ready. Run run.bat.")


if __name__ == "__main__":
    main()
