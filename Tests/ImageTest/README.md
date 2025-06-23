# Image Finder Documentation

## Project Overview

The Image Finder is a Python-based tool designed to locate a template image (like an icon) within a larger screenshot. It's particularly robust, able to handle slight variations in size and appearance of the template image.

## Project Structure

```
image_finder/
├── __init__.py        # Package initialization
├── constants.py       # Configuration constants
├── finder.py         # Main ImageFinder class
└── utils/
    └── image_processing.py  # Image processing utilities
main.py              # Command-line interface
```

## Detailed Code Documentation

### constants.py

This file contains all the configuration constants used throughout the project:

```python
DEFAULT_THRESHOLD = 0.6  # Default confidence threshold for matches
SCALE_FACTORS = [0.95, 0.975, 1.0, 1.025, 1.05]  # Different scales to try
MATCHING_METHODS = [  # Template matching methods with weights
    ('TM_CCOEFF_NORMED', 1.0),  # Best for exact matches
    ('TM_CCORR_NORMED', 0.9),   # Better with intensity variations
]
```

### utils/image_processing.py

Contains utility functions for image processing:

1. `load_and_preprocess_image(image_path)`
   
   - Loads an image from path
   - Converts it to grayscale for better matching
   - Returns both color and grayscale versions

2. `apply_template_matching(screenshot_gray, template_gray, method_id)`
   
   - Applies OpenCV's template matching
   - Returns the best match location and confidence

3. `scale_image(image, scale)`
   
   - Resizes an image by a given scale factor
   - Used for multi-scale template matching

### finder.py

The main `ImageFinder` class that implements the image finding functionality:

1. `__init__(threshold)`
   
   - Initializes with configurable confidence threshold
   - Sets up matching method mapping

2. `find_best_match(template_path, screenshot_path)`
   
   - Main matching function
   - Steps:
     1. Loads and preprocesses both images
     2. Tries different scales of the template
     3. Applies multiple matching methods
     4. Returns the best match found

3. `draw_match(screenshot_path, match, output_path)`
   
   - Visualizes the match result
   - Draws a rectangle around the match
   - Shows confidence score
   - Saves or returns the result image

### main.py

Command-line interface for the tool:

```python
Usage: python main.py <template_path> <screenshot_path>
```

Features:

- Measures and reports processing time
- Prints match location and confidence
- Saves visual result to "result.jpg"

## How It Works

1. **Multi-scale Matching**
   
   - Tries different sizes of the template (95% to 105%)
   - Helps find matches when icon size varies

2. **Multiple Matching Methods**
   
   - Uses complementary matching algorithms
   - Weighted combination for better accuracy
   - TM_CCOEFF_NORMED: Good for exact matches
   - TM_CCORR_NORMED: Better with lighting changes

3. **Preprocessing**
   
   - Converts images to grayscale
   - Makes matching more robust to color variations

4. **Visualization**
   
   - Green rectangle around matches
   - Confidence score display
   - Black background for text visibility

## Performance Considerations

- Grayscale conversion reduces processing load
- Skip invalid template sizes early
- Efficient numpy operations for matching
- Balance between accuracy and speed through:
  - Number of scales tried
  - Number of matching methods
  - Confidence threshold

## Future Expansion

The project is structured for easy expansion:

1. **New Features**
   
   - Add new matching methods in constants.py
   - Implement new preprocessing in image_processing.py
   - Add new visualization options

2. **Configuration**
   
   - All constants in one place
   - Easy to modify behavior

3. **New Utilities**
   
   - Add new modules in utils/
   - Keep code modular and reusable

4. **Possible Enhancements**
   
   - GPU acceleration
   - More preprocessing options
   - Multiple template matching
   - Real-time video processing
   - API endpoint implementation
   - GUI interface

## Error Handling

- Proper error messages for file loading
- Size validation for templates
- Confidence threshold checking
- Exception handling in main script
