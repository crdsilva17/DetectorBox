import cv2
from numpy import ndarray

from models import camera_model

class Camera(camera_model.Camera[ndarray]):
    def __init__(self, name: str, id: int):
        super().__init__(name, id)
        self.name = name
        self.id = id
        self.capture_device = cv2.VideoCapture(id)

    def capture(self) -> ndarray:
        ret, frame = self.capture_device.read()
        if ret:
            return frame
        else:
            raise Exception("Failed to capture image")