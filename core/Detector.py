
from core import ImageProcessor
from numpy import ndarray
import cv2


class Detector(ImageProcessor.ImageProcessor):
    def __init__(self):
        super().__init__()
    
    def save(self, image: ndarray, filename: str):
        if not isinstance(image, ndarray):
            raise TypeError("Input image must be a numpy ndarray.")
        cv2.imwrite(filename, image)

    def detect(self, image) -> ndarray:
        # Precess the image before detection
        if not isinstance(image, ndarray):
            raise TypeError("Input image must be a numpy ndarray.")
        
        image_resized = self.resize_image(image, 640, 480)
        image_gray = self.convert_to_grayscale(image_resized)
        image_processed = self.apply_gaussian_blur(image_gray)
        return image_processed
