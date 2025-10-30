from trigger_actor import ArduinoActor
from trigger import find_arduino_ports

devices = find_arduino_ports()
pins = {"Shutter": 0, "Detectors": 1, "SDI": 2, "DSCAN": 3, "Aux.": 4}
device_info = {'port': devices['ports'][0], 'serial_number': devices['serial_numbers'][0], 'pins': pins}
actor = ArduinoActor(name="shooter_actor", device_info=device_info, port=12300, host="192.168.178.15", publisher_name="shooter_actor", proxy_address="192.168.178.15", proxy_port=11100)