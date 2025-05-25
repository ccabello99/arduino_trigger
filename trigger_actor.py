from pyleco.actors.actor import Actor
from trigger import ArduinoTrigger, find_arduino_ports

# Parameters
ports = find_arduino_ports()
pins = {"Pin2": 0, "Pin3": 1, "Pin4": 2}


class ArduinoActor(Actor):
    def __init__(self, name: str, device_port: str, pins: dict, **kwargs):
        super().__init__(name=name, device_class=ArduinoTrigger, **kwargs)
        self.connect(device_port=device_port, pins=pins)
        self.device_port = device_port
        self.pins = pins

        # Register functions for remote calls
        self.register_device_method(self.device.sendPulse)
        self.register_device_method(self.device.sendPulseSequence)
        self.register_device_method(self.device.updateCFile)
        self.register_device_method(self.device.stop)

        # Start listening for incoming messages
        self.listen()



