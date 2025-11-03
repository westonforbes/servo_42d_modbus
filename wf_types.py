from typing import Annotated
from enum import Enum

uint_8 = Annotated[int, "An unsigned 8-bit integer (0-255)"]
uint_16 = Annotated[int, "An unsigned 16-bit integer (0-65535)"]
uint_32 = Annotated[int, "An unsigned 32-bit integer (0-4294967295)"]

class TriggerLevel(Enum):
    LOW = 0
    HIGH = 1

class HoldCurrentPercentage(Enum):
    PERCENT_10 = 0
    PERCENT_20 = 1
    PERCENT_30 = 2
    PERCENT_40 = 3
    PERCENT_50 = 4
    PERCENT_60 = 5
    PERCENT_70 = 6
    PERCENT_80 = 7
    PERCENT_90 = 8
    PERCENT_100 = 9

class Direction(Enum):
    CW = 0x00
    CCW = 0x01

class WorkMode(Enum):
    CR_OPEN = 0
    CR_CLOSE = 1
    CR_VFOC = 2
    SR_OPEN = 3
    SR_CLOSE = 4
    SR_VFOC = 5

class EnableDisable(Enum):
    ENABLE = 1
    DISABLE = 0

class Status(Enum):
    READ_FAIL = 0
    STOP = 1
    SPEED_UP = 2
    SPEED_DOWN = 3
    FULL_SPEED = 4
    HOMING = 5
    CALIBRATION = 6

class TypeCheck:

    @staticmethod
    def is_enum(value, enum_type) -> bool:
        """Check if value is an instance of the given enum type."""
        return isinstance(value, enum_type)

    @staticmethod
    def is_str(value) -> bool:
        """Check if value is a string."""
        return isinstance(value, str)

    @staticmethod
    def is_bool(value) -> bool:
        """Check if value is a boolean."""
        return isinstance(value, bool)

    @staticmethod
    def is_uint8(value) -> bool:
        """Check if value is an integer in the uint8 range."""
        return isinstance(value, int) and 0 <= value <= 255

    @staticmethod
    def is_uint16(value) -> bool:
        """Check if value is a valid 16-bit unsigned integer (0-65535)."""
        return isinstance(value, int) and 0 <= value <= 65535
    
    @staticmethod
    def is_uint32(value) -> bool:
        """Check if value is a valid 32-bit unsigned integer (0-4294967295)."""
        return isinstance(value, int) and 0 <= value <= 4294967295

    @staticmethod
    def is_int_list(value) -> bool:
        """Check if value is a list of integers."""
        return isinstance(value, list) and all(isinstance(item, int) for item in value)