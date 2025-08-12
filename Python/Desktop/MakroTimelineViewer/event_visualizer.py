from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath
from PySide6.QtCore import Qt

class EventVisualizer:
    def __init__(self, timeline):
        self.timeline = timeline

    def draw_events(self, painter, width, height, center_y):
        """Draw all events on the timeline"""
        clustered_events = self.cluster_events(width)
        # store last clustered for hit-testing convenience
        self.timeline._last_clustered = clustered_events
        for event_data in clustered_events:
            x = self.timeline.time_to_pixel(event_data["time"], width)
            if -100 <= x <= width + 100:
                self.draw_single_event(painter, event_data, x, center_y)

    def cluster_events(self, width):
        """Group events that are close together on the timeline"""
        if not self.timeline.events:
            return []
            
        min_box_width = 80
        min_time_distance = min_box_width / self.timeline.scale
        sorted_events = sorted(self.timeline.events, key=lambda e: e["time"])
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
        """Draw a single event or cluster on the timeline"""
        event_color = event_data["color"]
        text_color = QColor(255, 255, 255)
        time_color = QColor(200, 200, 200)
        
        # Set fonts
        font = QFont("Arial", 9, QFont.Bold if not event_data.get("is_cluster", False) else QFont.Normal)
        painter.setFont(font)
        
        # Calculate dimensions
        label = event_data["label"]
        text_rect = painter.fontMetrics().boundingRect(label)
        
        time_font = QFont("Arial", 8)
        painter.setFont(time_font)
        time_label = self.timeline.format_time(event_data["time"])
        time_rect = painter.fontMetrics().boundingRect(time_label)
        
        # Box dimensions
        box_padding = 8
        box_width = max(text_rect.width(), time_rect.width()) + 2 * box_padding
        box_height = text_rect.height() + time_rect.height() + 3 * box_padding
        box_radius = 8
        box_y = center_y - 80
        box_x = x - box_width // 2
        box_x = max(5, min(self.timeline.width() - box_width - 5, box_x))
        
        # Draw connector line
        line_start_x = box_x + box_width // 2
        line_end_x = x
        painter.setPen(QPen(event_color, 2))
        painter.drawLine(line_start_x, box_y + box_height, line_end_x, center_y - 8)
        
        # Draw event marker
        painter.setPen(QPen(event_color, 3))
        painter.setBrush(event_color)
        painter.drawEllipse(x - 4, center_y - 4, 8, 8)
        
        # Draw event box
        path = QPainterPath()
        path.addRoundedRect(box_x, box_y, box_width, box_height, box_radius, box_radius)
        painter.setPen(QPen(event_color, 2))
        bg_color = QColor(60, 60, 60, 220) if event_data.get("is_cluster", False) else QColor(40, 40, 40, 240)
        painter.setBrush(bg_color)
        painter.drawPath(path)
        
        # Draw accent line
        accent_width = 4
        accent_path = QPainterPath()
        accent_path.addRoundedRect(box_x, box_y, accent_width, box_height, box_radius, box_radius)
        painter.setBrush(event_color)
        painter.drawPath(accent_path)
        
        # Draw time and label text
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
        
        # Save draw metadata for hit-testing
        event_data['_draw_info'] = {
            'box_x': box_x, 'box_y': box_y, 'box_w': box_width, 'box_h': box_height,
            'marker_x': x, 'marker_y': center_y
        }
