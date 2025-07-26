import cv2

from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QComboBox, QHBoxLayout
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

class Screen01(QWidget):
    def __init__(self, cameras, detectors):
        super().__init__()
        self.cameras = cameras  # Dict: {name: Camera}
        self.detectors = detectors  # Dict: {name: Detector}
        self.selected_camera = None
        self.selected_detector = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('DetectorBox - Seleção de Câmera e Detector')
        self.setFixedSize(1024, 768)
        layout = QVBoxLayout()


        # Dropdown para seleção de câmera
        self.combo_camera = QComboBox()
        self.combo_camera.addItems(list(self.cameras.keys()))
        self.combo_camera.currentIndexChanged.connect(self.on_camera_change)
        layout.addWidget(self.combo_camera)

        # (Removido campo de inserção manual de índice de câmera)

        # Dropdown para seleção de detector
        self.combo_detector = QComboBox()
        self.combo_detector.addItems(list(self.detectors.keys()))
        self.combo_detector.currentIndexChanged.connect(self.on_detector_change)
        layout.addWidget(self.combo_detector)

        # Botão de captura
        self.capture_btn = QPushButton('Capturar Imagem')
        self.capture_btn.clicked.connect(self.capture_image)
        layout.addWidget(self.capture_btn)

        # Labels para imagens
        self.label_original = QLabel('Imagem Original')
        self.label_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_original)

        self.label_processed = QLabel('Imagem Pós-Processamento')
        self.label_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_processed)

        self.setLayout(layout)
        self.on_camera_change(0)
        self.on_detector_change(0)

        # Dropdown para seleção de detector
        self.combo_detector = QComboBox()
        self.combo_detector.addItems(list(self.detectors.keys()))
        self.combo_detector.currentIndexChanged.connect(self.on_detector_change)
        layout.addWidget(self.combo_detector)

        # Botão de captura
        self.capture_btn = QPushButton('Capturar Imagem')
        self.capture_btn.clicked.connect(self.capture_image)
        layout.addWidget(self.capture_btn)

        # Labels para imagens
        self.label_original = QLabel('Imagem Original')
        self.label_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_original)

        self.label_processed = QLabel('Imagem Pós-Processamento')
        self.label_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_processed)

        self.setLayout(layout)
        self.on_camera_change(0)
        self.on_detector_change(0)

    def on_camera_change(self, index):
        camera_name = self.combo_camera.currentText()
        self.selected_camera = self.cameras[camera_name]
        self.label_original.clear()
        self.label_processed.clear()

    def on_detector_change(self, index):
        detector_name = self.combo_detector.currentText()
        self.selected_detector = self.detectors[detector_name]

    def capture_image(self):
        if self.selected_camera is None or self.selected_detector is None:
            return
        try:
            frame = self.selected_camera.capture()
        except Exception as e:
            self.label_original.setText(f'Falha ao capturar imagem: {e}')
            self.label_processed.clear()
            return
        # Exibe imagem original
        self.show_image(self.label_original, frame)
        # Processamento pelo detector
        try:
            processed = self.selected_detector.detect(frame)
        except Exception as e:
            self.label_processed.setText(f'Erro no processamento: {e}')
            return
        # Se imagem processada for 2D, converte para 3 canais para exibir
        if len(processed.shape) == 2:
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        self.show_image(self.label_processed, processed)

    def show_image(self, label, img):
        h, w, ch = img.shape
        bytes_per_line = ch * w
        qt_img = QImage(img.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qt_img)
        label.setPixmap(pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio))


