import wf_servo
import time
from wf_console import Console
Console.clear()
Console.fancy_print("<INFO>servo 42d modbus test</INFO>")

CALIBRATE_SERVO = True

# Initialize the servo instance.
Console.fancy_print("<INFO>initializing servo...</INFO>")
servo = wf_servo.Servo42dModbus(com_port='COM4',
                                 slave_id=1,
                                 work_current=100,
                                 hold_current_percent=wf_servo.HoldCurrentPercentage.PERCENT_10,
                                 steps_per_revolution=200,
                                 micro_steps_per_step=16)
Console.fancy_print("<GOOD>servo initialized.</GOOD>")

# Calibrate the servo.
if CALIBRATE_SERVO:
    Console.fancy_print("<INFO>calibrating servo...</INFO>")
    servo.calibrate()
    time.sleep(10)
    Console.fancy_print("<GOOD>servo calibrated.</GOOD>")

servo.move_relative_by_pulses(wf_servo.Direction.CW, 20, 200, 5000)
