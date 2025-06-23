import cv2
import numpy as np
import time

def find_icon_in_screenshot(icon_path, screenshot_path, threshold=0.6):
    """
    Find the best matching location of an icon within a screenshot,
    with tolerance for slight variations.
    
    Args:
        icon_path (str): Path to the icon image
        screenshot_path (str): Path to the screenshot image
        threshold (float): Base matching threshold (0-1)
    
    Returns:
        tuple: (x, y, width, height, confidence) of the best match, or None if no match found
    """
    # Read the images
    screenshot = cv2.imread(screenshot_path)
    icon = cv2.imread(icon_path)
    
    if screenshot is None or icon is None:
        raise ValueError("Could not load one or both images")
    
    # Convert images to grayscale for more robust matching
    screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    icon_gray = cv2.cvtColor(icon, cv2.COLOR_BGR2GRAY)
    
    # Store original dimensions
    icon_height, icon_width = icon.shape[:2]
    best_match = None
    best_confidence = -1
    
    # Scale factors to try (both smaller and larger)
    scales = [0.95, 0.975, 1.0, 1.025, 1.05]
    
    # Try different scales of the icon
    for scale in scales:
        # Calculate new dimensions
        new_width = int(icon_width * scale)
        new_height = int(icon_height * scale)
        
        # Skip if scaled size is too small or too large
        if new_width < 10 or new_height < 10 or \
           new_width > screenshot.shape[1] or new_height > screenshot.shape[0]:
            continue
        
        # Resize icon
        scaled_icon = cv2.resize(icon_gray, (new_width, new_height))
        
        # Apply template matching with multiple methods
        results = []
        methods = [
            (cv2.TM_CCOEFF_NORMED, 1.0),  # Exact matching
            (cv2.TM_CCORR_NORMED, 0.9),   # More tolerant to intensity changes
        ]
        
        for method, weight in methods:
            result = cv2.matchTemplate(screenshot_gray, scaled_icon, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            results.append((max_val * weight, max_loc))
        
        # Combine results from different methods
        for confidence, loc in results:
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = (loc[0], loc[1], new_width, new_height, confidence)
    
    # If no good match found
    if best_confidence < threshold:
        return None
    
    return best_match

def draw_match(screenshot_path, match, output_path=None):
    """
    Draw a rectangle and information about the match on the screenshot.
    
    Args:
        screenshot_path (str): Path to the screenshot
        match (tuple): (x, y, width, height, confidence) tuple
        output_path (str): Path to save the marked image (optional)
    """
    if match is None:
        return None
        
    screenshot = cv2.imread(screenshot_path)
    x, y, w, h, conf = match
    
    # Draw rectangle around match
    cv2.rectangle(screenshot, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # Draw confidence value with background for better visibility
    text = f"Confidence: {conf:.2f}"
    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.rectangle(screenshot, (x, y-25), (x + text_w, y-5), (0, 0, 0), -1)
    cv2.putText(screenshot, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    if output_path:
        cv2.imwrite(output_path, screenshot)
    
    return screenshot

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python test.py <icon_path> <screenshot_path>")
        sys.exit(1)
    
    icon_path = sys.argv[1]
    screenshot_path = sys.argv[2]
    
    try:
        # Time the operation
        start_time = time.time()
        
        # Find best match
        match = find_icon_in_screenshot(icon_path, screenshot_path)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        if match is None:
            print("No match found.")
            sys.exit(0)
        
        x, y, w, h, confidence = match
        print(f"Best match found at (x={x}, y={y})")
        print(f"Match confidence: {confidence:.2f}")
        print(f"Processing time: {process_time:.3f} seconds")
        
        # Draw and save result
        output_path = "result.jpg"
        draw_match(screenshot_path, match, output_path)
        print(f"Result saved to {output_path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)