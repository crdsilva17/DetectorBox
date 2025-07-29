
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

    def detect(self, image) -> tuple[ndarray, ndarray]:
        # Precess the image before detection
        if not isinstance(image, ndarray):
            raise TypeError("Input image must be a numpy ndarray.")
        
        image_resized = self.resize_image(image, 640, 480)
        image_gray = self.convert_to_grayscale(image_resized)
        image_processed = self.apply_gaussian_blur(image_gray)
        image_canny = self.adaptive_canny(image_processed)
        return image_processed, image_canny

    def detect_circles(self, image: ndarray) -> tuple[ndarray, list]:
        if not isinstance(image, ndarray):
            raise TypeError("Input image must be a numpy ndarray.")
        img = self.binary_inv_canny(image)
        img = cv2.Canny(img, 100, 200)
        circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1.2, 100)
        
        if circles is not None:
            circles = circles[0, :, :].astype(int)
            for (x, y, r) in circles:
                cv2.circle(image, (x, y), r, (0, 255, 0), 4)
        return img, circles.tolist() if circles is not None else []