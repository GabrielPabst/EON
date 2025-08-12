import math
import numpy as np
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath
from PySide6.QtCore import Qt

class GraphVisualizer:
    def __init__(self, timeline):
        self.timeline = timeline
        self.graph_height = None
        self.graph_top = None
        
    def draw_background_graph(self, painter, width, height, center_y):
        """Draw the background movement graph"""
        if len(self.timeline.graph_times) == 0:
            return
            
        self.graph_height = height * 0.4
        self.graph_top = height * 0.1
        start_time = self.timeline.offset - width / (2 * self.timeline.scale)
        end_time = self.timeline.offset + width / (2 * self.timeline.scale)
        
        self.draw_y_axis_scale(painter, width, height)
        
        padding = max((end_time - start_time) * 0.5, 1.0)
        mask = (self.timeline.graph_times >= start_time - padding) & (self.timeline.graph_times <= end_time + padding)
        visible_times = self.timeline.graph_times[mask]
        visible_values = self.timeline.graph_values[mask]
        
        if len(visible_times) == 0:
            return
            
        # Extend visible range by one point on each side if possible
        min_idx = np.where(self.timeline.graph_times == visible_times[0])[0][0]
        max_idx = np.where(self.timeline.graph_times == visible_times[-1])[0][0]
        
        if min_idx > 0:
            visible_times = np.insert(visible_times, 0, self.timeline.graph_times[min_idx - 1])
            visible_values = np.insert(visible_values, 0, self.timeline.graph_values[min_idx - 1])
        if max_idx < len(self.timeline.graph_times) - 1:
            visible_times = np.append(visible_times, self.timeline.graph_times[max_idx + 1])
            visible_values = np.append(visible_values, self.timeline.graph_values[max_idx + 1])
            
        # Smooth the data
        x_new, y_smooth = self._smooth_data(visible_times, visible_values)
        
        # Scale and draw the graph
        self._draw_graph(painter, x_new, y_smooth, visible_times, visible_values, width, height)

    def draw_y_axis_scale(self, painter, width, height):
        """Draw the y-axis scale and labels"""
        if not hasattr(self.timeline, 'graph_values') or len(self.timeline.graph_values) == 0:
            return
            
        painter.save()
        font = QFont("Arial", 8)
        painter.setFont(font)
        label_color = QColor(200, 200, 200, 180)
        line_color = QColor(100, 100, 100, 100)
        
        max_value = np.max(self.timeline.graph_values)
        scale_steps = 5
        step_size = self._round_to_nice_number(max_value / scale_steps) if max_value > 0 else 1
        max_scale = step_size * (math.ceil(max_value / step_size)) if max_value > 0 else step_size
        
        # Draw scale lines and labels
        for i in range(scale_steps + 1):
            value = i * step_size
            if value > max_scale:
                break
            y_ratio = value / max_scale if max_scale > 0 else 0
            y_pos = height - (self.graph_top + y_ratio * self.graph_height)
            
            # Draw horizontal grid line
            painter.setPen(QPen(line_color, 1, Qt.DashLine))
            painter.drawLine(30, y_pos, width - 10, y_pos)
            
            # Draw value label
            painter.setPen(label_color)
            label = str(int(value))
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(5, 
                           y_pos + text_rect.height() // 2 - 2, 
                           25, 
                           text_rect.height(),
                           Qt.AlignRight | Qt.AlignVCenter,
                           label)
        
        # Draw y-axis title
        painter.setPen(label_color)
        font.setPointSize(9)
        painter.setFont(font)
        text_rect = painter.fontMetrics().boundingRect("Movements per second")
        painter.drawText(30, 
                        height - (height * 0.1) + text_rect.height() + 5,
                        text_rect.width() + 10, 
                        text_rect.height(),
                        Qt.AlignLeft | Qt.AlignTop,
                        "Movements per second")
        painter.restore()

    def _round_to_nice_number(self, value):
        """Round a number to a 'nice' value for axis labels"""
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

    def _smooth_data(self, visible_times, visible_values):
        """Smooth the graph data using interpolation"""
        x_new, y_smooth = visible_times, visible_values
        try:
            from scipy.interpolate import make_interp_spline
            if len(visible_times) >= 2:
                zoom_factor = min(self.timeline.scale, 100)
                num_points = max(200, int(len(visible_times) * zoom_factor))
                if self.timeline.scale > 10:
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
        return x_new, y_smooth

    def _draw_graph(self, painter, x_new, y_smooth, visible_times, visible_values, width, height):
        """Draw the actual graph with area fill and data points"""
        if len(y_smooth) > 0 and np.max(y_smooth) > np.min(y_smooth):
            y_min, y_max = np.min(y_smooth), np.max(y_smooth)
            normalized_values = (y_smooth - y_min) / (y_max - y_min)
            scaled_values = self.graph_top + normalized_values * self.graph_height
        else:
            scaled_values = np.full_like(y_smooth, self.graph_top + self.graph_height * 0.5)
            
        # Create paths for area and line
        path = QPainterPath()
        stroke_path = QPainterPath()
        points = []
        
        for i, (time_val, y_val) in enumerate(zip(x_new, scaled_values)):
            x_pixel = self.timeline.time_to_pixel(time_val, width)
            y_pixel = height - y_val
            points.append((x_pixel, y_pixel))
            if i == 0:
                path.moveTo(x_pixel, y_pixel)
                stroke_path.moveTo(x_pixel, y_pixel)
            else:
                path.lineTo(x_pixel, y_pixel)
                stroke_path.lineTo(x_pixel, y_pixel)
                
        # Draw area fill and line
        if len(points) > 1:
            path.lineTo(points[-1][0], height - (height * 0.1))
            path.lineTo(points[0][0], height - (height * 0.1))
            path.closeSubpath()
            
            painter.save()
            fill_color = QColor(79, 195, 247, 60)
            stroke_color = QColor(79, 195, 247, 150)
            
            # Draw fill
            painter.setBrush(fill_color)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path)
            
            # Draw line
            painter.setPen(QPen(stroke_color, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(stroke_path)
            
            # Draw data points
            dot_color = QColor(255, 82, 82, 120)
            painter.setBrush(dot_color)
            painter.setPen(Qt.NoPen)
            
            for time_val, value in zip(visible_times, visible_values):
                x_pixel = self.timeline.time_to_pixel(time_val, width)
                if np.max(visible_values) > np.min(visible_values):
                    norm_val = (value - np.min(visible_values)) / (np.max(visible_values) - np.min(visible_values))
                else:
                    norm_val = 0.5
                y_pixel = height - (height * 0.1 + norm_val * height * 0.4)
                painter.drawEllipse(int(x_pixel - 3), int(y_pixel - 3), 6, 6)
                
            painter.restore()
