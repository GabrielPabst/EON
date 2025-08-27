import os
import time
import json
import pyautogui
from pynput import mouse, keyboard

class ActionRecorder:
    ACTIONS_LOG = "actions.log"
    MOUSE_LOG = "mouse_moves.log"

    def __init__(self, screenshot_radius=20, screenshot_dir="screenshots"):
        self.actions = []
        self.screenshot_radius = screenshot_radius
        self.screenshot_dir = screenshot_dir
        self.key_press_times = {}
        self.mouse_press_times = {}
        os.makedirs(self.screenshot_dir, exist_ok=True)
        open(self.ACTIONS_LOG, "w").close()
        open(self.MOUSE_LOG, "w").close()

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
        # Stop recording on 'q'
        if key_str == 'q':
            return False

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
        with open(self.MOUSE_LOG, "a", encoding='utf-8') as f:
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
        with open(self.MOUSE_LOG, "a", encoding='utf-8') as f:
            f.write(json.dumps(action, ensure_ascii=False) + "\n")

    def _take_screenshot(self, x, y):
        left = max(0, x - self.screenshot_radius)
        top = max(0, y - self.screenshot_radius)
        width = self.screenshot_radius * 2
        height = self.screenshot_radius * 2
        filename = os.path.join(self.screenshot_dir, f"screenshot_{int(time.time()*1000)}_{x}_{y}.png")
        print(f"Taking screenshot at {filename} with region ({left}, {top}, {width}, {height})")
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screenshot.save(filename)
        return filename

    def _log_action(self, action):
        if 'duration' in action and (action['duration'] is None or action['duration'] == 0.0):
            return
        with open(self.ACTIONS_LOG, "a", encoding='utf-8') as f:
            f.write(json.dumps(action, ensure_ascii=False) + "\n")

    @staticmethod
    def _current_time():
        return time.time()

class RecorderClient:
    def __init__(self):
        self.recorder = ActionRecorder()

    def run(self):
        print("Recording started. Press 'q' to stop.")
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