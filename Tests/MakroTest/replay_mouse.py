import time
import os
from pynput.mouse import Controller
import time
import json
import pyautogui

mouse = Controller()
BIN_FILE = 'mouse_moves.log'  # Path to the JSON log file containing mouse moves

# Read all mouse movement points from the JSON log file
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
                    moves.append((x, y, t))
            except Exception as e:
                print(f"Error parsing line: {line.strip()}\n{e}")
    return moves

def replay_mouse_moves(moves):
    print(moves)
    if not moves:
        print('No mouse moves to replay.')
        return
    # Use high-precision timer for accurate replay
    start_time = time.perf_counter()
    first_event_time = moves[0][2] if moves else 0.0
    for x, y, t in moves:
        # Calculate the absolute time to perform this move
        target_time = (t - first_event_time)
        now = time.perf_counter() - start_time
        sleep_time = max(0, target_time - now)
        if sleep_time > 0:
            time.sleep(sleep_time)
        mouse.position = (x, y)
        
        print(f'Moved mouse to using pynput ({x}, {y})')
        print(f'Current mouse position using pyautogui: {pyautogui.position()}')


if __name__ == '__main__':
    moves = read_mouse_moves(BIN_FILE)
    print(f'Replaying {len(moves)} mouse moves...')
    replay_mouse_moves(moves)
    print('Replay finished.')
