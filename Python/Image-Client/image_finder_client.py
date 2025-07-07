import cv2
import numpy as np
import time

class ImageFinderClient:
    # Method options
    METHOD_TEMPLATE = "TEMPLATE"
    METHOD_SIFT = "SIFT"
    METHOD_SURF = "SURF"
    # Set this constant to switch method
    FINDER_METHOD = METHOD_TEMPLATE  # Change to METHOD_SIFT or METHOD_SURF as needed

    # Config
    DEFAULT_THRESHOLD = 0.6
    SCALE_FACTORS = [0.95, 0.975, 1.0, 1.025, 1.05]
    MATCHING_METHODS = [
        (cv2.TM_CCOEFF_NORMED, 1.0),
        (cv2.TM_CCORR_NORMED, 0.9),
    ]
    MATCH_COLOR = (0, 255, 0)
    FONT_SCALE = 0.7
    FONT_THICKNESS = 2
    TEXT_COLOR = (0, 255, 0)
    RECT_THICKNESS = 2
    MIN_TEMPLATE_SIZE = 10

    def __init__(self, threshold=None):
        self.threshold = threshold if threshold is not None else self.DEFAULT_THRESHOLD

    def find(self, icon_path, screenshot_path, region=None):
        if self.FINDER_METHOD == self.METHOD_TEMPLATE:
            return self._find_template(icon_path, screenshot_path, region)
        elif self.FINDER_METHOD == self.METHOD_SIFT:
            return self._find_sift(icon_path, screenshot_path, region)
        elif self.FINDER_METHOD == self.METHOD_SURF:
            return self._find_surf(icon_path, screenshot_path, region)
        else:
            raise ValueError("Unknown finder method")

    def _find_template(self, icon_path, screenshot_path, region=None):
        screenshot = cv2.imread(screenshot_path)
        icon = cv2.imread(icon_path)
        if screenshot is None or icon is None:
            raise ValueError("Could not load one or both images")
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        icon_gray = cv2.cvtColor(icon, cv2.COLOR_BGR2GRAY)
        if region is not None:
            x, y, w, h = region
            search_area = screenshot_gray[y:y+h, x:x+w]
        else:
            x, y, w, h = 0, 0, screenshot_gray.shape[1], screenshot_gray.shape[0]
            search_area = screenshot_gray
        icon_height, icon_width = icon.shape[:2]
        best_match = None
        best_confidence = -1
        for scale in self.SCALE_FACTORS:
            new_width = int(icon_width * scale)
            new_height = int(icon_height * scale)
            if new_width < self.MIN_TEMPLATE_SIZE or new_height < self.MIN_TEMPLATE_SIZE or new_width > w or new_height > h:
                continue
            scaled_icon = cv2.resize(icon_gray, (new_width, new_height))
            for method, weight in self.MATCHING_METHODS:
                result = cv2.matchTemplate(search_area, scaled_icon, method)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                confidence = max_val * weight
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = (max_loc[0] + x, max_loc[1] + y, new_width, new_height, confidence)
        if best_confidence < self.threshold:
            return None
        return best_match

    def _find_sift(self, icon_path, screenshot_path, region=None):
        sift = cv2.SIFT_create()
        img1 = cv2.imread(icon_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            raise ValueError("Could not load one or both images")
        if region is not None:
            x, y, w, h = region
            img2 = img2[y:y+h, x:x+w]
        else:
            x, y = 0, 0
        kp1, des1 = sift.detectAndCompute(img1, None)
        kp2, des2 = sift.detectAndCompute(img2, None)
        if des1 is None or des2 is None:
            return None
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)
        good = [m for m, n in matches if m.distance < 0.75 * n.distance]
        if len(good) > 4:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None:
                h_img, w_img = img1.shape
                pts = np.float32([[0, 0], [0, h_img - 1], [w_img - 1, h_img - 1], [w_img - 1, 0]]).reshape(-1, 1, 2)
                dst = cv2.perspectiveTransform(pts, M)
                x0, y0, w0, h0 = cv2.boundingRect(dst)
                confidence = len(good) / len(matches)
                # Offset by region x/y if region is set
                return (x0 + x, y0 + y, w0, h0, confidence)
        return None

    def _find_surf(self, icon_path, screenshot_path, region=None):
        if not hasattr(cv2, 'xfeatures2d'):
            raise RuntimeError("OpenCV-contrib-python is required for SURF")
        surf = cv2.xfeatures2d.SURF_create()
        img1 = cv2.imread(icon_path, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            raise ValueError("Could not load one or both images")
        if region is not None:
            x, y, w, h = region
            img2 = img2[y:y+h, x:x+w]
        else:
            x, y = 0, 0
        kp1, des1 = surf.detectAndCompute(img1, None)
        kp2, des2 = surf.detectAndCompute(img2, None)
        if des1 is None or des2 is None:
            return None
        bf = cv2.BFMatcher()
        matches = bf.knnMatch(des1, des2, k=2)
        good = [m for m, n in matches if m.distance < 0.75 * n.distance]
        if len(good) > 4:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            if M is not None:
                h_img, w_img = img1.shape
                pts = np.float32([[0, 0], [0, h_img - 1], [w_img - 1, h_img - 1], [w_img - 1, 0]]).reshape(-1, 1, 2)
                dst = cv2.perspectiveTransform(pts, M)
                x0, y0, w0, h0 = cv2.boundingRect(dst)
                confidence = len(good) / len(matches)
                return (x0 + x, y0 + y, w0, h0, confidence)
        return None

    def draw_match(self, screenshot_path, match, output_path=None):
        if match is None:
            return None
        screenshot = cv2.imread(screenshot_path)
        x, y, w, h, conf = match
        cv2.rectangle(screenshot, (x, y), (x + w, y + h), self.MATCH_COLOR, self.RECT_THICKNESS)
        text = f"Confidence: {conf:.2f}"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, self.FONT_SCALE, self.FONT_THICKNESS)
        cv2.rectangle(screenshot, (x, y-25), (x + text_w, y-5), (0, 0, 0), -1)
        cv2.putText(screenshot, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, self.FONT_SCALE, self.TEXT_COLOR, self.FONT_THICKNESS)
        if output_path:
            cv2.imwrite(output_path, screenshot)
        return screenshot

    def run(self, icon_path, screenshot_path, output_path="result.jpg", region=None):
        start_time = time.time()
        match = self.find(icon_path, screenshot_path, region=region)
        process_time = time.time() - start_time
        if match is None:
            print("No match found.")
            return False
        x, y, w, h, confidence = match
        print(f"Best match found at (x={x}, y={y})")
        print(f"Match confidence: {confidence:.2f}")
        print(f"Processing time: {process_time:.3f} seconds")
        self.draw_match(screenshot_path, match, output_path)
        print(f"Result saved to {output_path}")
        return True
