import os
import time
import json
import threading
from typing import List, Dict, Any, Optional, Tuple

import pyautogui
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
from image_finder_client import ImageFinderClient
import cv2

ACTIONS_LOG = "actions.log"
MOUSE_LOG = "mouse_moves.log"

# Thread-safe mouseEventOffset
mouseEventOffset = (0, 0)
mouseEventOffsetLock = threading.Lock()

def get_mouse_event_offset():
    with mouseEventOffsetLock:
        return mouseEventOffset

def set_mouse_event_offset(offset):
    global mouseEventOffset
    with mouseEventOffsetLock:
        mouseEventOffset = offset

mouseEvent = threading.Event()

class FileUtils:
    @staticmethod
    def read_json_lines(filepath: str) -> List[Dict[str, Any]]:
        if not os.path.exists(filepath):
            print(f"File {filepath} does not exist.")
            return []
        with open(filepath, "r") as f:
            return [json.loads(line) for line in f if line.strip()]

class KeyParser:
    @staticmethod
    def parse_key(key_str: str):
        if key_str.startswith('Key.'):
            key_name = key_str.split('.', 1)[1]
            return getattr(Key, key_name, key_str)
        if key_str.startswith("'") and key_str.endswith("'"):
            return key_str[1:-1]
        return key_str

    @staticmethod
    def parse_mouse_button(key_str: str):
        if key_str.startswith('mouse_Button.'):
            btn = key_str.split('.', 1)[1]
            return getattr(Button, btn, Button.left)
        return None

class MouseReplay:
    def __init__(self, mouse_log: str = MOUSE_LOG):
        self.mouse_log = mouse_log
        self.mouse = MouseController()
        self.events = self._load_events()

    def _load_events(self) -> List[Dict[str, Any]]:
        events = []
        for entry in FileUtils.read_json_lines(self.mouse_log):
            if entry.get('type') == 'move':
                events.append({
                    'type': 'move',
                    'x': entry['x'],
                    'y': entry['y'],
                    'time': entry['time']
                })
            elif entry.get('type') == 'scroll':
                events.append({
                    'type': 'scroll',
                    'x': entry['x'],
                    'y': entry['y'],
                    'dx': entry.get('dx', 0),
                    'dy': entry.get('dy', 0),
                    'time': entry['time']
                })
        return events

    def replay(self, start_time: float, first_event_time: float):
        global mouseEventOffset
        for event in self.events:
            target_time = event['time'] - first_event_time
            now = time.perf_counter() - start_time
            sleep_time = max(0, target_time - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
            if event['type'] == 'move':
                offset = get_mouse_event_offset()
                event['x'] += offset[0]
                event['y'] += offset[1]
                print("offset", offset)
                print(f"Moving mouse to ({event['x']}, {event['y']})")
                self.mouse.position = (event['x'], event['y'])
            elif event['type'] == 'scroll':
                self.mouse.position = (event['x'], event['y'])
                self.mouse.scroll(event['dx'], event['dy'])

class KeyboardReplay:
    def __init__(self, actions_log: str = ACTIONS_LOG):
        self.actions_log = actions_log
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        self.events = self._load_events()

    def _load_events(self) -> List[Dict[str, Any]]:
        events = []
        for entry in FileUtils.read_json_lines(self.actions_log):
            t = entry.get('time')
            if entry.get('type') in ('press', 'release'):
                key = entry['key']
                if key.startswith('mouse_Button.'):
                    btn = KeyParser.parse_mouse_button(key)
                    x = entry.get('x')
                    y = entry.get('y')
                    events.append({
                        'type': entry['type'],
                        'btn': btn,
                        'x': x,
                        'y': y,
                        'time': t,
                        'screenshot': entry.get('screenshot')
                    })
                else:
                    key_parsed = KeyParser.parse_key(key)
                    events.append({
                        'type': entry['type'],
                        'key': key_parsed,
                        'time': t
                    })
        return events

    
    def _take_screenshot(self):
        filename = os.path.join("screenshots", f"screenshot_.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        return filename
    
    def replay(self, start_time: float, first_event_time: float):
        global mouseEventOffset
        for event in self.events:
            target_time = event['time'] - first_event_time
            now = time.perf_counter() - start_time
            sleep_time = max(0, target_time - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
            if event['type'] in ('press', 'release'):
                print(f"Replaying event: {event}")
                #For keyboard events
                if 'key' in event: 
                    if event['type'] == 'press':
                        self.keyboard.press(event['key'])
                    elif event['type'] == 'release':
                        self.keyboard.release(event['key'])
                #For mouse button events
                elif 'btn' in event and event['btn'] is not None and event['x'] is not None and event['y'] is not None:
                    mouseScreenshotFinder = MouseScreenshotFinder()
                    if event['type'] == 'press':
                        match = mouseScreenshotFinder.find_click_position(
                            icon_path=event.get('screenshot', ''),
                            screenshot_path=self._take_screenshot(),
                            click_x=event['x'],
                            click_y=event['y']
                        )
                        if match is not None:
                            if match[0] != event['x'] or match[1] != event['y']:
                                print(f"Click position adjusted from ({event['x']}, {event['y']}) to {match[0]}, {match[1]}")
                                set_mouse_event_offset((match[0] - event['x'], match[1] - event['y']))
                            print(f"Click position found: {match}")
                            self.mouse.position = (match[0], match[1])
                            self.mouse.press(event['btn'])
                        else:
                            ValueError(f"Could not find click position for {event['screenshot']} at ({event['x']}, {event['y']})")
                    elif event['type'] == 'release':
                        offset = get_mouse_event_offset()
                        event['x'] += offset[0]
                        event['y'] += offset[1]
                        print("offset", offset)
                        print(f"Releasing mouse button at ({event['x']}, {event['y']})")
                        self.mouse.release(event['btn'])
                        set_mouse_event_offset((0, 0))

class MouseScreenshotFinder:
    CONFIDENCE_THRESHOLD = 0.8
    MAX_ATTEMPTS = 3
    RETRY_DELAY = 2.0  # seconds
    SEARCH_REGION_SIZE = 100  # pixels (width/height of region around click)

    def __init__(self, finder: Optional[ImageFinderClient] = None):
        self.finder = finder if finder is not None else ImageFinderClient()

    def find_click_position(self, icon_path: str, screenshot_path: str, click_x: int, click_y: int) -> Optional[Tuple[int, int, int, int, float]]:
        attempt = 0
        screenshot = cv2.imread(screenshot_path)
        if screenshot is None:
            print("Could not load screenshot.")
            return None
        h, w = screenshot.shape[:2]
        # Define region around click
        region_x = max(0, click_x - self.SEARCH_REGION_SIZE // 2)
        region_y = max(0, click_y - self.SEARCH_REGION_SIZE // 2)
        region_w = min(self.SEARCH_REGION_SIZE, w - region_x)
        region_h = min(self.SEARCH_REGION_SIZE, h - region_y)
        region = (region_x, region_y, region_w, region_h)

        while attempt < self.MAX_ATTEMPTS:
            # 1. Try small region
            print(icon_path, screenshot_path, region)
            match = self.finder.run(icon_path, screenshot_path, region=region, output_path="" )
            if match is not None and match[-1] >= self.CONFIDENCE_THRESHOLD:
                print(f"Found match in region on attempt {attempt+1} with confidence {match[-1]:.2f}")
                print(f"Match details: {match}")
                return match
            # 2. Try whole screenshot
            match = self.finder.run(icon_path, screenshot_path, region=None,  output_path="")
            if match is not None and match[-1] >= self.CONFIDENCE_THRESHOLD:
                print(f"Found match in full screenshot on attempt {attempt+1} with confidence {match[-1]:.2f}")
                print(f"Match details: {match}")
                return match
            # 3. Wait and retry
            print(f"No confident match found on attempt {attempt+1}. Retrying in {self.RETRY_DELAY}s...")
            attempt += 1
            time.sleep(self.RETRY_DELAY)
        print("Aborted: No match found after maximum attempts.")
        return None

class MacroReplayManager:
    def __init__(self, mouse_log: str = MOUSE_LOG, actions_log: str = ACTIONS_LOG):
        self.mouse_replay = MouseReplay(mouse_log)
        self.keyboard_replay = KeyboardReplay(actions_log)
        
    def replay_all(self):
        all_events = sorted(
            self.mouse_replay.events + self.keyboard_replay.events,
            key=lambda e: e['time']
        )
        if not all_events:
            print("No events to replay.")
            return
        first_event_time = all_events[0]['time']
        start_time = time.perf_counter()

        mouse_thread = threading.Thread(
            target=self.mouse_replay.replay, args=(start_time, first_event_time)
        )
        keyboard_thread = threading.Thread(
            target=self.keyboard_replay.replay, args=(start_time, first_event_time)
        )

        print(f"Replaying {len(self.mouse_replay.events)} mouse events and {len(self.keyboard_replay.events)} keyboard events...")
        mouse_thread.start()
        keyboard_thread.start()
        print("Replay finished.")
