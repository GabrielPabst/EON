import sys
import math
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QWheelEvent, QMouseEvent

class ZoomableTimeline(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 400)
        
        # Timeline state
        self.scale = 1.0  # pixels per second
        self.offset = 300.0  # offset in seconds (start at 5 minutes)
        self.min_scale = 0.02  # minimum zoom (1 pixel = 50 seconds, shows ~22 hours on 1600px screen)
        self.max_scale = 1000.0  # maximum zoom (1000 pixels = 1 second)
        self.min_time = 0.0  # minimum time (can't go below 0)
        
        # Mouse interaction
        self.dragging = False
        self.last_mouse_pos = None
        
        # Animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(16)  # ~60 FPS
        self.animation_time = 0
        
        # Sample timeline events
        self.events = [
            {"time": 0, "label": "Project Start", "color": QColor(255, 100, 100)},
            {"time": 15, "label": "Setup Complete", "color": QColor(100, 255, 100)},
            {"time": 30, "label": "Development Begin", "color": QColor(100, 150, 255)},
            {"time": 35, "label": "First Commit", "color": QColor(255, 200, 100)},
            {"time": 120, "label": "Alpha Release", "color": QColor(100, 100, 255)},
            {"time": 300, "label": "Beta Testing", "color": QColor(255, 255, 100)},
            {"time": 320, "label": "Bug Fixes", "color": QColor(255, 150, 150)},
            {"time": 450, "label": "Final Review", "color": QColor(255, 100, 255)},
            {"time": 600, "label": "Production Deploy", "color": QColor(100, 255, 255)},
        ]
        
        self.setMouseTracking(True)
    
    def animate(self):
        self.animation_time += 0.016
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Clear background
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        
        width = self.width()
        height = self.height()
        center_y = height // 2
        
        # Draw main timeline
        self.draw_timeline(painter, width, height, center_y)
        
        # Draw events
        self.draw_events(painter, width, height, center_y)
        
        # Draw time labels
        self.draw_time_labels(painter, width, height, center_y)
        
        # Draw info
        self.draw_info(painter)
    
    def draw_timeline(self, painter, width, height, center_y):
        # Main timeline line
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.drawLine(0, center_y, width, center_y)
        
        # Calculate tick intervals based on zoom level
        pixel_range = width / self.scale  # seconds visible on screen
        
        # Determine appropriate tick interval (more conservative ranges)
        if pixel_range > 7200:  # > 2 hours visible
            major_interval = 3600  # 1 hour
            minor_interval = 1800  # 30 minutes
        elif pixel_range > 3600:  # > 1 hour visible
            major_interval = 1800  # 30 minutes
            minor_interval = 600   # 10 minutes
        elif pixel_range > 1800:  # > 30 minutes visible
            major_interval = 600   # 10 minutes
            minor_interval = 300   # 5 minutes
        elif pixel_range > 600:   # > 10 minutes visible
            major_interval = 300   # 5 minutes
            minor_interval = 60    # 1 minute
        elif pixel_range > 60:    # > 1 minute visible
            major_interval = 60    # 1 minute
            minor_interval = 10    # 10 seconds
        elif pixel_range > 10:    # > 10 seconds visible
            major_interval = 10    # 10 seconds
            minor_interval = 1     # 1 second
        else:                     # < 10 seconds visible
            major_interval = 1     # 1 second
            minor_interval = 0.1   # 100 milliseconds
        
        # Draw ticks
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        
        # Minor ticks
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        minor_start = math.floor(start_time / minor_interval) * minor_interval
        time = minor_start
        while time <= end_time:
            x = self.time_to_pixel(time, width)
            if 0 <= x <= width:
                painter.drawLine(x, center_y - 5, x, center_y + 5)
            time += minor_interval
        
        # Major ticks
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        major_start = math.floor(start_time / major_interval) * major_interval
        time = major_start
        while time <= end_time:
            x = self.time_to_pixel(time, width)
            if 0 <= x <= width:
                painter.drawLine(x, center_y - 15, x, center_y + 15)
            time += major_interval
    
    def draw_events(self, painter, width, height, center_y):
        # First, cluster events that are too close together
        clustered_events = self.cluster_events(width)
        
        for event_data in clustered_events:
            x = self.time_to_pixel(event_data["time"], width)
            if -100 <= x <= width + 100:  # Draw events slightly outside viewport
                self.draw_single_event(painter, event_data, x, center_y)
    
    def cluster_events(self, width):
        """Cluster events that would overlap when drawn"""
        if not self.events:
            return []
        
        # Calculate minimum box width (approximate)
        min_box_width = 80  # minimum pixels between event centers
        min_time_distance = min_box_width / self.scale
        
        # Sort events by time
        sorted_events = sorted(self.events, key=lambda e: e["time"])
        clustered = []
        
        i = 0
        while i < len(sorted_events):
            current_event = sorted_events[i]
            cluster_events = [current_event]
            cluster_start_time = current_event["time"]
            
            # Look ahead for events that should be clustered
            j = i + 1
            while j < len(sorted_events):
                next_event = sorted_events[j]
                if next_event["time"] - cluster_start_time < min_time_distance:
                    cluster_events.append(next_event)
                    j += 1
                else:
                    break
            
            # Create cluster or single event
            if len(cluster_events) > 1:
                # Create clustered event
                avg_time = sum(e["time"] for e in cluster_events) / len(cluster_events)
                clustered.append({
                    "time": avg_time,
                    "label": f"Clustered Events ({len(cluster_events)})",
                    "color": QColor(150, 150, 150),
                    "is_cluster": True,
                    "cluster_events": cluster_events
                })
            else:
                # Single event
                event = cluster_events[0].copy()
                event["is_cluster"] = False
                clustered.append(event)
            
            i = j
        
        return clustered
    
    def draw_single_event(self, painter, event_data, x, center_y):
        """Draw a single event with rounded box and pointer line"""
        # Event colors
        event_color = event_data["color"]
        text_color = QColor(255, 255, 255)
        time_color = QColor(200, 200, 200)
        
        # Text setup for event label
        font = QFont("Arial", 9, QFont.Bold if not event_data.get("is_cluster", False) else QFont.Normal)
        painter.setFont(font)
        
        label = event_data["label"]
        text_rect = painter.fontMetrics().boundingRect(label)
        
        # Time label setup
        time_font = QFont("Arial", 8)
        painter.setFont(time_font)
        time_label = self.format_time(event_data["time"])
        time_rect = painter.fontMetrics().boundingRect(time_label)
        
        # Box dimensions (accommodate both texts)
        box_padding = 8
        box_width = max(text_rect.width(), time_rect.width()) + 2 * box_padding
        box_height = text_rect.height() + time_rect.height() + 3 * box_padding  # Extra space between texts
        box_radius = 8
        
        # Position box above timeline
        box_y = center_y - 80
        box_x = x - box_width // 2
        
        # Ensure box stays within screen bounds
        box_x = max(5, min(self.width() - box_width - 5, box_x))
        
        # Draw pointer line from box to exact timestamp
        line_start_x = box_x + box_width // 2
        line_end_x = x
        
        painter.setPen(QPen(event_color, 2))
        painter.drawLine(line_start_x, box_y + box_height, line_end_x, center_y - 8)
        
        # Draw timestamp marker on timeline
        painter.setPen(QPen(event_color, 3))
        painter.setBrush(event_color)
        painter.drawEllipse(x - 4, center_y - 4, 8, 8)
        
        # Create the rounded rectangle path manually for better control
        from PySide6.QtGui import QPainterPath
        
        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(box_x, box_y, box_width, box_height, box_radius, box_radius)
        
        # Draw event box with proper rounded corners
        painter.setPen(QPen(event_color, 2))
        
        # Create gradient for box background
        if event_data.get("is_cluster", False):
            # Cluster box - darker background
            bg_color = QColor(60, 60, 60, 220)
        else:
            # Regular event - lighter background with event color tint
            bg_color = QColor(40, 40, 40, 240)
        
        painter.setBrush(bg_color)
        painter.drawPath(path)
        
        # Draw colored accent bar on left side (also rounded)
        accent_width = 4
        accent_path = QPainterPath()
        accent_path.addRoundedRect(box_x, box_y, accent_width, box_height, box_radius, box_radius)
        painter.setBrush(event_color)
        painter.drawPath(accent_path)
        
        # Draw time label at the top
        painter.setFont(time_font)
        painter.setPen(QPen(time_color, 1))
        time_x = box_x + box_padding
        time_y = box_y + box_padding + time_rect.height()
        painter.drawText(time_x, time_y, time_label)
        
        # Draw event label below time
        painter.setFont(font)
        painter.setPen(QPen(text_color, 1))
        text_x = box_x + box_padding
        text_y = time_y + box_padding + text_rect.height()
        painter.drawText(text_x, text_y, label)
    
    def draw_time_labels(self, painter, width, height, center_y):
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        
        # Calculate label positions
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        pixel_range = width / self.scale
        
        # Determine label interval (more conservative)
        if pixel_range > 7200:  # > 2 hours visible
            label_interval = 3600  # 1 hour labels
        elif pixel_range > 3600:  # > 1 hour visible
            label_interval = 1800  # 30 minute labels
        elif pixel_range > 1800:  # > 30 minutes visible
            label_interval = 600   # 10 minute labels
        elif pixel_range > 600:   # > 10 minutes visible
            label_interval = 300   # 5 minute labels
        elif pixel_range > 60:    # > 1 minute visible
            label_interval = 60    # 1 minute labels
        elif pixel_range > 10:    # > 10 seconds visible
            label_interval = 10    # 10 second labels
        else:
            label_interval = 1     # 1 second labels
        
        # Draw labels
        label_start = math.floor(start_time / label_interval) * label_interval
        time = label_start
        while time <= end_time:
            x = self.time_to_pixel(time, width)
            if 0 <= x <= width:
                label = self.format_time(time)
                text_rect = painter.fontMetrics().boundingRect(label)
                painter.drawText(x - text_rect.width() // 2, center_y + 35, label)
            time += label_interval
    
    def draw_info(self, painter):
        painter.setFont(QFont("Arial", 10))
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        
        info_lines = [
            f"Scale: 1 pixel = {1/self.scale:.3f} seconds",
            f"Visible range: {self.width()/self.scale:.1f} seconds",
            f"Offset: {self.format_time(self.offset)}",
            "Mouse: Drag to pan, Wheel to zoom"
        ]
        
        for i, line in enumerate(info_lines):
            painter.drawText(10, 20 + i * 15, line)
    
    def format_time(self, seconds):
        """Format time in hours:minutes:seconds.milliseconds (positive only)"""
        # Ensure we don't show negative times
        abs_seconds = abs(seconds)
        
        hours = int(abs_seconds // 3600)
        minutes = int((abs_seconds % 3600) // 60)
        secs = abs_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        elif minutes > 0:
            return f"{minutes:02d}:{secs:06.3f}"
        else:
            return f"{secs:.3f}s"
    
    def time_to_pixel(self, time, width):
        """Convert time to pixel position"""
        return width // 2 + (time - self.offset) * self.scale
    
    def pixel_to_time(self, pixel, width):
        """Convert pixel position to time"""
        return self.offset + (pixel - width // 2) / self.scale
    
    def wheelEvent(self, event: QWheelEvent):
        # Zoom functionality
        mouse_x = event.position().x()
        mouse_time = self.pixel_to_time(mouse_x, self.width())
        
        # Zoom factor
        zoom_factor = 1.2 if event.angleDelta().y() > 0 else 1.0 / 1.2
        new_scale = self.scale * zoom_factor
        
        # Clamp scale
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        
        if new_scale != self.scale:
            # Adjust offset to zoom around mouse position
            old_scale = self.scale
            self.scale = new_scale
            
            # Keep the time under the mouse cursor the same
            new_mouse_time = self.pixel_to_time(mouse_x, self.width())
            new_offset = self.offset + mouse_time - new_mouse_time
            
            # Restrict to positive time range after zoom
            leftmost_time = new_offset - self.width() / (2 * self.scale)
            if leftmost_time >= self.min_time:
                self.offset = new_offset
            else:
                # Adjust offset so leftmost visible time is exactly min_time
                self.offset = self.min_time + self.width() / (2 * self.scale)
        
        self.update()
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.position()
        event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and self.last_mouse_pos:
            # Pan functionality
            delta_x = event.position().x() - self.last_mouse_pos.x()
            delta_time = -delta_x / self.scale  # negative for natural scrolling
            new_offset = self.offset + delta_time
            
            # Restrict to positive time range
            # Calculate the leftmost time that should be visible
            leftmost_time = new_offset - self.width() / (2 * self.scale)
            if leftmost_time >= self.min_time:
                self.offset = new_offset
            else:
                # Adjust offset so leftmost visible time is exactly min_time
                self.offset = self.min_time + self.width() / (2 * self.scale)
            
            self.last_mouse_pos = event.position()
            self.update()
        event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.last_mouse_pos = None
        event.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zoomable Timeline - Seconds/Hours/Milliseconds")
        self.setGeometry(100, 100, 1000, 500)
        
        # Create timeline widget
        self.timeline = ZoomableTimeline()
        self.setCentralWidget(self.timeline)

def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()