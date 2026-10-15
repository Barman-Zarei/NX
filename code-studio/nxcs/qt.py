"""Qt binding shim. main: PySide6 (Qt 6). LEGACY branch ships PySide2 (Qt 5.15) for Windows 7 / old PCs."""
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    BINDING = "PySide6"
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    BINDING = "PySide2"
Signal = QtCore.Signal


def exec_app(app):
    return app.exec() if hasattr(app, "exec") and BINDING == "PySide6" else app.exec_()


def exec_dialog(dlg):
    return dlg.exec() if BINDING == "PySide6" else dlg.exec_()
