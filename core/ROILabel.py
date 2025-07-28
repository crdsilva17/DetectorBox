from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QMouseEvent

# Subclasse QLabel para capturar eventos de mouse corretamente
class ROILabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_screen = None
    def mousePressEvent(self, ev):
        if self.parent_screen and isinstance(ev, QMouseEvent) and ev.button() == 1:
            self.parent_screen.start_roi(ev)
    def mouseMoveEvent(self, ev):
        if self.parent_screen and isinstance(ev, QMouseEvent) and ev.buttons() & 1:
            self.parent_screen.update_roi(ev)
    def mouseReleaseEvent(self, ev):
        if self.parent_screen and isinstance(ev, QMouseEvent) and ev.button() == 1:
            self.parent_screen.end_roi(ev)