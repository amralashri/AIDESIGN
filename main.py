from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        print("PySide6 is not installed.")
        print("Run run.bat or install.bat from the AIDESIGN project folder.")
        return 1

    from app.application import AIDesignApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AIDESIGN")
    app.setOrganizationName("AIDESIGN")

    window = AIDesignApplication()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
