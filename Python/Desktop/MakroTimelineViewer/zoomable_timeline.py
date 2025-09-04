import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QWheelEvent, QMouseEvent

from event_loader import EventLoader
from event_visualizer import EventVisualizer
from graph_visualizer import GraphVisualizer


class ZoomableTimeline(QWidget):
    def __init__(self, action_log_path=None, mouse_moves_log_path="mouse_moves.log", event_data=None):
        super().__init__()
        self.setMinimumSize(400,200)
        
        # Initialize components
        self.event_visualizer = EventVisualizer(self)
        self.graph_visualizer = GraphVisualizer(self)
        
        # Timeline state
        self.min_scale = 0.02
        self.max_scale = 10000.0
        self.min_time = -10.0
        self.scale = 1.0
        self.offset = 0.0
        
        # Mouse interaction
        self.dragging = False
        self.last_mouse_pos = None
        self.mouse_press_pos = None
        
        # Animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(16)
        self.animation_time = 0
        
        # Load data
        self.load_data(action_log_path, event_data, mouse_moves_log_path)
        
        self.setMouseTracking(True)
        
    def load_data(self, action_log_path, event_data, mouse_moves_log_path):
        """Load event and movement data"""
        # Load events
        if action_log_path is None:
            self.events = EventLoader.process_events(event_data)
        else:
            self.events = EventLoader.load_events_from_log(action_log_path)
        
        # Initialize scale and offset based on events
        if self.events:
            event_times = [float(event["time"]) for event in self.events if event.get("time") is not None]
            if event_times:
                min_time = min(event_times)
                max_time = max(event_times)
                time_range = max_time - min_time if max_time != min_time else 1.0
                padding = time_range * 0.1
                visible_range = time_range + (2 * padding)
                self.scale = (self.width() * 0.8) / visible_range
                self.scale = max(self.min_scale, min(self.max_scale, self.scale))
                self.offset = (max_time + min_time) / 2
        # Load movement data
        try:
            self.graph_times, self.graph_values = EventLoader.load_movements_per_second(mouse_moves_log_path)
        except:
            self.graph_times, self.graph_values = [], []
        
    def set_events(self, events):
        self.events = events
        self.update()
        
    def paintEvent(self, event):
        """Handle paint event"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(self.rect(), QColor(20, 20, 20))
            
            width = self.width()
            height = self.height()
            center_y = height // 2 -50
            
            # Draw components
            self.graph_visualizer.draw_background_graph(painter, width, height, center_y)
            self.draw_timeline(painter, width, height, center_y)
            self.event_visualizer.draw_events(painter, width, height, center_y)
            self.draw_time_labels(painter, width, height, center_y)
            self.draw_info(painter)
            
        finally:
            # Ensure painter is properly ended
            painter.end()
        
    def draw_timeline(self, painter, width, height, center_y):
        """Draw the main timeline"""
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.drawLine(0, center_y, width, center_y)
        
        pixel_range = width / self.scale
        major_interval, minor_interval = self.get_intervals(pixel_range)
        
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        
        # Draw minor ticks
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        if minor_interval > 0:
            minor_start = math.floor(start_time / minor_interval) * minor_interval
            time = minor_start
            while time <= end_time:
                x = self.time_to_pixel(time, width)
                if 0 <= x <= width:
                    painter.drawLine(x, center_y - 5, x, center_y + 5)
                time += minor_interval
                
        # Draw major ticks
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        major_start = math.floor(start_time / major_interval) * major_interval
        time = major_start
        while time <= end_time:
            x = self.time_to_pixel(time, width)
            if 0 <= x <= width:
                painter.drawLine(x, center_y - 15, x, center_y + 15)
            time += major_interval
            
    def get_intervals(self, pixel_range):
        """Calculate appropriate intervals for timeline ticks"""
        if pixel_range > 7200:
            return 3600, 1800
        elif pixel_range > 3600:
            return 1800, 600
        elif pixel_range > 1800:
            return 600, 300
        elif pixel_range > 600:
            return 300, 60
        elif pixel_range > 60:
            return 60, 10
        elif pixel_range > 10:
            return 10, 1
        else:
            return 1, 0.1
            
    def draw_time_labels(self, painter, width, height, center_y):
        """Draw time labels on the timeline"""
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        pixel_range = width / self.scale
        
        label_interval = self.get_label_interval(pixel_range)
        label_start = math.floor(start_time / label_interval) * label_interval
        
        time = label_start
        while time <= end_time:
            x = self.time_to_pixel(time, width)
            if 0 <= x <= width:
                label = self.format_time(time)
                text_rect = painter.fontMetrics().boundingRect(label)
                painter.drawText(x - text_rect.width() // 2, center_y + 35, label)
            time += label_interval
            
    def get_label_interval(self, pixel_range):
        """Calculate appropriate interval for time labels"""
        if pixel_range > 7200:
            return 3600
        elif pixel_range > 3600:
            return 1800
        elif pixel_range > 1800:
            return 600
        elif pixel_range > 600:
            return 300
        elif pixel_range > 60:
            return 60
        elif pixel_range > 10:
            return 10
        else:
            return 1
            
    def draw_info(self, painter):
        """Draw information overlay"""
        painter.setFont(QFont("Arial", 10))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        info_lines = [
        ]
        for i, line in enumerate(info_lines):
            painter.drawText(10, 20 + i * 15, line)
            
    def format_time(self, seconds):
        """Format time value as string"""
        if seconds < 0:
            return ""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        elif minutes > 0:
            return f"{minutes:02d}:{secs:06.3f}"
        else:
            return f"{secs:.3f}s"
            
    def time_to_pixel(self, time, width):
        """Convert time value to pixel position"""
        return width // 2 + (time - self.offset) * self.scale
        
    def pixel_to_time(self, pixel, width):
        """Convert pixel position to time value"""
        return self.offset + (pixel - width // 2) / self.scale
        
    def animate(self):
        """Handle animation timer"""
        self.animation_time += 0.016
        self.update()
        
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel zoom"""
        mouse_x = event.position().x()
        mouse_time = self.pixel_to_time(mouse_x, self.width())
        
        zoom_factor = 1.2 if event.angleDelta().y() > 0 else 1.0 / 1.2
        new_scale = self.scale * zoom_factor
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        
        if new_scale != self.scale:
            old_scale = self.scale
            self.scale = new_scale
            new_mouse_time = self.pixel_to_time(mouse_x, self.width())
            new_offset = self.offset + mouse_time - new_mouse_time
            
            leftmost_time = new_offset - self.width() / (2 * self.scale)
            if leftmost_time >= self.min_time:
                self.offset = new_offset
            else:
                self.offset = self.min_time + self.width() / (2 * self.scale)
                
        self.update()
        event.accept()
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            self.mouse_press_pos = event.position()
            if self.dragging:
                self.dragging = False
                self.last_mouse_pos = None
            else:
                self.dragging = True
            self.last_mouse_pos = event.position()
        event.accept()
        
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse movement"""
        if self.dragging and self.last_mouse_pos:
            delta_x = event.position().x() - self.last_mouse_pos.x()
            delta_time = -delta_x / self.scale
            new_offset = self.offset + delta_time
            
            leftmost_time = new_offset - self.width() / (2 * self.scale)
            if leftmost_time >= self.min_time:
                self.offset = new_offset
            else:
                self.offset = self.min_time + self.width() / (2 * self.scale)
                
            self.last_mouse_pos = event.position()
            self.update()
        event.accept()