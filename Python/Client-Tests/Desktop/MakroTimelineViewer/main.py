import sys 
import os 

# Add the Desktop directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../Python/Desktop/MakroTimelineViewer')))
from timeline_window import TimelineWindow
import sys
from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    window = TimelineWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

