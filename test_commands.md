# You must set up a coordinator in a conda environment with pyleco installed by running
``` bas
coordinator -p <port_number>
```

- If you do not provide a port_number, it will default to 12300.

# Then, in another terminal, start IPython and run:
``` python
from arduino_trigger.src.trigger_actor import ArduinoActor
from arduino_trigger.src.trigger import find_arduino_ports

devices = find_arduino_ports()
pins = {"Pin2": 0, "Pin3": 1, "Pin4": 2}
device_info = {'port': devices['ports'][0], 'serial_number': devices['serial_numbers'][0], 'pins': pins}
actor = ArduinoActor(name="testing", device_info=device_info, port=<coordinator_port>, host=<"coordinator_ip">,
                    publisher_name="testing", proxy_port=<proxy_port>, proxy_address=<"proxy_ip">)
```

Where you should provide the proper `coordinator_port` and `coordinator_ip`.

- The actor will immediately begin listening for commands from a director upon initialization, which is blocking in this case.

# Then, in a separate terminal, start IPython and run:
``` python
from arduino_trigger.src.trigger_director import ArduinoDirector
director = ArduinoDirector(actor="testing", name="ArduinoDirector", port=<coordinator_port>, host=<"host_ip">)
```

- You must provide the same name to `actor` which was used as the `name` argument for the actor.
- You also must provide the same `coordinator_port` and `coordinator_ip` to ensure communication.

# Finally, in the same terminal as the director, run:
``` python
from arduino_trigger.src.trigger_events import Pulse
pins = {"Pin2": 0, "Pin3": 1, "Pin4": 2}
pulse1 = Pulse(pin=pins["Pin2"], delay=500, width=100)
director.sendPulse(pulse1.command)
```

This will send a command to the Arduino to emit a pulse with a width of 100 ms with a delay of 500 ms from the time for which the command was received.
