# region: Imports----------------------------------------------------------------------------------------------------------------
import minimalmodbus
import warnings
from enum import Enum

# endregion

# region: Enum classes for various settings.-------------------------------------------------------------------------------------
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

# endregion

class Servo42dModbus:

    # region: Class attributes---------------------------------------------------------------------------------------------------
    modbus: minimalmodbus.Instrument
    work_current_mA: int
    hold_current_percentage: int
    steps_per_revolution: int
    micro_steps_per_step: int
    work_mode: WorkMode
    enable_disable: EnableDisable

    # endregion

    # region: Initialization-----------------------------------------------------------------------------------------------------
    def __init__(self, 
                 com_port: str = 'COM4',
                 slave_id: int = 1,
                 work_current: int = 3000,
                 hold_current_percent: HoldCurrentPercentage = HoldCurrentPercentage.PERCENT_90,
                 steps_per_revolution: int = 200,
                 micro_steps_per_step: int = 16,
                 work_mode: WorkMode = WorkMode.SR_CLOSE) -> None:


        # Create a modbus instrument instance.
        self.modbus = minimalmodbus.Instrument(com_port, slave_id)

        # Serial port settings.
        self.modbus.serial.baudrate = 38400
        self.modbus.serial.bytesize = 8
        self.modbus.serial.parity = minimalmodbus.serial.PARITY_NONE
        self.modbus.serial.stopbits = 1
        self.modbus.serial.timeout = 1

        # Set parameters.
        self.set_work_current(work_current)
        self.set_hold_current_percentage(hold_current_percent)
        self.set_microsteps_per_step(micro_steps_per_step)
        self.steps_per_revolution = steps_per_revolution
        self.set_work_mode(work_mode)

    # endregion

    # region: Functions that are complete, commented, parameter sanitized and rock-solid-----------------------------------------
    
    def calibrate(self) -> None:

        # Write to register.
        self.modbus.write_register(functioncode = 6, registeraddress = 0x80, value=1)
   
    def set_enable_disable(self, enable: EnableDisable) -> None:

        # Type check parameter.
        if not isinstance(enable, EnableDisable): raise TypeError("enable must be an instance of EnableDisable enum.")

        # Set enable/disable.
        self.enable_disable = enable.value

        # Write to register.
        self.modbus.write_register(functioncode=6, registeraddress=0x85, value=self.enable_disable)
   
    def set_hold_current_percentage(self, percent: HoldCurrentPercentage) -> None:
        
        # Type check parameter.
        if not isinstance(percent, HoldCurrentPercentage): raise TypeError("percent must be an instance of HoldCurrentPercentage enum.")

        # Set hold current percentage.
        self.hold_current_percentage = percent.value

        # Write to register.
        self.modbus.write_register(functioncode = 6 , registeraddress = 0x9B, value = self.hold_current_percentage)

    def set_work_mode(self, mode: WorkMode) -> None:

        # Type check parameter.
        if not isinstance(mode, WorkMode): raise TypeError("mode must be an instance of WorkMode enum.")

        # Set work mode.
        self.work_mode = mode.value

        # Write to register.
        self.modbus.write_register(functioncode = 6, registeraddress = 0x82, value = self.work_mode)
    # endregion

    # region: Functions that are in-the-works or otherwise not rock-solid--------------------------------------------------------
    
    # !!! NEEDS PARAMETER SANITIZER BROKEN OUT !!!
    def set_work_current(self, current_mA: int) -> None:
        
        # Check and warn for limits.
        if current_mA > 3000: warnings.warn("Max current for servo_42D is 3000mA. Setting to max.")
        if current_mA < 0: warnings.warn("Current cannot be negative. Setting to 0mA.")
        
        # Set current within limits.
        self.work_current_mA = max(min(current_mA, 3000), 0)

        # Write to register.
        self.modbus.write_register(functioncode = 6, registeraddress = 0x83, value = self.work_current_mA)

    # !!! NEEDS PARAMETER SANITIZER !!!
    def set_microsteps_per_step(self, micro_steps_per_step: int) -> None:

        # Set microsteps per step.
        self.micro_steps_per_step = micro_steps_per_step

        # Write to register.
        self.modbus.write_register(functioncode = 6, registeraddress=0x84, value=self.micro_steps_per_step)

    # !!! UNTESTED !!!
    def move_by_speed(self, direction: Direction, acceleration: int, speed: int) -> None:

        # Sanitize inputs.
        Servo42dModbus.sanitize_speed(speed)
        Servo42dModbus.sanitize_acceleration(acceleration)

        # Pack direction and acceleration into single 16-bit value.
        dir_acceleration = direction.value << 8 | acceleration
        
        # Write to register.
        self.modbus.write_registers(registeraddress = 0xF6, values = [dir_acceleration, speed])

    # !!! UNTESTED !!!
    def stop_movement(self, deceleration: int) -> None:

        # Sanitize input.
        Servo42dModbus.sanitize_acceleration(deceleration)

        # Write to register.
        self.modbus.write_registers(registeraddress = 0xF6, values = [0x00, deceleration, 0x00])

    def move_relative_by_pulses(self, direction: Direction, acceleration: int, speed: int, pulses: int) -> None:
        
        # Sanitize inputs.
        Servo42dModbus.sanitize_acceleration(acceleration)
        Servo42dModbus.sanitize_speed(speed)
        Servo42dModbus.check_pulses(pulses)

        # Pack direction and acceleration into single 16-bit value.
        dir_acc = direction.value << 8 | acceleration

        # Split pulses into high and low words.
        pulses_low = pulses & 0xFFFF
        pulses_high = (pulses >> 16) & 0xFFFF
        
        # Write to register.
        values = [dir_acc, speed, pulses_high, pulses_low]
        self.modbus.write_registers(registeraddress=0xFD, values=values)
        self.wait_until_status(Status.STOP)

    def wait_until_status(self, desired_status: Status) -> None:

        while 1:
            status = self.read_status()
            print("reading")
            if status == desired_status: break

    def read_status(self) -> Status:
        status = self.modbus.read_registers(functioncode = 4, registeraddress = 0xF1, number_of_registers = 1)
        return Status(status[0])

    # endregion

    # region: Helper functions that are used for parameter sanitization----------------------------------------------------------

    @staticmethod
    def sanitize_speed(speed: int) -> int:
        if not isinstance(speed, int):
            raise TypeError("speed must be an integer.")
        if speed > 3000:
            warnings.warn("speed too high, limit is 3000. setting to max.")
            return 3000
        if speed < 0:
            warnings.warn("speed cannot be negative. setting to 0.")
            return 0
        else:
            return speed

    @staticmethod
    def sanitize_acceleration(acc: int) -> int:
        if not isinstance(acc, int):
            raise TypeError("acceleration must be an integer.")
        if acc > 255:
            warnings.warn("acceleration too high, limit is 255. setting to max.")
            return 255
        if acc < 0:
            warnings.warn("acceleration cannot be negative. setting to 0.")
            return 0
        else:
            return acc
    
    @staticmethod
    def check_pulses(pulses: int) -> None:
        if not isinstance(pulses, int): raise TypeError("pulses must be an integer.")
        if pulses < 0 or pulses > 0xFFFFFF: raise ValueError("pulses must be between 0 and 16,777,215 (0xFFFFFF).")
    # endregion