
import sys
import math
import json
from collections import defaultdict
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QDialog, QLabel, QGridLayout, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QWheelEvent, QMouseEvent, QPainterPath, QPixmap
import os

class ZoomableTimeline(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 400)

        # Timeline state
        self.min_scale = 0.02
        self.max_scale = 10000.0
        self.min_time = -10.0

        # Mouse interaction
        self.dragging = False
        self.last_mouse_pos = None
        self.mouse_press_pos = None

        # Animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate)
        self.animation_timer.start(16)
        self.animation_time = 0

        # Load events and graph data
        self.events = self.load_events_from_log("actions.log")

        if self.events:
            event_times = [event["time"] for event in self.events]
            min_time = min(event_times)
            max_time = max(event_times)
            time_range = max_time - min_time if max_time != min_time else 1.0
            padding = time_range * 0.1
            visible_range = time_range + (2 * padding)
            self.scale = (self.width() * 0.8) / visible_range
            self.scale = max(self.min_scale, min(self.max_scale, self.scale))
            self.offset = (max_time + min_time) / 2
        else:
            self.scale = 1.0
            self.offset = 0.0

        self.graph_times, self.graph_values = self.load_movements_per_second("mouse_moves.log")

        self.setMouseTracking(True)
    
    def load_movements_per_second(self, log_file):
        try:
            timestamps = []
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("type") == "move":
                            timestamps.append(event["time"])
                    except json.JSONDecodeError:
                        continue
            if not timestamps:
                return self.get_sample_data()
            start_time = min(timestamps)
            counts = defaultdict(int)
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("type") == "move":
                            relative_time = event["time"] - start_time
                            sec = int(relative_time)
                            counts[sec] += 1
                    except json.JSONDecodeError:
                        continue
            if counts:
                times = sorted(counts.keys())
                values = [counts[t] for t in times]
                return np.array(times), np.array(values)
            else:
                return self.get_sample_data()
        except FileNotFoundError:
            return self.get_sample_data()
    
    def get_sample_data(self):
        times = np.array([0, 30, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600])
        values = np.array([5, 15, 25, 35, 20, 40, 30, 45, 25, 35, 15, 10])
        return times, values
    
    def load_events_from_log(self, log_file):
        """Load events from actions.log file and keep raw event data for popup"""
        try:
            events = []
            first_time = None
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if first_time is None:
                            first_time = event["time"]
                        relative_time = event["time"] - first_time
                        label = f"{event.get('type', '')} {event.get('key', '')}".strip()
                        if event.get('x') is not None and event.get('y') is not None:
                            label += f" at ({event['x']}, {event['y']})"
                        if event.get('type') == 'press':
                            color = QColor(255, 100, 100)
                        elif event.get('type') == 'release':
                            color = QColor(100, 255, 100)
                        else:
                            color = QColor(100, 100, 255)
                        # Keep the raw event dictionary so we can show all fields later
                        events.append({
                            "time": relative_time,
                            "label": label,
                            "color": color,
                            "raw": event  # <-- raw stored here
                        })
                    except json.JSONDecodeError:
                        continue
            if not events:
                return []
            return events
        except FileNotFoundError:
            return []

    def animate(self):
        self.animation_time += 0.016
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(20, 20, 20))
        width = self.width()
        height = self.height()
        center_y = height // 2
        self.draw_background_graph(painter, width, height, center_y)
        self.draw_timeline(painter, width, height, center_y)
        self.draw_events(painter, width, height, center_y)
        self.draw_time_labels(painter, width, height, center_y)
        self.draw_info(painter)
    
    def draw_y_axis_scale(self, painter, width, height):
        if not hasattr(self, 'graph_values') or len(self.graph_values) == 0:
            return
        painter.save()
        font = QFont("Arial", 8)
        painter.setFont(font)
        label_color = QColor(200, 200, 200, 180)
        line_color = QColor(100, 100, 100, 100)
        max_value = np.max(self.graph_values)
        scale_steps = 5
        step_size = self.round_to_nice_number(max_value / scale_steps) if max_value > 0 else 1
        max_scale = step_size * (math.ceil(max_value / step_size)) if max_value>0 else step_size
        for i in range(scale_steps + 1):
            value = i * step_size
            if value > max_scale:
                break
            y_ratio = value / max_scale if max_scale>0 else 0
            y_pos = height - (self.graph_top + y_ratio * self.graph_height)
            painter.setPen(QPen(line_color, 1, Qt.DashLine))
            painter.drawLine(30, y_pos, width - 10, y_pos)
            painter.setPen(label_color)
            label = str(int(value))
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(5, 
                           y_pos + text_rect.height() // 2 - 2, 
                           25, 
                           text_rect.height(),
                           Qt.AlignRight | Qt.AlignVCenter,
                           label)
        painter.setPen(label_color)
        font.setPointSize(9)
        painter.setFont(font)
        text_rect = painter.fontMetrics().boundingRect("Movements per second")
        painter.drawText(30, 
                        height - (height * 0.1) + text_rect.height() + 5,
                        text_rect.width() +10, 
                        text_rect.height(),
                        Qt.AlignLeft | Qt.AlignTop,
                        "Movements per second")
        painter.restore()
        
    def round_to_nice_number(self, value):
        if value <= 0:
            return 1
        magnitude = 10 ** math.floor(math.log10(value))
        normalized = value / magnitude
        if normalized < 1.5:
            nice_number = 1
        elif normalized < 3:
            nice_number = 2
        elif normalized < 7:
            nice_number = 5
        else:
            nice_number = 10
        return nice_number * magnitude
        
    def draw_background_graph(self, painter, width, height, center_y):
        if len(self.graph_times) == 0:
            return
        self.graph_height = height * 0.4
        self.graph_top = height * 0.1
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        self.draw_y_axis_scale(painter, width, height)
        padding = max((end_time - start_time) * 0.5, 1.0)
        mask = (self.graph_times >= start_time - padding) & (self.graph_times <= end_time + padding)
        visible_times = self.graph_times[mask]
        visible_values = self.graph_values[mask]
        if len(visible_times) == 0:
            return
        min_idx = np.where(self.graph_times == visible_times[0])[0][0]
        max_idx = np.where(self.graph_times == visible_times[-1])[0][0]
        if min_idx > 0:
            visible_times = np.insert(visible_times, 0, self.graph_times[min_idx - 1])
            visible_values = np.insert(visible_values, 0, self.graph_values[min_idx - 1])
        if max_idx < len(self.graph_times) - 1:
            visible_times = np.append(visible_times, self.graph_times[max_idx + 1])
            visible_values = np.append(visible_values, self.graph_values[max_idx + 1])
        x_new, y_smooth = visible_times, visible_values
        try:
            from scipy.interpolate import make_interp_spline
            if len(visible_times) >= 2:
                zoom_factor = min(self.scale, 100)
                num_points = max(200, int(len(visible_times) * zoom_factor))
                if self.scale > 10:
                    x_new = np.linspace(visible_times.min(), visible_times.max(), num_points)
                    y_smooth = np.interp(x_new, visible_times, visible_values)
                else:
                    x_new = np.linspace(visible_times.min(), visible_times.max(), num_points)
                    k = min(3, len(visible_times)-1) if len(visible_times) > 3 else 1
                    spline = make_interp_spline(visible_times, visible_values, k=k)
                    y_smooth = spline(x_new)
        except ImportError:
            if len(visible_times) >= 2:
                x_new = np.linspace(visible_times.min(), visible_times.max(), 200)
                y_smooth = np.interp(x_new, visible_times, visible_values)
        if len(y_smooth) > 0 and np.max(y_smooth) > np.min(y_smooth):
            graph_height = height * 0.4
            graph_top = height * 0.1
            y_min, y_max = np.min(y_smooth), np.max(y_smooth)
            normalized_values = (y_smooth - y_min) / (y_max - y_min)
            scaled_values = graph_top + normalized_values * graph_height
        else:
            graph_height = height * 0.4
            graph_top = height * 0.1
            scaled_values = np.full_like(y_smooth, graph_top + graph_height * 0.5)
        path = QPainterPath()
        stroke_path = QPainterPath()
        points = []
        for i, (time_val, y_val) in enumerate(zip(x_new, scaled_values)):
            x_pixel = self.time_to_pixel(time_val, width)
            y_pixel = height - y_val
            points.append((x_pixel, y_pixel))
            if i == 0:
                path.moveTo(x_pixel, y_pixel)
                stroke_path.moveTo(x_pixel, y_pixel)
            else:
                path.lineTo(x_pixel, y_pixel)
                stroke_path.lineTo(x_pixel, y_pixel)
        if len(points) > 1:
            path.lineTo(points[-1][0], height - (height * 0.1))
            path.lineTo(points[0][0], height - (height * 0.1))
            path.closeSubpath()
            painter.save()
            fill_color = QColor(79, 195, 247, 60)
            stroke_color = QColor(79, 195, 247, 150)
            painter.setBrush(fill_color)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path)
            painter.setPen(QPen(stroke_color, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(stroke_path)
            dot_color = QColor(255, 82, 82, 120)
            painter.setBrush(dot_color)
            painter.setPen(Qt.NoPen)
            for time_val, value in zip(visible_times, visible_values):
                x_pixel = self.time_to_pixel(time_val, width)
                if np.max(visible_values) > np.min(visible_values):
                    norm_val = (value - np.min(visible_values)) / (np.max(visible_values) - np.min(visible_values))
                else:
                    norm_val = 0.5
                y_pixel = height - (height * 0.1 + norm_val * height * 0.4)
                painter.drawEllipse(int(x_pixel - 3), int(y_pixel - 3), 6, 6)
            painter.restore()
    
    def draw_timeline(self, painter, width, height, center_y):
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.drawLine(0, center_y, width, center_y)
        pixel_range = width / self.scale
        if pixel_range > 7200:
            major_interval = 3600; minor_interval = 1800
        elif pixel_range > 3600:
            major_interval = 1800; minor_interval = 600
        elif pixel_range > 1800:
            major_interval = 600; minor_interval = 300
        elif pixel_range > 600:
            major_interval = 300; minor_interval = 60
        elif pixel_range > 60:
            major_interval = 60; minor_interval = 10
        elif pixel_range > 10:
            major_interval = 10; minor_interval = 1
        else:
            major_interval = 1; minor_interval = 0.1
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        if minor_interval > 0:
            minor_start = math.floor(start_time / minor_interval) * minor_interval
            time = minor_start
            while time <= end_time:
                x = self.time_to_pixel(time, width)
                if 0 <= x <= width:
                    painter.drawLine(x, center_y - 5, x, center_y + 5)
                time += minor_interval
        painter.setPen(QPen(QColor(120, 120, 120), 2))
        major_start = math.floor(start_time / major_interval) * major_interval
        time = major_start
        while time <= end_time:
            x = self.time_to_pixel(time, width)
            if 0 <= x <= width:
                painter.drawLine(x, center_y - 15, x, center_y + 15)
            time += major_interval
    
    def draw_events(self, painter, width, height, center_y):
        clustered_events = self.cluster_events(width)
        # store last clustered for hit-testing convenience
        self._last_clustered = clustered_events
        for event_data in clustered_events:
            x = self.time_to_pixel(event_data["time"], width)
            if -100 <= x <= width + 100:
                self.draw_single_event(painter, event_data, x, center_y)
    
    def cluster_events(self, width):
        if not self.events:
            return []
        min_box_width = 80
        min_time_distance = min_box_width / self.scale
        sorted_events = sorted(self.events, key=lambda e: e["time"])
        clustered = []
        i = 0
        while i < len(sorted_events):
            current_event = sorted_events[i]
            cluster_events = [current_event]
            cluster_start_time = current_event["time"]
            j = i + 1
            while j < len(sorted_events):
                next_event = sorted_events[j]
                if next_event["time"] - cluster_start_time < min_time_distance:
                    cluster_events.append(next_event)
                    j += 1
                else:
                    break
            if len(cluster_events) > 1:
                avg_time = sum(e["time"] for e in cluster_events) / len(cluster_events)
                clustered.append({
                    "time": avg_time,
                    "label": f"Clustered Events ({len(cluster_events)})",
                    "color": QColor(150, 150, 150),
                    "is_cluster": True,
                    "cluster_events": cluster_events
                })
            else:
                event = cluster_events[0].copy()
                event["is_cluster"] = False
                clustered.append(event)
            i = j
        return clustered
    
    def draw_single_event(self, painter, event_data, x, center_y):
        event_color = event_data["color"]
        text_color = QColor(255, 255, 255)
        time_color = QColor(200, 200, 200)
        font = QFont("Arial", 9, QFont.Bold if not event_data.get("is_cluster", False) else QFont.Normal)
        painter.setFont(font)
        label = event_data["label"]
        text_rect = painter.fontMetrics().boundingRect(label)
        time_font = QFont("Arial", 8)
        painter.setFont(time_font)
        time_label = self.format_time(event_data["time"])
        time_rect = painter.fontMetrics().boundingRect(time_label)
        box_padding = 8
        box_width = max(text_rect.width(), time_rect.width()) + 2 * box_padding
        box_height = text_rect.height() + time_rect.height() + 3 * box_padding
        box_radius = 8
        box_y = center_y - 80
        box_x = x - box_width // 2
        box_x = max(5, min(self.width() - box_width - 5, box_x))
        line_start_x = box_x + box_width // 2
        line_end_x = x
        painter.setPen(QPen(event_color, 2))
        painter.drawLine(line_start_x, box_y + box_height, line_end_x, center_y - 8)
        painter.setPen(QPen(event_color, 3))
        painter.setBrush(event_color)
        painter.drawEllipse(x - 4, center_y - 4, 8, 8)
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(box_x, box_y, box_width, box_height, box_radius, box_radius)
        painter.setPen(QPen(event_color, 2))
        if event_data.get("is_cluster", False):
            bg_color = QColor(60, 60, 60, 220)
        else:
            bg_color = QColor(40, 40, 40, 240)
        painter.setBrush(bg_color)
        painter.drawPath(path)
        accent_width = 4
        accent_path = QPainterPath()
        accent_path.addRoundedRect(box_x, box_y, accent_width, box_height, box_radius, box_radius)
        painter.setBrush(event_color)
        painter.drawPath(accent_path)
        painter.setFont(time_font)
        painter.setPen(QPen(time_color, 1))
        time_x = box_x + box_padding
        time_y = box_y + box_padding + time_rect.height()
        painter.drawText(time_x, time_y, time_label)
        painter.setFont(font)
        painter.setPen(QPen(text_color, 1))
        text_x = box_x + box_padding
        text_y = time_y + box_padding + text_rect.height()
        painter.drawText(text_x, text_y, label)
        # Save draw metadata for hit-testing (used by click detection)
        event_data['_draw_info'] = {
            'box_x': box_x, 'box_y': box_y, 'box_w': box_width, 'box_h': box_height,
            'marker_x': x, 'marker_y': center_y
        }
    
    def draw_time_labels(self, painter, width, height, center_y):
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        start_time = self.offset - width / (2 * self.scale)
        end_time = self.offset + width / (2 * self.scale)
        pixel_range = width / self.scale
        if pixel_range > 7200:
            label_interval = 3600
        elif pixel_range > 3600:
            label_interval = 1800
        elif pixel_range > 1800:
            label_interval = 600
        elif pixel_range > 600:
            label_interval = 300
        elif pixel_range > 60:
            label_interval = 60
        elif pixel_range > 10:
            label_interval = 10
        else:
            label_interval = 1
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
            "Mouse: Drag to pan, Wheel to zoom, Click events for details"
        ]
        for i, line in enumerate(info_lines):
            painter.drawText(10, 20 + i * 15, line)
    
    def format_time(self, seconds):
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
        return width // 2 + (time - self.offset) * self.scale
    
    def pixel_to_time(self, pixel, width):
        return self.offset + (pixel - width // 2) / self.scale
    
    def wheelEvent(self, event: QWheelEvent):
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
        if event.button() == Qt.LeftButton:
            self.mouse_press_pos = event.position()
            self.dragging = True
            self.last_mouse_pos = event.position()
        event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
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
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        # If small movement since press -> treat as click
        if event.button() == Qt.LeftButton:
            if self.mouse_press_pos is not None:
                dx = abs(event.position().x() - self.mouse_press_pos.x())
                dy = abs(event.position().y() - self.mouse_press_pos.y())
                moved = (dx > 6) or (dy > 6)
            else:
                moved = False
            self.dragging = False
            self.last_mouse_pos = None
            press = self.mouse_press_pos
            self.mouse_press_pos = None
            if not moved:
                # Handle click
                self.handle_click(event.position())
        event.accept()
    
    def handle_click(self, pos):
        """Check if click hits an event marker or its box and open popup"""
        x = pos.x()
        y = pos.y()
        width = self.width()
        height = self.height()
        # Ensure we have last draw metadata; if not, recompute clustered
        clustered = getattr(self, "_last_clustered", None)
        if clustered is None:
            clustered = self.cluster_events(width)
        # Hit test: first check boxes, then marker proximity
        for ev in clustered:
            di = ev.get('_draw_info')
            if not di:
                # we might not have draw info (e.g., first click before paint) -- compute approx
                ex = self.time_to_pixel(ev["time"], width)
                box_w = 100
                box_h = 40
                box_x = ex - box_w//2
                box_y = (height//2) - 80
            else:
                box_x = di['box_x']; box_y = di['box_y']; box_w = di['box_w']; box_h = di['box_h']
            # If click inside box
            if (box_x <= x <= box_x + box_w) and (box_y <= y <= box_y + box_h):
                self.open_event_dialog(ev)
                return
        # If not inside any box, check markers (distance)
        for ev in clustered:
            di = ev.get('_draw_info')
            marker_x = di['marker_x'] if di else self.time_to_pixel(ev['time'], width)
            marker_y = di['marker_y'] if di else height//2
            dist_sq = (marker_x - x)**2 + (marker_y - y)**2
            if dist_sq <= (10 ** 2):
                self.open_event_dialog(ev)
                return
        # nothing hit
        return
    
    def open_event_dialog(self, event_data):
        """Open a dialog showing details. If cluster -> list each event."""
        dlg = QDialog(self, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        title = event_data.get('label', 'Event')
        if event_data.get('is_cluster', False):
            dlg.setWindowTitle(f"{title} - details")
        else:
            raw = event_data.get('raw', {})
            tlabel = self.format_time(event_data.get('time', 0))
            dlg.setWindowTitle(f"{title} — {tlabel}")
        dlg_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout()
        content.setLayout(grid)
        scroll.setWidget(content)
        def make_card_widget(header_text, time_text, raw, screenshot_path=None):
            card = QWidget()
            card_layout = QVBoxLayout(card)
            card.setStyleSheet("""
                background: #23272e;
                border-radius: 12px;
                border: 1px solid #444;
                margin: 8px;
                padding: 12px;
            """)
            header = QLabel(header_text)
            header.setStyleSheet("font-size: 15px; font-weight: bold; color: #fff; margin-bottom: 4px;")
            header.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card_layout.addWidget(header)
            time_label = QLabel(time_text)
            time_label.setStyleSheet("color: #aaa; font-size: 13px; margin-bottom: 8px;")
            time_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card_layout.addWidget(time_label)
            # Show key info in a grid
            info_grid = QGridLayout()
            row = 0
            for k in ["type", "key", "x", "y"]:
                if k in raw:
                    key_lbl = QLabel(f"<b>{k.capitalize()}</b>")
                    key_lbl.setStyleSheet("color: #7ec6ff;")
                    val_lbl = QLabel(str(raw[k]))
                    val_lbl.setStyleSheet("color: #fff;")
                    info_grid.addWidget(key_lbl, row, 0)
                    info_grid.addWidget(val_lbl, row, 1)
                    row += 1
            card_layout.addLayout(info_grid)
            # Show all details as pretty JSON
            details = QLabel(f"<pre style='color:#ccc'>{json.dumps(raw, indent=2)}</pre>")
            details.setTextInteractionFlags(Qt.TextSelectableByMouse)
            details.setStyleSheet("background: #181a20; border-radius: 6px; padding: 6px; font-size: 12px;")
            card_layout.addWidget(details)
            # Screenshot
            if screenshot_path:
                if os.path.exists(screenshot_path):
                    pix = QPixmap(screenshot_path)
                    if not pix.isNull():
                        img_label = QLabel()
                        img_label.setPixmap(pix.scaledToWidth(400, Qt.SmoothTransformation))
                        img_label.setStyleSheet("border: 2px solid #7ec6ff; border-radius: 8px; margin-top: 8px;")
                        card_layout.addWidget(img_label)
                else:
                    missing = QLabel(f"Screenshot listed but not found: {screenshot_path}")
                    missing.setStyleSheet("color: #ff7e7e; margin-top: 8px;")
                    missing.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    card_layout.addWidget(missing)
            return card
        if event_data.get('is_cluster', False):
            cluster = event_data.get('cluster_events', [])
            for idx, ev in enumerate(cluster):
                raw = ev.get('raw', {})
                label = ev.get('label', '')
                time_label = self.format_time(ev.get('time', 0))
                screenshot_path = raw.get('screenshot')
                card = make_card_widget(f"{label}", time_label, raw, screenshot_path)
                grid.addWidget(card, idx, 0)
        else:
            raw = event_data.get('raw', {})
            label = event_data.get('label','')
            time_label = self.format_time(event_data.get('time', 0))
            screenshot_path = raw.get('screenshot')
            card = make_card_widget(label, time_label, raw, screenshot_path)
            grid.addWidget(card, 0, 0)
        dlg_layout.addWidget(scroll)
        dlg.setLayout(dlg_layout)
        dlg.resize(700, 500)
        dlg.exec()
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zoomable Timeline with Background Graph")
        self.setGeometry(100, 100, 1000, 500)
        self.timeline = ZoomableTimeline()
        self.setCentralWidget(self.timeline)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

