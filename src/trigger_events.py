import time
from typing import Optional, List

class RisingEdge:
    def __init__(self, pin, 
                delay: Optional[int] = None, 
                timestamp: Optional[int] = None):
        self.pin = pin
        self.delay = delay
        self.timestamp = timestamp
        self.pulse = None
        if self.timestamp is not None:
            now_ms = int(time.time_ns() / 1e6)
            ts_ms = int(self.timestamp / 1e6)
            ts_delay = max(ts_ms - now_ms, 0)

            if self.delay is not None:
                self.delay += ts_delay
            else:
                self.delay = ts_delay

        elif self.delay is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")

        # Now create the command as string
        self.command = f"({self.pin},{self.delay},1);"

class FallingEdge:
    def __init__(self, pin, 
                 delay: Optional[int] = None, 
                 timestamp: Optional[int] = None):
        self.pin = pin
        self.delay = delay
        self.timestamp = timestamp
        self.pulse = None
        if self.timestamp is not None:
            now_ms = int(time.time_ns() / 1e6)
            ts_ms = int(self.timestamp / 1e6)
            ts_delay = max(ts_ms - now_ms, 0)

            if self.delay is not None:
                self.delay += ts_delay
            else:
                self.delay = ts_delay

        elif self.delay is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")

        # Now create the pulse command as string
        self.command = f"({self.pin},{self.delay},0);"


class Pulse:
    def __init__(self, pin, width, 
                 delay: Optional[int] = None, 
                 timestamp: Optional[int] = None):
        self.pin = pin
        self.delay = delay
        self.width = width
        self.timestamp = timestamp
        self.pulse = None
        if self.timestamp is not None:
            now_ms = int(time.time_ns() / 1e6)
            ts_ms = int(self.timestamp / 1e6)
            ts_delay = max(ts_ms - now_ms, 0)

            if self.delay is not None:
                self.delay += ts_delay
            else:
                self.delay = ts_delay

        elif self.delay is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")

        # Now create the pulse command as string
        self.command = f"({self.pin},{self.delay},1);({self.pin},{self.delay+self.width},0);"

class SyncPulseAndEdge:
    """
    Sends a pulse on one pin and a rising or falling edge on another pin
    as close to simultaneously as possible, by using the same delay for both.
    
    Args:
        pulse_pin (int):        Pin to send the pulse on.
        pulse_width (int):      Width of the pulse in ms.
        edge_pin (int):         Pin to send the rising/falling edge on.
        edge_type (str):        'rising' or 'falling'.
        delay (int, optional):  Delay in ms before both events fire.
        timestamp (int, optional): Absolute timestamp in ns (like time.time_ns()).
    """
    def __init__(self, pulse_pin: int, pulse_width: int,
                 edge_pin: int, edge_type: str,
                 delay: Optional[int] = None,
                 timestamp: Optional[int] = None):

        if edge_type not in ('rising', 'falling'):
            raise ValueError("edge_type must be 'rising' or 'falling'.")

        self.pulse_pin = pulse_pin
        self.pulse_width = pulse_width
        self.edge_pin = edge_pin
        self.edge_type = edge_type
        self.delay = delay
        self.timestamp = timestamp

        if self.timestamp is not None:
            now_ms = int(time.time_ns() / 1e6)
            ts_ms = int(self.timestamp / 1e6)
            ts_delay = max(ts_ms - now_ms, 0)
            if self.delay is not None:
                self.delay += ts_delay
            else:
                self.delay = ts_delay
        elif self.delay is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")

        # Both events use the exact same resolved delay so they fire together
        edge_state = 1 if edge_type == 'rising' else 0
        pulse_cmd = f"({self.pulse_pin},{self.delay},1);({self.pulse_pin},{self.delay + self.pulse_width},0);"
        edge_cmd  = f"({self.edge_pin},{self.delay},{edge_state});"

        self.command = pulse_cmd + edge_cmd        

class PulseSequence:
    def __init__(self, pulses: List[Pulse]):
        if not pulses:
            raise ValueError("PulseSequence must contain at least one Pulse.")

        self.pulses = pulses
        ref_pulse = pulses[0]

        # Ensure timestamp of first pulse is our zero point if it exists
        if ref_pulse.timestamp is not None:
            ref_time = ref_pulse.timestamp
            for i, pulse in enumerate(pulses[1:], start=1):
                # Compute absolute timestamp relative to the first pulse
                if pulse.timestamp is None:
                    delay_ms = pulse.delay if pulse.delay is not None else 0
                    pulse.timestamp = ref_time + delay_ms / 1000.0
                    # Recalculate delay based on new timestamp
                    now_ms = int(time.time() * 1000)
                    ts_ms = int(pulse.timestamp * 1000)
                    pulse.delay = max(ts_ms - now_ms, 0)
                    pulse.command = f"({pulse.pin},{pulse.delay},1);({pulse.pin},{pulse.delay + pulse.width},0);"

        # Now create the command sequence as a string
        self.command = ""
        for pulse in pulses:
            self.command += pulse.command