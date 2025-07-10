import pyautogui
from pynput.mouse import Controller
# Get current mouse position
x, y = pyautogui.position()
print(f"Current mouse position-PyAutoGUI: ({x}, {y})")
x,y = Controller().position
print(f"Current mouse position-Pynput: ({x}, {y})")