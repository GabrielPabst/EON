import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Makro-Client')))
from image_finder_client import ImageFinderClient

if __name__ == "__main__":
    # Set the method you want to use (optional, defaults to TEMPLATE)
    # ImageFinderClient.FINDER_METHOD = ImageFinderClient.METHOD_SIFT
    # ImageFinderClient.FINDER_METHOD = ImageFinderClient.METHOD_SURF

    icon_path = "test-assets/icon.jpg"
    screenshot_path = "test-assets/screenshot.jpg"
    output_path = "result.jpg"
    

    finder = ImageFinderClient()
    
    success = finder.run(icon_path, screenshot_path, output_path)
    if success:
        print("Icon found and result image saved.")
    else:
        print("Icon not found.")

# from image_finder_client import ImageFinderClient
#
# if __name__ == "__main__":
#     icon_path = "path/to/icon.jpg"
#     screenshot_path = "path/to/screenshot.jpg"
#     output_path = "result.jpg"
#     region = (100, 200, 300, 400)  # x, y, width, height
#
#     finder = ImageFinderClient()
#     # Only search in the specified region of the screenshot
#     finder.run(icon_path, screenshot_path, output_path, region=region)
