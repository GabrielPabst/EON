import pyautogui
import os
import time
from pynput import keyboard
import json

class ActionRecorder:
    def __init__(self, screenshot_radius=50, screenshot_dir="screenshots"):
        self.actions = []
        self.screenshot_radius = screenshot_radius
        self.screenshot_dir = screenshot_dir
        self.key_press_times = {}
        self.mouse_press_times = {}  # Track mouse button press times
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def on_click(self, x, y, button, pressed):
        button_str = str(button)
        now = self.current_time()
        key = f"mouse_{button_str}"
        if pressed:
            self.mouse_press_times[key] = now
        else:
            start_time = self.mouse_press_times.pop(key, None)
            screenshot = self.take_screenshot(x, y)
            action = {
                'type': 'click',
                'key': key,
                'x': x,
                'y': y,
                'time': now,
                'screenshot': screenshot
            }
            self.actions.append(action)
            self.log_action(action)

    def on_press(self, key):
        key_str = str(key)
        now = self.current_time()
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
            self.log_action(action)
        if key == keyboard.KeyCode.from_char('q'):
            return False

    def on_release(self, key):
        key_str = str(key)
        now = self.current_time()
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
        self.log_action(action)

    def on_move(self, x, y):
        now = self.current_time()
        action = {
            'type': 'move',
            'x': x,
            'y': y,
            'time': now
        }
        with open("mouse_moves.log", "a") as f:
            f.write(json.dumps(action) + "\n")

    def on_scroll(self, x, y, dx, dy):
        now = self.current_time()
        action = {
            'type': 'scroll',
            'x': x,
            'y': y,
            'dx': dx,
            'dy': dy,
            'time': now
        }
        with open("mouse_moves.log", "a") as f:
            f.write(json.dumps(action) + "\n")

    def take_screenshot(self, x, y):
        left = max(x - self.screenshot_radius, 0)
        top = max(y - self.screenshot_radius, 0)
        width = self.screenshot_radius * 2
        height = self.screenshot_radius * 2
        filename = f"{self.screenshot_dir}/screenshot_{int(time.time()*1000)}_{x}_{y}.png"
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screenshot.save(filename)
        return filename

    def log_action(self, action):
        # Only log if duration is not present or is > 0
        if 'duration' in action and (action['duration'] is None or action['duration'] == 0.0):
            return
        with open("actions.log", "a") as f:
            f.write(json.dumps(action) + "\n")

    def current_time(self):
        from time import time
        return time()