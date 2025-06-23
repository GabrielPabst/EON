#!/usr/bin/env python3
import sys
import time
from image_finder.finder import ImageFinder

def main():
    """Main entry point for the image finder script."""
    if len(sys.argv) != 3:
        print("Usage: python main.py <template_path> <screenshot_path>")
        sys.exit(1)
    
    template_path = sys.argv[1]
    screenshot_path = sys.argv[2]
    
    try:
        # Time the operation
        start_time = time.time()
        
        # Create finder instance and find best match
        finder = ImageFinder()
        match = finder.find_best_match(template_path, screenshot_path)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        if match is None:
            print("No match found.")
            sys.exit(0)
        
        # Print results
        x, y, w, h, confidence = match
        print(f"Best match found at (x={x}, y={y})")
        print(f"Match confidence: {confidence:.2f}")
        print(f"Processing time: {process_time:.3f} seconds")
        
        # Draw and save result
        output_path = "result.jpg"
        finder.draw_match(screenshot_path, match, output_path)
        print(f"Result saved to {output_path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
