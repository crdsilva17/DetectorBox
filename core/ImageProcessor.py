import cv2

from numpy import ndarray

class ImageProcessor:
    @staticmethod
    def resize_image(image: ndarray, width: int, height: int) -> ndarray:
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def convert_to_grayscale(image: ndarray) -> ndarray:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def apply_gaussian_blur(image: ndarray, kernel_size: tuple = (5, 5)) -> ndarray:
        return cv2.GaussianBlur(image, kernel_size, 0)
    
    @staticmethod
    def binary_canny(image: ndarray, threshold: int = 127) -> ndarray:
        ret, binary_image = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY)
        return binary_image

    @staticmethod
    def binary_inv_canny(image: ndarray, threshold: int = 127) -> ndarray:
        ret, binary_image = cv2.threshold(image, threshold, 255, cv2.THRESH_BINARY_INV)
        return binary_image
    
    @staticmethod
    def adaptive_canny(image: ndarray) -> ndarray:
        binary_image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 10 )
        return binary_image