from pyleco.actors.actor import Actor
from trigger import ArduinoTrigger, find_arduino_ports
from pyleco.utils.events import Event, SimpleEvent

# Parameters
ports = find_arduino_ports()
pins = {"Pin2": 0, "Pin3": 1, "Pin4": 2}

class ArduinoActor(Actor):
    def __init__(self, name: str, device_info: dict, publisher_name: str, proxy_address: str, proxy_port: int, **kwargs):
        super().__init__(name=name, device_class=ArduinoTrigger, **kwargs)
        self.connect(device_info=device_info, publisher_name=publisher_name, proxy_address=proxy_address, proxy_port=proxy_port)
        self.device_port = device_info['port']
        self.pins = device_info['pins']

        # Register functions for remote calls
        self.register_device_method(self.device.createPulse)
        self.register_device_method(self.device.sendPulse)
        self.register_device_method(self.device.sendPulseSequence)
        self.register_device_method(self.device.updateCFile)
        self.register_device_method(self.device.stop)
        
        # Start listening for incoming messages
        self.listen()

    def listen(self, stop_event: Event = SimpleEvent(), waiting_time: int = 100, **kwargs) -> None:
        """Listen for zmq communication until `stop_event` is set or until KeyboardInterrupt.

        :param stop_event: Event to stop the listening loop.
        :param waiting_time: Time to wait for a readout signal in ms.
        """
        self.stop_event = stop_event
        poller = self._listen_setup(**kwargs)
        # Loop
        try:
            while not stop_event.is_set():
                self._listen_loop_element(poller=poller, waiting_time=waiting_time)
        except KeyboardInterrupt:
            pass
        finally:
            # Make sure to close port connection when we stop listening
            self.device.arduino.close()
            print(f"Connection to arduino on port {self.device_port} has been closed.")
            self._listen_close(waiting_time=waiting_time)
