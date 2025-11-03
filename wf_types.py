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

class Parse:
    @staticmethod
    def parse_int16(b1, b2):
        """Helper to parse a signed 16-bit integer from two bytes (big-endian)."""
        val = (b1 << 8) | b2
        return val - (1 << 16) if val & (1 << 15) else val

    @staticmethod
    def parse_int32(b1, b2, b3, b4):
        """Helper to parse a signed 32-bit integer from four bytes (big-endian)."""
        val = (b1 << 24) | (b2 << 16) | (b3 << 8) | b4
        return val - (1 << 32) if val & (1 << 31) else val

    @staticmethod
    def parse_int48(b1, b2, b3, b4, b5, b6):
        """Helper to parse a signed 48-bit integer from six bytes (big-endian)."""
        val = (b1 << 40) | (b2 << 32) | (b3 << 24) | (b4 << 16) | (b5 << 8) | b6
        return val - (1 << 48) if val & (1 << 47) else val
    
    @staticmethod
    def _parse_uint32(b1, b2, b3, b4):
        """Helper to parse an unsigned 32-bit integer from four bytes (big-endian)."""
        # For unsigned integers, we just combine the bytes with shifting. No two's complement correction is needed.
        return (b1 << 24) | (b2 << 16) | (b3 << 8) | b4

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
    def is_float(value) -> bool:
        """Check if value is a float."""
        return isinstance(value, float)

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