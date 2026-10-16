try:
    from PySide6 import QtCore, QtGui, QtWidgets
    BINDING = "PySide6"
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    BINDING = "PySide2"
