import time
import json
import os
import threading
import pyautogui
from pynput.mouse import Controller
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller
from pynput.mouse import Controller as MouseController, Button


KEY_LOG_FILE = 'actions.log'
MOUSE_LOG_FILE = 'mouse_moves.log'

keyboard = KeyboardController()
mouse = Controller()

def parse_key(key_str):
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

def read_mouse_moves(log_file):
    moves = []
    if not os.path.exists(log_file):
        print(f"File {log_file} does not exist.")
        return moves
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if entry.get('type') == 'move':
                    x = entry['x']
                    y = entry['y']
                    t = entry['time']
                    moves.append({'type': 'move', 'x': x, 'y': y, 'time': t})
                elif entry.get('type') == 'scroll':
                    x = entry['x']
                    y = entry['y']
                    dx = entry.get('dx', 0)
                    dy = entry.get('dy', 0)
                    t = entry['time']
                    moves.append({'type': 'scroll', 'x': x, 'y': y, 'dx': dx, 'dy': dy, 'time': t})
            except Exception as e:
                print(f"Error parsing line: {line.strip()}\n{e}")
    return moves

def read_key_actions(log_file):
    actions = []
    if not os.path.exists(log_file):
        print(f"File {log_file} does not exist.")
        return actions
    with open(log_file, 'r') as f:
        for line in f:
            entry = json.loads(line)
            t = entry.get('time')
            if entry.get('type') in ('press', 'release'):
                key = entry['key']
                if key.startswith('mouse_Button.'):
                    btn = parse_mouse_button(key)
                    x = entry.get('x')
                    y = entry.get('y')
                    actions.append({'type': entry['type'], 'btn': btn, 'x': x, 'y': y, 'time': t})
                else:
                    key_parsed = parse_key(key)
                    actions.append({'type': entry['type'], 'key': key_parsed, 'time': t})
    return actions

def replay_mouse_events(mouse_events, start_time, first_event_time):
    for event in mouse_events:
        target_time = event['time'] - first_event_time
        now = time.perf_counter() - start_time
        sleep_time = max(0, target_time - now)
        if sleep_time > 0:
            time.sleep(sleep_time)
        if event['type'] == 'move':
            mouse.position = (event['x'], event['y'])
            #print(f'Moved mouse to using pynput ({event["x"]}, {event["y"]})')
            #print(f'Current mouse position using pyautogui: {pyautogui.position()}')
        elif event['type'] == 'scroll':
            mouse.position = (event['x'], event['y'])
            mouse.scroll(event['dx'], event['dy'])
            print(f'Scrolled at ({event["x"]}, {event["y"]}) by ({event["dx"]}, {event["dy"]})')

def replay_keyboard_events(key_events, start_time, first_event_time):
    for event in key_events:
        target_time = event['time'] - first_event_time
        now = time.perf_counter() - start_time
        sleep_time = max(0, target_time - now)
        if sleep_time > 0:
            time.sleep(sleep_time)
        if event['type'] in ('press', 'release'):
            if 'key' in event:
                # Keyboard event
                if event['type'] == 'press':
                    keyboard.press(event['key'])
                    print(f'Pressed key: {event["key"]}')
                elif event['type'] == 'release':
                    keyboard.release(event['key'])
                    print(f'Released key: {event["key"]}')
            elif 'btn' in event and event['btn'] is not None and event['x'] is not None and event['y'] is not None:
                # Mouse button event
                mouse.position = (event['x'], event['y'])
                if event['type'] == 'press':
                    mouse.press(event['btn'])
                    print(f'Pressed mouse button {event["btn"]} at ({event["x"]}, {event["y"]})')
                elif event['type'] == 'release':
                    mouse.release(event['btn'])
                    print(f'Released mouse button {event["btn"]} at ({event["x"]}, {event["y"]})')

if __name__ == '__main__':
    mouse_events = read_mouse_moves(MOUSE_LOG_FILE)
    key_events = read_key_actions(KEY_LOG_FILE)

    if not mouse_events and not key_events:
        print('No events to replay.')
        exit()

    all_events = sorted(mouse_events + key_events, key=lambda e: e['time'])
    first_event_time = all_events[0]['time']
    start_time = time.perf_counter()

    # Create threads
    mouse_thread = threading.Thread(target=replay_mouse_events, args=(mouse_events, start_time, first_event_time))
    keyboard_thread = threading.Thread(target=replay_keyboard_events, args=(key_events, start_time, first_event_time))

    print(f'Replaying {len(mouse_events)} mouse events and {len(key_events)} keyboard events...')

    # Start threads
    mouse_thread.start()
    keyboard_thread.start()

    # Wait for threads to finish
    mouse_thread.join()
    keyboard_thread.join()

    print('Replay finished.')
