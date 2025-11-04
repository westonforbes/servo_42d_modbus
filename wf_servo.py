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
            Clear motor protection on the motor. This is typically done after a 
            fault or error state to allow motor operation to resume.
                    
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
                bool: True if the register write was successful (response matches command), 
                    False otherwise.
                    
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

    # endregion
    
    # region: Work region--------------------------------------------------------------------------------------------------------


    # endregion

    # region: Needs cleanup------------------------------------------------------------------------------------------------------





    def read_en_pin_status(self, verbose: bool = False) -> bool:
        """
        Read the EN (Enable) pin status from the servo.
        Args:
            verbose (bool, optional)
        Returns:
            bool: True if the EN pin is enabled, False if disabled.
        Raises:
            TypeError: If verbose parameter is not a boolean.
            ValueError: If the response from the servo is invalid or unexpected.
        """
    
        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.7, Page 58.
        if verbose: Console.fancy_print("<INFO>\nreading EN pin status... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.7, Page 58.</INFO>")

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        command, response = self.modbus.read_input_registers(
            slave_address = self.slave_address,
            starting_address = 0x003A,
            register_quantity = 0x0001,
            response_length = 7,
            verbose = verbose
        )

        # Generate expected response for EN pin enabled status.
        expected_packet_enabled = bytearray()
        expected_packet_enabled.append(self.slave_address)           # Slave address.
        expected_packet_enabled.append(0x04)                         # Function code for read input registers.
        expected_packet_enabled.append(0x02)                         # Bytes count (1 register = 2 bytes).
        expected_packet_enabled.append(0x00)                         # Reserved portion of payload.
        expected_packet_enabled.append(0x01)                         # Enabled indication.
        expected_packet_enabled.extend(Modbus._calculate_modbus_crc(expected_packet_enabled))
        
        
        # Generate expected response for EN pin disabled status.
        expected_packet_disabled = bytearray()
        expected_packet_disabled.append(self.slave_address)           # Slave address.
        expected_packet_disabled.append(0x04)                         # Function code for read input registers.
        expected_packet_disabled.append(0x02)                         # Bytes count (1 register = 2 bytes).
        expected_packet_disabled.append(0x00)                         # Reserved portion of payload.
        expected_packet_disabled.append(0x00)                         # Disabled indication.
        expected_packet_disabled.extend(Modbus._calculate_modbus_crc(expected_packet_disabled))
        
        # Check response and extract en pin status.
        if bytearray(response) == expected_packet_enabled: 
            if verbose: Console.fancy_print("<GOOD>EN pin is enabled.</GOOD>")
            return True
        elif bytearray(response) == expected_packet_disabled: 
            if verbose: Console.fancy_print("<GOOD>EN pin is disabled.</GOOD>")
            return False
        else: 
            if verbose: Console.fancy_print("<BAD>failed to read en pin status from servo.</BAD>")
            raise ValueError("failed to read en pin status from servo.")

    def read_motor_shaft_protection_status(self, verbose: bool = False) -> bool:
        """
        Read the motor shaft protection status from the servo controller.
        Args:
            verbose (bool, optional)
        Returns:
            bool: True if motor shaft protection is enabled, False if disabled.
        Raises:
            TypeError: If verbose parameter is not a boolean.
            ValueError: If the response from the servo controller is invalid or
                cannot be interpreted as a valid shaft protection status.
        """


        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.9, Page 58.
        if verbose: Console.fancy_print("<INFO>\nreading motor shaft protection status... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.9, Page 58.</INFO>")

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        command, response = self.modbus.read_input_registers(
            slave_address = self.slave_address,
            starting_address = 0x003E,
            register_quantity = 0x0001,
            response_length = 7,
            verbose = verbose
        )

        # Generate expected response for shaft protection status.
        expected_packet_enabled = bytearray()
        expected_packet_enabled.append(self.slave_address)           # Slave address.
        expected_packet_enabled.append(0x04)                         # Function code for read input registers.
        expected_packet_enabled.append(0x02)                         # Bytes count (1 register = 2 bytes).
        expected_packet_enabled.append(0x00)                         # Reserved portion of payload.
        expected_packet_enabled.append(0x01)                         # Enabled indication.
        expected_packet_enabled.extend(Modbus._calculate_modbus_crc(expected_packet_enabled))
        
        
        # Generate expected response for shaft protection status.
        expected_packet_disabled = bytearray()
        expected_packet_disabled.append(self.slave_address)           # Slave address.
        expected_packet_disabled.append(0x04)                         # Function code for read input registers.
        expected_packet_disabled.append(0x02)                         # Bytes count (1 register = 2 bytes).
        expected_packet_disabled.append(0x00)                         # Reserved portion of payload.
        expected_packet_disabled.append(0x00)                         # Disabled indication.
        expected_packet_disabled.extend(Modbus._calculate_modbus_crc(expected_packet_disabled))
        
        # Check response and extract shaft protection status.
        if bytearray(response) == expected_packet_enabled:
            if verbose: Console.fancy_print("<GOOD>motor shaft protection is enabled.</GOOD>")
            return True
        elif bytearray(response) == expected_packet_disabled:
            if verbose: Console.fancy_print("<GOOD>motor shaft protection is disabled.</GOOD>")
            return False
        else: raise ValueError("failed to read shaft protection status from servo.")

    def restart(self, verbose: bool = False) -> bool:
        """
        Restarts the servo motor.

        Args:
            verbose (bool, optional): If True, prints detailed Modbus communication. Defaults to False.
                    
        Returns:
            bool: True if restart command was successfully sent, False otherwise.
                
        Raises:
            TypeError: If verbose is not a boolean.    
        """

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.4, Page 60.
        if verbose: Console.fancy_print("<INFO>\nrestarting motor... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.4, Page 60.</INFO>")
                
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0041,
            register_value = 0x0001,
            response_length= 8,
            verbose = verbose
        )

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>motor restarted successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to restart motor.</BAD>")
            return False

    def set_zero(self, verbose: bool = False) -> bool:

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.19, Page 67.
        if verbose: Console.fancy_print("<INFO>\nsetting zero... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.19, Page 67.</INFO>")

        # Type check parameters.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0092,
            register_value = 0x0001,
            response_length= 8,
            verbose = verbose
        )

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>zeroed.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to zero.</BAD>")
            return False

    def set_work_mode(self, work_mode: wf_types.WorkMode, verbose: bool = False) -> bool:
        """
        Set the work mode of the servo motor.

        Args:
            work_mode (wf_types.WorkMode): The desired work mode for the servo motor.
                Must be a valid WorkMode enum value.
            verbose (bool, optional)
        
        Returns:
            bool: True if the work mode was successfully set (response matches command),
                False otherwise.
        
        Raises:
            TypeError: If verbose is not a boolean or work_mode is not a valid 
                WorkMode enum.
        """
        
        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.6, Page 61.
        if verbose: Console.fancy_print("<INFO>\nsetting work mode... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.6, Page 61.</INFO>")

        # Type check parameters.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")
        if not TypeCheck.is_enum(work_mode, wf_types.WorkMode): raise TypeError("work_mode must be a valid WorkMode enum.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0082,
            register_value = work_mode.value,
            response_length= 8,
            verbose = verbose
        )

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>work mode set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set work mode.</BAD>")
            return False

    def set_serial_mode_motor_enable(self, enable_disable: wf_types.EnableDisable, verbose: bool = False) -> bool:
        """
        Set the serial mode motor enable state for the servo motor.
        Args:
            enable_disable (wf_types.EnableDisable): The enable/disable state to set for the motor.
            verbose (bool, optional)
        Returns:
            bool: True if the motor enable state was set successfully, False otherwise.
        Raises:
            TypeError: If verbose parameter is not a boolean.
        Note:
            The function writes to register address 0x00F3 with the enable/disable value.
            Success is determined by comparing the command sent with the response received.
        """

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.20, Page 67.
        if verbose: Console.fancy_print("<INFO>\nsetting serial mode motor enable... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.20, Page 67.</INFO>")
                
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x00 << 8 | 0xF3,
            register_value = 0x00 << 8 | enable_disable.value,
            response_length= 8,
            verbose = verbose
        )

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>serial mode motor enable set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set serial mode motor enable.</BAD>")
            return False

    def set_holding_current_percentage(self, holding_current_percentage: wf_types.HoldCurrentPercentage, verbose: bool = False) -> bool:
        """
        Set the holding current percentage for the servo motor.
        This method writes to register 0x0083 to configure the holding current as a percentage
        of the rated current. The holding current is the current supplied to the motor when
        it is stationary to maintain position.
        Args:
            holding_current_percentage (wf_types.HoldCurrentPercentage): The holding current 
                percentage enum value to set.
            verbose (bool, optional): If True, enables verbose output for debugging. 
                Defaults to False.
        Returns:
            bool: True if the command was successfully executed (response matches command),
                False otherwise.
        Raises:
            TypeError: If holding_current_percentage is not a valid HoldCurrentPercentage enum
                or if verbose is not a boolean.
        Note:
            Refer to MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.8, Page 62 for
            detailed documentation.
        """

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.8, Page 62.
        if verbose: Console.fancy_print("<INFO>\nsetting holding current percentage... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.8, Page 62.</INFO>")

        # Type check parameters.
        if not TypeCheck.is_enum(holding_current_percentage, wf_types.HoldCurrentPercentage): raise TypeError("holding_current_percentage must be a valid HoldCurrentPercentage enum.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x009B,
            register_value = holding_current_percentage.value,
            response_length= 8,
            verbose = verbose
        )

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>holding current percentage set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set holding current percentage.</BAD>")
            return False

    def set_step_parameters(self, microsteps: wf_types.uint_16, steps_per_revolution: wf_types.uint_8 = 200, verbose: bool = False) -> bool:

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.9, Page 62.
        if verbose: Console.fancy_print("<INFO>\nsetting step parameters... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.9, Page 62.</INFO>")

        # Type check parameters.
        if not TypeCheck.is_uint16(microsteps): raise TypeError("microsteps must be a valid uint_16.")
        if not TypeCheck.is_uint8(steps_per_revolution): raise TypeError("steps_per_revolution must be a valid uint_8.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0084,
            register_value = microsteps,
            response_length = 8,
            verbose = verbose
        )

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
        Set the working current for the servo motor.
        Args:
            working_current_ma (wf_types.uint_16): The working current in milliamps.
                Must be between 0 and 3000 mA for the SERVO42D motor.
            verbose (bool, optional): Enable verbose output for debugging. Defaults to False.
        Returns:
            bool: True if the current was successfully set, False otherwise.
        Raises:
            TypeError: If working_current_ma is not a valid uint_16 or verbose is not a boolean.
            ValueError: If working_current_ma is outside the valid range of 0-3000 mA.
        Note:
            Based on MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.7, Page 61.
            The valid range is specific to the SERVO42D model and may differ for other models.
        """

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.7, Page 61.
        if verbose: Console.fancy_print("<INFO>\nsetting working current... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.7, Page 61.</INFO>")

        # Type check parameters.
        if not TypeCheck.is_uint16(working_current_ma): raise TypeError("working_current must be a valid uint_16.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Check the valid range for working current. According to the manual, it should be between 0 and 3000 mA for the SERVO42D.
        # Its higher for the SERVO57D but we're focusing on the 42D here. Room for future expansion.
        # Values below 250 mA may not be effective for operation.
        if working_current_ma < 250 or working_current_ma > 3000:
            raise ValueError("working_current must be between 250 and 3000 mA.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0083,
            register_value = working_current_ma,
            response_length = 8,
            verbose = verbose
        )

        # Check response.
        if response == command:
            if verbose: Console.fancy_print("<GOOD>working current set successfully.</GOOD>")
            return True
        else:
            if verbose: Console.fancy_print("<BAD>failed to set working current.</BAD>")
            return False

    def setup_routine(self, verbose = True) -> bool:
        """
        This routine is for getting you to a known baseline that'll enable proper operation.
        Before running this routine:
        1. Via the controllers onboard screen, select "Restore" (factory reset) and reset controller.
        2. Via the controllers onboard screen, select "Cal" to perform a calibration.
        3. Via the controllers onboard screen, select "MB_RTU" and set to enable.
        4. Run this routine.

        Performing these steps will put your motor controller into a known state for the setup routine.
        If you need to abort the routine to do these tasks, press Ctrl + C to interrupt this script.
        """

        # Calibrate servo. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.5, Page 60.
        #if verbose: Console.fancy_print("<INFO>\ncalibrating motor (required for SR_CLOSE mode)... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.5, Page 60.</INFO>")
        #return_value = self.calibrate(verbose=True)
        #if verbose:
        #    if return_value: Console.fancy_print("<GOOD>Calibration command sent. Wait for device to finish.</GOOD>")
        #    else: Console.fancy_print("<BAD>Failed to send calibration command.</BAD>")
        #time.sleep(15)  # Wait 15 seconds for calibration to complete.

        
        self.disable_enable_pin(verbose=True)
        self.set_work_mode(wf_types.WorkMode.SR_CLOSE, verbose=True)
        self.set_serial_mode_motor_enable(wf_types.EnableDisable.ENABLE, verbose=True)
        self.clear_motor_protection(verbose=True)
        self.set_working_current(working_current_ma = 1000, verbose = True)
        self.set_holding_current_percentage(wf_types.HoldCurrentPercentage.PERCENT_50, verbose=True)
        self.set_step_parameters(microsteps=16, steps_per_revolution=200, verbose=True)
        self.read_all_config_parameters(verbose=True)

    def read_all_config_parameters(self, verbose: bool = False) -> dict:

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.2, Page 73.
        if verbose: Console.fancy_print("<INFO>\nreading all configuration parameters... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.2, Page 73.</INFO>")

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        command, response = self.modbus.read_input_registers(
            slave_address = self.slave_address,
            starting_address = 0x1147,
            register_quantity = 0x0013,
            response_length=43,
            verbose = False
        )

        parameters = self.configuration

        # Ensure the header is correct.
        if response and response[0] == self.slave_address and response[1] == 0x04 and response[2] == 0x26:
            
            data = [0] + response
            
            # Byte 4: Mode
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.2, Page 9.
            match data[4]: 
                case 0: parameters["mode"] = "CR_OPEN"
                case 1: parameters["mode"] = "CR_CLOSE"
                case 2: parameters["mode"] = "CR_vFOC"
                case 3: parameters["mode"] = "SR_OPEN"
                case 4: parameters["mode"] = "SR_CLOSE"
                case 5: parameters["mode"] = "SR_vFOC"
                case _: parameters["mode"] = "unknown"

            # Byte 5: Holdling current (as a percentage of working current)
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.4, Page 9.
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

            # Byte 6-7: Working current (mA)
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.3, Page 9.
            parameters["working_current_mA"] = (data[6] << 8) | data[7]

            # Byte 8: Microsteps per step
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.5, Page 9.
            parameters["microsteps_per_step"] = data[8]
            
            # Byte 9: Enable pin mode
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.6, Page 10.
            match data[9]:
                case 0: parameters["enable_pin_mode"] = "active low"
                case 1: parameters["enable_pin_mode"] = "active high"
                case 2: parameters["enable_pin_mode"] = "always active"
                case _: parameters["enable_pin_mode"] = "unknown"
            
            # Byte 10: Direction
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.7, Page 10.
            match data[10]:
                case 0: parameters["direction"] = "CW"
                case 1: parameters["direction"] = "CCW"
                case _: parameters["direction"] = "unknown"

            # Byte 11: Auto Screen Off (AutoSDD)
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.8, Page 10.
            match data[11]:
                case 0: parameters["auto_screen_off"] = "disabled"
                case 1: parameters["auto_screen_off"] = "enabled"
                case _: parameters["auto_screen_off"] = "unknown"

            # Byte 12: Stall Protection (Protect)
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.9, Page 10.
            match data[12]:
                case 0: parameters["stall_protection"] = "disabled"
                case 1: parameters["stall_protection"] = "enabled"
                case _: parameters["stall_protection"] = "unknown"

            # Byte 13: Subdivision Interpolation (Mplyer)
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.10, Page 10.
            match data[13]:
                case 0: parameters["subdivision_interpolation"] = "disabled"
                case 1: parameters["subdivision_interpolation"] = "enabled"
                case _: parameters["subdivision_interpolation"] = "unknown"

            # Byte 14: Null

            # Byte 15: Baud Rate
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.11, Page 10.
            match data[15]:
                case 1: parameters["baud_rate"] = 9600
                case 2: parameters["baud_rate"] = 19200
                case 3: parameters["baud_rate"] = 25000
                case 4: parameters["baud_rate"] = 38400
                case 5: parameters["baud_rate"] = 57600
                case 6: parameters["baud_rate"] = 115200
                case 7: parameters["baud_rate"] = 256000
                case _: parameters["baud_rate"] = "unknown"

            # Byte 16: Slave Address
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 5.2.12, Page 22.
            parameters["slave_address"] = data[16]
            
            # Byte 17: Group Address
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 5.2.16, Page 24.
            parameters["group_address"] = data[17]

            # Byte 18-19: Response Mode
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 5.2.13, Page 23.
            parameters["respond"] = (data[18] << 8) | data[19]
            match parameters["respond"]:
                case 0: parameters["respond_enabled"] = "enabled respond"
                case 1: parameters["respond_enabled"] = "disabled respond"
                case 2: parameters["respond_enabled"] = "enabled active"
                case 3: parameters["respond_enabled"] = "disabled active"
                case _: parameters["respond_enabled"] = "unknown"
            
            # Byte 20: Modbus RTU Enabled
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.14, Page 11.
            match data[20]:
                case 0: parameters["modbus_rtu_enabled"] = "disabled"
                case 1: parameters["modbus_rtu_enabled"] = "enabled"
                case _: parameters["modbus_rtu_enabled"] = "unknown"

            # Byte 21: Key Lock
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 5.2.15, Page 24.
            match data[21]:
                case 0: parameters["key_lock"] = "unlocked"
                case 1: parameters["key_lock"] = "locked"
                case _: parameters["key_lock"] = "unknown"

            # Byte 22: Home Trigger Level
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.19, Page 11.
            match data[22]:
                case 0: parameters["home_trigger_level"] = "low"
                case 1: parameters["home_trigger_level"] = "high"
                case _: parameters["home_trigger_level"] = "unknown"

            # Byte 23: Home Direction
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.20, Page 12.
            match data[23]:
                case 0: parameters["home_direction"] = "CW"
                case 1: parameters["home_direction"] = "CCW"
                case _: parameters["home_direction"] = "unknown"

            # Byte 24-25: Home Speed
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.21, Page 12.
            parameters["home_speed"] = (data[24] << 8) | data[25]

            # Byte 26: NULL

            # Byte 27: Endstop Limit Function
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.24, Page 12.
            match data[27]:
                case 0: parameters["endstop_limit_function"] = "disabled"
                case 1: parameters["endstop_limit_function"] = "enabled"
                case _: parameters["endstop_limit_function"] = "unknown"


            # Byte 28-31: "noLimit" Home Reverse Angle
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 5.4.4, Page 27.
            parameters["nolimit_home_reverse_angle"] = (data[28] << 24) | (data[29] << 16) | (data[30] << 8) | data[31]

            # Byte 32: NULL

            # Byte 33: Home Mode (Hm-mode)
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.22, Page 12.
            match data[33]:
                case 0: parameters["home_mode"] = "limited (uses switch)"
                case 1: parameters["home_mode"] = "no limit (stall homing)"
                case _: parameters["home_mode"] = "unknown"


            # Byte 34-35: "noLimit" Home Current
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.23, Page 12.
            parameters["nolimit_home_current_mA"] = (data[34] << 8) | data[35]

            # Byte 36: NULL

            # Byte 37: Limit Port Remap
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 5.4.5, Page 28.
            match data[37]:
                case 0: parameters["limit_port_remap"] = "disabled"
                case 1: parameters["limit_port_remap"] = "enabled"
                case _: parameters["limit_port_remap"] = "unknown"

            # Byte 38: Power-on Zero Mode
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.15, Page 11.
            match data[38]:
                case 0: parameters["power_on_zero_mode"] = "disabled"
                case 1: parameters["power_on_zero_mode"] = "DirMode"
                case 2: parameters["power_on_zero_mode"] = "NearMode"
                case _: parameters["power_on_zero_mode"] = "unknown"

            # Byte 39: Reserved (FF)

            # Byte 40: Power-on Zero Speed
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.17, Page 11.
            parameters["power_on_zero_speed"] = data[40] # Value 0-4

            # Byte 41: Power-on Zero Direction
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 3.18, Page 11.
            match data[41]:
                case 0: parameters["power_on_zero_direction"] = "CW"
                case 1: parameters["power_on_zero_direction"] = "CCW"
                case _: parameters["power_on_zero_direction"] = "unknown"
        
        else:
            if verbose:
                Console.fancy_print(f"<BAD>Failed to read config. Invalid response: {[f'0x{b:02X}' for b in response]}</BAD>")
            raise ValueError(f"Failed to read config. Invalid response: {[f'0x{b:02X}' for b in response]}")

        if verbose:
            Console.fancy_print("<GOOD>Configuration parameters read successfully:</GOOD>")
            for key, value in parameters.items():
                Console.fancy_print(f"  - {key}: {value}")
        self.configuration = parameters
        return parameters
            
    def relative_move_by_degrees(self, direction: wf_types.Direction, acceleration: wf_types.uint_8, speed: wf_types.uint_16, degrees: float, verbose: bool = False) -> bool:
        
        if not TypeCheck.is_enum(direction, wf_types.Direction): raise TypeError("direction must be a valid Direction enum.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")
        if not TypeCheck.is_uint8(acceleration): raise TypeError("acceleration must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(speed): raise TypeError("speed must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_float(degrees): raise TypeError("degrees must be a float.")

        microsteps = int(degrees / self.configuration["degrees_per_microstep"])
        return self.relative_move_by_pulses(direction, acceleration, speed, microsteps, verbose)

    def relative_move_by_pulses(self, direction: wf_types.Direction, acceleration: wf_types.uint_8, speed: wf_types.uint_16, pulses: wf_types.uint_32, verbose: bool = False) -> bool:

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.4.1, Page 79.
        if verbose: Console.fancy_print("<INFO>\nsending relative move by pulses command... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.4.1, Page 79.</INFO>")

        # Type check parameters.
        if not TypeCheck.is_enum(direction, wf_types.Direction): raise TypeError("direction must be a valid Direction enum.")
        if not TypeCheck.is_uint8(acceleration): raise TypeError("acceleration must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(speed): raise TypeError("speed must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint32(pulses): raise TypeError("pulses must be an unsigned 32-bit integer (0-4294967295).")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # --- CORRECTION: Byte order for Reg 0x00FD must be HI-LO (Acceleration-Direction) ---
        
        command, response = self.modbus.write_multiple_registers(
            slave_address = self.slave_address,
            starting_address = 0x00FD,
            register_quantity = 0x0004,
            byte_quantity=0x08,
            payload = [
                direction.value,
                acceleration,
                (speed >> 8) & 0xFF,            # Byte 2
                speed & 0xFF,                         # Byte 3
                
                # Reg 0xFF & 0x100: Pulses (4 bytes, HI to LO) - correct
                (pulses >> 8* 3) & 0xFF,     # Byte 4 (Pulse DWord Byte 3)
                (pulses >> 8* 2) & 0xFF,     # Byte 5 (Pulse DWord Byte 2)
                (pulses >> 8* 1) & 0xFF,     # Byte 6 (Pulse DWord Byte 1)
                pulses & 0xFF               # Byte 7 (Pulse DWord Byte 0)
            ],
            response_length= 8,
            verbose = verbose
        )

        # A successful write_multiple_registers response echoes the start address and quantity
        # Expected: [Slave, 0x10, 0x00, 0xFD, 0x00, 0x04, CRC_HI, CRC_LO]
        if response and response[:6] == [self.slave_address, 0x10, 0x00, 0xFD, 0x00, 0x04]:
            if verbose: Console.fancy_print("<GOOD>relative move by pulses command sent successfully.</GOOD>")
            return True
        else: 
            if verbose: Console.fancy_print("<BAD>failed to send relative move by pulses command.</BAD>")
            return False

    # endregion



