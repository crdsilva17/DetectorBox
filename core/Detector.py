
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

    def detect_circles(self, image: ndarray, dp=1.2, minDist=90, param1=100, adaptive=False, 
                       param2=35, minRadius=30, maxRadius=40, size=(640, 480)) -> tuple[ndarray, list]:
        if not isinstance(image, ndarray):
            raise TypeError("Input image must be a numpy ndarray.")
        image_resized = cv2.resize(image, (640, 480), interpolation=cv2.INTER_LINEAR)
        image_gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)
        image_gray = cv2.medianBlur(image_gray, 5)
        if adaptive:
            image_gray = self.adaptive_canny(image_gray)
        else:
            image_gray = cv2.Canny(image_gray, 50, 150)
        cv2.imshow("Canny Image", image_gray)
        circles = cv2.HoughCircles(image_gray, cv2.HOUGH_GRADIENT, dp, minDist,
                                   param1=param1, param2=param2, minRadius=minRadius, maxRadius=maxRadius)
        output = image_resized.copy()
        if circles is not None:
            circles = circles[0, :, :].astype(int)
            for (x, y, r) in circles:
                cv2.circle(output, (x, y), r, (0, 255, 0), 4)
        # output = cv2.resize(output, (640, 480), interpolation=cv2.INTER_LINEAR)
        return output, circles.tolist() if circles is not None else []
    