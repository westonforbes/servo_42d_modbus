from wf_console import Console
from wf_types import TypeCheck
import wf_types

import serial

class Modbus:

    # Declare class parameters.
    slave_address: int
    serial_connection: serial.Serial

    def __init__(self, slave_address, com_port: str, timeout: float = 1.0):
        
        # Set slave address.
        self.slave_address = slave_address

        # Open serial connection.
        try: self.serial_connection = self._open_serial_connection(port=com_port)
        except Exception as e: raise e

    def read_holding_registers(self, slave_address: wf_types.uint_8, starting_address: wf_types.uint_16, register_quantity: wf_types.uint_16, verbose: bool = False) -> tuple[list[int], list[int]]:
        """
        Read holding registers using Modbus RTU Function Code 0x03.
        
        Args:
            slave_address: Modbus slave device address (0-255)
            starting_address: Address of the first register to read (0-65535)
            register_quantity: Number of registers to read (1-125)
            verbose: Enable debug output
            
        Returns:
            tuple[list[int], list[int]]: Command packet and response packet from the device
            
        Raises:
            TypeError: If any parameter is not the correct type or range
        """
        
        # Validate parameters.
        if not TypeCheck.is_uint8(slave_address): raise TypeError("slave_address must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(starting_address): raise TypeError("starting_address must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint16(register_quantity): raise TypeError("register_quantity must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean value (True or False).")

        # Function code to read holding registers.
        function_code = 0x03

        # Build the packet without CRC.
        packet = bytearray()
        packet.append(slave_address)
        packet.append(function_code)
        packet.append((starting_address >> 8) & 0xFF)  # High byte of starting address
        packet.append(starting_address & 0xFF)         # Low byte of starting address
        packet.append((register_quantity >> 8) & 0xFF) # High byte of register quantity
        packet.append(register_quantity & 0xFF)        # Low byte of register quantity
        
        # Calculate and append CRC.
        crc = Modbus._calculate_modbus_crc(packet)
        packet.extend(crc)

        # Convert packet to list of integers for transmission.
        command_packet = list(packet)
        
        # Send packet and receive response.
        response_packet = self._send_and_receive_packet(command_packet=command_packet, verbose=verbose)

        # Return packets.
        return command_packet, response_packet

    def read_input_registers(self, slave_address: wf_types.uint_8, starting_address: wf_types.uint_16, register_quantity: wf_types.uint_16, verbose: bool = False) -> tuple[list[int], list[int]]:
        """
        Read input registers using Modbus RTU Function Code 0x04.
        
        Args:
            slave_address: Modbus slave device address (0-255)
            starting_address: Address of the first register to read (0-65535)
            register_quantity: Number of registers to read (1-125)
            verbose: Enable debug output
            
        Returns:
            tuple[list[int], list[int]]: Command packet and response packet from the device
            
        Raises:
            TypeError: If any parameter is not the correct type or range
        """
        
        # Validate parameters.
        if not TypeCheck.is_uint8(slave_address): raise TypeError("slave_address must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(starting_address): raise TypeError("starting_address must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint16(register_quantity): raise TypeError("register_quantity must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean value (True or False).")

        # Function code to read input registers.
        function_code = 0x04

        # Build the packet without CRC.
        packet = bytearray()
        packet.append(slave_address)
        packet.append(function_code)
        packet.append((starting_address >> 8) & 0xFF)  # High byte of starting address
        packet.append(starting_address & 0xFF)         # Low byte of starting address
        packet.append((register_quantity >> 8) & 0xFF) # High byte of register quantity
        packet.append(register_quantity & 0xFF)        # Low byte of register quantity
        
        # Calculate and append CRC.
        crc = Modbus._calculate_modbus_crc(packet)
        packet.extend(crc)

        # Convert packet to list of integers for transmission.
        command_packet = list(packet)
        
        # Send packet and receive response.
        response_packet = self._send_and_receive_packet(command_packet=command_packet, verbose=verbose)

        # Return packets.
        return command_packet, response_packet

    def write_single_register(self, slave_address: wf_types.uint_8, register_address: wf_types.uint_16, register_value: wf_types.uint_16, verbose: bool = False) -> list[int]:
        """
        Write a single register using Modbus RTU Function Code 0x06.
        
        Args:
            slave_address: Modbus slave device address (0-255)
            register_address: Address of the register to write (0-65535)
            register_value: 16-bit value to write to the register (0-65535)
            verbose: Enable debug output
            
        Returns:
            list[int]: Response packet from the device
            
        Raises:
            TypeError: If any parameter is not the correct type or range
        """
        
        # Validate parameters.
        if not TypeCheck.is_uint8(slave_address): raise TypeError("slave_address must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(register_address): raise TypeError("register_address must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint16(register_value): raise TypeError("register_value must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean value (True or False).")

        # Function code to write single register.
        function_code = 0x06

        # Build the packet without CRC.
        packet = bytearray()
        packet.append(slave_address)
        packet.append(function_code)
        packet.append((register_address >> 8) & 0xFF)  # High byte of register address
        packet.append(register_address & 0xFF)         # Low byte of register address
        packet.append((register_value >> 8) & 0xFF)    # High byte of register value
        packet.append(register_value & 0xFF)           # Low byte of register value
        
        # Calculate and append CRC.
        crc = Modbus._calculate_modbus_crc(packet)
        packet.extend(crc)

        # Convert packet to list of integers for transmission.
        command_packet = list(packet)
        
        # Send packet and receive response.
        response_packet = self._send_and_receive_packet(command_packet=command_packet, verbose=verbose)

        # Return packets.
        return command_packet, response_packet

    def write_multiple_registers(self, slave_address: wf_types.uint_8, starting_address: wf_types.uint_16, register_quantity: wf_types.uint_16, byte_quantity: wf_types.uint_8, payload: list[int], verbose: bool = False) -> list[int]:

        # Validate parameters.
        if not TypeCheck.is_uint8(slave_address): raise TypeError("slave_address must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_uint16(starting_address): raise TypeError("starting_address must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint16(register_quantity): raise TypeError("register_quantity must be an unsigned 16-bit integer (0-65535).")
        if not TypeCheck.is_uint8(byte_quantity): raise TypeError("byte_quantity must be an unsigned 8-bit integer (0-255).")
        if not TypeCheck.is_int_list(payload): raise TypeError("payload must be a list of integers.")
        if not TypeCheck.is_bool(verbose): raise TypeError("verbose must be a boolean value (True or False).")
        
        # Function code to write multiple registers.
        function_code = 0x10 
        
        # Build the packet without CRC.
        packet = bytearray()
        packet.append(slave_address)
        packet.append(function_code)
        packet.append((starting_address >> 8) & 0xFF)  # High byte of starting address
        packet.append(starting_address & 0xFF)         # Low byte of starting address
        packet.append((register_quantity >> 8) & 0xFF)  # High byte of register quantity
        packet.append(register_quantity & 0xFF)         # Low byte of register quantity
        packet.append(byte_quantity)
        packet.extend(payload)

        # Calculate and append CRC.
        crc = Modbus._calculate_modbus_crc(packet)
        packet.extend(crc)

        # Convert packet to list of integers for transmission.
        command_packet = list(packet)

        # Send packet and receive response.
        response_packet = self._send_and_receive_packet(command_packet=command_packet, verbose=verbose)

        # Return packets.
        return command_packet, response_packet

    def _send_and_receive_packet(self, command_packet: list[int], verbose: bool = False) -> list[int]:
        
        # Send command packet.
        self.serial_connection.write(bytearray(command_packet))

        # Read response packet.
        response = self.serial_connection.readline()  # Readline is blocking by timeout length by default.

        # Convert response to list of integers.
        response_packet = list(response)

        # Debug output.
        if verbose:
            Console.fancy_print(f"<DATA>     sent command packet: {[f'0x{b:02X}' for b in command_packet]}</DATA>")
            Console.fancy_print(f"<DATA>received response packet: {[f'0x{b:02X}' for b in response_packet]}</DATA>")

        return response_packet

    def _open_serial_connection(self, port: str, baudrate: int = 38400, timeout: float = 1.0) -> serial.Serial:
        
        try:
            connection = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=timeout
            )
            return connection
        except Exception as e:
            raise RuntimeError(f"could not open serial connection on port '{port}': {e}")

    def _calculate_modbus_crc(data: bytes | bytearray, verbose: bool = False) -> bytearray:
        """
        Calculate CRC-16 checksum for Modbus RTU.
        
        The Modbus RTU protocol uses CRC-16-ANSI (also called CRC-16-IBM) for error detection.
        This is a polynomial-based checksum that can detect most transmission errors.
        
        Args:
            data: bytes or bytearray containing the Modbus message (without CRC)
                Example: [0x01, 0x03, 0x00, 0x00, 0x00, 0x02]
        
        Returns:
            bytes: 2-byte CRC in little-endian format (low byte first, high byte second)
        """
        
        # Step 1: Initialize CRC register to 0xFFFF (all bits set to 1).
        # This is the starting value specified by the Modbus protocol.
        crc = 0xFFFF
        
        # Step 2: Process each byte in the message.
        for byte in data:
            
            # Step 2a: XOR the current byte with the low byte of the CRC register.
            # This "mixes" the data byte into our running CRC calculation.
            crc ^= byte
            
            # Step 2b: Process each bit of the byte (8 bits total).
            # We shift and check bits from LSB (least significant bit) to MSB.
            for _ in range(8):
                
                # Step 2c: Check if the LSB (rightmost bit) is 1.
                # We use bitwise AND with 0x0001 to isolate the LSB.
                # Example: 0b1010_1101 & 0b0000_0001 = 0b0000_0001 (True)
                #          0b1010_1100 & 0b0000_0001 = 0b0000_0000 (False)
                if crc & 0x0001:
                    
                    # Step 2d: If LSB is 1, shift right by 1 bit (divide by 2)
                    # This drops the LSB off the right side.
                    # Example: 0b1010_1101 >> 1 = 0b0101_0110
                    crc >>= 1
                    
                    # Step 2e: XOR with the polynomial 0xA001.
                    # This is the Modbus polynomial in reversed bit order.
                    # The polynomial creates the mathematical properties that
                    # make CRC good at detecting errors.
                    # 0xA001 = 0b1010_0000_0000_0001.
                    crc ^= 0xA001
                    
                else:
                    # Step 2f: If LSB is 0, just shift right by 1 bit.
                    # No polynomial XOR needed in this case.
                    crc >>= 1
        
        # Step 3: Extract the low byte and high byte from the 16-bit CRC.
        # Modbus RTU transmits CRC in LITTLE-ENDIAN format (low byte first).
        # 
        # crc & 0xFF extracts the low byte (bits 0-7)
        # Example: 0x1234 & 0xFF = 0x34
        #
        # (crc >> 8) & 0xFF shifts right 8 bits and extracts the high byte
        # Example: (0x1234 >> 8) & 0xFF = 0x12 & 0xFF = 0x12
        #
        # bytes([...]) converts the list of integers to a bytes object
        final_checksum = bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        
        # Debug output.
        if verbose:
            Console.fancy_print(f"<DATA>CRC-16-ANSI Checksum: {[f'0x{b:02X}' for b in final_checksum]}</DATA>")
        
        return final_checksum
