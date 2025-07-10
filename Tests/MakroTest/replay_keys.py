import time
import json
import os
from pynput.keyboard import Controller, Key
from pynput.mouse import Controller as MouseController, Button


KEY_LOG_FILE = 'actions.log'  # Path to the log file containing key and mouse actions
keyboard = Controller()
mouse = MouseController()

def parse_key(key_str):
    # Handles both Key.<name> and character keys like 'a', '\t', etc.
    if key_str.startswith('Key.'):
        key_name = key_str.split('.', 1)[1]
        return getattr(Key, key_name, key_str)
    if key_str.startswith("'") and key_str.endswith("'"):
        return key_str[1:-1]
    return key_str

def parse_mouse_button(key_str):
    # key_str is like 'mouse_Button.left' or 'mouse_Button.right'
    if key_str.startswith('mouse_Button.'):
        btn = key_str.split('.', 1)[1]
        return getattr(Button, btn, Button.left)
    return None

def read_key_actions(log_file):
    actions = []
    if not os.path.exists(log_file):
        print(f"File {log_file} does not exist.")
        return actions
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                t = entry.get('time')
                if entry.get('type') in ('press', 'release'):
                    key = entry['key']
                    if key.startswith('mouse_Button.'):
                        btn = parse_mouse_button(key)
                        x = entry.get('x')
                        y = entry.get('y')
                        actions.append((entry['type'], btn, t, x, y))
                    else:
                        key_parsed = parse_key(key)
                        actions.append((entry['type'], key_parsed, t))
            except Exception as e:
                print(f"Error parsing line: {line.strip()}\n{e}")
    return actions

def replay_key_actions(actions):
    if not actions:
        print('No actions to replay.')
        return
    # Find the first event time for timing reference
    first_event_time = None
    for act in actions:
        if act[0] in ('press', 'release'):
            first_event_time = act[2]
            break
    if first_event_time is None:
        print('No valid actions to replay.')
        return
    start_time = time.perf_counter()
    for act in actions:
        if act[0] in ('press', 'release'):
            if len(act) == 3:
                # Keyboard event
                action_type, key, t = act
                target_time = (t - first_event_time)
                now = time.perf_counter() - start_time
                sleep_time = max(0, target_time - now)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                if action_type == 'press':
                    keyboard.press(key)
                elif action_type == 'release':
                    keyboard.release(key)
                print(f"{action_type} {key}")
            elif len(act) == 5:
                # Mouse button event
                action_type, btn, t, x, y = act
                target_time = (t - first_event_time)
                now = time.perf_counter() - start_time
                sleep_time = max(0, target_time - now)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                if btn is not None and x is not None and y is not None:
                    mouse.position = (x, y)
                    if action_type == 'press':
                        mouse.press(btn)
                    elif action_type == 'release':
                        mouse.release(btn)
                    print(f"{action_type} {btn} at ({x},{y})")

if __name__ == '__main__':
    actions = read_key_actions(KEY_LOG_FILE)
    print(f'Replaying {len(actions)} actions...')
    replay_key_actions(actions)
    print('Replay finished.')
