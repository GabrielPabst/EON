import os
import time
import json
import pyautogui
import numpy as np
import cv2
from PIL import Image
from pynput import mouse, keyboard
from config import ACTIONS_LOG, MOUSE_LOG, STOP_KEY

class ActionRecorder:

    def __init__(self, screenshot_radius=20, screenshot_dir="screenshots"):
        self.actions = []
        self.screenshot_radius = screenshot_radius
        self.screenshot_dir = screenshot_dir
        self.key_press_times = {}
        self.mouse_press_times = {}
        os.makedirs(self.screenshot_dir, exist_ok=True)
        open(ACTIONS_LOG, "w").close()
        open(MOUSE_LOG, "w").close()

    def normalize_key(self, key):
        """Normalize key to get raw key without modifiers"""
        try:
            # Handle special keys (Ctrl, Alt, Shift, etc.)
            if hasattr(key, 'name'):
                return "Key." + key.name.lower()
        
            # Handle character keys
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
            
                # Handle control characters (Ctrl+A = \u0001, Ctrl+B = \u0002, etc.)
                if len(char) == 1 and ord(char) <= 31:
                    # Convert control character back to the base letter
                    if ord(char) >= 1 and ord(char) <= 26:
                        return chr(ord(char) + ord('a') - 1)  # \u0001 -> 'a', \u0002 -> 'b', etc.
                    else:
                        # Other control characters, just return as is
                        return char
            
                # Regular character - return lowercase (this handles Unicode chars like äöü properly)
                return char.lower()
        
            # Fallback to string representation for any other cases
            key_str = str(key)
        
            # Remove quotes and prefixes that pynput adds
            if key_str.startswith("'") and key_str.endswith("'"):
                key_str = key_str[1:-1]
            
            # Handle numpad keys with Num Lock on (they come as <97>, <98>, etc.)
            if key_str.startswith('<') and key_str.endswith('>'):
                ascii_code = key_str[1:-1]
                try:
                    code = int(ascii_code)
                    # Map numpad ASCII codes to their intended numpad values
                    numpad_mapping = {
                        97: '1',   # numpad 1
                        98: '2',   # numpad 2  
                        99: '3',   # numpad 3
                        100: '4',  # numpad 4
                        101: '5',  # numpad 5
                        102: '6',  # numpad 6
                        103: '7',  # numpad 7
                        104: '8',  # numpad 8
                        105: '9',  # numpad 9
                        96: '0',   # numpad 0
                        110: '.',  # numpad decimal point
                        111: '/',  # numpad divide
                        106: '*',  # numpad multiply
                        109: '-',  # numpad subtract
                        107: '+',  # numpad add
                        13: 'Key.enter'  # numpad enter
                    }
                    
                    if code in numpad_mapping:
                        return numpad_mapping[code]
                    else:
                        # For other codes, convert to character if printable
                        return chr(code) if 32 <= code <= 126 else key_str
                except ValueError:
                    pass
        
            return key_str.lower()
        
        except Exception:
            # Fallback for any unexpected key format
            return str(key).replace("'", "").lower()

    def on_click(self, x, y, button, pressed):
        button_str = str(button)
        now = self._current_time()
        key = f"mouse_{button_str}"
        if pressed:
            screenshot = self._take_screenshot(x, y)
            self.mouse_press_times[key] = now
            action = {
                'type': 'press',
                'key': key,
                'x': x,
                'y': y,
                'time': now,
                'screenshot': screenshot
            }
            self.actions.append(action)
            self._log_action(action)
        else:
            action = {
                'type': 'release',
                'key': key,
                'x': x,
                'y': y,
                'time': now,
                'screenshot': None
            }
            self.actions.append(action)
            self._log_action(action)

    def on_press(self, key):
        key_str = self.normalize_key(key)
        now = self._current_time()
        if key_str == STOP_KEY:
            return False
        if key_str not in self.key_press_times:
            self.key_press_times[key_str] = now
            action = {
                'type': 'press',
                'key': key_str,
                'x': None,
                'y': None,
                'time': now,
                'screenshot': None
            }
            self.actions.append(action)
            self._log_action(action)
        

    def on_release(self, key):
        key_str = self.normalize_key(key)
        now = self._current_time()
        if key_str in self.key_press_times:
            del self.key_press_times[key_str]
        action = {
            'type': 'release',
            'key': key_str,
            'x': None,
            'y': None,
            'time': now,
            'screenshot': None
        }
        self.actions.append(action)
        self._log_action(action)

    def on_move(self, x, y):
        now = self._current_time()
        action = {
            'type': 'move',
            'x': x,
            'y': y,
            'time': now
        }
        with open(MOUSE_LOG, "a", encoding='utf-8') as f:
            f.write(json.dumps(action, ensure_ascii=False) + "\n")

    def on_scroll(self, x, y, dx, dy):
        now = self._current_time()
        action = {
            'type': 'scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'time': now
        }
        with open(MOUSE_LOG, "a", encoding='utf-8') as f:
            f.write(json.dumps(action, ensure_ascii=False) + "\n")



    def _take_screenshot(self, x, y):
        # Take a larger screenshot around the point
        left = max(0, x - self.screenshot_radius * 3)
        top = max(0, y - self.screenshot_radius * 3)
        width = self.screenshot_radius * 6
        height = self.screenshot_radius * 6
        
        print(f"Taking screenshot with region ({left}, {top}, {width}, {height})")
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        
        # Convert PIL to OpenCV format
        img_array = np.array(screenshot)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Find the bounding box of the object at center
        crop_coords = self._find_object_bounds_cv(img_cv, 
                                                center_x=width // 2, 
                                                center_y=height // 2)
        
        if crop_coords:
            # Crop to the detected bounds
            crop_left, crop_top, crop_right, crop_bottom = crop_coords
            screenshot = screenshot.crop((crop_left, crop_top, crop_right, crop_bottom))
            print(f"Cropped to bounds: ({crop_left}, {crop_top}, {crop_right}, {crop_bottom})")
        else:
            print("Could not detect object bounds, using full screenshot")
        
        # Save the cropped screenshot
        filename = os.path.join(self.screenshot_dir, 
                            f"screenshot_{int(time.time()*1000)}_{x}_{y}.png")
        screenshot.save(filename)
        print(f"Saved screenshot to {filename}")
        
        return filename

    def _find_object_bounds_cv(self, img_cv, center_x, center_y):
        """
        Find the bounding box of an object at the center point using OpenCV.
        Uses multiple detection methods for robustness.
        
        Args:
            img_cv: OpenCV image (BGR format)
            center_x, center_y: center point coordinates in the image
        
        Returns:
            Tuple of (left, top, right, bottom) or None if detection fails
        """
        height, width = img_cv.shape[:2]
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Edge detection with contours (best for icons and buttons)
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate edges to connect nearby components
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find the contour that contains the center point
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if (x <= center_x <= x + w) and (y <= center_y <= y + h):
                # Add padding
                padding = 5
                left = max(0, x - padding)
                top = max(0, y - padding)
                right = min(width, x + w + padding)
                bottom = min(height, y + h + padding)
                
                return (left, top, right, bottom)
        
        # Method 2: Adaptive thresholding (good for text)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                    cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find contours on thresholded image
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if (x <= center_x <= x + w) and (y <= center_y <= y + h):
                # Add padding
                padding = 5
                left = max(0, x - padding)
                top = max(0, y - padding)
                right = min(width, x + w + padding)
                bottom = min(height, y + h + padding)
                
                return (left, top, right, bottom)
        
        # Method 3: Flood fill from center (fallback for uniform objects)
        mask = np.zeros((height + 2, width + 2), np.uint8)
        cv2.floodFill(gray, mask, (center_x, center_y), 255, 
                    loDiff=20, upDiff=20, flags=4 | (255 << 8))
        
        # Get bounding box from flood fill mask
        mask = mask[1:-1, 1:-1]  # Remove padding
        coords = cv2.findNonZero(mask)
        
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            padding = 5
            left = max(0, x - padding)
            top = max(0, y - padding)
            right = min(width, x + w + padding)
            bottom = min(height, y + h + padding)
            
            # Validate bounds
            if right - left >= 5 and bottom - top >= 5:
                return (left, top, right, bottom)
        
        return None

    def _log_action(self, action):
        if 'duration' in action and (action['duration'] is None or action['duration'] == 0.0):
            return
        with open(ACTIONS_LOG, "a", encoding='utf-8') as f:
            f.write(json.dumps(action, ensure_ascii=False) + "\n")

    @staticmethod
    def _current_time():
        return time.time()

class RecorderClient:
    def __init__(self):
        self.recorder = ActionRecorder()

    def run(self):
        print("Recording started. Press "+STOP_KEY+" to stop.")
        with keyboard.Listener(
            on_press=self.recorder.on_press,
            on_release=self.recorder.on_release
        ) as keyboard_listener, mouse.Listener(
            on_click=self.recorder.on_click,
            on_move=self.recorder.on_move,
            on_scroll=self.recorder.on_scroll
        ) as mouse_listener:
            keyboard_listener.join()
            mouse_listener.stop()
        print("Recording stopped.")

if __name__ == "__main__":
    RecorderClient().run()