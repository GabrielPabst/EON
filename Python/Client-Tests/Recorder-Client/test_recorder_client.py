import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Recorder-Client')))
from recorder_client import RecorderClient

def main():
    # Optionally specify screenshot_radius or other parameters here
    client = RecorderClient()
    client.run()

if __name__ == "__main__":
    main()
