"""Qt binding shim. main branch: PySide6 (falls back to PySide2). LEGACY branch: PySide2 only."""
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    BINDING = "PySide6"
    QAction = QtGui.QAction
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    BINDING = "PySide2"
    QAction = QtWidgets.QAction


def exec_dialog(obj):
    return obj.exec() if hasattr(obj, "exec") and BINDING == "PySide6" else obj.exec_()
