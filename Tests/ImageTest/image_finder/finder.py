import cv2
import numpy as np
from typing import Optional, Tuple, Dict

from .constants import (
    DEFAULT_THRESHOLD,
    SCALE_FACTORS,
    MATCHING_METHODS,
    MIN_TEMPLATE_SIZE,
    MATCH_COLOR,
    FONT_SCALE,
    FONT_THICKNESS,
    TEXT_COLOR,
    RECT_THICKNESS
)
from .utils.image_processing import (
    load_and_preprocess_image,
    apply_template_matching,
    scale_image
)

class ImageFinder:
    """
    A class for finding template images within larger screenshots,
    with support for variations in size and appearance.
    """
    
    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        """
        Initialize the ImageFinder.
        
        Args:
            threshold: Minimum confidence threshold for matches (0-1)
        """
        self.threshold = threshold
        self._method_map = {
            'TM_CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'TM_CCORR_NORMED': cv2.TM_CCORR_NORMED
        }
    
    def find_best_match(
        self,
        template_path: str,
        screenshot_path: str
    ) -> Optional[Tuple[int, int, int, int, float]]:
        """
        Find the best matching location of a template within a screenshot.
        
        Args:
            template_path: Path to the template image file
            screenshot_path: Path to the screenshot image file
            
        Returns:
            Tuple of (x, y, width, height, confidence) or None if no match found
        """
        # Load and preprocess images
        screenshot_bgr, screenshot_gray = load_and_preprocess_image(screenshot_path)
        template_bgr, template_gray = load_and_preprocess_image(template_path)
        
        # Store original dimensions
        template_height, template_width = template_bgr.shape[:2]
        best_match = None
        best_confidence = -1
        
        # Try different scales of the template
        for scale in SCALE_FACTORS:
            # Calculate new dimensions
            new_width = int(template_width * scale)
            new_height = int(template_height * scale)
            
            # Skip if scaled size is too small or too large
            if (new_width < MIN_TEMPLATE_SIZE or
                new_height < MIN_TEMPLATE_SIZE or
                new_width > screenshot_bgr.shape[1] or
                new_height > screenshot_bgr.shape[0]):
                continue
            
            # Scale template
            scaled_template = scale_image(template_gray, scale)
            
            # Try different matching methods
            for method_name, weight in MATCHING_METHODS:
                method_id = self._method_map[method_name]
                confidence, location = apply_template_matching(
                    screenshot_gray,
                    scaled_template,
                    method_id
                )
                
                weighted_confidence = confidence * weight
                if weighted_confidence > best_confidence:
                    best_confidence = weighted_confidence
                    best_match = (*location, new_width, new_height, weighted_confidence)
        
        return best_match if best_confidence >= self.threshold else None
    
    @staticmethod
    def draw_match(
        screenshot_path: str,
        match: Optional[Tuple[int, int, int, int, float]],
        output_path: Optional[str] = None
    ) -> Optional[np.ndarray]:
        """
        Draw the match result on the screenshot.
        
        Args:
            screenshot_path: Path to the screenshot image
            match: Match data (x, y, width, height, confidence)
            output_path: Optional path to save the result image
            
        Returns:
            The result image with the match drawn, or None if no match
        """
        if match is None:
            return None
            
        screenshot = cv2.imread(screenshot_path)
        x, y, w, h, conf = match
        
        # Draw rectangle around match
        cv2.rectangle(
            screenshot,
            (x, y),
            (x + w, y + h),
            MATCH_COLOR,
            RECT_THICKNESS
        )
        
        # Draw confidence value with background
        text = f"Confidence: {conf:.2f}"
        (text_w, text_h), _ = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            FONT_SCALE,
            FONT_THICKNESS
        )
        cv2.rectangle(
            screenshot,
            (x, y-25),
            (x + text_w, y-5),
            (0, 0, 0),
            -1
        )
        cv2.putText(
            screenshot,
            text,
            (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            FONT_SCALE,
            TEXT_COLOR,
            FONT_THICKNESS
        )
        
        if output_path:
            cv2.imwrite(output_path, screenshot)
        
        return screenshot
