import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Makro-Client')))
from macro_replay import MacroReplayManager

def main():
    # Optionally specify custom log file paths here
    manager = MacroReplayManager("mouse_moves.log","actions.log1")
    manager.replay_all()

if __name__ == "__main__":
    main()
