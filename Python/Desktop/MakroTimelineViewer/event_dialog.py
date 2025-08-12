from PySide6.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QWidget, QGridLayout, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import json
import os

class EventDialog(QDialog):
    def __init__(self, event_data, timeline, parent=None):
        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.timeline = timeline
        self.event_data = event_data
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI"""
        title = self.event_data.get('label', 'Event')
        if self.event_data.get('is_cluster', False):
            self.setWindowTitle(f"{title} - details")
        else:
            raw = self.event_data.get('raw', {})
            tlabel = self.timeline.format_time(self.event_data.get('time', 0))
            self.setWindowTitle(f"{title} — {tlabel}")
            
        dlg_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout()
        content.setLayout(grid)
        scroll.setWidget(content)
        
        if self.event_data.get('is_cluster', False):
            cluster = self.event_data.get('cluster_events', [])
            for idx, ev in enumerate(cluster):
                raw = ev.get('raw', {})
                label = ev.get('label', '')
                time_label = self.timeline.format_time(ev.get('time', 0))
                screenshot_path = raw.get('screenshot')
                card = self.make_card_widget(label, time_label, raw, screenshot_path)
                grid.addWidget(card, idx, 0)
        else:
            raw = self.event_data.get('raw', {})
            label = self.event_data.get('label','')
            time_label = self.timeline.format_time(self.event_data.get('time', 0))
            screenshot_path = raw.get('screenshot')
            card = self.make_card_widget(label, time_label, raw, screenshot_path)
            grid.addWidget(card, 0, 0)
            
        dlg_layout.addWidget(scroll)
        self.setLayout(dlg_layout)
        self.resize(700, 500)
        
    def make_card_widget(self, header_text, time_text, raw, screenshot_path=None):
        """Create a card widget for displaying event information"""
        card = QWidget()
        card_layout = QVBoxLayout(card)
        card.setStyleSheet("""
            background: #23272e;
            border-radius: 12px;
            border: 1px solid #444;
            margin: 8px;
            padding: 12px;
        """)
        
        # Header
        header = QLabel(header_text)
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #fff; margin-bottom: 4px;")
        header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(header)
        
        # Time label
        time_label = QLabel(time_text)
        time_label.setStyleSheet("color: #aaa; font-size: 13px; margin-bottom: 8px;")
        time_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(time_label)
        
        # Key information grid
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
        
        # JSON details
        details = QLabel(f"<pre style='color:#ccc'>{json.dumps(raw, indent=2)}</pre>")
        details.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details.setStyleSheet("background: #181a20; border-radius: 6px; padding: 6px; font-size: 12px;")
        card_layout.addWidget(details)
        
        # Screenshot (if available)
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
