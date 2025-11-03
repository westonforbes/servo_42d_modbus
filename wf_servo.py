# region: Imports----------------------------------------------------------------------------------------------------------------
from wf_modbus import Modbus
from wf_types import TypeCheck
from wf_console import Console
import wf_types
import time

# endregion

class Servo42dModbus:

    # region: Class attributes---------------------------------------------------------------------------------------------------
    com_port: str
    slave_address: int
    modbus: Modbus
    # endregion

    # region: Initialization-----------------------------------------------------------------------------------------------------
    def __init__(self, com_port: str, slave_address: wf_types.uint_8 = 1, execute_setup_routine: bool = False) -> None:

        # Type check parameters.
        if not TypeCheck.is_str(com_port): raise TypeError("com_port must be a string.")
        if not TypeCheck.is_uint8(slave_address): raise TypeError("slave_address must be an unsigned 8-bit integer (0-255).")

        # Set class attributes.
        self.com_port = com_port
        self.slave_address = slave_address

        # Create a Modbus instance.
        self.modbus = Modbus(slave_address=self.slave_address, com_port=self.com_port)

        # Execute setup routine if specified.
        if execute_setup_routine:
            self.setup_routine(verbose=True)

    # endregion

    # region: Functions that are complete, commented, parameter sanitized and rock-solid-----------------------------------------

    def setup_routine(self, verbose = True) -> bool:
        """
        If you're having issues with the motor, do the following.
        1. Disengage the motor shaft from any mechanical load.
        2. Via the motor screen, scroll down to "Restore" (factory reset) and reset.
        3. Once reset is complete, via the motor screen, scroll down to "MB_RTU" and set to enable.
        4. Initialize this class with the correct COM port and slave address (slave address is 0x01 by default).
        5. Call this setup_routine() method to configure the motor for serial control.
        6. Verify the motor calibrates (movement for a couple of seconds), then stops, then performs a test move.
        7. Re-engage the motor shaft to the mechanical load.
        
        """

        # Calibrate servo. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.5, Page 60.
        #if verbose: Console.fancy_print("<INFO>\ncalibrating motor (required for SR_CLOSE mode)... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.5, Page 60.</INFO>")
        #return_value = self.calibrate(verbose=True)
        #if verbose:
        #    if return_value: Console.fancy_print("<GOOD>Calibration command sent. Wait for device to finish.</GOOD>")
        #    else: Console.fancy_print("<BAD>Failed to send calibration command.</BAD>")
        #time.sleep(15)  # Wait 15 seconds for calibration to complete.

        # Disable the enable pin. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.10, Page 63.
        if verbose: Console.fancy_print("<INFO>\ndisabling enable pin... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.10, Page 63.</INFO>")
        return_value = self.disable_enable_pin(verbose=True)
        if verbose:
            if return_value: Console.fancy_print("<GOOD>enable pin disabled.</GOOD>")
            else: Console.fancy_print("<BAD>failed to disable enable pin.</BAD>")

        # Read the enable status. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.7, Page 58.
        if verbose: Console.fancy_print("<INFO>\nreading enable status... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.7, Page 58.</INFO>")
        return_value = self.read_en_pin_status(verbose=True)
        if verbose:
            if return_value: Console.fancy_print("<GOOD>enabled.</GOOD>")
            else: Console.fancy_print("<BAD>disabled.</BAD>")

        # Set workmode to SR_CLOSE. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.6, Page 61.
        if verbose: Console.fancy_print("<INFO>\nsetting workmode to SR_CLOSE... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.6, Page 61.</INFO>")
        return_value = self.set_work_mode(wf_types.WorkMode.SR_CLOSE, verbose=True)
        if verbose:
            if return_value: Console.fancy_print("<GOOD>workmode set to SR_CLOSE.</GOOD>")
            else: Console.fancy_print("<BAD>failed to set workmode to SR_CLOSE.</BAD>")

        # Enable serial mode motor control. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.20, Page 67.
        if verbose: Console.fancy_print("<INFO>\nallowing serial control of motor... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.20, Page 67.</INFO>")
        return_value = self.set_serial_mode_motor_enable(wf_types.EnableDisable.ENABLE, verbose=True)
        if verbose:
            if return_value: Console.fancy_print("<GOOD>serial control enabled.</GOOD>")
            else: Console.fancy_print("<BAD>failed to enable serial control.</BAD>")

        # Clear motor protection. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.13, Page 64.
        if verbose: Console.fancy_print("<INFO>\nclearing motor protection... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.13, Page 64.</INFO>")
        return_value = self.clear_motor_protection(verbose=True)
        if verbose:
            if return_value: Console.fancy_print("<GOOD>motor protection cleared.</GOOD>")
            else: Console.fancy_print("<BAD>failed to clear motor protection.</BAD>")

        # Read the motor shaft protection status. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.9, Page 58.
        if verbose: Console.fancy_print("<INFO>\nreading motor shaft protection status... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.9, Page 58.</INFO>")
        return_value = self.read_motor_shaft_protection_status(verbose=True)
        if verbose:
            if not return_value: Console.fancy_print("<GOOD>disabled.</GOOD>")
            else: Console.fancy_print("<BAD>enabled.</BAD>")

        # Perform a relative move by pulses to verify communication. Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.4.1, Page 79.
        if verbose: Console.fancy_print("<INFO>\nperforming test relative move by pulses... Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.4.1, Page 79.</INFO>")
        return_value = self.relative_move_by_pulses(direction = wf_types.Direction.CW, acceleration = 100, speed = 1000, pulses = 50000, verbose=True)
        if verbose: Console.fancy_print("<GOOD>test relative move command sent.</GOOD>")

    def calibrate(self, verbose: bool = False) -> bool:
        """
        Calibrates the servo motor.
                
        Args:
            verbose (bool, optional): If True, prints detailed Modbus communication. Defaults to False.
                    
        Returns:
            bool: True if calibration command was successfully sent, False otherwise.
                
        Raises:
            TypeError: If verbose is not a boolean.    
        """

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.5, Page 60.
                
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0080,
            register_value = 0x0001,
            verbose = verbose
        )

        # Check response.
        if response == command: return True
        else: return False

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
                
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0041,
            register_value = 0x0001,
            verbose = verbose
        )

        # Check response.
        if response == command: return True
        else: return False

    def set_work_mode(self, work_mode: wf_types.WorkMode, verbose: bool = False) -> bool:
        """
        Set the work mode of the servo motor.

        Args:
            work_mode (wf_types.WorkMode): The desired work mode for the servo motor.
                Must be a valid WorkMode enum value.
            verbose (bool, optional): If True, enables verbose output during the 
                modbus communication. Defaults to False.
        
        Returns:
            bool: True if the work mode was successfully set (response matches command),
                False otherwise.
        
        Raises:
            TypeError: If verbose is not a boolean or work_mode is not a valid 
                WorkMode enum.
        """
        

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.4, Page 60.

        # Type check parameters.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")
        if not TypeCheck.is_enum(work_mode, wf_types.WorkMode): raise TypeError("work_mode must be a valid WorkMode enum.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x0082,
            register_value = work_mode.value,
            verbose = verbose
        )

        # Check response.
        if response == command: return True
        else: return False

    # endregion

    def read_en_pin_status(self, verbose: bool = False) -> bool:
        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.7, Page 58.

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        command, response = self.modbus.read_input_registers(
            slave_address = self.slave_address,
            starting_address = 0x003A,
            register_quantity = 0x0001,
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
        if bytearray(response) == expected_packet_enabled: return True
        elif bytearray(response) == expected_packet_disabled: return False
        else: raise ValueError("failed to read en pin status from servo.")

    def read_motor_shaft_protection_status(self, verbose: bool = False) -> bool:
        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.1.9, Page 58.

        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Read from register.
        command, response = self.modbus.read_input_registers(
            slave_address = self.slave_address,
            starting_address = 0x003E,
            register_quantity = 0x0001,
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
        if bytearray(response) == expected_packet_enabled: return True
        elif bytearray(response) == expected_packet_disabled: return False
        else: raise ValueError("failed to read shaft protection status from servo.")

    def relative_move_by_pulses(self, direction: wf_types.Direction, acceleration: wf_types.uint_8, speed: wf_types.uint_16, pulses: wf_types.uint_32, verbose: bool = False) -> bool:


        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.3.4.1, Page 79.

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
            verbose = verbose
        )

        # A successful write_multiple_registers response echoes the start address and quantity
        # Expected: [Slave, 0x10, 0x00, 0xFD, 0x00, 0x04, CRC_HI, CRC_LO]
        if response and response[:6] == [self.slave_address, 0x10, 0x00, 0xFD, 0x00, 0x04]:
            return True
        else: 
            return False

    def set_serial_mode_motor_enable(self, enable_disable: wf_types.EnableDisable, verbose: bool = False) -> bool:

        # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.20, Page 67.
                
        # Type check parameter.
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

        # Write to register.
        command, response = self.modbus.write_single_register(
            slave_address = self.slave_address,
            register_address = 0x00 << 8 | 0xF3,
            register_value = 0x00 << 8 | enable_disable.value,
            verbose = verbose
        )

        # Check response.
        if response == command: return True
        else: return False

    def set_homing_parameters(self, 
                                trigger_level: wf_types.TriggerLevel, 
                                direction: wf_types.Direction, 
                                speed: wf_types.uint_16, 
                                endlimit_enable: wf_types.EnableDisable, 
                                verbose: bool = False) -> bool:
            """
            Sets all homing parameters, including the EndLimit feature.
            To disable "homing disables motor", set endlimit_enable to wf_types.EnableDisable.DISABLE.
            
            Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.21, Page 68.
                Register map inferred from Read Config, Section 8.3.2, Page 73 (REG 10-12).
            """

            # Type check parameters.
            if not TypeCheck.is_enum(trigger_level, wf_types.TriggerLevel): raise TypeError("trigger_level must be a valid TriggerLevel enum.")
            if not TypeCheck.is_enum(direction, wf_types.Direction): raise TypeError("direction must be a valid Direction enum.")
            if not TypeCheck.is_uint16(speed): raise TypeError("speed must be an unsigned 16-bit integer (0-65535).")
            if not TypeCheck.is_enum(endlimit_enable, wf_types.EnableDisable): raise TypeError("endlimit_enable must be a valid EnableDisable enum.")
            if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

            # This command writes 3 registers (6 bytes)
            # REG 0x0090: [hmTrig (HI), hmDir (LO)]
            # REG 0x0091: [HmSpeed (HI), HmSpeed (LO)]
            # REG 0x0092: [NULL (HI), EndLimit (LO)]
            
            command, response = self.modbus.write_multiple_registers(
                slave_address = self.slave_address,
                starting_address = 0x0090,
                register_quantity = 0x0003,
                byte_quantity = 0x0006,
                payload = [
                    trigger_level.value & 0xFF,  # REG 0x90 HI: HmTrig (0=Low, 1=High)
                    direction.value & 0xFF,      # REG 0x90 LO: HmDir (0=CW, 1=CCW)
                    (speed >> 8) & 0xFF,         # REG 0x91 HI: HmSpeed
                    speed & 0xFF,                # REG 0x91 LO: HmSpeed
                    0x00,                        # REG 0x92 HI: NULL (Reserved)
                    endlimit_enable.value & 0xFF # REG 0x92 LO: EndLimit (0=Disable, 1=Enable)
                ],
                verbose = verbose
            )

            # A successful write_multiple_registers response echoes the start address and quantity
            # Expected: [Slave, 0x10, 0x00, 0x90, 0x00, 0x03, CRC_HI, CRC_LO]
            # We can just check the first 6 bytes
            if response and response[:6] == [self.slave_address, 0x10, 0x00, 0x90, 0x00, 0x03]:
                return True
            else:
                return False
            
    def release_stall_protection(self, verbose: bool = False) -> bool:
            """
            Releases the motor shaft locked-rotor protection state ("Wrong..." on screen).
            
            Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.2, Page 60.
            """
                    
            # Type check parameter.
            if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

            # Write to register.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x003D,
                register_value = 0x0001,  # 0x0001 = Release
                verbose = verbose
            )

            # Check response. A successful write echoes the command.
            if response == command: 
                return True
            else: 
                return False
            
    def disable_enable_pin(self, verbose: bool = False) -> bool:
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.10, Page 63.

            # Type check parameter.
            if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

            # Write to register.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0085,
                register_value = 0x0002, # Board always active.
                verbose = verbose
            )

            # Check response. A successful write echoes the command.
            if response == command: 
                return True
            else: 
                return False
            
    def clear_motor_protection(self, verbose: bool = False) -> bool:
            # Docs: MKS SERVO42D RS485 User Manual V1.0.6, Section 8.2.13, Page 64.

            # Type check parameter.
            if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean.")

            # Write to register.
            command, response = self.modbus.write_single_register(
                slave_address = self.slave_address,
                register_address = 0x0088,
                register_value = 0x0000,
                verbose = verbose
            )

            # Check response. A successful write echoes the command.
            if response == command: 
                return True
            else: 
                return False
            
# endregion

if __name__ == "__main__":
     
     Console.clear()
     servo = Servo42dModbus(com_port='COM4', slave_address=1, execute_setup_routine=True)