import re

# Danh sách chuyển đổi enum từ PyQt5 → PyQt6 
replacements = {
    # Qt enums
    r'\bQtCore\.Qt\.ApplicationModal\b': 'QtCore.Qt.WindowModality.ApplicationModal',
    r'\bQtCore\.Qt\.LeftToRight\b': 'QtCore.Qt.LayoutDirection.LeftToRight',
    r'\bQtCore\.Qt\.NoFocus\b': 'QtCore.Qt.FocusPolicy.NoFocus',
    r'\bQtCore\.Qt\.TabFocus\b': 'QtCore.Qt.FocusPolicy.TabFocus',
    r'\bQtCore\.Qt\.WheelFocus\b': 'QtCore.Qt.FocusPolicy.WheelFocus',
    r'\bQtCore\.Qt\.NoContextMenu\b': 'QtCore.Qt.ContextMenuPolicy.NoContextMenu',
    r'\bQtCore\.Qt\.PlainText\b': 'QtCore.Qt.TextFormat.PlainText',
    r'\bQtCore\.Qt\.ImhDigitsOnly\b': 'QtCore.Qt.InputMethodHint.ImhDigitsOnly',
    r'\bQtCore\.Qt\.NoPen\b': 'QtCore.Qt.PenStyle.NoPen',

    # QLayout
    r'\bQtWidgets\.QLayout\.SetDefaultConstraint\b': 'QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint',

    # QSizePolicy
    r'\bQtWidgets\.QSizePolicy\.Preferred\b': 'QtWidgets.QSizePolicy.Policy.Preferred',

    # QFrame
    r'\bQtWidgets\.QFrame\.NoFrame\b': 'QtWidgets.QFrame.Shape.NoFrame',
    r'\bQtWidgets\.QFrame\.Plain\b': 'QtWidgets.QFrame.Shadow.Plain',
    r'\bQtWidgets\.QFrame\.Raised\b': 'QtWidgets.QFrame.Shadow.Raised',
    r'\bQtWidgets\.QFrame\.Shape\.Plain\b': 'QtWidgets.QFrame.Shadow.Plain',
    r'\bQtWidgets\.QFrame\.Shape\.Raised\b': 'QtWidgets.QFrame.Shadow.Raised',

    # QLineEdit
    r'\bQtWidgets\.QLineEdit\.Password\b': 'QtWidgets.QLineEdit.EchoMode.Password',
    r'\bQtWidgets\.QLineEdit\.Mode\.Normal\b': 'QtWidgets.QLineEdit.EchoMode.Normal',

    # QFormLayout
    r'\bQtWidgets\.QFormLayout\.LabelRole\b': 'QtWidgets.QFormLayout.ItemRole.LabelRole',

    # QAbstractItemView
    r'\bQtWidgets\.QAbstractItemView\.ExtendedSelection\b': 'QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection',
    r'\bQtWidgets\.QAbstractItemView\.SelectRows\b': 'QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows',

    # QIcon
    r'\bQtGui\.QIcon\.Normal\b': 'QtGui.QIcon.Mode.Normal',
    r'\bQtGui\.QIcon\.Off\b': 'QtGui.QIcon.State.Off',
    r'\bQIcon\.Normal\b': 'QIcon.Mode.Normal',
    r'\bQIcon\.Off\b': 'QIcon.State.Off',

    # QPixmap
    r'\bQtGui\.QPixmap\b': 'QPixmap',

    # setCursorMoveStyle
    r'\.setCursorMoveStyle\([^)]*\)': '',  # xóa dòng setCursorMoveStyle

    # setEchoMode dạng sai
    r'\.setEchoMode\(QtWidgets\.QLineEdit\.Mode': '.setEchoMode(QtWidgets.QLineEdit.EchoMode',
    r'\.setEchoMode\(QtWidgets\.QLineEdit\.EchoMode\.Mode\.': '.setEchoMode(QtWidgets.QLineEdit.EchoMode.',

    # setInputMethodHints dạng sai
    r'\.setInputMethodHints\(QtCore\.Qt\.ImhDigitsOnly\)': '.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhDigitsOnly)',

    # setDockOptions
    r'\bQMainWindow\.AllowTabbedDocks\b': 'QMainWindow.DockOption.AllowTabbedDocks',
    r'\bQMainWindow\.AnimatedDocks\b': 'QMainWindow.DockOption.AnimatedDocks',

    # Alignment
    r'\bQt::Align[A-Za-z]+\b': lambda m: m.group(0).replace('Qt::Align', 'Qt.AlignmentFlag.Align'),

        # QGraphicsView DragMode
    r'\bQtWidgets\.QGraphicsView\.ScrollHandDrag\b': 'QtWidgets.QGraphicsView.DragMode.ScrollHandDrag',
    r'\bQGraphicsView\.ScrollHandDrag\b': 'QGraphicsView.DragMode.ScrollHandDrag',

    # QGraphicsView RenderHint
    r'\bQGraphicsView\.Antialiasing\b': 'QGraphicsView.RenderHint.Antialiasing',
    r'\bQtWidgets\.QGraphicsView\.Antialiasing\b': 'QtWidgets.QGraphicsView.RenderHint.Antialiasing',
    r'\bQtWidgets\.QGraphicsView\.NoDrag\b': 'QtWidgets.QGraphicsView.DragMode.NoDrag',
    r'\bQtWidgets\.QGraphicsView\.RubberBandDrag\b': 'QtWidgets.QGraphicsView.DragMode.RubberBandDrag',

}

def convert_pyqt6_enums(code: str) -> str:
    for pattern, repl in replacements.items():
        if callable(repl):
            code = re.sub(pattern, repl, code)
        else:
            code = re.sub(pattern, repl, code)
    return code


# Dùng thử
if __name__ == "__main__":
    input_file = "main_ui.py"  # hoặc bất kỳ file .py nào bạn muốn sửa
    with open(input_file, "r", encoding="utf-8") as f:
        original_code = f.read()

    converted_code = convert_pyqt6_enums(original_code)

    with open(input_file, "w", encoding="utf-8") as f:
        f.write(converted_code)

    print(f"Doi enum PyQt6 trong file: {input_file}")

'''
from PyQt6.QtGui import QPixmap
from resources import resources_rc
'''