
import sys

import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../Python/Desktop/MakroTimelineViewer')))
from action_log_manager import ActionsLogManager


def main():

    """CLI interface for testing ActionsLogManager functionality"""


    

    manager = None

    

    def print_help():

        print("\n=== ActionsLogManager CLI ===")

        print("Commands:")

        print("  load <file_path>           - Load actions log file")

        print("  save [file_path]           - Save to file (uses loaded path if not specified)")

        print("  create <type> <key> <time> [x] [y] [screenshot] - Create new event")

        print("  modify <index> <field>=<value> [field2=value2] ... - Modify event")

        print("  delete <index>             - Delete event and its pair")

        print("  list [start] [end]         - List events (optionally in range)")

        print("  get <index>                - Get specific event")

        print("  validate                   - Validate all events")

        print("  keys                       - Show available key types")

        print("  help                       - Show this help")

        print("  exit                       - Exit CLI")

        print("\nExamples:")

        print("  create press 'q' 123.45")

        print("  create press mouse_Button.left 124.0 100 200 screenshot.png")

        print("  modify 0 time=125.0 x=150")

        print("  delete 1")

    

    def create_sample_file():

        """Create a sample actions.log file for testing"""

        sample_content = '''{"type": "press", "key": "mouse_Button.left", "x": 65, "y": 23, "time": 1753098358.6290236, "screenshot": "screenshots\\\\screenshot_1753098358629_65_23.png"}

{"type": "release", "key": "mouse_Button.left", "x": 257, "y": 13, "time": 1753098361.7343316, "screenshot": null}

{"type": "press", "key": "'q'", "x": null, "y": null, "time": 1753098372.3127646, "screenshot": null}

{"type": "release", "key": "'q'", "x": null, "y": null, "time": 1753098373.0, "screenshot": null}'''

        

        with open('sample_actions.log', 'w') as f:

            f.write(sample_content)

        print("Created sample_actions.log for testing")

    

    print("ActionsLogManager CLI - Type 'help' for commands")

    

    # Create sample file if none exists

    if not os.path.exists('sample_actions.log'):

        create_sample_file()

        print("Loading sample_actions.log...")

        try:

            manager = ActionsLogManager('sample_actions.log')

            print(f"Loaded {len(manager.events)} events")

        except Exception as e:

            print(f"Error loading sample: {e}")

    

    while True:

        try:

            cmd = input("\n> ").strip().split()

            if not cmd:

                continue

            

            command = cmd[0].lower()

            

            if command in ['exit', 'quit', 'q']:

                break

            

            elif command == 'help':

                print_help()

            

            elif command == 'load':

                if len(cmd) != 2:

                    print("Usage: load <file_path>")

                    continue

                try:

                    manager = ActionsLogManager(cmd[1])

                    print(f"Loaded {len(manager.events)} events from {cmd[1]}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'save':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                try:

                    file_path = cmd[1] if len(cmd) > 1 else None

                    manager.save_to_file(file_path)

                    save_path = file_path or manager.log_file_path

                    print(f"Saved to {save_path}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'create':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                if len(cmd) < 4:

                    print("Usage: create <type> <key> <time> [x] [y] [screenshot]")

                    continue

                try:

                    event_type = cmd[1]

                    key = cmd[2]

                    time = float(cmd[3])

                    x = int(cmd[4]) if len(cmd) > 4 and cmd[4] != 'null' else None

                    y = int(cmd[5]) if len(cmd) > 5 and cmd[5] != 'null' else None

                    screenshot = cmd[6] if len(cmd) > 6 and cmd[6] != 'null' else None

                    

                    index = manager.create_event(event_type, key, x, y, time, screenshot)

                    print(f"Created event at index {index}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'modify':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                if len(cmd) < 3:

                    print("Usage: modify <index> <field>=<value> [field2=value2] ...")

                    continue

                try:

                    index = int(cmd[1])

                    kwargs = {}

                    for arg in cmd[2:]:

                        if '=' not in arg:

                            print(f"Invalid argument format: {arg}. Use field=value")

                            continue

                        field, value = arg.split('=', 1)

                        # Convert value to appropriate type

                        if field in ['x', 'y']:

                            kwargs[field] = int(value) if value != 'null' else None

                        elif field == 'time':

                            kwargs[field] = float(value)

                        elif field == 'screenshot':

                            kwargs[field] = value if value != 'null' else None

                        else:

                            kwargs[field] = value

                    

                    manager.modify_event(index, **kwargs)

                    print(f"Modified event at index {index}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'delete':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                if len(cmd) != 2:

                    print("Usage: delete <index>")

                    continue

                try:

                    index = int(cmd[1])

                    deleted = manager.delete_event(index)

                    print(f"Deleted events at indices: {deleted}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'list':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                try:

                    start = int(cmd[1]) if len(cmd) > 1 else 0

                    end = int(cmd[2]) if len(cmd) > 2 else len(manager.events)

                    

                    print(f"\nEvents {start}-{end-1}:")

                    for i in range(start, min(end, len(manager.events))):

                        event = manager.events[i]

                        print(f"  [{i:2d}] {event.type:7s} {event.key:15s} t={event.time:12.3f} x={str(event.x):4s} y={str(event.y):4s}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'get':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                if len(cmd) != 2:

                    print("Usage: get <index>")

                    continue

                try:

                    index = int(cmd[1])

                    event = manager.get_event(index)

                    print(f"Event {index}: {event.to_dict()}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'validate':

                if not manager:

                    print("No manager loaded. Use 'load' first.")

                    continue

                try:

                    is_valid = manager.validate_all_events()

                    print(f"Events are {'valid' if is_valid else 'invalid'}")

                except Exception as e:

                    print(f"Error: {e}")

            

            elif command == 'keys':

                print("\nAvailable key types (examples):")

                print("Mouse: mouse_Button.left, mouse_Button.right, mouse_Button.middle")

                print("Letters: 'a', 'b', ..., 'z', 'A', 'B', ..., 'Z'")

                print("Numbers: '0', '1', ..., '9'")

                print("Numpad: Key.num_0, Key.num_1, ..., Key.num_9")

                print("Function: Key.f1, Key.f2, ..., Key.f24")

                print("Special: Key.enter, Key.space, Key.shift_l, Key.ctrl_l")

                print("Arrows: Key.up, Key.down, Key.left, Key.right")

                print("Symbols: '!', '@', '#', ', '%', '^', '&', '*', etc.")

                print("\nFor full list, check KeyType enum in the code.")

            

            else:

                print(f"Unknown command: {command}. Type 'help' for available commands.")

        

        except KeyboardInterrupt:

            print("\nExiting...")

            break

        except Exception as e:

            print(f"Unexpected error: {e}")



if __name__ == "__main__":

    main()