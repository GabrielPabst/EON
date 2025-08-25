import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../Python/Desktop/MakroTimelineViewer')))
from action_log_frontend import ActionLogFrontend
# -----------------------------
# Entry Point
# -----------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Actions Log Viewer")
    #app.setStyle("Fusion")
    win = ActionLogFrontend()
    win.show()

    try:
        win.manager.load_from_file("actions.log", "mouse_moves.log")
        win.table_model.refresh()
        win._refresh_timeline()
        if win.manager.events:
            win._select_real_index(0)
        win.status.showMessage(f"Loaded actions.log and mouse_moves.log ({len(win.manager.events)} events)")
    except Exception:
        pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()