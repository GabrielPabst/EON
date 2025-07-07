import pyautogui
import time

# Set the start and end positions (x, y)
start_pos = (100, 100)  # Change as needed
end_pos = (500, 500)    # Change as needed

def move_mouse(start, end, duration=1):
    """
    Moves the mouse from start to end position over the given duration (in seconds).
    """
    pyautogui.moveTo(end[0], end[1], duration=duration)

if __name__ == "__main__":
    print(f"Moving mouse from {start_pos} to {end_pos}...")
    move_mouse(start_pos, end_pos, duration=0.5)
    print("Done.")
