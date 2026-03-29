from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget

def set_bold(widget: QWidget):
    font = widget.font()
    font.setWeight(QFont.Weight.Bold)
    widget.setFont(font)

def set_regular(widget: QWidget):
    font = widget.font()
    font.setWeight(QFont.Weight.Normal)
    widget.setFont(font)

def set_font_weight(widget: QWidget, weight: int):
    font = widget.font()
    font.setWeight(weight)
    widget.setFont(font)

def set_bold_for_widgets(widgets: list[QWidget]):
    for w in widgets:
        set_bold(w)

def set_regular_for_widgets(widgets: list[QWidget]):
    for w in widgets:
        set_regular(w)
