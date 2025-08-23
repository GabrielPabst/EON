import json

import copy

from typing import List, Dict, Any, Optional, Union

from dataclasses import dataclass

from enum import Enum



class EventType(Enum):

    PRESS = "press"

    RELEASE = "release"



class KeyType(Enum):

    # Mouse buttons

    MOUSE_LEFT = "mouse_Button.left"

    MOUSE_RIGHT = "mouse_Button.right"

    MOUSE_MIDDLE = "mouse_Button.middle"

    MOUSE_X1 = "mouse_Button.x1"

    MOUSE_X2 = "mouse_Button.x2"



    # Letter keys (lowercase)

    KEY_A = "'a'"

    KEY_B = "'b'"

    KEY_C = "'c'"

    KEY_D = "'d'"

    KEY_E = "'e'"

    KEY_F = "'f'"

    KEY_G = "'g'"

    KEY_H = "'h'"

    KEY_I = "'i'"

    KEY_J = "'j'"

    KEY_K = "'k'"

    KEY_L = "'l'"

    KEY_M = "'m'"

    KEY_N = "'n'"

    KEY_O = "'o'"

    KEY_P = "'p'"

    KEY_Q = "'q'"

    KEY_R = "'r'"

    KEY_S = "'s'"

    KEY_T = "'t'"

    KEY_U = "'u'"

    KEY_V = "'v'"

    KEY_W = "'w'"

    KEY_X = "'x'"

    KEY_Y = "'y'"

    KEY_Z = "'z'"



    # Number keys (main keyboard)

    KEY_0 = "'0'"

    KEY_1 = "'1'"

    KEY_2 = "'2'"

    KEY_3 = "'3'"

    KEY_4 = "'4'"

    KEY_5 = "'5'"

    KEY_6 = "'6'"

    KEY_7 = "'7'"

    KEY_8 = "'8'"

    KEY_9 = "'9'"



    # Function keys

    KEY_F1 = "Key.f1"

    KEY_F2 = "Key.f2"

    KEY_F3 = "Key.f3"

    KEY_F4 = "Key.f4"

    KEY_F5 = "Key.f5"

    KEY_F6 = "Key.f6"

    KEY_F7 = "Key.f7"

    KEY_F8 = "Key.f8"

    KEY_F9 = "Key.f9"

    KEY_F10 = "Key.f10"

    KEY_F11 = "Key.f11"

    KEY_F12 = "Key.f12"



    # Special keys

    KEY_SPACE = "Key.space"

    KEY_ENTER = "Key.enter"

    KEY_TAB = "Key.tab"

    KEY_BACKSPACE = "Key.backspace"

    KEY_DELETE = "Key.delete"

    KEY_ESC = "Key.esc"

    KEY_INSERT = "Key.insert"

    KEY_HOME = "Key.home"

    KEY_END = "Key.end"

    KEY_PAGE_UP = "Key.page_up"

    KEY_PAGE_DOWN = "Key.page_down"

    KEY_CAPS_LOCK = "Key.caps_lock"

    KEY_NUM_LOCK = "Key.num_lock"

    KEY_SCROLL_LOCK = "Key.scroll_lock"

    KEY_PRINT_SCREEN = "Key.print_screen"

    KEY_PAUSE = "Key.pause"

    KEY_MENU = "Key.menu"



    # Arrow keys

    KEY_LEFT = "Key.left"

    RIGHT = "Key.right"

    KEY_UP = "Key.up"

    KEY_DOWN = "Key.down"



    # Modifier keys

    KEY_SHIFT_L = "Key.shift_l"

    KEY_SHIFT_R = "Key.shift_r"

    KEY_CTRL_L = "Key.ctrl_l"

    KEY_CTRL_R = "Key.ctrl_r"

    KEY_ALT_L = "Key.alt_l"

    KEY_ALT_R = "Key.alt_r"

    KEY_CMD_L = "Key.cmd_l"

    KEY_CMD_R = "Key.cmd_r"



    # Numpad keys

    KEY_NUM_0 = "Key.num_0"

    KEY_NUM_1 = "Key.num_1"

    KEY_NUM_2 = "Key.num_2"

    KEY_NUM_3 = "Key.num_3"

    KEY_NUM_4 = "Key.num_4"

    KEY_NUM_5 = "Key.num_5"

    KEY_NUM_6 = "Key.num_6"

    KEY_NUM_7 = "Key.num_7"

    KEY_NUM_8 = "Key.num_8"

    KEY_NUM_9 = "Key.num_9"

    KEY_NUM_DECIMAL = "Key.num_decimal"

    KEY_NUM_ENTER = "Key.num_enter"

    KEY_NUM_ADD = "Key.num_add"

    KEY_NUM_SUBTRACT = "Key.num_subtract"

    KEY_NUM_MULTIPLY = "Key.num_multiply"

    KEY_NUM_DIVIDE = "Key.num_divide"



    # Symbol keys

    KEY_BACKTICK = "'`'"

    KEY_MINUS = "'-'"

    KEY_EQUALS = "'='"

    KEY_LEFT_BRACKET = "'['"

    KEY_RIGHT_BRACKET = "']'"

    KEY_BACKSLASH = "'\\'"

    KEY_SEMICOLON = "';'"

    KEY_QUOTE = "'\''"

    KEY_COMMA = "','"

    KEY_PERIOD = "'.'"

    KEY_SLASH = "'/'"



    # Media keys (if supported by the system)

    KEY_VOLUME_MUTE = "Key.media_volume_mute"

    KEY_VOLUME_DOWN = "Key.media_volume_down"

    KEY_VOLUME_UP = "Key.media_volume_up"

    KEY_MEDIA_PLAY_PAUSE = "Key.media_play_pause"

    KEY_MEDIA_NEXT = "Key.media_next"

    KEY_MEDIA_PREVIOUS = "Key.media_previous"





@dataclass

class ActionEvent:

    """Represents a single action event"""

    type: str

    key: str

    x: Optional[int]

    y: Optional[int]

    time: float

    screenshot: Optional[str]

    

    def to_dict(self) -> Dict[str, Any]:

        """Convert to dictionary format for JSON serialization"""

        return {

            "type": self.type,

            "key": self.key,

            "x": self.x,

            "y": self.y,

            "time": self.time,

            "screenshot": self.screenshot

        }

    

    @classmethod

    def from_dict(cls, data: Dict[str, Any]) -> 'ActionEvent':

        """Create ActionEvent from dictionary"""

        return cls(

            type=data["type"],

            key=data["key"],

            x=data["x"],

            y=data["y"],

            time=data["time"],

            screenshot=data["screenshot"]

        )



class ValidationError(Exception):

    """Custom exception for validation errors"""

    pass



class ActionsLogManager:

    """Manager class for handling actions.log files"""

    

    def __init__(self, log_file_path: str = None):

        self.log_file_path = log_file_path

        self.events: List[ActionEvent] = []

        if log_file_path:

            self.load_from_file(log_file_path, "")

    
    def _sort_events_by_time(self) -> None:
        """Keep events sorted by their time"""
        self.events.sort(key=lambda e: e.time)

    @staticmethod
    def is_mouse_key(key: str) -> bool:
        """Check if a key is a mouse button"""
        mouse_keys = [
            KeyType.MOUSE_LEFT.value,
            KeyType.MOUSE_RIGHT.value,
            KeyType.MOUSE_MIDDLE.value,
            KeyType.MOUSE_X1.value,
            KeyType.MOUSE_X2.value
        ]
        return key in mouse_keys

    @staticmethod
    def validate_coordinates(key: str, x: Optional[int], y: Optional[int]) -> None:
        """Validate that coordinates are only present for mouse events"""
        is_mouse = ActionsLogManager.is_mouse_key(key)
        has_coordinates = x is not None or y is not None
        
        if not is_mouse and has_coordinates:
            raise ValidationError(f"Non-mouse event with key '{key}' cannot have x or y coordinates")
        
        # Optional: You could also enforce that mouse events MUST have coordinates
        # if is_mouse and not has_coordinates:
        #     raise ValidationError(f"Mouse event with key '{key}' must have x and y coordinates")

    def load_from_file(self, file_path_actions: str, file_path_movements: str) -> None:

        """Load events from a log file"""

        self.log_file_path = file_path_actions
        self.log_file_path_movements = file_path_movements
        self.events = []
        
        

        

        try:

            with open(file_path_actions, 'r') as file:

                for line in file:

                    line = line.strip()

                    if line:

                        data = json.loads(line)
                        
                        # Validate coordinates before creating event
                        self.validate_coordinates(data["key"], data["x"], data["y"])
                        
                        self.events.append(ActionEvent.from_dict(data))
                        
                        self._sort_events_by_time()

        except FileNotFoundError:

            raise FileNotFoundError(f"Log file not found: {file_path_actions}")

        except json.JSONDecodeError as e:

            raise ValueError(f"Invalid JSON format in log file: {e}")

    

    def save_to_file(self, file_path: str = None) -> None:

        """Save events to a log file"""

        target_path = file_path or self.log_file_path

        if not target_path:

            raise ValueError("No file path specified")

        

        with open(target_path, 'w') as file:

            for event in self.events:

                json.dump(event.to_dict(), file)

                file.write('\n')

    

    @staticmethod

    def get_valid_keys() -> List[str]:

        """Get list of all valid key values"""

        return [key.value for key in KeyType]

    

    @staticmethod

    def is_valid_key(key: str) -> bool:

        """Check if a key is valid"""

        return key in ActionsLogManager.get_valid_keys()

    

    def create_event(self, event_type: str, key: str, x: Optional[int] = None, 

                    y: Optional[int] = None, time: float = 0.0, 

                    screenshot: Optional[str] = None, insert_index: Optional[int] = None) -> int:

        """Create a new event and add it to the log"""

        # Validate coordinates for mouse events
        self.validate_coordinates(key, x, y)
        
        # Validate event type

        if event_type not in [EventType.PRESS.value, EventType.RELEASE.value]:

            raise ValidationError(f"Invalid event type: {event_type}")

        

        # Validate time

        if time < 0:

            raise ValidationError("Time cannot be negative")

        

        # Validate press/release pairing

        if event_type == EventType.RELEASE.value:

            if not self._has_unpaired_press_for_key(key, time):

                raise ValidationError(f"Cannot create release event for key '{key}' - no corresponding unpaired press event found")

        elif event_type == EventType.PRESS.value:

            if self._has_unpaired_press_for_key_at_any_time(key):

                raise ValidationError(f"Cannot create press event for key '{key}' - there's already an unpaired press event for this key")

        

        # Create event

        event = ActionEvent(

            type=event_type,

            key=key,

            x=x,

            y=y,

            time=time,

            screenshot=screenshot

        )



        # Insert at specified index or append

        if insert_index is not None:

            if insert_index < 0 or insert_index > len(self.events):

                raise ValidationError(f"Invalid insert index: {insert_index}")

            self.events.insert(insert_index, event)
            
            self._sort_events_by_time()
            return insert_index

        else:

            self.events.append(event)
            self._sort_events_by_time()
            return len(self.events) - 1

    

    def modify_event(self, index: int, **kwargs) -> None:

        """Modify an existing event"""

        if index < 0 or index >= len(self.events):

            raise ValidationError(f"Invalid event index: {index}")

        

        event = self.events[index]

        original_event = copy.deepcopy(event)

        

        # Apply modifications

        for field, value in kwargs.items():

            if hasattr(event, field):

                setattr(event, field, value)

            else:

                raise ValidationError(f"Invalid field: {field}")

        

        # Validate modifications

        try:

            # Validate coordinates after modification
            self.validate_coordinates(event.key, event.x, event.y)
            
            self._validate_event_modification(index, original_event)
            self._sort_events_by_time()

        except ValidationError:

            self.events[index] = original_event

            raise

    

    def delete_event(self, index: int) -> List[int]:

        """Delete an event and its linked event if applicable"""

        if index < 0 or index >= len(self.events):

            raise ValidationError(f"Invalid event index: {index}")

        

        deleted_indices = [index]

        

        # Find and delete linked event

        linked_index = self._find_linked_event(index)

        if linked_index is not None:

            deleted_indices.append(linked_index)

        

        # Sort indices in descending order to delete from end first

        deleted_indices.sort(reverse=True)

        

        # Delete events

        for idx in deleted_indices:

            del self.events[idx]

        self._sort_events_by_time()

        return sorted(deleted_indices)

    

    def get_events(self) -> List[ActionEvent]:

        """Get all events"""

        return self.events.copy()

    

    def get_event(self, index: int) -> ActionEvent:

        """Get a specific event by index"""

        if index < 0 or index >= len(self.events):

            raise ValidationError(f"Invalid event index: {index}")

        return copy.deepcopy(self.events[index])

    

    def get_events_by_type(self, event_type: str) -> List[tuple[int, ActionEvent]]:

        """Get all events of a specific type with their indices"""

        return [(i, copy.deepcopy(event)) for i, event in enumerate(self.events) 

                if event.type == event_type]

    

    def get_events_by_key(self, key: str) -> List[tuple[int, ActionEvent]]:

        """Get all events for a specific key with their indices"""

        return [(i, copy.deepcopy(event)) for i, event in enumerate(self.events) 

                if event.key == key]

    

    def get_events_in_time_range(self, start_time: float, end_time: float) -> List[tuple[int, ActionEvent]]:

        """Get all events within a time range with their indices"""

        return [(i, copy.deepcopy(event)) for i, event in enumerate(self.events) 

                if start_time <= event.time <= end_time]

    

    def validate_all_events(self) -> bool:

        """Validate all events in the log"""

        try:

            # Check for negative times and coordinate validation

            for i, event in enumerate(self.events):

                if event.time < 0:

                    raise ValidationError(f"Negative time at index {i}")
                
                # Validate coordinates for each event
                self.validate_coordinates(event.key, event.x, event.y)

            

            # Check press/release pairs for each key

            keys = set(event.key for event in self.events)

            for key in keys:

                key_events = [(i, e) for i, e in enumerate(self.events) if e.key == key]

                key_events.sort(key=lambda x: x[1].time)

                

                press_count = 0

                for i, event in key_events:

                    if event.type == EventType.PRESS.value:

                        press_count += 1

                    elif event.type == EventType.RELEASE.value:

                        if press_count <= 0:

                            raise ValidationError(f"Unmatched release at index {i}")

                        press_count -= 1

            

            return True

        except ValidationError:

            return False

    

    def _has_unpaired_press_for_key(self, key: str, release_time: float) -> bool:

        """Check if there's an unpaired press event before the release time"""

        key_events = [(i, e) for i, e in enumerate(self.events) if e.key == key]

        key_events.sort(key=lambda x: x[1].time)

        

        unpaired_press_count = 0

        for i, event in key_events:

            if event.time > release_time:

                break

                

            if event.type == EventType.PRESS.value:

                unpaired_press_count += 1

            elif event.type == EventType.RELEASE.value:

                unpaired_press_count = max(0, unpaired_press_count - 1)

        

        return unpaired_press_count > 0

    

    def _has_unpaired_press_for_key_at_any_time(self, key: str) -> bool:

        """Check if there's ANY unpaired press event for the given key"""

        key_events = [(i, e) for i, e in enumerate(self.events) if e.key == key]

        key_events.sort(key=lambda x: x[1].time)

        

        unpaired_press_count = 0

        for i, event in key_events:

            if event.type == EventType.PRESS.value:

                unpaired_press_count += 1

            elif event.type == EventType.RELEASE.value:

                unpaired_press_count = max(0, unpaired_press_count - 1)

        

        return unpaired_press_count > 0

    

    def _find_linked_event(self, index: int) -> Optional[int]:

        """Find the linked press/release event for the given event"""

        event = self.events[index]

        

        if event.type == EventType.PRESS.value:

            # Look for corresponding release

            for i in range(index + 1, len(self.events)):

                other = self.events[i]

                if (other.type == EventType.RELEASE.value and 

                    other.key == event.key and

                    other.time >= event.time):

                    return i

        elif event.type == EventType.RELEASE.value:

            # Look for corresponding press

            for i in range(index - 1, -1, -1):

                other = self.events[i]

                if (other.type == EventType.PRESS.value and 

                    other.key == event.key and

                    other.time <= event.time):

                    return i

        

        return None

    

    def _validate_event_modification(self, index: int, original_event: ActionEvent) -> None:

        """Validate that an event modification is valid"""

        event = self.events[index]

        

        # Check time is not negative

        if event.time < 0:

            raise ValidationError("Time cannot be negative")

        

        # Check event type is valid

        if event.type not in [EventType.PRESS.value, EventType.RELEASE.value]:

            raise ValidationError(f"Invalid event type: {event.type}")

        

        # Check type changes

        if original_event.type != event.type:

            if (original_event.type == EventType.PRESS.value and event.type == EventType.RELEASE.value):

                # Changed from press to release - check if there's an unpaired press

                self.events[index] = original_event

                has_unpaired = self._has_unpaired_press_for_key(event.key, event.time)

                self.events[index] = event

                

                if not has_unpaired:

                    raise ValidationError(f"Cannot change to release event for key '{event.key}' - no corresponding unpaired press event found")

            

            elif (original_event.type == EventType.RELEASE.value and event.type == EventType.PRESS.value):

                # Changed from release to press - check if there's already an unpaired press

                self.events[index] = original_event

                has_unpaired = self._has_unpaired_press_for_key_at_any_time(event.key)

                self.events[index] = event

                

                if has_unpaired:

                    raise ValidationError(f"Cannot change to press event for key '{event.key}' - there's already an unpaired press event for this key")

        

        # Validate press/release order

        self._validate_press_release_order(index)

    

    def _validate_press_release_order(self, modified_index: int) -> None:

        """Validate press/release order for the modified event"""

        event = self.events[modified_index]

        

        # Get all events with the same key

        same_key_events = [(i, e) for i, e in enumerate(self.events) if e.key == event.key]

        same_key_events.sort(key=lambda x: x[1].time)

        

        # Check that press comes before release in pairs

        press_stack = []

        for i, evt in same_key_events:

            if evt.type == EventType.PRESS.value:

                press_stack.append((i, evt))

            elif evt.type == EventType.RELEASE.value:

                if not press_stack:

                    raise ValidationError(f"Release event at index {i} has no corresponding press event")

                press_stack.pop()