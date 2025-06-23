import cv2
import numpy as np
from typing import Optional, Tuple

def load_and_preprocess_image(image_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load an image and convert it to both BGR and grayscale formats.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Tuple of (BGR image, grayscale image)
        
    Raises:
        ValueError: If the image cannot be loaded
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image, gray

def apply_template_matching(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
    method_id: int
) -> Tuple[float, Tuple[int, int]]:
    """
    Apply template matching with a specific method.
    
    Args:
        screenshot_gray: Grayscale screenshot image
        template_gray: Grayscale template image
        method_id: OpenCV template matching method ID
        
    Returns:
        Tuple of (maximum correlation value, location of maximum)
    """
    result = cv2.matchTemplate(screenshot_gray, template_gray, method_id)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return max_val, max_loc

def scale_image(image: np.ndarray, scale: float) -> np.ndarray:
    """
    Scale an image by a given factor.
    
    Args:
        image: Image to scale
        scale: Scale factor
        
    Returns:
        Scaled image
    """
    new_width = int(image.shape[1] * scale)
    new_height = int(image.shape[0] * scale)
    return cv2.resize(image, (new_width, new_height))
