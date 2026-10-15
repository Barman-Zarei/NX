"""Qt binding for the LEGACY branch: PySide2 (Qt 5.15) ONLY, so the GUI runs on Windows 7 SP1+ and older PCs
(Python 3.8, PySide2 5.15.2.1). PySide6/Qt 6 is deliberately NOT imported here: it does not run on Windows 7."""
from PySide2 import QtCore, QtGui, QtWidgets
BINDING = "PySide2"
Signal = QtCore.Signal


def exec_app(app):
    return app.exec_()


def exec_dialog(dlg):
    return dlg.exec_()
