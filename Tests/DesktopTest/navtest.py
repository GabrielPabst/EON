import sys
import math
from PySide6.QtCore import Qt, QPointF, QRectF, QPropertyAnimation, QEasingCurve, QObject, Property
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem


class AnimatedCircle(QObject):
    """Wrapper to animate position of a QGraphicsEllipseItem."""
    def __init__(self, item):
        super().__init__()
        self.item = item

    def get_pos(self):
        return self.item.pos()

    def set_pos(self, pos):
        self.item.setPos(pos)

    pos = Property(QPointF, get_pos, set_pos)


class CircularMenu(QGraphicsView):
    def __init__(self):
        super().__init__()

        self.setRenderHint(QPainter.Antialiasing)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.central_radius = 50
        self.small_radius = 20
        self.num_small_circles = 6
        self.circle_distance = 90

        # Central big circle
        self.central_circle = QGraphicsEllipseItem(
            QRectF(-self.central_radius, -self.central_radius,
                   self.central_radius * 2, self.central_radius * 2)
        )
        self.central_circle.setBrush(QBrush(QColor("#4CAF50")))
        self.central_circle.setZValue(1)
        self.scene.addItem(self.central_circle)
        self.central_circle.setPos(0, 0)

        self.scene.setSceneRect(-200, -200, 400, 400)

        # Small circles
        self.small_circles = []
        self.animations = []
        for _ in range(self.num_small_circles):
            circle = QGraphicsEllipseItem(
                QRectF(-self.small_radius, -self.small_radius,
                       self.small_radius * 2, self.small_radius * 2)
            )
            circle.setBrush(QBrush(QColor("#2196F3")))
            circle.setZValue(0)
            circle.setPos(0, 0)
            self.scene.addItem(circle)
            self.small_circles.append(circle)

        self.menu_open = False

    def mousePressEvent(self, event):
        """Detect if click was inside the central circle."""
        scene_pos = self.mapToScene(event.pos())
        if self.central_circle.contains(self.central_circle.mapFromScene(scene_pos)):
            self.toggle_menu()
        super().mousePressEvent(event)

    def toggle_menu(self):
        self.menu_open = not self.menu_open
        print("Toggling menu:", self.menu_open)
        self.animations.clear()

        for i, circle in enumerate(self.small_circles):
            angle = (2 * math.pi / self.num_small_circles) * i
            target_x = math.cos(angle) * self.circle_distance
            target_y = math.sin(angle) * self.circle_distance
            target_pos = QPointF(target_x, target_y) if self.menu_open else QPointF(0, 0)

            anim_obj = AnimatedCircle(circle)
            anim = QPropertyAnimation(anim_obj, b"pos")
            anim.setDuration(400)
            anim.setEasingCurve(QEasingCurve.OutBack if self.menu_open else QEasingCurve.InBack)
            anim.setStartValue(circle.pos())
            anim.setEndValue(target_pos)
            anim.start()
            self.animations.append(anim)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    view = CircularMenu()
    view.setWindowTitle("Circular Navigation")
    view.resize(500, 500)
    view.show()
    sys.exit(app.exec())
