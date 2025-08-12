import json
from collections import defaultdict
import sys
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget


def load_movements_per_second(log_file):
    counts = defaultdict(int)
    with open(log_file, "r") as f:
        for line in f:
            try:
                event = json.loads(line)
                if event.get("type") == "move":
                    sec = int(event["time"])
                    counts[sec] += 1
            except json.JSONDecodeError:
                continue
    times = sorted(counts.keys())
    values = [counts[t] for t in times]
    return np.array(times), np.array(values)


class MovementPlot(QWidget):
    def __init__(self, times, values):
        super().__init__()
        layout = QVBoxLayout(self)
        fig, ax = plt.subplots(figsize=(10, 4), dpi=100)

        # Modern dark background
        fig.patch.set_facecolor("#2b2b2b")
        ax.set_facecolor("#2b2b2b")

        # Smooth interpolation
        if len(times) > 1:
            from scipy.interpolate import make_interp_spline
            x_new = np.linspace(times.min(), times.max(), 500)
            spline = make_interp_spline(times, values, k=3)
            y_smooth = spline(x_new)
        else:
            x_new, y_smooth = times, values

        # Plot
        ax.plot(x_new, y_smooth, color="#4FC3F7", linewidth=2)
        ax.fill_between(x_new, y_smooth, color="#4FC3F7", alpha=0.2)
        ax.scatter(times, values, color="#FF5252", s=20, zorder=5)

        # Style
        ax.grid(True, linestyle="--", alpha=0.3, color="white")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Movements")
        ax.set_title("Mouse Movements per Second")

        # Clamp so it never scrolls before 0
        def on_xlim_changed(event_ax):
            xmin, xmax = event_ax.get_xlim()
            if xmin < 0:
                shift = -xmin
                event_ax.set_xlim(xmin + shift, xmax + shift)
                fig.canvas.draw_idle()

        ax.callbacks.connect("xlim_changed", on_xlim_changed)

        # Add matplotlib canvas and toolbar
        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)

        layout.addWidget(toolbar)
        layout.addWidget(canvas)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mouse Movement Graph (Interactive)")
        times, values = load_movements_per_second("mouse_moves.log")
        self.setCentralWidget(MovementPlot(times, values))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
