#!/usr/bin/env python3
import sys
import time

# Allow user to choose finder type via command line argument
USAGE = """Usage: python main.py <template_path> <screenshot_path> [finder_type] [sift|surf]"""

# Default to image_finder
FINDER_TYPE_IMAGE = "image"
FINDER_TYPE_SIFT = "sift"
FINDER_TYPE_SURF = "surf"
FINDER_TYPE_ORB = "orb"


def main():
    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)

    template_path = sys.argv[1]
    screenshot_path = sys.argv[2]
    finder_type = sys.argv[3].lower() if len(sys.argv) > 3 else FINDER_TYPE_IMAGE
    sift_surf_method = sys.argv[4].upper() if len(sys.argv) > 4 else "SIFT"

    try:
        start_time = time.time()

        if finder_type == FINDER_TYPE_IMAGE:
            from image_finder.finder import ImageFinder
            finder = ImageFinder()
            match = finder.find_best_match(template_path, screenshot_path)
            draw_func = finder.draw_match
        elif finder_type in [FINDER_TYPE_SIFT, FINDER_TYPE_SURF]:
            from sift_surf_finder.finder import SIFTSURFFinder
            method = "SIFT" if finder_type == FINDER_TYPE_SIFT else "SURF"
            finder = SIFTSURFFinder(method=sift_surf_method)
            match = finder.find(template_path, screenshot_path)
            draw_func = finder.draw_match
        elif finder_type == FINDER_TYPE_ORB:
            from orb_finder.finder import ORBFinder
            finder = ORBFinder()
            match = finder.find(template_path, screenshot_path)
            draw_func = finder.draw_match
        else:
            print(f"Unknown finder type: {finder_type}")
            print(USAGE)
            sys.exit(1)

        process_time = time.time() - start_time

        if match is None:
            print("No match found.")
            sys.exit(0)

        x, y, w, h, confidence = match
        print(f"Best match found at (x={x}, y={y})")
        print(f"Match confidence: {confidence:.2f}")
        print(f"Processing time: {process_time:.3f} seconds")

        output_path = "result.jpg"
        draw_func(screenshot_path, match, output_path)
        print(f"Result saved to {output_path}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
