#!/usr/bin/env python3
import sys

from viewer.app import ViewerApp
from viewer.main_window import MainWindow


def main():
    app = ViewerApp(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
