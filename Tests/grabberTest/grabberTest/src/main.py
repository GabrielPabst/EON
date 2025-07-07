from pynput import mouse, keyboard
from utils.recorder import ActionRecorder

def main():
    recorder = ActionRecorder(screenshot_radius=50)  # You can change the radius here

    # Start keyboard listener first so we can stop both on 'q'
    with keyboard.Listener(on_press=recorder.on_press, on_release=recorder.on_release) as keyboard_listener:
        with mouse.Listener(on_click=recorder.on_click, on_move=recorder.on_move, on_scroll=recorder.on_scroll) as mouse_listener:
            # Wait for either listener to stop
            keyboard_listener.join()
            mouse_listener.stop()  # Stop mouse listener if keyboard listener ends

if __name__ == "__main__":
    main()