%run trigger_leco.py

actor = ArduinoActor(name="testing", device_port=ports[0], pins=pins, port=<host port>, host="<host ip addr>", namespace="<host namespace>")


# in a separate terminal run:
director = ArduinoDirector(actor="testing", name="ArduinoDirector", port=<coordinator port>, host="<host ip addr>",namespace="<coordinator namespace>")

# then in this terminal
%run pulse.py
pulse1 = Pulse(pin=pins["Pin2"], delay=500, width=100)
director.sendPulse(pulse1.pulse)

