from PyQt6.QtWidgets import QWidget
import pyqtgraph as pg
import time
from collections import deque

class PlotTelemetry(QWidget):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui

        # --- 3 layout đã có sẵn trong Qt Designer ---
        self.layout_imu  = self.ui.imupac
        self.layout_odom = self.ui.odompac
        self.layout_cte  = self.ui.cte

        self.imu_loss = 0.0
        self.odom_loss = 0.0

        # --- Check xem còn widget cũ k --- 
        for lay in (self.layout_imu, self.layout_odom, self.layout_cte):
            while lay.count():
                item = lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # --- Tạo 3 PlotWidget ---
        self.plot_imu = pg.PlotWidget(title="IMU Packet Loss (%)")
        self.plot_odom = pg.PlotWidget(title="Odom Packet Loss (%)")
        self.plot_cte = pg.PlotWidget(title="CTE Error (m)")

        # --- Style chung --- 
        for p in (self.plot_imu, self.plot_odom, self.plot_cte):
            p.setBackground('w')
            p.showGrid(x=True, y=True)
            p.setLabel('left', color='black', size='10pt')
            p.setLabel('bottom', 'Time (s)', color='black', size='10pt')

        # --- Thêm vào đúng layout tương ứng --- 
        self.layout_imu.addWidget(self.plot_imu)
        self.layout_odom.addWidget(self.plot_odom)
        self.layout_cte.addWidget(self.plot_cte)

        # --- Data buffers ---
        self.max_points = 1000
        self.t_imu = deque(maxlen=self.max_points)
        self.v_imu = deque(maxlen=self.max_points)

        self.t_odom = deque(maxlen=self.max_points)
        self.v_odom = deque(maxlen=self.max_points)

        self.t_cte = deque(maxlen=self.max_points)
        self.v_cte = deque(maxlen=self.max_points)

        self.start_time = time.time()

        # --- Curves ---
        self.curve_imu  = self.plot_imu.plot( pen=pg.mkPen('#e74c3c', width=2), name="IMU Loss")
        self.curve_odom = self.plot_odom.plot(pen=pg.mkPen('#3498db', width=2), name="Odom Loss")
        self.curve_cte  = self.plot_cte.plot( pen=pg.mkPen('#2ecc71', width=2), name="CTE")

    # ==============================================================

    def update_cte(self, cte):
        now = time.time() - self.start_time
        value = cte
        self.t_cte.append(now)
        self.v_cte.append(value)
        self.curve_cte.setData(self.t_cte, self.v_cte)
        self.plot_cte.setXRange(max(0, now - 15), now)   # show the last 15 secs


    def update_packet_loss(self, imu, odom, send):
        expected_imu = send
        expected_odom = send

        self.imu_loss = max(0.0, 100.0 * (expected_imu - imu) / expected_imu)
        self.odom_loss = max(0.0, 100.0 * (expected_odom - odom) / expected_odom)

        now = time.time() - self.start_time

        # Thêm điểm vào buffer
        self.t_imu.append(now)
        self.v_imu.append(self.imu_loss)

        self.t_odom.append(now)
        self.v_odom.append(self.odom_loss)

        # Update đồ thị ngay lập tức
        self.curve_imu.setData(self.t_imu, self.v_imu)
        self.curve_odom.setData(self.t_odom, self.v_odom)

        # XRange 2 phút
        self.plot_imu.setXRange(max(0, now - 120), now)
        self.plot_odom.setXRange(max(0, now - 120), now)
