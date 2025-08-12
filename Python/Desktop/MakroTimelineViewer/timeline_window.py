from PySide6.QtWidgets import QMainWindow
from zoomable_timeline import ZoomableTimeline

class TimelineWindow(QMainWindow):
    def __init__(self, action_log_path="actions.log", mouse_moves_log_path="mouse_moves.log"):
        super().__init__()
        self.setWindowTitle("Zoomable Timeline with Background Graph")
        self.setGeometry(100, 100, 1000, 500)
        self.timeline = ZoomableTimeline(action_log_path, mouse_moves_log_path)
        self.setCentralWidget(self.timeline)
