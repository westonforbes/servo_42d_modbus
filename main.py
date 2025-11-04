import wf_servo
from wf_console import Console
import wf_types
import time

Console.clear()
Console.fancy_print("<INFO>servo 42d modbus test</INFO>")

# Initialize the servo instance.
Console.fancy_print("<INFO>initializing servo...</INFO>")
servo = wf_servo.Servo42dModbus(com_port='COM4', slave_address=1, microsteps_per_step=16, steps_per_revolution=200)
Console.fancy_print("<GOOD>servo initialized.</GOOD>")
Console.press_enter_pause()

# Loop the main menu.
while True:
    Console.clear()

    # Create main menu.
    menu_options = [
        "run setup routine",
        "set zero",
        "relative move 90 degrees CW (negative)",
        "relative move 90 degrees CCW (positive)",
        "relative move 360 degrees CCW (positive)",
        "move at speed for 5 seconds",
        "read motor shaft protection status",
        "read encoder value",
        "reset",
        "exit"
    ]
    int_selection, str_selection = Console.integer_only_menu_with_validation("main menu", menu_options, "select an option: ")

    Console.clear()

    if str_selection == "run setup routine":
        Console.fancy_print("<INFO>running setup routine...</INFO>")
        text = """
        Before running this routine:
        1. Via the controllers onboard screen, select "Restore" (factory reset) and reset controller.
        2. Via the controllers onboard screen, select "Cal" to perform a calibration.
        3. Via the controllers onboard screen, select "MB_RTU" and set to enable.
        4. Run this routine.

        Performing these steps will put your motor controller into a known state for the setup routine.
        If you need to abort the routine to do these tasks, press Ctrl + C to interrupt this script.
        """
        Console.fancy_print(text)
        Console.press_enter_pause()
        result = servo.setup_routine()
        Console.fancy_print("<GOOD>setup routine completed.</GOOD>")
        Console.press_enter_pause()

    elif str_selection == "set zero":
        Console.fancy_print("<INFO>setting zero...</INFO>")
        servo.set_zero(verbose=True)
        Console.fancy_print("<GOOD>zero set.</GOOD>")
        Console.press_enter_pause()

    elif str_selection == "relative move 90 degrees CW (negative)":
        Console.fancy_print("<INFO>moving 90 degrees CW...</INFO>")
        servo.relative_move_by_degrees(direction=wf_types.Direction.CW, acceleration=100, speed=1000, degrees=90.0, verbose=True)
        Console.fancy_print("<GOOD>move completed.</GOOD>")
        Console.press_enter_pause()

    elif str_selection == "relative move 90 degrees CCW (positive)":
        Console.fancy_print("<INFO>moving 90 degrees CCW...</INFO>")
        servo.relative_move_by_degrees(direction=wf_types.Direction.CCW, acceleration=100, speed=1000, degrees=90.0, verbose=True)
        Console.fancy_print("<GOOD>move completed.</GOOD>")
        Console.press_enter_pause()

    elif str_selection == "relative move 360 degrees CCW (positive)":
        Console.fancy_print("<INFO>moving 360 degrees CCW...</INFO>")
        servo.relative_move_by_degrees(direction=wf_types.Direction.CCW, acceleration=100, speed=1000, degrees=360.0, verbose=True)
        Console.fancy_print("<GOOD>move completed.</GOOD>")
        Console.press_enter_pause()

    elif str_selection == "move at speed for 5 seconds":
        Console.fancy_print("<INFO>moving at speed for 5 seconds...</INFO>")
        servo.move_at_speed(direction=wf_types.Direction.CCW, acceleration=100, speed=2000, verbose=True)
        for i in range(5, 0, -1):
            Console.clear()
            Console.fancy_print(f"<INFO>time remaining: {i} seconds...</INFO>")
            time.sleep(1)
        servo.move_at_speed(direction=wf_types.Direction.CCW, acceleration=255, speed=0, verbose=True)
        Console.fancy_print("<GOOD>move completed.</GOOD>")
        Console.press_enter_pause()

    elif str_selection == "read encoder value":
        Console.fancy_print("<INFO>reading encoder value...</INFO>")
        encoder_value = servo.read_encoder_value(verbose=True)
        Console.press_enter_pause()

    elif str_selection == "read motor shaft protection status":
        Console.fancy_print("<INFO>reading motor shaft protection status...</INFO>")
        status = servo.read_motor_shaft_protection_status(verbose=True)
        Console.press_enter_pause()

    elif str_selection == "reset":
        Console.fancy_print("<INFO>resetting controller...</INFO>")
        result = servo.restart(verbose=True)
        if result:
            Console.fancy_print("<GOOD>controller reset.</GOOD>")
        else:
            Console.fancy_print("<BAD>controller reset failed.</BAD>")
        Console.press_enter_pause()

    elif str_selection == "exit":
        Console.fancy_print("<INFO>exiting...</INFO>")
        exit(0)
