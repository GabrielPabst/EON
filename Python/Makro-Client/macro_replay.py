import os
import time
import json
import threading
from typing import List, Dict, Any, Optional, Tuple

import pyautogui
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

ACTIONS_LOG = "actions.log"
MOUSE_LOG = "mouse_moves.log"

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
        for event in self.events:
            target_time = event['time'] - first_event_time
            now = time.perf_counter() - start_time
            sleep_time = max(0, target_time - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
            if event['type'] == 'move':
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
                        'time': t
                    })
                else:
                    key_parsed = KeyParser.parse_key(key)
                    events.append({
                        'type': entry['type'],
                        'key': key_parsed,
                        'time': t
                    })
        return events

    def replay(self, start_time: float, first_event_time: float):
        for event in self.events:
            target_time = event['time'] - first_event_time
            now = time.perf_counter() - start_time
            sleep_time = max(0, target_time - now)
            if sleep_time > 0:
                time.sleep(sleep_time)
            if event['type'] in ('press', 'release'):
                if 'key' in event:
                    if event['type'] == 'press':
                        self.keyboard.press(event['key'])
                    elif event['type'] == 'release':
                        self.keyboard.release(event['key'])
                elif 'btn' in event and event['btn'] is not None and event['x'] is not None and event['y'] is not None:
                    self.mouse.position = (event['x'], event['y'])
                    if event['type'] == 'press':
                        self.mouse.press(event['btn'])
                    elif event['type'] == 'release':
                        self.mouse.release(event['btn'])

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
        mouse_thread.join()
        keyboard_thread.join()
        print("Replay finished.")

if __name__ == "__main__":
    MacroReplayManager().replay_all()
    MacroReplayManager().replay_all()
