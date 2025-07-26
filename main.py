from core.Camera import Camera
from core.Detector import Detector
from core.screen_01 import Screen01

import cv2 
import sys
from PyQt5.QtWidgets import QApplication



def main():
   # Exemplo de uso
    app = QApplication(sys.argv)
    # Descobre câmeras disponíveis (0, 1, 2...)
    cameras = {}
    for i in range(6):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras[f'Camera {i}'] = Camera(name=f'Camera {i}', id=i, capture_device=cap)
    if not cameras:
        print('Nenhuma câmera encontrada.')
        sys.exit(1)
    # Cria detector disponível
    # Aqui você pode especificar o caminho do modelo que deseja usar
    detector = Detector()
    # Cria a janela principal
    window = Screen01(cameras, detector)
    window.show()
    app.exec_()
    # Libera recursos das câmeras
    for cam in cameras.values():
        cam.release()
    cv2.destroyAllWindows()

    

if __name__ == "__main__":
    main()
