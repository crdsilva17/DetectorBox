import cv2

import os
import numpy as np

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QComboBox, \
    QHBoxLayout, QSizePolicy, QInputDialog, QFileDialog, QMenuBar, QMenu, QSpinBox, QCheckBox, QMessageBox
from PyQt5.QtGui import QPixmap, QImage, QCursor
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtCore import Qt

from core.ROILabel import ROILabel




class Screen01(QWidget):
    def __init__(self, cameras, detector):
        super().__init__()
        self.cameras = cameras  # Dict: {name: Camera}
        self.selected_camera = None
        self.selected_detector = detector
        self.image_canny = None
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
        self._width = 1536
        self._height = 500
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
        # Limite da ROI: apenas a área da imagem realmente visível no QLabel
        # Calcula o retângulo visível em coordenadas da imagem original
        scale = getattr(self, '_scale', 1.0)
        offset_x = getattr(self, '_offset_x', 0)
        offset_y = getattr(self, '_offset_y', 0)
        if hasattr(self, '_img_shape'):
            img_h, img_w = self._img_shape
        else:
            img_h, img_w, _ = self.last_frame.shape
        # Tamanho do QLabel
        label_h = self.label_original.height()
        label_w = self.label_original.width()
        # Tamanho do pixmap exibido
        pixmap = self.label_original.pixmap()
        if pixmap is not None:
            pixmap_h = pixmap.height()
            pixmap_w = pixmap.width()
        else:
            pixmap_h = label_h
            pixmap_w = label_w
        # Área visível da imagem original (em coordenadas da imagem)
        vis_x0 = int(max(0, (0 - offset_x) / scale))
        vis_y0 = int(max(0, (0 - offset_y) / scale))
        vis_x1 = int(min(img_w, (pixmap_w - offset_x) / scale))
        vis_y1 = int(min(img_h, (pixmap_h - offset_y) / scale))
        # print(f"[DEBUG] ROI visível: x0={vis_x0}, y0={vis_y0}, x1={vis_x1}, y1={vis_y1}")
        if hasattr(self, 'resizing') and self.resizing:
            # Redimensionamento pelas bordas
            _, on_right, _, on_bottom = self.resize_dir
            new_rx, new_ry = rx, ry
            new_rw, new_rh = rw, rh
            if on_right:
                new_rw = max(10, min(x - rx, vis_x1 - rx))
            if on_bottom:
                new_rh = max(10, min(y - ry, vis_y1 - new_ry))
                if new_ry + new_rh > vis_y1:
                    new_rh = vis_y1 - new_ry
                print(f"[DEBUG] Altura ROI ao redimensionar: {new_rh} (y={new_ry}, y_max={vis_y1})")
            # Garante que a ROI não ultrapasse o topo
            if new_ry < vis_y0:
                new_ry = vis_y0
            self.roi_rect = (new_rx, new_ry, new_rw, new_rh)
        elif self.drag_offset:
            # Move ROI
            dx, dy = self.drag_offset
            new_rx = x - dx
            new_ry = y - dy
            # Mantém ROI dentro da área visível
            new_rx = max(vis_x0, min(new_rx, vis_x1 - rw))
            if new_rx + rw > vis_x1:
                new_rx = vis_x1 - rw
            new_ry = max(vis_y0, min(new_ry, vis_y1 - rh))
            if new_ry + rh > vis_y1:
                new_ry = vis_y1 - rh
            if new_ry < vis_y0:
                new_ry = vis_y0
            if new_ry + rh > vis_y1:
                new_ry = vis_y1 - rh
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
        self.setWindowTitle('DetectorBox - Inspetor de Caixas')
        # Layout principal horizontal
        main_layout = QHBoxLayout()

        # --- Menu lateral (VBox) ---
        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(20, 20, 20, 20)
        menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        menu_layout.setSpacing(15)

        # Menu bar
        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet("background-color: #fcfcfc; color: black; font-size: 16px; font-weight: bold;")
        main_layout.setMenuBar(menu_bar)
        file_menu = QMenu('File', self)
        file_menu.addAction('Save Image', self.save_image)
        file_menu.addAction('New Recipe', self.create_new_box)
        file_menu.addAction('Save Recipe', self.save_recipe)
        file_menu.addAction('Load Recipe', lambda: self.on_recipe_change(QFileDialog.getOpenFileName(self, "Select Image",
                                                                                                "./recipes", "Images (*.json)")[0]))
        file_menu.addAction('Delete Recipe', self.delete_recipe)
        file_menu.addAction('Exit', self.close)
        menu_bar.addMenu(file_menu)
        
        setup_menu = QMenu('Setup', self)
        setup_menu.addAction('Camera Select', lambda: self.combo_camera.showPopup())
        setup_menu.addAction('Connection', lambda: None)
        menu_bar.addMenu(setup_menu)

        # Dropdown para seleção de câmera
        self.combo_camera = QComboBox()
        self.combo_camera.setFixedSize(200, 40)
        self.combo_camera.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 16px; font-weight: bold;")
        self.combo_camera.addItems(list(self.cameras.keys()))
        self.combo_camera.currentIndexChanged.connect(self.on_camera_change)
        # menu_layout.addWidget(self.combo_camera)



        # Lista de seleção de recipes existentes
        self.recipe_dir = os.path.join(os.path.dirname(__file__), '..', 'recipes')
        os.makedirs(self.recipe_dir, exist_ok=True)
        self.combo_recipe = QComboBox()
        self.combo_recipe.setFixedSize(200, 40)
        self.combo_recipe.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 16px; font-weight: bold;")
        self.update_recipe_list()
        self.combo_recipe.currentIndexChanged.connect(self.on_recipe_change)
        menu_layout.addWidget(self.combo_recipe)

        # Botão para criar nova caixa/recipe
        self.btn_new_box = QPushButton('New Recipe')
        self.btn_new_box.setFixedSize(200, 40)
        self.btn_new_box.clicked.connect(self.create_new_box)
        self.btn_new_box.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 14px; font-weight: bold;")
        menu_layout.addWidget(self.btn_new_box)

        # Botão para salvar imagem
        self.btn_save_image = QPushButton('Save Image')
        self.btn_save_image.setFixedSize(200, 60)
        self.btn_save_image.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 14px; font-weight: bold;")
        self.btn_save_image.clicked.connect(self.save_image)
        menu_layout.addWidget(self.btn_save_image)

        # Botão para carregar imagem
        self.btn_load_image = QPushButton('Load Image')
        self.btn_load_image.setFixedSize(200, 60)
        self.btn_load_image.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 14px; font-weight: bold;")
        self.btn_load_image.clicked.connect(lambda: self.load_image(QFileDialog.getOpenFileName(self, "Select Image",
                                                                                                "./resource", "Images (*.png *.jpg)")[0]))
        menu_layout.addWidget(self.btn_load_image)

        # Botão para editar ROI
        self.btn_edit_roi = QPushButton('Edit Area')
        self.btn_edit_roi.setFixedSize(200, 60)
        self.btn_edit_roi.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 14px; font-weight: bold;")
        self.btn_edit_roi.setCheckable(True)
        self.btn_edit_roi.toggled.connect(self.toggle_edit_roi)
        menu_layout.addWidget(self.btn_edit_roi)
        
        # Botão de captura
        self.capture_btn = QPushButton('Photo')
        self.capture_btn.setFixedSize(200, 100)
        font = self.capture_btn.font()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)  # QtGui.QFont.Bold is 75
        font.setFamily('Arial')
        self.capture_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.capture_btn.setFont(font)
        self.capture_btn.clicked.connect(self.capture_image)
        menu_layout.addWidget(self.capture_btn)

        # Parametros de tratamento de imagem
        menu_hLayout = [QHBoxLayout() for _ in range(5)]
        for hLayout in menu_hLayout:
            hLayout.setContentsMargins(0, 0, 0, 0)
            hLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hLayout.setSpacing(10)
            menu_layout.addLayout(hLayout)
        self.edit_minDistance = QSpinBox()
        self.edit_minDistance.setRange(0, 500)
        self.edit_minDistance.setValue(90)
        self.edit_minDistance.setObjectName("edit_minDistance")
        self.edit_minDistance.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 20px; font-weight: bold;")
        self.edit_minDistance.setFixedSize(100, 40)
        label = QLabel("Min Distance")
        label.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        menu_hLayout[0].addWidget(label)
        menu_hLayout[0].addWidget(self.edit_minDistance)
        self.edit_parameter1 = QSpinBox()
        self.edit_parameter1.setRange(0, 500)
        self.edit_parameter1.setValue(100)
        self.edit_parameter1.setObjectName("edit_minDistance")
        self.edit_parameter1.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 20px; font-weight: bold;")
        self.edit_parameter1.setFixedSize(100, 40)
        label = QLabel("Parameter 1")
        label.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        menu_hLayout[1].addWidget(label)
        menu_hLayout[1].addWidget(self.edit_parameter1)
        self.edit_parameter2 = QSpinBox()
        self.edit_parameter2.setRange(0, 500)
        self.edit_parameter2.setValue(35)
        self.edit_parameter2.setObjectName("edit_minDistance")
        self.edit_parameter2.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 20px; font-weight: bold;")
        self.edit_parameter2.setFixedSize(100, 40)
        label = QLabel("Parameter 2")
        label.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        menu_hLayout[2].addWidget(label)
        menu_hLayout[2].addWidget(self.edit_parameter2)
        self.edit_minRadius = QSpinBox()
        self.edit_minRadius.setRange(0, 500)
        self.edit_minRadius.setValue(30)
        self.edit_minRadius.setObjectName("edit_minDistance")
        self.edit_minRadius.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 20px; font-weight: bold;")
        self.edit_minRadius.setFixedSize(100, 40)
        label = QLabel("Min Radius")
        label.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        menu_hLayout[3].addWidget(label)
        menu_hLayout[3].addWidget(self.edit_minRadius)
        self.edit_maxRadius = QSpinBox()
        self.edit_maxRadius.setRange(0, 500)
        self.edit_maxRadius.setValue(40)
        self.edit_maxRadius.setObjectName("edit_minDistance")
        self.edit_maxRadius.setStyleSheet("background-color: #f0f0f0; color: black; font-size: 20px; font-weight: bold;")
        self.edit_maxRadius.setFixedSize(100, 40)
        label = QLabel("Max Radius")
        label.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        menu_hLayout[4].addWidget(label)
        menu_hLayout[4].addWidget(self.edit_maxRadius)
        self.adaptive_checkbox = QCheckBox("Adaptive Canny")
        self.adaptive_checkbox.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        menu_layout.addWidget(self.adaptive_checkbox)
        # altera valores
        self.edit_minDistance.valueChanged.connect(self.update_roi_overlay)
        self.edit_parameter1.valueChanged.connect(self.update_roi_overlay)
        self.edit_parameter2.valueChanged.connect(self.update_roi_overlay)
        self.edit_minRadius.valueChanged.connect(self.update_roi_overlay)
        self.edit_maxRadius.valueChanged.connect(self.update_roi_overlay)
        self.adaptive_checkbox.stateChanged.connect(self.update_roi_overlay)

        # Expansor para empurrar os botões para o topo
        menu_layout.addStretch(1)

        # --- Área de imagens (VBox) ---
        images_layout = QVBoxLayout()
        images_layout.setSpacing(20)

        screen = QGuiApplication.primaryScreen()
        if screen is not None and hasattr(screen, 'size'):
            screen_size = screen.size()
            max_width = int(screen_size.width() * 0.8)
            max_height = int(max_width * 9 / 16)  # Mantém proporção 16:9
        else:
            # Valor padrão caso não consiga obter o tamanho da tela
            max_width = 1536  # 80% de 1920
            max_height = int(max_width * 9 / 16)  # Mantém proporção 16:
        
        self._width = min(max_width, 1536)  # Limita a largura máxima
        self._height = min(max_height, 500)  # Limita a altura máxima

        # Container horizontal para imagem original
        original_container = QWidget()
        original_hbox = QHBoxLayout()
        original_hbox.setContentsMargins(0, 0, 0, 0)
        original_hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_original = ROILabel()
        # Remover tamanho mínimo fixo para permitir expansão
        self.label_original.setMinimumSize(self._width, self._height)
        self.label_original.setMaximumSize(max_width, max_height)
        self.label_original.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_original.setMouseTracking(True)
        self.label_original.setScaledContents(False)
        self.label_original.parent_screen = self
        original_hbox.addWidget(self.label_original)
        original_container.setLayout(original_hbox)
        images_layout.addWidget(original_container)

        # Container horizontal para imagem processada
        processed_container = QWidget()
        processed_hbox = QHBoxLayout()
        processed_hbox.setContentsMargins(0, 0, 0, 0)
        processed_hbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_processed = QLabel()
        self.label_processed.setMinimumSize(self._width, self._height)
        self.label_processed.setMaximumSize(max_width, max_height)
        self.label_processed.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_processed.setScaledContents(False)
        processed_hbox.addWidget(self.label_processed)
        processed_container.setLayout(processed_hbox)
        images_layout.addWidget(processed_container)

        # Adiciona layouts ao layout principal
        main_layout.addLayout(menu_layout, stretch=0)
        main_layout.addSpacing(30)
        main_layout.addLayout(images_layout, stretch=3)

        self.setLayout(main_layout)

        # Imagem preta inicial padronizada
        black_img = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        self.last_frame = black_img.copy()
        self.show_image(self.label_original, black_img)
        self.show_image(self.label_processed, black_img)
        # Desenha ROI sobre a imagem preta
        self.update_roi_overlay()
        self.on_camera_change(self.combo_camera.currentIndex())  # Seleciona a primeira câmera por padrão

    def toggle_edit_roi(self, checked):
        self.editing_roi = checked
        if checked:
            self.label_original.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.label_original.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
        self.update_roi_overlay()

    def update_recipe_list(self):
        self.combo_recipe.clear()
        recipes = [f.removesuffix('.json') for f in os.listdir(self.recipe_dir) if f.endswith('.json')]
        self.combo_recipe.addItems(recipes)
        if recipes:
            self.selected_recipe = recipes[0]
        else:
            self.selected_recipe = None
    
    def save_recipe(self):
        if self.selected_recipe is None:
            return
        path = os.path.join(self.recipe_dir, self.selected_recipe)
        if not os.path.exists(path):
            return
        layout = []
        info = ""
        with open(path, 'r') as f:
            import json
            data = f.read()
            json_data = json.loads(data)
            layout = json_data.get('layout', [1, 1])
            info = json_data.get('info')
        
        data_recipe = {
                "layout": layout,
                "info": info,
                "minDistance": self.edit_minDistance.value(),
                "parameter1": self.edit_parameter1.value(),
                "parameter2": self.edit_parameter2.value(),
                "minRadius": self.edit_minRadius.value(),
                "maxRadius": self.edit_maxRadius.value(),
                "adaptive": self.adaptive_checkbox.isChecked()
            }
        
        with open(path, 'w') as f:
            json.dump(data_recipe, f, indent=2)

    def delete_recipe(self):
        if self.selected_recipe is None:
            return
        if not self.selected_recipe.endswith(".json"):
            self.selected_recipe = f"{self.selected_recipe}.json"
        message = QMessageBox(self)
        message.setText(f"Do you want to delete the recipe {self.selected_recipe}?")
        message.setWindowTitle("Delete Recipe")
        message.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        response = message.exec()
        if self.selected_recipe is None or response == QMessageBox.Cancel:
            return
        path = os.path.join(self.recipe_dir, self.selected_recipe)
        if os.path.exists(path):
            os.remove(path)
            print(f"[DEBUG] Receita {self.selected_recipe} deletada.")
            self.update_recipe_list()
           


    def on_recipe_change(self, index = None):
        if index is not None and index != self.combo_recipe.currentIndex():
            recipe = index.split('/')[-1]
            self.combo_recipe.setCurrentText(recipe.removesuffix('.json'))
        
        self.selected_recipe = f"{self.combo_recipe.currentText()}.json"
        path = os.path.join(self.recipe_dir, self.selected_recipe)
        if not os.path.exists(path):
            return
        with open(path, 'r') as f:
            import json
            data = f.read()
            json_data = json.loads(data)
            self.edit_minDistance.setValue(json_data.get("minDistance"))
            self.edit_parameter1.setValue(json_data.get("parameter1"))
            self.edit_parameter2.setValue(json_data.get("parameter2"))
            self.edit_minRadius.setValue(json_data.get("minRadius"))
            self.edit_maxRadius.setValue(json_data.get("maxRadius"))
            self.adaptive_checkbox.setChecked(json_data.get("adaptive"))
        print(f"[DEBUG] Receita selecionada: {self.selected_recipe}")

    def create_new_box(self):
        name, ok = QInputDialog.getText(self, 'New Box/Recipe', 'FileName of Box:')
        if ok and name:
            path = os.path.join(self.recipe_dir, f'{name}.json')
            import json
            columns, ok = QInputDialog.getText(self, 'New Box/Recipe', 'columns of the box:')
            if not columns or not ok:
                return
            rows, ok = QInputDialog.getText(self, 'New Box/Recipe', 'rows of the box:')
            if not rows or not ok:
                return

            box_data = {
                        "layout": [int(columns), int(rows)], 
                        "info": name,
                        "minDistance": self.edit_minDistance.value(),
                        "parameter1": self.edit_parameter1.value(),
                        "parameter2": self.edit_parameter2.value(),
                        "minRadius": self.edit_minRadius.value(),
                        "maxRadius": self.edit_maxRadius.value(),
                        "adaptive": self.adaptive_checkbox.isChecked()
                        }
            with open(path, 'w') as f:
                json.dump(box_data, f, indent=2)
            self.update_recipe_list()
    
    def save_image(self):
        if self.last_frame is None:
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save Image", "./resource", "Images (*.png)")
        if filename:
            cv2.imwrite(filename, self.last_frame)
            print(f"[DEBUG] Imagem salva em: {filename}")

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
        # Recorta ROI para processamento
        if self.roi_rect is not None:
            rx, ry, rw, rh = self.roi_rect
            roi = img[ry:ry+rh, rx:rx+rw]
        else:
            roi = img
        # Processamento pelo detector
        try:
            processed, self.image_canny = self.selected_detector.detect(roi)
            processed = cv2.resize(processed, (self._width, self._height), interpolation=cv2.INTER_LINEAR)
            self.image_canny = cv2.resize(self.image_canny, (self._width, self._height), interpolation=cv2.INTER_LINEAR)
            print(f"[DEBUG] Imagem processada: shape={processed.shape} dtype={processed.dtype}")
        except Exception as e:
            self.label_processed.setText(f'Erro no processamento: {e}')
            return

        # Inspeciona a imagem canny para validar quantos objetos circulares foram detectados
        self.image_canny, circles = self.selected_detector.detect_circles(roi, minDist=self.edit_minDistance.value(), 
                                                                          size=(self._width, self._height),
                                                                          param1=self.edit_parameter1.value(),
                                                                            param2=self.edit_parameter2.value(),
                                                                            minRadius=self.edit_minRadius.value(),
                                                                            maxRadius=self.edit_maxRadius.value(),
                                                                            adaptive=self.adaptive_checkbox.isChecked())
        if self.image_canny is None:
            return
        
        print(f"[DEBUG] circulos detectados: {len(circles)}")
        
        # Se imagem processada for 2D, converte para 3 canais para exibir
        if len(processed.shape) == 2:
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        # Exibe imagem processada
        self.show_image(self.label_processed, self.image_canny)

    def load_image(self, filename=""):
        if not os.path.exists(filename):
            return
        image = cv2.imread(filename)
        if image is None:
            raise ValueError(f"Could not read image file {filename}.")
        # Redimensiona a imagem para o tamanho máximo permitido
        frame = cv2.resize(image, (self._width, self._height), interpolation=cv2.INTER_LINEAR)
        self.last_frame = frame.copy()
        # self.show_image(self.label_original, image)
        self.update_roi_overlay()


    def on_camera_change(self, index):
        camera_name = self.combo_camera.currentText()
        self.selected_camera = self.cameras[camera_name]
        # Redesenha imagem preta e ROI ao trocar de câmera
        black_img = np.zeros((self._height, self._width, 3), dtype=np.uint8)
        self.last_frame = black_img.copy()
        self.show_image(self.label_original, black_img)
        self.show_image(self.label_processed, black_img)
        self.update_roi_overlay()

    def capture_image(self):
        if self.selected_camera is None or self.selected_detector is None:
            return
        try:
            frame = self.selected_camera.capture()
            frame = cv2.resize(frame, (self._width, self._height), interpolation=cv2.INTER_LINEAR)
            print(f"[DEBUG] Frame capturado: shape={frame.shape} dtype={frame.dtype}")
            self.on_recipe_change(self.combo_recipe.currentIndex())
        except Exception as e:
            self.label_original.setText(f'Falha ao capturar imagem: {e}')
            self.label_processed.clear()
            return
        # Exibe imagem original com ROI desenhada
        self.last_frame = frame.copy()
        self.update_roi_overlay()
        

    def show_image(self, label, img):
        print(f"[DEBUG] show_image: shape={img.shape} dtype={img.dtype}")
        h, w, ch = img.shape
        bytes_per_line = ch * w
        qt_img = QImage(img.data, w, h, bytes_per_line, QImage.Format_BGR888)
        # Calcula o tamanho máximo possível mantendo proporção widescreen
        label_width = label.width() if label.width() > 1 else self._width
        label_height = label.height() if label.height() > 1 else self._height
        # Mantém proporção da imagem
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(label_width, label_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        # Centraliza a imagem no QLabel
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(scaled_pixmap)
        # Atualiza escala e offsets para conversão de coordenadas
        if label == self.label_original:
            sw, sh = scaled_pixmap.width(), scaled_pixmap.height()
            self._img_shape = (h, w)
            self._scale = min(label_width / w, label_height / h)
            self._offset_x = (label_width - sw) // 2
            self._offset_y = (label_height - sh) // 2


