import cv2

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtGui import QPixmap, QImage, QMouseEvent
from PyQt5.QtCore import Qt


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

class Screen01(QWidget):
    def __init__(self, cameras, detector):
        super().__init__()
        self.cameras = cameras  # Dict: {name: Camera}
        self.selected_camera = None
        self.selected_detector = detector
        self.vlayout = QVBoxLayout()
        self.roi_start = [100, 100]
        self.roi_end = [250, 250]
        self.roi_rect = (self.roi_start[0], self.roi_start[1], 
                         self.roi_end[0], self.roi_end[1])
        self._scale = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self.last_frame = None
        self.editing_roi = False
        self.drag_offset = None
        self.init_ui()
    # --- Métodos de manipulação de ROI via mouse ---
    def start_roi(self, event):
        if not self.editing_roi or self.last_frame is None:
            return
        x, y = self._map_mouse_to_image(event, self.last_frame)
        if self.roi_rect is None:
            self.roi_rect = (100, 100, 150, 150)
        rx, ry, rw, rh = self.roi_rect
        r = 12
        # Pontos de resize: borda inferior e borda direita
        bottom_pt = (int(rx+rw//2), int(ry+rh))
        right_pt = (int(rx+rw), int(ry+rh//2))
        resize_points = [bottom_pt, right_pt]
        resize_dirs = [(False, False, False, True), (False, True, False, False)]  # bottom, right
        clicked_resize = False
        print(f"[DEBUG] Resize points: {resize_points}, Mouse pos: ({x}, {y})")
        for idx, pt in enumerate(resize_points):
            dist = ((pt[0] - x) ** 2 + (pt[1] - y) ** 2) ** 0.5
            if dist <= r:
                clicked_resize = True
                self.resizing = True
                self.resize_dir = resize_dirs[idx]
                self.drag_offset = None
                break
        if not clicked_resize and rx < x < rx+rw and ry < y < ry+rh:
            self.resizing = False
            self.drag_offset = (x - rx, y - ry)
            self.resize_dir = (False, False, False, False)
        elif not clicked_resize:
            self.resizing = False
            self.drag_offset = None
            self.resize_dir = (False, False, False, False)
        self.roi_start = (x, y)
        self.roi_end = None
        self.last_mouse_pos = (x, y)

    def update_roi(self, event):
        if not self.editing_roi or self.roi_start is None or self.last_frame is None or self.roi_rect is None:
            return
        x, y = self._map_mouse_to_image(event, self.last_frame)
        rx, ry, rw, rh = self.roi_rect
        h, w, _ = self.last_frame.shape
        if hasattr(self, 'resizing') and self.resizing:
            # Redimensionamento pelas bordas
            _, on_right, _, on_bottom = self.resize_dir
            new_rx, new_ry = rx, ry
            new_rw, new_rh = rw, rh
            if on_right:
                new_rw = max(10, min(x - rx, w - rx))
            if on_bottom:
                new_rh = max(10, min(y - ry, h - ry))
            self.roi_rect = (new_rx, new_ry, new_rw, new_rh)
        elif self.drag_offset:
            # Move ROI
            dx, dy = self.drag_offset
            new_rx = x - dx
            new_ry = y - dy
            # Mantém ROI dentro da imagem
            new_rx = max(0, min(new_rx, w - rw))
            new_ry = max(0, min(new_ry, h - rh))
            self.roi_rect = (new_rx, new_ry, rw, rh)
        self.last_mouse_pos = (x, y)
        self.update_roi_overlay()

    def end_roi(self, event):
        if not self.editing_roi or self.roi_start is None or self.last_frame is None or self.roi_rect is None:
            return
        x, y = self._map_mouse_to_image(event, self.last_frame)
        self.roi_end = (x, y)
        self.drag_offset = None
        self.resizing = False
        self.update_roi_overlay(final=True)

    def _map_mouse_to_image(self, event, image):
        # Converte as coordenadas do mouse do QLabel para a imagem original
        x_widget, y_widget = event.pos().x(), event.pos().y()
        scale = getattr(self, '_scale', 1.0)
        offset_x = getattr(self, '_offset_x', 0)
        offset_y = getattr(self, '_offset_y', 0)
        x_img = int((x_widget - offset_x) / scale)
        y_img = int((y_widget - offset_y) / scale)
        # Garante que está dentro dos limites da imagem
        h, w = getattr(self, '_img_shape', (image.shape[0], image.shape[1]))
        x_img = max(0, min(x_img, w - 1))
        y_img = max(0, min(y_img, h - 1))
        return x_img, y_img

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

        # Botão para editar ROI
        self.btn_edit_roi = QPushButton('Editar ROI')
        self.btn_edit_roi.setCheckable(True)
        self.btn_edit_roi.toggled.connect(self.toggle_edit_roi)
        self.vlayout.addWidget(self.btn_edit_roi)

        # Labels para imagens
        import numpy as np
        self.label_original = ROILabel()
        self.label_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_original.setMouseTracking(True)
        self.label_original.parent_screen = self
        self.vlayout.addWidget(self.label_original)

        self.label_processed = QLabel()
        self.label_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vlayout.addWidget(self.label_processed)
        self.setLayout(self.vlayout)

        # Imagem preta inicial padronizada
        black_img = np.zeros((480, 640, 3), dtype=np.uint8)
        self.show_image(self.label_original, black_img)
        self.show_image(self.label_processed, black_img)
        # Desenha ROI sobre a imagem preta
        self.update_roi_overlay()
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
        # ...existing code for start_roi...

        # ...existing code for update_roi...

        self.drag_offset = None
        self.resizing = False
        self.update_roi_overlay(final=True)

    def update_roi_overlay(self, final=False):
        # Desenha o retângulo da ROI sobre a última imagem capturada
        if self.last_frame is None or self.roi_rect is None:
            return
        img = self.last_frame.copy()
        rx, ry, rw, rh = self.roi_rect
        cv2.rectangle(img, (int(rx), int(ry)), (int(rx+rw), int(ry+rh)), (0,255,0), 2)
        # Se modo edição, desenha marcadores
        if self.editing_roi:
            # Círculos apenas nas bordas de resize
            handle_color = (0, 255, 255)
            r = 12
            bottom_pt = (int(rx+rw//2), int(ry+rh))
            right_pt = (int(rx+rw), int(ry+rh//2))
            cv2.circle(img, bottom_pt, r, handle_color, -1)
            cv2.circle(img, right_pt, r, handle_color, -1)
            # Círculo central para mover
            center = (int(rx+rw//2), int(ry+rh//2))
            cv2.circle(img, center, r, (0, 128, 255), -1)
        self.show_image(self.label_original, img)

    def on_camera_change(self, index):
        import numpy as np
        camera_name = self.combo_camera.currentText()
        self.selected_camera = self.cameras[camera_name]
        # Redesenha imagem preta e ROI ao trocar de câmera
        black_img = np.zeros((480, 640, 3), dtype=np.uint8)
        self.show_image(self.label_original, black_img)
        self.show_image(self.label_processed, black_img)
        self.update_roi_overlay()

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
        # Exibe imagem original com ROI desenhada
        self.last_frame = frame.copy()
        self.update_roi_overlay()
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
        # Calcula o tamanho do QLabel
        label_width = label.width() if label.width() > 1 else 500
        label_height = label.height() if label.height() > 1 else 500
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.AspectRatioMode.KeepAspectRatio)
        label.setPixmap(scaled_pixmap)
        # Atualiza escala e offsets para conversão de coordenadas
        if label == self.label_original:
            sw, sh = scaled_pixmap.width(), scaled_pixmap.height()
            self._img_shape = (h, w)
            self._scale = min(label_width / w, label_height / h)
            self._offset_x = (label_width - sw) // 2
            self._offset_y = (label_height - sh) // 2
            self.last_frame = img.copy()


