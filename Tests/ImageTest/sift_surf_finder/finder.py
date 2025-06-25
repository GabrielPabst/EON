import cv2
import numpy as np
from typing import Optional, Tuple

class SIFTSURFFinder:
    """
    A class for finding template images within larger screenshots using SIFT and SURF algorithms.
    """
    def __init__(self, method: str = 'SIFT', ratio_thresh: float = 0.75):
        """
        Args:
            method: 'SIFT' or 'SURF'
            ratio_thresh: Lowe's ratio test threshold
        """
        if method.upper() == 'SIFT':
            self.detector = cv2.SIFT_create()
        elif method.upper() == 'SURF':
            self.detector = cv2.xfeatures2d.SURF_create()
        else:
            raise ValueError("Method must be 'SIFT' or 'SURF'")
        self.ratio_thresh = ratio_thresh

    def find(self, template_path: str, screenshot_path: str) -> Optional[Tuple[int, int, int, int, float]]:
        img1 = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            return None
        kp1, des1 = self.detector.detectAndCompute(img1, None)
        kp2, des2 = self.detector.detectAndCompute(img2, None)
        if des1 is None or des2 is None:
            return None
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)
        good = []
        for m, n in matches:
            if m.distance < self.ratio_thresh * n.distance:
                good.append(m)
        if len(good) > 4:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None:
                h, w = img1.shape
                pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
                dst = cv2.perspectiveTransform(pts, M)
                x, y, w, h = cv2.boundingRect(dst)
                confidence = len(good) / len(matches)
                return (x, y, w, h, confidence)
        return None

    @staticmethod
    def draw_match(screenshot_path: str, match: Optional[Tuple[int, int, int, int, float]], output_path: Optional[str] = None) -> Optional[np.ndarray]:
        if match is None:
            return None
        screenshot = cv2.imread(screenshot_path)
        x, y, w, h, conf = match
        cv2.rectangle(screenshot, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = f"Confidence: {conf:.2f}"
        cv2.putText(screenshot, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if output_path:
            cv2.imwrite(output_path, screenshot)
        return screenshot
