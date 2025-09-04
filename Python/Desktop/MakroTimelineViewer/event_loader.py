import json
from collections import defaultdict
import numpy as np
from PySide6.QtGui import QColor

class EventLoader:
    
    
    
    @staticmethod
    def load_events_from_log(log_file):
        """Load events from actions.log file and keep raw event data for popup"""
        try:
            events = []
            first_time = None
            print( "fisttime" + str(first_time))
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if first_time is None:
                             first_time = event["time"]
                        relative_time = event["time"] - first_time
                        label = f"{event.get('type', '')} {event.get('key', '')}".strip()
                        if event.get('x') is not None and event.get('y') is not None:
                            label += f" at ({event['x']}, {event['y']})"
                        if event.get('type') == 'press':
                            color = QColor(255, 100, 100)
                        elif event.get('type') == 'release':
                            color = QColor(100, 255, 100)
                        else:
                            color = QColor(100, 100, 255)
                        # Keep the raw event dictionary so we can show all fields later
                        events.append({
                            "time": relative_time,
                            "label": label,
                            "color": color,
                            "raw": event  # raw stored here
                        })
                    except json.JSONDecodeError:
                        continue
            if not events:
                return []
            return events, first_time
        except FileNotFoundError:
            return []
    @staticmethod
    def process_events(events_array):
        events = []
        first_time = None

        for event in events_array:
            try:
                if first_time is None:
                    first_time = event["time"]
                relative_time = event["time"] - first_time
                print("first time" + str(first_time))
                label = f"{event.get('type', '')} {event.get('key', '')}".strip()
                if event.get('x') is not None and event.get('y') is not None:
                    label += f" at ({event['x']}, {event['y']})"

                if event.get('type') == 'press':
                    color = QColor(255, 100, 100)
                elif event.get('type') == 'release':
                    color = QColor(100, 255, 100)
                else:
                    color = QColor(100, 100, 255)

                events.append({
                    "time": relative_time,
                    "label": label,
                    "color": color,
                    "raw": event  # keep raw for later
                })
            except KeyError:
                continue  # skip malformed events

        return events, first_time

    @staticmethod
    def load_movements_per_second(log_file, start_time):
        """Load mouse movement data from mouse_moves.log"""
        try:
            timestamps = []
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("type") == "move":
                            timestamps.append(event["time"])
                    except json.JSONDecodeError:
                        continue
            if not timestamps:
                return EventLoader.get_sample_data()
            print( "start" + str(start_time))
            counts = defaultdict(int)
            
            with open(log_file, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("type") == "move":
                            relative_time = event["time"] - start_time
                            sec = int(relative_time)
                            counts[sec] += 1
                    except json.JSONDecodeError:
                        continue
                        
            if counts:
                times = sorted(counts.keys())
                values = [counts[t] for t in times]
                return np.array(times), np.array(values)
            else:
                return np.array([0]), np.array([0])
        except FileNotFoundError:
            return np.array([0]), np.array([0])

