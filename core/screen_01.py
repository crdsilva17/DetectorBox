import cv2

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QComboBox, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


# Subclasse QLabel para capturar eventos de mouse corretamente
class ROILabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_screen = None
    def mousePressEvent(self, ev):
        if self.parent_screen:
            self.parent_screen.start_roi(ev)
    def mouseMoveEvent(self, ev):
        if self.parent_screen:
            self.parent_screen.update_roi(ev)
    def mouseReleaseEvent(self, ev):
        if self.parent_screen:
            self.parent_screen.end_roi(ev)

class Screen01(QWidget):
    def __init__(self, cameras, detector):
        super().__init__()
        self.cameras = cameras  # Dict: {name: Camera}
        self.selected_camera = None
        self.selected_detector = detector
        self.vlayout = QVBoxLayout()
        self.roi_start = (50, 50)
        self.roi_end = (300, 300)
        self.roi_rect = (50, 50, 250, 250)
        self.last_frame = None
        self.editing_roi = False
        self.drag_offset = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('DetectorBox - Seleção de Câmera e Detector')
        self.setFixedSize(1024, 768)
        self.vlayout = QVBoxLayout()

        # Dropdown para seleção de câmera
        self.combo_camera = QComboBox()
        self.combo_camera.addItems(list(self.cameras.keys()))
        self.combo_camera.currentIndexChanged.connect(self.on_camera_change)
        self.vlayout.addWidget(self.combo_camera)


        # Botão para criar nova caixa/recipe
        self.btn_new_box = QPushButton('Nova Caixa/Recipe')
        self.vlayout.addWidget(self.btn_new_box)

        # Lista de seleção de recipes existentes
        import os
        self.recipe_dir = os.path.join(os.path.dirname(__file__), '..', 'recipes')
        os.makedirs(self.recipe_dir, exist_ok=True)
        self.combo_recipe = QComboBox()
        self.update_recipe_list()
        self.vlayout.addWidget(self.combo_recipe)

        # Botão de captura
        self.capture_btn = QPushButton('Capturar Imagem')
        self.capture_btn.clicked.connect(self.capture_image)
        self.vlayout.addWidget(self.capture_btn)

        # Labels para imagens
        self.label_original = ROILabel('Imagem Original')
        self.label_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_original.setMouseTracking(True)
        self.vlayout.addWidget(self.label_original)

        self.label_processed = QLabel('Imagem Pós-Processamento')
        self.label_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vlayout.addWidget(self.label_processed)
        self.setLayout(self.vlayout)
    def toggle_edit_roi(self, checked):
        from PyQt5.QtGui import QCursor
        self.editing_roi = checked
        if checked:
            self.label_original.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.label_original.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        # Não recria widgets/layout nem redefine ROI aqui. Apenas alterna modo de edição.
    def update_recipe_list(self):
        self.combo_recipe.clear()
        import os
        recipes = [f for f in os.listdir(self.recipe_dir) if f.endswith('.json')]
        self.combo_recipe.addItems(recipes)
        if recipes:
            self.selected_recipe = recipes[0]
        else:
            self.selected_recipe = None

    def on_recipe_change(self, index):
        self.selected_recipe = self.combo_recipe.currentText()

    def create_new_box(self):
        from PyQt5.QtWidgets import QInputDialog
        import os
        name, ok = QInputDialog.getText(self, 'Nova Caixa/Recipe', 'Nome do arquivo da caixa:')
        if ok and name:
            path = os.path.join(self.recipe_dir, f'{name}.json')
            import json
            box_data = {"layout": [4, 3], "info": "Exemplo"}
            with open(path, 'w') as f:
                json.dump(box_data, f, indent=2)
            self.update_recipe_list()
    # --- Seleção de ROI ---
    def start_roi(self, event):
        if not self.editing_roi or self.last_frame is None:
            return
        x, y = event.pos().x(), event.pos().y()
        if self.roi_rect is None:
            # Inicializa ROI padrão se necessário
            self.roi_rect = (x, y, 100, 100)
        rx, ry, rw, rh = self.roi_rect
        # Verifica se clicou dentro do ROI para mover
        if rx <= x <= rx+rw and ry <= y <= ry+rh:
            self.drag_offset = (x - rx, y - ry)
        else:
            self.drag_offset = None
        self.roi_start = (x, y)
        self.roi_end = None
        self.update_roi_overlay()

    def update_roi(self, event):
        if not self.editing_roi or self.roi_start is None or self.last_frame is None or self.roi_rect is None:
            return
        x, y = event.pos().x(), event.pos().y()
        if self.drag_offset:
            # Move ROI
            dx, dy = self.drag_offset
            new_rx = x - dx
            new_ry = y - dy
            # Mantém ROI dentro da imagem
            h, w, _ = self.last_frame.shape
            new_rx = max(0, min(new_rx, w - self.roi_rect[2]))
            new_ry = max(0, min(new_ry, h - self.roi_rect[3]))
            self.roi_rect = (new_rx, new_ry, self.roi_rect[2], self.roi_rect[3])
        else:
            # Redimensiona ROI
            rx, ry, _, _ = self.roi_rect
            new_rw = max(10, x - rx)
            new_rh = max(10, y - ry)
            h, w, _ = self.last_frame.shape
            new_rw = min(new_rw, w - rx)
            new_rh = min(new_rh, h - ry)
            self.roi_rect = (rx, ry, new_rw, new_rh)
        self.update_roi_overlay()

    def end_roi(self, event):
        if not self.editing_roi or self.roi_start is None or self.last_frame is None or self.roi_rect is None:
            return
        self.roi_end = (event.pos().x(), event.pos().y())
        self.drag_offset = None
        self.update_roi_overlay(final=True)

    def update_roi_overlay(self, final=False):
        # Desenha o retângulo da ROI sobre a última imagem capturada
        if self.last_frame is None or self.roi_rect is None:
            return
        img = self.last_frame.copy()
        rx, ry, rw, rh = self.roi_rect
        cv2.rectangle(img, (rx, ry), (rx+rw, ry+rh), (0,255,0), 2)
        self.show_image(self.label_original, img)

    def on_camera_change(self, index):
        camera_name = self.combo_camera.currentText()
        self.selected_camera = self.cameras[camera_name]
        self.label_original.clear()
        self.label_processed.clear()

    def capture_image(self):
        if self.selected_camera is None or self.selected_detector is None:
            return
        try:
            frame = self.selected_camera.capture()
            print(f"[DEBUG] Frame capturado: shape={frame.shape} dtype={frame.dtype}")
        except Exception as e:
            self.label_original.setText(f'Falha ao capturar imagem: {e}')
            self.label_processed.clear()
            return
        # Exibe imagem original
        self.show_image(self.label_original, frame)
        # Recorta ROI para processamento
        if self.roi_rect is not None:
            rx, ry, rw, rh = self.roi_rect
            roi = frame[ry:ry+rh, rx:rx+rw]
        else:
            roi = frame
        # Processamento pelo detector
        try:
            processed = self.selected_detector.detect(roi)
            print(f"[DEBUG] Imagem processada: shape={processed.shape} dtype={processed.dtype}")
        except Exception as e:
            self.label_processed.setText(f'Erro no processamento: {e}')
            return
        # Se imagem processada for 2D, converte para 3 canais para exibir
        if len(processed.shape) == 2:
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        self.show_image(self.label_processed, processed)

    def show_image(self, label, img):
        print(f"[DEBUG] show_image: shape={img.shape} dtype={img.dtype}")
        h, w, ch = img.shape
        bytes_per_line = ch * w
        qt_img = QImage(img.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qt_img)
        label.setPixmap(pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio))
        if label == self.label_original:
            self.last_frame = img.copy()


