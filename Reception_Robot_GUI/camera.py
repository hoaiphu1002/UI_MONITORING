# camera.py

import threading, requests, time
from PyQt6.QtCore import QUrl, QTimer, QLoggingCategory
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QWidget, QVBoxLayout

# Tat log từ Qt WebEngine
QLoggingCategory.setFilterRules("qt.webenginecontext=false")


class CameraController:
    def __init__(self):
        self.url_str = "http://10.177.199.230:5000"
        self.url = QUrl(self.url_str)
        self.browser = QWebEngineView()
        self.browser.setUrl(self.url)
        self.connected = True

        self.check_thread = threading.Thread(target=self._check_connection_loop, daemon=True)
        self.check_thread.start()

    def get_browser(self):
        return self.browser

    def _check_connection_loop(self):
        while True:
            try:
                res = requests.get(self.url_str, timeout=2)
                if res.status_code == 200 and not self.connected:
                    self.connected = True
                    QTimer.singleShot(0, self.browser.reload)
                elif res.status_code != 200:
                    raise Exception("status code not 200")
            except:
                self.connected = False
            time.sleep(5)


class CameraTab(QWidget):
    def __init__(self, ui_section, browser_widget):
        super().__init__()
        self.ui_section = ui_section
        self.browser = browser_widget

        layout = self.ui_section.layout()
        if layout is None:
            layout = QVBoxLayout(self.ui_section)
            self.ui_section.setLayout(layout)

        layout.addWidget(self.browser)
