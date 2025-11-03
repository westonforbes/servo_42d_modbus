import wf_servo
from wf_console import Console
import wf_types

Console.clear()
Console.fancy_print("<INFO>servo 42d modbus test</INFO>")

# Initialize the servo instance.
Console.fancy_print("<INFO>initializing servo...</INFO>")
servo = wf_servo.Servo42dModbus(com_port='COM4', slave_address=1, execute_setup_routine=False)
Console.fancy_print("<GOOD>servo initialized.</GOOD>")
Console.press_enter_pause()

# Loop the main menu.
while True:
    Console.clear()

    # Create main menu.
    menu_options = [
        "run setup routine",
        "set working current",
        "set holding current percentage",
        "relative move by pulses",
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

    elif str_selection == "set working current":
        Console.clear()
        Console.fancy_print("<BAD>WARNING: inputs are not sanitized at the input prompt. invalid values will cause the script to error out.</BAD>")
        Console.fancy_print("<BAD>WARNING: invalid values will not write to the controller.</BAD>")
        working_current = Console.fancy_input("what value would you like to set the working current to (in mA) (250 to 3000):")
        Console.fancy_print("<INFO>setting working current...</INFO>")
        result = servo.set_working_current(working_current_ma = int(working_current), verbose=True)
        if result:
            Console.fancy_print("<GOOD>working current set successfully.</GOOD>")
        else:
            Console.fancy_print("<BAD>failed to set working current.</BAD>")
        Console.press_enter_pause()

    elif str_selection == "set holding current percentage":
        Console.clear()
        Console.fancy_print("<BAD>WARNING: inputs are not sanitized at the input prompt. invalid values will cause the script to error out.</BAD>")
        Console.fancy_print("<BAD>WARNING: invalid values will not write to the controller.</BAD>")
        Console.fancy_print("holding current percentage options:")
        for option in wf_types.HoldCurrentPercentage:
            Console.fancy_print(f" - {option.name} ({option.value}0%)")
        holding_current_percentage = Console.fancy_input("what value would you like to set the holding current percentage to (type the enumeration 'PERCENT_XX'):")
        holding_current_percentage_enum = wf_types.HoldCurrentPercentage[holding_current_percentage]
        Console.fancy_print("<INFO>setting holding current percentage...</INFO>")
        result = servo.set_holding_current_percentage(holding_current_percentage = holding_current_percentage_enum, verbose=True)
        if result:
            Console.fancy_print("<GOOD>holding current percentage set successfully.</GOOD>")
        else:
            Console.fancy_print("<BAD>failed to set holding current percentage.</BAD>")
        Console.press_enter_pause()

    elif str_selection == "relative move by pulses":
        Console.fancy_print(f"<INFO>relative move by pulses...</INFO>")
        result = servo.relative_move_by_pulses(direction = wf_types.Direction.CW, acceleration = 100, speed = 1000, pulses = 50000, verbose=True)
        if result:
            Console.fancy_print("<GOOD>relative move command sent successfully.</GOOD>")
        else:
            Console.fancy_print("<BAD>failed to send relative move command.</BAD>")
        Console.press_enter_pause()

    elif str_selection == "exit":
        Console.fancy_print("<INFO>exiting...</INFO>")
        exit(0)