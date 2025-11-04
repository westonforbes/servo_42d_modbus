# region: Imports----------------------------------------------------------------------------------------------------------------
from unittest import case
from wf_modbus import Modbus
from wf_types import TypeCheck, Parse
from wf_console import Console
import wf_types
import time

# endregion

class Servo42dModbus:

    # region: Class attributes---------------------------------------------------------------------------------------------------
    com_port: str
    slave_address: int
    modbus: Modbus
    configuration: dict = {}
    # endregion

    # region: Initialization-----------------------------------------------------------------------------------------------------
    def __init__(self, com_port: str, slave_address: wf_types.uint_8 = 1, microsteps_per_step: wf_types.uint_8 = 16, steps_per_revolution: wf_types.uint_8 = 200) -> None:

        # Type check parameters.
        if not TypeCheck.is_str(com_port): raise TypeError("com_port must be a string.")
        if not TypeCheck.is_uint8(slave_address): raise TypeError("slave_address must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint8(microsteps_per_step): raise TypeError("microsteps_per_step must be a valid uint_8.")
        if not TypeCheck.is_uint8(steps_per_revolution): raise TypeError("steps_per_revolution must be a valid uint_8.")

        # Set class attributes.
        self.com_port = com_port
        self.slave_address = slave_address


        # Create a Modbus instance.
        self.modbus = Modbus(slave_address=self.slave_address, com_port=self.com_port)

        self.set_step_parameters(microsteps=microsteps_per_step, steps_per_revolution=steps_per_revolution, verbose=False)

    # endregion

    # region: Functions that are complete, commented, parameter sanitized and rock-solid-----------------------------------------

    def read_encoder_value(self, verbose: bool = False) -> tuple:
        """
        #### Description:
        Read the current encoder value.
       
        #### Args:
            verbose (bool, optional)
        
        #### Returns:
            tuple: A tuple containing:
                - encoder_count (int): Raw encoder count value (signed 48-bit integer).
                - total_degrees (float): Total angle in degrees from zero position.
                - rotations (int): Number of complete 360-degree rotations.
                - remaining_degrees (float): Remaining degrees after complete rotations.
        
        #### Raises:
            TypeError: If verbose parameter is not a boolean.
            RuntimeError: If reading encoder value fails.
        
        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.2, Page 55.

        #### Last Revision:
            2025-11-04 11:15 AM ET, Weston Forbes
        """

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create a empty response list.
        response = []

        # Try protect...
        try:

            # Get the encoder reading.
            command, response = self.modbus.read_input_registers(
                slave_address = self.slave_address,
                starting_address = 0x0031,
                register_quantity = 0x0003,
                response_length = 11,
                verbose = verbose
            )

        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>failed to read encoder value from servo: {e}</BAD>")
            raise RuntimeError(f"failed to read encoder value from servo: {e}")

        # Convert response to int48 (signed).
        encoder_count = Parse.parse_int48(response[3], response[4], response[5], response[6], response[7], response[8])

        # There are 16384 units per 360 degrees (0x4000).
        # Split into rotations and degrees.
        total_degrees = (360.0/16384.0) * encoder_count
        rotations, remaining_degrees = divmod(total_degrees, 360.0)
        rotations = int(rotations)

        if verbose:
            Console.fancy_print( "<INFO>reading encoder rotations and degrees...</INFO>")
            Console.fancy_print(f"<INFO>encoder location (units): {encoder_count}</INFO>")
            Console.fancy_print(f"<INFO>total angle (degrees): {total_degrees}</INFO>")
            Console.fancy_print(f"<INFO>rotations: {rotations}, degrees: {remaining_degrees}</INFO>")

        return encoder_count, total_degrees, rotations, remaining_degrees

    def move_at_speed(self, direction: wf_types.Direction, acceleration: wf_types.uint_8, speed: wf_types.uint_16, verbose: bool = False) -> bool:
        """
        #### Description:
        Move the motor at a specified speed and acceleration in a given direction.

        #### Args:
            direction (wf_types.Direction): The direction to move the motor (CW or CCW).
            acceleration (wf_types.uint_8): The acceleration value (0-255).
            speed (wf_types.uint_16): The speed value (0-65535).
            verbose (bool, optional): If True, prints detailed Modbus communication. Defaults to False.
        
        #### Raises:
            TypeError: If any parameter is of incorrect type.
            RuntimeError: If sending move command fails.

        #### Returns:
            bool: True if move command was successfully sent, False otherwise.

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.3.1, Page 77.

        #### Last Revision:
            2025-11-04 11:31 AM ET, Weston Forbes
        """

        if verbose: Console.fancy_print("<INFO>sending move at speed command...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_enum(direction, wf_types.Direction): raise TypeError("direction must be a valid Direction enum.")
        if not TypeCheck.is_uint8(acceleration): raise TypeError("acceleration must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(speed): raise TypeError("speed must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create a empty response list.
        response = []
        
        # Try protect...
        try:

            # Command the motor to move.
            command, response = self.modbus.write_multiple_registers(
                slave_address = self.slave_address,
                starting_address = 0x00F6,
                register_quantity = 0x0002,
                byte_quantity=0x04,
                payload = [
                    direction.value,
                    acceleration,
                    (speed >> 8) & 0xFF,
                    speed & 0xFF
                ],
                response_length=8,
                verbose = verbose
            )

        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while sending move at speed command: {e}</BAD>")
            raise RuntimeError(f"exception occurred while sending move at speed command: {e}")

        # Calculate expected response for verification.
        expected_response = Modbus.calculate_modbus_crc([self.slave_address, 0x10, 0x00, 0xF6, 0x00, 0x02])

        # Verify response.
        if response == expected_response:
            if verbose: Console.fancy_print("<GOOD>move at speed command sent successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to send move at speed command.</BAD>")
            return False
        
    def calibrate(self, verbose: bool = False) -> bool:
        """
        #### Description:
        Calibrates the motor. Calibration should be performed with no load on motor.
                
        #### Args:
            verbose (bool, optional)

        #### Returns:
            bool: True if calibration command was successfully sent, False otherwise.
                
        #### Raises:
            TypeError: If verbose is not a boolean.
            RuntimeError: If sending calibration command fails.

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.5, Page 60.

        #### Last Revision:
            2025-11-04 11:37 AM ET, Weston Forbes 
        """

        if verbose: Console.fancy_print("<INFO>\ncalibrating motor...</INFO>")
                
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create a empty response list.
        response = []
        
        # Try protect...
        try:

            # Write to register.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0080,
                register_value = 0x0001,
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting calibration: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting calibration: {e}")

        # Check response.
        if response == command: 
            if verbose: Console.fancy_print("<GOOD>motor calibrated successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to calibrate motor.</BAD>")
            return False

    def clear_motor_protection(self, verbose: bool = False) -> bool:
            """
            #### Description:
            Clear motor protection on the motor. This is typically done after a fault or error state to allow motor operation to resume.
                    
            #### Args:
                verbose (bool, optional)

            #### Returns:
                bool: True if motor protection was cleared successfully, False otherwise.
                    
            #### Raises:
                TypeError: If verbose parameter is not a boolean.
                RuntimeError: If sending the clear protection command fails.

            #### Documentation:
                MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.13, Page 64.

            #### Last Revision:
                2025-11-04 11:44 AM ET, Weston Forbes
            """

            if verbose: Console.fancy_print("<INFO>\nclearing motor protection...</INFO>")

            # Type check parameter.
            if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

            # Create an empty response list.
            response = []
            
            # Try protect...
            try:
                # Write to register.
                command, response = self.modbus.write_single_register(
                    slave_address = self.slave_address,
                    register_address = 0x0088,
                    register_value = 0x0000,
                    response_length= 8,
                    verbose = verbose
                )
            
            # Catch exceptions.
            except Exception as e:
                if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to clear motor protection: {e}</BAD>")
                raise RuntimeError(f"exception occurred while attempting to clear motor protection: {e}")

            # Check response. A successful write echoes the command.
            if response == command: 
                if verbose: Console.fancy_print("<GOOD>motor protection cleared successfully.</GOOD>")
                return True
            else: 
                if verbose: Console.fancy_print("<BAD>failed to clear motor protection.</BAD>")
                return False
    
    def disable_enable_pin(self, verbose: bool = False) -> bool:
            """
            #### Description:
            Disables the physical enable pin functionality on the controller.
                    
            #### Args:
                verbose (bool, optional)

            #### Returns:
                bool: True if the register write was successful (response matches command), False otherwise.
                    
            #### Raises:
                TypeError: If verbose parameter is not a boolean.
                RuntimeError: If sending the disable command fails (e.g., Modbus communication error).

            #### Documentation:
                MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.10, Page 63.

            #### Last Revision:
                2025-11-04 11:50 AM ET, Weston Forbes
            """
            
            if verbose: Console.fancy_print("<INFO>\ndisabling enable pin...</INFO>")

            # Type check parameter.
            if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

            # Create an empty response list.
            response = []
            
            # Try protect...
            try:
                # Write to register (0x0085 with value 0x0002 for 'Board always active').
                command, response = self.modbus.write_single_register(
                    slave_address = self.slave_address,
                    register_address = 0x0085,
                    register_value = 0x0002, # Value 0x0002 sets board to always be active (i.e., disables the physical enable pin).
                    response_length= 8,
                    verbose = verbose
                )

            # Catch exceptions.
            except Exception as e:
                if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to disable enable pin: {e}</BAD>")
                raise RuntimeError(f"exception occurred while attempting to disable enable pin: {e}")

            # Check response. A successful write echoes the command.
            if response == command: 
                if verbose: Console.fancy_print("<GOOD>enable pin disabled successfully.</GOOD>")
                return True
            else: 
                if verbose: Console.fancy_print("<BAD>failed to disable enable pin.</BAD>")
                return False

    def read_en_pin_status(self, verbose: bool = False) -> bool:
        """
        #### Description:
        Read the EN (Enable) pin status from the controller.

        #### Args:
            verbose (bool, optional)

        #### Returns:
            bool: True if the EN pin is asserted (enabled), False if de-asserted (disabled).

        #### Raises:
            TypeError: If verbose parameter is not a boolean.
            RuntimeError: If reading the register fails due to a communication error.
            ValueError: If the servo's response packet is invalid or cannot be interpreted as a valid EN pin status (0x00 or 0x01).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.7, Page 58.

        #### Last Revision:
            2025-11-04 13:02 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nreading EN pin status...</INFO>")

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        response = []
        try:
            command, response = self.modbus.read_input_registers(
                slave_address = self.slave_address,
                starting_address = 0x003A,
                register_quantity = 0x0001,
                response_length = 7,
                verbose = verbose
            )
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while reading EN pin status: {e}</BAD>")
            raise RuntimeError(f"exception occurred while reading EN pin status: {e}")

        # Generate expected response packets for status verification.
        expected_packet_enabled = bytearray([self.slave_address, 0x04, 0x02, 0x00, 0x01]) # Value 0x01 for enabled
        expected_packet_disabled = bytearray([self.slave_address, 0x04, 0x02, 0x00, 0x00]) # Value 0x00 for disabled
        expected_packet_enabled.extend(Modbus._calculate_modbus_crc(expected_packet_enabled))
        expected_packet_disabled.extend(Modbus._calculate_modbus_crc(expected_packet_disabled))
        
        # Check response and extract en pin status.
        response_ba = bytearray(response)
        if response_ba == expected_packet_enabled: 
            if verbose: Console.fancy_print("<GOOD>EN pin is enabled.</GOOD>")
            return True
        elif response_ba == expected_packet_disabled: 
            if verbose: Console.fancy_print("<GOOD>EN pin is disabled.</GOOD>")
            return False
        else: 
            if verbose: Console.fancy_print("<BAD>failed to read en pin status from controller(unexpected response).</BAD>")
            raise ValueError("failed to read en pin status from servo.")
        
    def read_motor_shaft_protection_status(self, verbose: bool = False) -> bool:
        """
        #### Description:
        Read the motor shaft protection status from the controller.

        #### Args:
            verbose (bool, optional)

        #### Returns:
            bool: True if motor shaft protection is active (enabled), False if inactive (disabled).

        #### Raises:
            TypeError: If verbose parameter is not a boolean.
            RuntimeError: If reading the register fails due to a communication error.
            ValueError: If the servo's response packet is invalid or cannot be interpreted as a valid protection status (0x00 or 0x01).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.9, Page 58.

        #### Last Revision:
            2025-11-04 13:03 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nreading motor shaft protection status...</INFO>")

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        response = []
        try:
            command, response = self.modbus.read_input_registers(
                slave_address = self.slave_address,
                starting_address = 0x003E,
                register_quantity = 0x0001,
                response_length = 7,
                verbose = verbose
            )
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while reading motor shaft protection status: {e}</BAD>")
            raise RuntimeError(f"exception occurred while reading motor shaft protection status: {e}")

        # Generate expected response packets for status verification.
        expected_packet_enabled = bytearray([self.slave_address, 0x04, 0x02, 0x00, 0x01]) # Value 0x01 for enabled
        expected_packet_disabled = bytearray([self.slave_address, 0x04, 0x02, 0x00, 0x00]) # Value 0x00 for disabled
        expected_packet_enabled.extend(Modbus.calculate_modbus_crc(expected_packet_enabled))
        expected_packet_disabled.extend(Modbus.calculate_modbus_crc(expected_packet_disabled))
        
        # Check response and extract shaft protection status.
        response_ba = bytearray(response)
        if response_ba == expected_packet_enabled:
            if verbose: Console.fancy_print("<GOOD>motor shaft protection is enabled.</GOOD>")
            return True
        elif response_ba == expected_packet_disabled:
            if verbose: Console.fancy_print("<GOOD>motor shaft protection is disabled.</GOOD>")
            return False
        else: 
            if verbose: Console.fancy_print("<BAD>failed to read shaft protection status from servo (unexpected response).</BAD>")
            raise ValueError("failed to read shaft protection status from servo.")

    def restart(self, verbose: bool = False) -> bool:
        """
        #### Description:
        Restarts the motor controller.

        #### Args:
            verbose (bool, optional)
                    
        #### Returns:
            bool: True if restart command was successfully sent and echoed by the servo, False otherwise.
                    
        #### Raises:
            TypeError: If verbose is not a boolean. 
            RuntimeError: If sending the restart command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.4, Page 60.

        #### Last Revision:
            2025-11-04 13:04 PM ET, Weston Forbes
        """

        if verbose: Console.fancy_print("<INFO>\nrestarting motor...</INFO>")
                    
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create an empty response list.
        response = []
        
        # Try protect...
        try:
            # Write to register (0x0041 with value 0x0001 for restart).
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0041,
                register_value = 0x0001,
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to restart motor: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to restart motor: {e}")

        # Check response. A successful write echoes the command.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>motor restarted successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to restart motor.</BAD>")
            return False
        
    def set_zero(self, verbose: bool = False) -> bool:
        """
        #### Description:
        Sets the current encoder position as the new zero position (absolute zero reset).

        #### Args:
            verbose (bool, optional)

        #### Returns:
            bool: True if the zero command was successfully sent and echoed, False otherwise.

        #### Raises:
            TypeError: If verbose is not a boolean. 
            RuntimeError: If sending the set zero command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.19, Page 67.

        #### Last Revision:
            2025-11-04 13:06 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsetting zero...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create an empty response list.
        response = []
        
        # Try protect...
        try:
            # Write to register (0x0092 with value 0x0001 for setting zero).
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0092,
                register_value = 0x0001,
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to set zero: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to set zero: {e}")

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>zeroed.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to zero.</BAD>")
            return False

    def set_work_mode(self, work_mode: wf_types.WorkMode, verbose: bool = False) -> bool:
        """
        #### Description:
        Set the operational work mode of the motor.

        #### Args:
            work_mode (wf_types.WorkMode): The desired work mode for the servo motor. Must be a valid WorkMode enum value.
            verbose (bool, optional)
        
        #### Returns:
            bool: True if the work mode was successfully set, False otherwise.
        
        #### Raises:
            TypeError: If verbose is not a boolean or work_mode is not a valid WorkMode enum.
            RuntimeError: If sending the set work mode command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.6, Page 61.

        #### Last Revision:
            2025-11-04 13:06 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsetting work mode...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")
        if not TypeCheck.is_enum(work_mode, wf_types.WorkMode): raise TypeError("work_mode must be a valid WorkMode enum.")

        # Create an empty response list.
        response = []
        
        # Try protect...
        try:
            # Write to register (0x0082 with the work_mode enum value).
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0082,
                register_value = work_mode.value,
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to set work mode: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to set work mode: {e}")


        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>work mode set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set work mode.</BAD>")
            return False

    def set_serial_mode_motor_enable(self, enable_disable: wf_types.EnableDisable, verbose: bool = False) -> bool:
        """
        #### Description:
        Set the serial mode motor enable state for the motor.

        #### Args:
            enable_disable (wf_types.EnableDisable): The enable/disable state (0x00 or 0x01) to set for the motor.
            verbose (bool, optional)

        #### Returns:
            bool: True if the motor enable state was set successfully, False otherwise.

        #### Raises:
            TypeError: If verbose is not a boolean or enable_disable is not a valid EnableDisable enum.
            RuntimeError: If sending the enable/disable command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.20, Page 67.

        #### Last Revision:
            2025-11-04 13:07 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsetting serial mode motor enable...</INFO>")
                    
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")
        if not TypeCheck.is_enum(enable_disable, wf_types.EnableDisable): raise TypeError("enable_disable must be a valid EnableDisable enum.")

        # Create an empty response list.
        response = []
        
        # Try protect...
        try:
            # Write to register (0x00F3 with the enable/disable enum value).
            # Note: The register address and value formatting (0x00 << 8 | X) are maintained 
            # from the original code, but 0x00F3 is equivalent to 0xF3 for the address.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x00 << 8 | 0xF3,
                register_value = 0x00 << 8 | enable_disable.value,
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to set serial mode motor enable: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to set serial mode motor enable: {e}")

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>serial mode motor enable set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set serial mode motor enable.</BAD>")
            return False

    def set_holding_current_percentage(self, holding_current_percentage: wf_types.HoldCurrentPercentage, verbose: bool = False) -> bool:
        """
        #### Description:
        Set the holding current percentage for the motor.

        #### Args:
            holding_current_percentage (wf_types.HoldCurrentPercentage): The holding current percentage enum value to set.
            verbose (bool, optional)

        #### Returns:
            bool: True if the command was successfully executed and echoed, False otherwise.

        #### Raises:
            TypeError: If holding_current_percentage is not a valid HoldCurrentPercentage enum or if verbose is not a boolean.
            RuntimeError: If sending the set holding current command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.8, Page 62.

        #### Last Revision:
            2025-11-04 13:08 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsetting holding current percentage...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_enum(holding_current_percentage, wf_types.HoldCurrentPercentage): raise TypeError("holding_current_percentage must be a valid HoldCurrentPercentage enum.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create an empty response list.
        response = []
        
        # Try protect...
        try:
            # Write to register (0x009B with the holding_current_percentage enum value).
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x009B,
                register_value = holding_current_percentage.value,
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to set holding current percentage: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to set holding current percentage: {e}")

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>holding current percentage set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set holding current percentage.</BAD>")
            return False

    def set_step_parameters(self, microsteps: wf_types.uint_16, steps_per_revolution: wf_types.uint_8 = 200, verbose: bool = False) -> bool:
        """
        #### Description:
        Sets the microstep resolution for the motor controller.

        #### Args:
            microsteps (wf_types.uint_16): The microsteps per full step (e.g., 16, 32, 64, etc.). Must be a valid unsigned 16-bit integer.
            steps_per_revolution (wf_types.uint_8, optional): The number of full steps per revolution (typically 200 for 1.8 degree motors). Defaults to 200.
            verbose (bool, optional)

        #### Returns:
            bool: True if the step parameters were successfully set and the response was echoed, False otherwise.

        #### Raises:
            TypeError: If any parameter is of incorrect type (uint_16, uint_8, or boolean).
            RuntimeError: If sending the command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.9, Page 62.

        #### Last Revision:
            2025-11-04 13:12 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsetting step parameters...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_uint16(microsteps): raise TypeError("microsteps must be a valid uint_16.")
        if not TypeCheck.is_uint8(steps_per_revolution): raise TypeError("steps_per_revolution must be a valid uint_8.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Create an empty response list.
        response = []

        # Try protect...
        try:
            # Write microsteps value to register 0x0084.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0084,
                register_value = microsteps,
                response_length = 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to set step parameters: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to set step parameters: {e}")

        # Check response.
        if response == command: 
            self.configuration["microsteps_per_step"] = microsteps
            self.configuration["steps_per_revolution"] = steps_per_revolution
            self.configuration["degrees_per_microstep"] = 360.0 / (microsteps * steps_per_revolution)
            if verbose: Console.fancy_print("<GOOD>step parameters set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set step parameters.</BAD>")
            return False

    def set_working_current(self, working_current_ma: wf_types.uint_16, verbose: bool = False) -> bool:
        """
        #### Description:
        Set the working current for the servo motor in milliamps (mA).

        #### Args:
            working_current_ma (wf_types.uint_16): The working current in milliamps. Must be between 250 and 3000 mA for the SERVO42D.
            verbose (bool, optional): If True, enables verbose output for debugging. Defaults to False.

        #### Returns:
            bool: True if the current was successfully set, False otherwise.

        #### Raises:
            TypeError: If working_current_ma is not a valid uint_16 or verbose is not a boolean.
            ValueError: If working_current_ma is outside the valid range of 250-3000 mA.
            RuntimeError: If sending the command fails (e.g., Modbus communication error).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.7, Page 61.

        #### Last Revision:
            2025-11-04 13:14 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsetting working current...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_uint16(working_current_ma): raise TypeError("working_current must be a valid uint_16.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Check the valid range for working current.
        if working_current_ma < 250 or working_current_ma > 3000:
            raise ValueError("working_current must be between 250 and 3000 mA.")

        # Create an empty response list.
        response = []

        # Try protect...
        try:
            # Write current value to register 0x0083.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0083,
                register_value = working_current_ma,
                response_length = 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting to set working current: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting to set working current: {e}")


        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>working current set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set working current.</BAD>")
            return False

    def setup_routine(self, verbose: bool = True) -> bool:
        """
        #### Description:
        This routine executes a series of configuration commands to bring the motor controller to a known baseline state, enabling proper operation with the Modbus library.

        #### Prerequisite Steps:
        Before running this routine, the following steps must be performed on the controller's onboard screen:
        1. Select "Restore" (factory reset) and reset controller.
        2. Select "Cal" to perform a calibration.
        3. Select "MB_RTU" and set to enable.

        #### Function Calls:
        The routine performs the following internal configuration calls:
        * `disable_enable_pin()`
        * `set_work_mode(SR_CLOSE)`
        * `set_serial_mode_motor_enable(ENABLE)`
        * `clear_motor_protection()`
        * `set_working_current(1000 mA)`
        * `set_holding_current_percentage(PERCENT_50)`
        * `set_step_parameters(microsteps=16, steps_per_revolution=200)`
        * `read_all_config_parameters()`

        #### Args:
            verbose (bool, optional)

        #### Returns:
            bool: True if the setup routine completes without raising an exception, False otherwise (though individual failures are handled by called methods).

        #### Raises:
            TypeError: If verbose is not a boolean. 
            RuntimeError: If any critical configuration step fails due to an unhandled exception during the routine execution.

        #### Last Revision:
            2025-11-04 13:14 PM ET, Weston Forbes
        """
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        if verbose: Console.fancy_print("\n<INFO>Running servo setup routine to establish known state...</INFO>")
        
        try:
            # Execute configuration steps
            self.disable_enable_pin(verbose=True)
            self.set_work_mode(wf_types.WorkMode.SR_CLOSE, verbose=True)
            self.set_serial_mode_motor_enable(wf_types.EnableDisable.ENABLE, verbose=True)
            self.clear_motor_protection(verbose=True)
            self.set_working_current(working_current_ma = 1000, verbose = True)
            self.set_holding_current_percentage(wf_types.HoldCurrentPercentage.PERCENT_50, verbose=True)
            self.set_step_parameters(microsteps=16, steps_per_revolution=200, verbose=True)
            self.read_all_config_parameters(verbose=True)
            
            if verbose: Console.fancy_print("<GOOD>Setup routine completed successfully.</GOOD>")
            return True
            
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>Setup routine failed: {e}</BAD>")
            # Re-raise the exception after logging, or return False if failure is acceptable.
            # Given the context of the other methods, re-raising is the safer choice for critical setup.
            raise RuntimeError(f"Setup routine failed: {e}")

    def read_all_config_parameters(self, verbose: bool = False) -> dict:
        """
        #### Description:
        Reads all configuration parameters from controller.

        #### Args:
            verbose (bool, optional)

        #### Returns:
            dict: A dictionary containing all parsed configuration parameters.

        #### Raises:
            TypeError: If verbose parameter is not a boolean.
            RuntimeError: If reading the registers fails due to a communication error.
            ValueError: If the response header is invalid or does not match the expected format for a read operation (e.g., incorrect slave address, function code, or byte count).

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.2, Page 73 (Read parameters). Reference sections 3.2 to 5.4.5 for parameter decoding.

        #### Last Revision:
            2025-11-04 13:17 PM ET, Weston Forbes
        """

        if verbose: Console.fancy_print("<INFO>\nreading all configuration parameters...</INFO>")

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        response = []
        try:
            command, response = self.modbus.read_input_registers(
                slave_address = self.slave_address,
                starting_address = 0x1147,
                register_quantity = 0x0013, # 19 registers * 2 bytes/reg = 38 data bytes + 5 header/CRC = 43 bytes total
                response_length=43,
                verbose = False
            )
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while reading configuration parameters: {e}</BAD>")
            raise RuntimeError(f"exception occurred while reading configuration parameters: {e}")

        parameters = self.configuration

        # Ensure the header is correct. Expected: [Slave, 0x04, 0x26 (38 decimal bytes)]
        if response and response[0] == self.slave_address and response[1] == 0x04 and response[2] == 0x26:
            
            # Pad data with a leading zero to align indices with original code (response[3] is first data byte).
            data = [0] + response 
            
            # --- Parameter Decoding ---
            # Byte 4: Mode (Reg 0x1147)
            match data[4]: 
                case 0: parameters["mode"] = "CR_OPEN"
                case 1: parameters["mode"] = "CR_CLOSE"
                case 2: parameters["mode"] = "CR_vFOC"
                case 3: parameters["mode"] = "SR_OPEN"
                case 4: parameters["mode"] = "SR_CLOSE"
                case 5: parameters["mode"] = "SR_vFOC"
                case _: parameters["mode"] = "unknown"

            # Byte 5: Holding current percentage (Reg 0x1147)
            match data[5]:
                case 0: parameters["hold_current_percentage"] = 10
                case 1: parameters["hold_current_percentage"] = 20
                case 2: parameters["hold_current_percentage"] = 30
                case 3: parameters["hold_current_percentage"] = 40
                case 4: parameters["hold_current_percentage"] = 50
                case 5: parameters["hold_current_percentage"] = 60
                case 6: parameters["hold_current_percentage"] = 70
                case 7: parameters["hold_current_percentage"] = 80
                case 8: parameters["hold_current_percentage"] = 90
                case _: parameters["hold_current_percentage"] = "unknown"

            # Byte 6-7: Working current (mA) (Reg 0x1148)
            parameters["working_current_mA"] = (data[6] << 8) | data[7]

            # Byte 8: Microsteps per step (Reg 0x1149)
            parameters["microsteps_per_step"] = data[8]
            
            # Byte 9: Enable pin mode (Reg 0x1149)
            match data[9]:
                case 0: parameters["enable_pin_mode"] = "active low"
                case 1: parameters["enable_pin_mode"] = "active high"
                case 2: parameters["enable_pin_mode"] = "always active"
                case _: parameters["enable_pin_mode"] = "unknown"
            
            # Byte 10: Direction (Reg 0x114A)
            match data[10]:
                case 0: parameters["direction"] = "CW"
                case 1: parameters["direction"] = "CCW"
                case _: parameters["direction"] = "unknown"

            # Byte 11: Auto Screen Off (AutoSDD) (Reg 0x114A)
            match data[11]:
                case 0: parameters["auto_screen_off"] = "disabled"
                case 1: parameters["auto_screen_off"] = "enabled"
                case _: parameters["auto_screen_off"] = "unknown"

            # Byte 12: Stall Protection (Protect) (Reg 0x114B)
            match data[12]:
                case 0: parameters["stall_protection"] = "disabled"
                case 1: parameters["stall_protection"] = "enabled"
                case _: parameters["stall_protection"] = "unknown"

            # Byte 13: Subdivision Interpolation (Mplyer) (Reg 0x114B)
            match data[13]:
                case 0: parameters["subdivision_interpolation"] = "disabled"
                case 1: parameters["subdivision_interpolation"] = "enabled"
                case _: parameters["subdivision_interpolation"] = "unknown"

            # Byte 14: Null (Reg 0x114C)

            # Byte 15: Baud Rate (Reg 0x114C)
            match data[15]:
                case 1: parameters["baud_rate"] = 9600
                case 2: parameters["baud_rate"] = 19200
                case 3: parameters["baud_rate"] = 25000
                case 4: parameters["baud_rate"] = 38400
                case 5: parameters["baud_rate"] = 57600
                case 6: parameters["baud_rate"] = 115200
                case 7: parameters["baud_rate"] = 256000
                case _: parameters["baud_rate"] = "unknown"

            # Byte 16: Slave Address (Reg 0x114D)
            parameters["slave_address"] = data[16]
            
            # Byte 17: Group Address (Reg 0x114D)
            parameters["group_address"] = data[17]

            # Byte 18-19: Response Mode (Reg 0x114E)
            parameters["respond"] = (data[18] << 8) | data[19]
            match parameters["respond"]:
                case 0: parameters["respond_enabled"] = "enabled respond"
                case 1: parameters["respond_enabled"] = "disabled respond"
                case 2: parameters["respond_enabled"] = "enabled active"
                case 3: parameters["respond_enabled"] = "disabled active"
                case _: parameters["respond_enabled"] = "unknown"
            
            # Byte 20: Modbus RTU Enabled (Reg 0x114F)
            match data[20]:
                case 0: parameters["modbus_rtu_enabled"] = "disabled"
                case 1: parameters["modbus_rtu_enabled"] = "enabled"
                case _: parameters["modbus_rtu_enabled"] = "unknown"

            # Byte 21: Key Lock (Reg 0x114F)
            match data[21]:
                case 0: parameters["key_lock"] = "unlocked"
                case 1: parameters["key_lock"] = "locked"
                case _: parameters["key_lock"] = "unknown"

            # Byte 22: Home Trigger Level (Reg 0x1150)
            match data[22]:
                case 0: parameters["home_trigger_level"] = "low"
                case 1: parameters["home_trigger_level"] = "high"
                case _: parameters["home_trigger_level"] = "unknown"

            # Byte 23: Home Direction (Reg 0x1150)
            match data[23]:
                case 0: parameters["home_direction"] = "CW"
                case 1: parameters["home_direction"] = "CCW"
                case _: parameters["home_direction"] = "unknown"

            # Byte 24-25: Home Speed (Reg 0x1151)
            parameters["home_speed"] = (data[24] << 8) | data[25]

            # Byte 26: NULL (Reg 0x1152)

            # Byte 27: Endstop Limit Function (Reg 0x1152)
            match data[27]:
                case 0: parameters["endstop_limit_function"] = "disabled"
                case 1: parameters["endstop_limit_function"] = "enabled"
                case _: parameters["endstop_limit_function"] = "unknown"


            # Byte 28-31: "noLimit" Home Reverse Angle (Reg 0x1153 - 0x1154)
            parameters["nolimit_home_reverse_angle"] = (data[28] << 24) | (data[29] << 16) | (data[30] << 8) | data[31]

            # Byte 32: NULL (Reg 0x1155)

            # Byte 33: Home Mode (Hm-mode) (Reg 0x1155)
            match data[33]:
                case 0: parameters["home_mode"] = "limited (uses switch)"
                case 1: parameters["home_mode"] = "no limit (stall homing)"
                case _: parameters["home_mode"] = "unknown"


            # Byte 34-35: "noLimit" Home Current (Reg 0x1156)
            parameters["nolimit_home_current_mA"] = (data[34] << 8) | data[35]

            # Byte 36: NULL (Reg 0x1157)

            # Byte 37: Limit Port Remap (Reg 0x1157)
            match data[37]:
                case 0: parameters["limit_port_remap"] = "disabled"
                case 1: parameters["limit_port_remap"] = "enabled"
                case _: parameters["limit_port_remap"] = "unknown"

            # Byte 38: Power-on Zero Mode (Reg 0x1158)
            match data[38]:
                case 0: parameters["power_on_zero_mode"] = "disabled"
                case 1: parameters["power_on_zero_mode"] = "DirMode"
                case 2: parameters["power_on_zero_mode"] = "NearMode"
                case _: parameters["power_on_zero_mode"] = "unknown"

            # Byte 39: Reserved (FF) (Reg 0x1158) - Skip

            # Byte 40: Power-on Zero Speed (Reg 0x1159)
            parameters["power_on_zero_speed"] = data[40] # Value 0-4

            # Byte 41: Power-on Zero Direction (Reg 0x1159)
            match data[41]:
                case 0: parameters["power_on_zero_direction"] = "CW"
                case 1: parameters["power_on_zero_direction"] = "CCW"
                case _: parameters["power_on_zero_direction"] = "unknown"
        
        else:
            if verbose:
                Console.fancy_print(f"<BAD>Failed to read config. Invalid response header: {[f'0x{b:02X}' for b in response]}</BAD>")
            raise ValueError(f"Failed to read config. Invalid response: {[f'0x{b:02X}' for b in response]}")

        if verbose:
            Console.fancy_print("<GOOD>Configuration parameters read successfully:</GOOD>")
            for key, value in parameters.items():
                Console.fancy_print(f"  - {key}: {value}")
        self.configuration = parameters
        return parameters

    def relative_move_by_degrees(self, direction: wf_types.Direction, acceleration: wf_types.uint_8, speed: wf_types.uint_16, degrees: float, verbose: bool = False) -> bool:
        """
        #### Description:
        Calculates the required microsteps (pulses) for a desired angular movement 
        and executes a relative move command via the `relative_move_by_pulses` method.

        #### Args:
            direction (wf_types.Direction): The direction of movement (CW or CCW).
            acceleration (wf_types.uint_8): The acceleration setting (0-255).
            speed (wf_types.uint_16): The movement speed (0-65535).
            degrees (float): The angular distance to move, in degrees.
            verbose (bool, optional)

        #### Returns:
            bool: True if the relative move command was successfully sent, False otherwise.

        #### Raises:
            TypeError: If any parameter is of incorrect type.
            KeyError: If `degrees_per_microstep` is not defined in `self.configuration`.
            RuntimeError: Propagated from `relative_move_by_pulses` if communication fails.

        #### Documentation:
            Composite method leveraging `set_step_parameters` output for calculation.

        #### Last Revision:
            2025-11-04 13:18 PM ET, Weston Forbes
        """
        if not TypeCheck.is_enum(direction, wf_types.Direction): raise TypeError("direction must be a valid Direction enum.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")
        if not TypeCheck.is_uint8(acceleration): raise TypeError("acceleration must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(speed): raise TypeError("speed must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_float(degrees): raise TypeError("degrees must be a float.")

        try:
            microsteps = int(degrees / self.configuration["degrees_per_microstep"])
        except KeyError:
            if verbose: Console.fancy_print("<BAD>configuration error: 'degrees_per_microstep' not set. run set_step_parameters first.</BAD>")
            raise KeyError("configuration item 'degrees_per_microstep' not found. run set_step_parameters first.")

        # Pass the calculated microsteps to the pulses method.
        # Communication error handling is delegated to relative_move_by_pulses.
        return self.relative_move_by_pulses(direction, acceleration, speed, microsteps, verbose)

    def relative_move_by_pulses(self, direction: wf_types.Direction, acceleration: wf_types.uint_8, speed: wf_types.uint_16, pulses: wf_types.uint_32, verbose: bool = False) -> bool:
        """
        #### Description:
        Sends a relative (incremental) move command to the servo controller.
        #### Args:
            direction (wf_types.Direction): The direction of movement (CW=0x00 or CCW=0x01).
            acceleration (wf_types.uint_8): The acceleration setting (0-255).
            speed (wf_types.uint_16): The movement speed (0-65535).
            pulses (wf_types.uint_32): The distance to move in microsteps (pulses) (0-4,294,967,295).
            verbose (bool, optional)

        #### Returns:
            bool: True if the multi-register write command was successfully sent and acknowledged, 
                  False otherwise.

        #### Raises:
            TypeError: If any parameter is of incorrect type.
            RuntimeError: If sending the command fails due to a communication error.

        #### Documentation:
            MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.4.1, Page 79.

        #### Last Revision:
            2025-11-04 13:20 PM ET, Weston Forbes
        """
        if verbose: Console.fancy_print("<INFO>\nsending relative move by pulses command...</INFO>")

        # Type check parameters.
        if not TypeCheck.is_enum(direction, wf_types.Direction): raise TypeError("direction must be a valid Direction enum.")
        if not TypeCheck.is_uint8(acceleration): raise TypeError("acceleration must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(speed): raise TypeError("speed must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint32(pulses): raise TypeError("pulses must be an unsigned 32-bit integer (0-4294967295).")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Expected successful response for write_multiple_registers is 8 bytes: 
        # [Slave, 0x10, StartAddr_HI, StartAddr_LO, NumRegs_HI, NumRegs_LO, CRC_HI, CRC_LO]
        response = []

        # Try protect...
        try:
            command, response = self.modbus.write_multiple_registers(
                slave_address = self.slave_address,
                starting_address = 0x00FD,
                register_quantity = 0x0004,
                byte_quantity=0x08,
                payload = [
                    # Register 0x00FD (1 byte Direction, 1 byte Acceleration)
                    direction.value,
                    acceleration,
                    
                    # Register 0x00FE (2 bytes Speed)
                    (speed >> 8) & 0xFF,
                    speed & 0xFF,
                    
                    # Register 0x00FF & 0x0100 (4 bytes Pulses) - Big Endian (HI to LO)
                    (pulses >> 8 * 3) & 0xFF,
                    (pulses >> 8 * 2) & 0xFF,
                    (pulses >> 8 * 1) & 0xFF,
                    pulses & 0xFF
                ],
                response_length= 8,
                verbose = verbose
            )
        
        # Catch exceptions.
        except Exception as e:
            if verbose: Console.fancy_print(f"<BAD>exception occurred while attempting relative move by pulses: {e}</BAD>")
            raise RuntimeError(f"exception occurred while attempting relative move by pulses: {e}")

        # Check response.
        if response and response[:6] == [self.slave_address, 0x10, 0x00, 0xFD, 0x00, 0x04]:
            if verbose: Console.fancy_print("<GOOD>relative move by pulses command sent successfully.</GOOD>")
            return True
        else: 
            if verbose: Console.fancy_print("<BAD>failed to send relative move by pulses command (unexpected response).</BAD>")
            return False

    # endregion
    
    # region: Work region--------------------------------------------------------------------------------------------------------


    # endregion

    # region: Needs cleanup------------------------------------------------------------------------------------------------------


    # endregion



