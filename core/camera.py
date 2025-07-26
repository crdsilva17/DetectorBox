import cv2
from numpy import ndarray

from models import camera_model

class Camera(camera_model.Camera[ndarray, cv2.VideoCapture]):
    def __init__(self, name: str, id: int, capture_device: cv2.VideoCapture):
        super().__init__(name, id, capture_device)

    def capture(self) -> ndarray:
        ret, frame = self.capture_device.read()
        if ret:
            return frame
        else:
            raise Exception("Failed to capture image")
    
    def delete(self):
        if self.capture_device.isOpened():
            self.capture_device.release()
        cv2.destroyAllWindows()
    
    def release(self):
        self.delete()
        