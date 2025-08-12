import sys 
import os 

from MakroTimelineViewer.timeline_window import TimelineWindow
import sys
from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    window = TimelineWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
