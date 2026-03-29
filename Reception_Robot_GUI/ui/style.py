# ui/style.py
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
import os

def load_stylesheet(filename):
    full_path = os.path.join(os.path.dirname(__file__), filename)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

QMSGBOX_STYLE = load_stylesheet("style.qss")

def show_custom_dialog(title, message, icon=QMessageBox.Icon.Information, main_window=None, offset_x=0, offset_y=0):
    msg = QMessageBox(main_window)  # Truyền main_window làm parent
    msg.setWindowTitle(title)
    msg.setIcon(icon)
    msg.setText(message)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.setStyleSheet(QMSGBOX_STYLE)

    def move_box():
        # Đảm bảo kích thước được cập nhật
        msg.adjustSize()
        
        # Tính toán vị trí dựa trên main_window
        if main_window and main_window.isVisible():  # Kiểm tra main_window hợp lệ và hiển thị
            parent_geom = main_window.geometry()
            new_x = parent_geom.x() + (parent_geom.width() - msg.width()) // 2 + offset_x
            new_y = parent_geom.y() + (parent_geom.height() - msg.height()) // 2 + offset_y
        else:
            # Dự phòng: căn giữa màn hình nếu không có main_window hoặc không hiển thị
            screen = msg.screen()
            if screen:  # Kiểm tra screen có hợp lệ không
                screen_geom = screen.geometry()
                new_x = screen_geom.x() + (screen_geom.width() - msg.width()) // 2 + offset_x
                new_y = screen_geom.y() + (screen_geom.height() - msg.height()) // 2 + offset_y
            else:
                new_x, new_y = offset_x, offset_y  # Dự phòng nếu không lấy được screen

        msg.move(int(new_x), int(new_y))  # Ép kiểu để đảm bảo giá trị nguyên

    # Đợi layout hoàn thiện với độ trễ nhỏ
    QTimer.singleShot(50, move_box)  # Độ trễ 50ms để đảm bảo layout hoàn thiện
    msg.exec()  # Hiển thị dialog