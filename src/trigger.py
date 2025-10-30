try:
    from serial import Serial, SerialException
except ImportError:
    Serial = None
    SerialException = None

import os
import re
import pyduinocli
import time
from typing import Optional, List
from serial.tools import list_ports
from qtpy import QtCore
from pyleco.utils.data_publisher import DataPublisher
from trigger_events import Pulse, PulseSequence, RisingEdge, FallingEdge
import platform
import threading

RISING_FALLING_PATTERN = re.compile(r"\((\d+),(\d+),(\d+)\);")
PULSE_SEQUENCE_PATTERN = re.compile(r"\((\d+),(\d+),1\);\(\d+?,(\d+),0\);")

def find_arduino_ports():
    ports = list_ports.comports()
    arduino_ports = {'ports': [], 'serial_numbers': []}

    for port in ports:
        if port.manufacturer == None:
            continue
        if platform.system() == "Windows":
            if port.serial_number == '85133323136351201241':
            	arduino_ports["ports"].append(port.device)
            	arduino_ports["serial_numbers"].append(port.serial_number)
        else:
            if "Arduino" in port.manufacturer:
                arduino_ports["ports"].append(port.device)
                arduino_ports["serial_numbers"].append(port.serial_number)

    return arduino_ports
            

class ArduinoTrigger:
    def __init__(self, device_info: dict, publisher_name: str, proxy_address: str, proxy_port: int):
        self.device_port = device_info['port']
        self.serial_number = device_info['serial_number']
        self.pins = device_info['pins']
        self.arduino = Serial(self.device_port, 115200, timeout=1, rtscts=False, dsrdtr=False)
        self.shotNumber = 0
        self.data_publisher = DataPublisher(full_name=publisher_name, host=proxy_address, port=proxy_port)
    
    def read_response(self):
        start = time.time()
        lines = []
        while time.time() - start < 0.1:  # Wait max 100ms
            if self.arduino.in_waiting:
                line = self.arduino.readline().decode(errors='ignore').strip()
                if line:
                    lines.append(line)
            else:
                time.sleep(0.001)
        return "\n".join(lines)

    def calculate_crc(self,data):
        crc = 0
        for char in data:
            crc ^= ord(char)
        return crc
        
    def write_to_device(self, signal: str):
        crc = self.calculate_crc(signal)
        signal = f"<{signal}{crc}>"
        self.arduino.write(signal.encode('utf-8'))
        self.arduino.flush()

        # Wait only until a response is available (up to 50ms)
        timeout_ms = 50
        wait_time = 0
        while not self.arduino.in_waiting and wait_time < timeout_ms:
            time.sleep(0.001)
            wait_time += 1

        return self.read_response()
    
    def stop(self):
        response = self.write_to_device("STOP;")
        print(response)

        # Tell proxy server we have issued a command
        payload = self.make_metadata_payload("STOP;", response, "stop", 
                                             f"Stopped all events, set all pins to zero, and clear all planned events")
        self.send_data_async(payload)
        return response
    
    def createRisingEdge(self, pin: int, delay: Optional[int] = None, timestamp: Optional[int] = None):
        if delay is None and timestamp is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")
        return RisingEdge(pin=pin, delay=delay, timestamp=timestamp).command
    
    def createFallingEdge(self, pin: int, delay: Optional[int] = None, timestamp: Optional[int] = None):
        if delay is None and timestamp is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")
        return FallingEdge(pin=pin, delay=delay, timestamp=timestamp).command
    
    def createPulse(self, pin: int, width: int, delay: Optional[int] = None, timestamp: Optional[int] = None):
        if delay is None and timestamp is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")
        return Pulse(pin=pin, width=width, delay=delay, timestamp=timestamp).command
    
    def sendRisingEdge(self, event: str):
        response = self.write_to_device(event)
        print(response)

        match = RISING_FALLING_PATTERN.match(event)
        if match:
            pin = int(match.group(1))
            delay = int(match.group(2))

        # Tell proxy server we have issued a command
        payload = self.make_metadata_payload(event, response, "send_rising_edge", 
                                             f"Sending a rising edge to pin {pin} with delay of {delay} ms")
        self.send_data_async(payload)
        return response
    
    def sendFallingEdge(self, event: str):
        response = self.write_to_device(event)
        print(response)

        match = RISING_FALLING_PATTERN.match(event)
        if match:
            pin = int(match.group(1))
            delay = int(match.group(2))
        
        # Tell proxy server we have issued a command
        payload = self.make_metadata_payload(event, response, "send_falling_edge", 
                                             f"Sending a falling edge to pin {pin} with delay of {delay} ms")
        self.send_data_async(payload)
        return response

    def sendPulse(self, pulse: str):
        response = self.write_to_device(pulse)
        print(response)

        match = PULSE_SEQUENCE_PATTERN.match(pulse)
        if match:
            pin = int(match.group(1))
            delay = int(match.group(2))
            delay2 = int(match.group(3))
            width = delay2 - delay
        
        # Tell proxy server we have issued a command
        payload = self.make_metadata_payload(pulse, response, "send_pulse", 
                                             f"Sending a pulse to pin {pin} with delay of {delay} ms and pulse width of {width} ms")
        self.send_data_async(payload)
        return response

    def sendPulseSequence(self, sequence: str):
        response = self.write_to_device(sequence)
        print(response)


        # Regular expression to match each pair of ON and OFF events
        matches = re.findall(PULSE_SEQUENCE_PATTERN, sequence)
        delays = []
        widths = []
        for match in matches:
            pin = int(match[0])
            delay = int(match[1])
            delay2 = int(match[2])
            width = delay2 - delay
            delays.append(delay)
            widths.append(width)

        num_pulses = len(matches)

        # Tell proxy server we have issued a command
        payload = self.make_metadata_payload(sequence, response, "send_pulse_sequence", 
                                             f"Sending a pulse sequence of {num_pulses} pulses to pin {pin} with delays of {delays} ms and pulse widths of {widths} ms")
        self.send_data_async(payload)

        return response

    def send_data_async(self, payload):
        if self.data_publisher is None:
            return

        def send():
            try:
                self.data_publisher.send_data(payload)
            except Exception as e:
                print(f"[send_data_async] Error: {e}")

        thread = threading.Thread(target=send)
        thread.daemon = True
        thread.start()

    def make_metadata_payload(self, command: str, response: str, msg_type: str, description: str):
        return {
            self.data_publisher.full_name: {
                'metadata': {
                    'trigger_command': command,
                    'response': response,
                    'message_type': msg_type,
                    'description': description
                },
                'message_type': 'trigger',
                'serial_number': self.serial_number
            }
        }

    def updateCFile(self, CFilePath: str):
        self.compileCFile(CFilePath)
        self.uploadCompiledFile()
        QtCore.QThread.msleep(2000)
        info = "Arduino sketch compiled and uploaded successfully"
        return info

    def compileCFile(self, CFilePath: str):
        # Initialize Arduino CLI
        cli = arduino = pyduinocli.Arduino("arduino-cli")

        # Define the sketch directory and output paths
        sketch_dir = os.path.dirname(CFilePath)
        self.compiledHexPath = CFilePath.replace(".ino", ".hex")  # For uploading

        try:
            # Compile the sketch
            cli.compile(sketch = sketch_dir,  fqbn="arduino:avr:uno", output_dir=os.path.dirname(self.compiledHexPath))
            print("Compilation successful.")
        except Exception as e:
            print(f"Compilation failed: {str(e)}")

    def uploadCompiledFile(self):
        if hasattr(self, 'compiledHexPath') and self.compiledHexPath:
            cli = pyduinocli.Arduino("arduino-cli")
            try:
                # Close the serial port if it's open
                if hasattr(self, 'arduino') and self.arduino and self.arduino.is_open:
                    print("Closing serial port to allow upload...")
                    self.arduino.close()
                    time.sleep(1)

                # Upload via arduino-cli
                cli.upload(sketch=os.path.dirname(self.compiledHexPath), fqbn="arduino:avr:uno", port=self.device_port)
                print("Upload successful.")

                # Reopen serial port after upload
                self.arduino = Serial(self.device_port, 115200, timeout=1, rtscts=False, dsrdtr=False)
                time.sleep(2)
                self.arduino.reset_input_buffer()

            except Exception as e:
                print(f"Upload failed: {str(e)}")

if __name__ == "__main__":
    # Create an instance on file execution
    arduino_ports = find_arduino_ports()
    if arduino_ports:
        device_port = arduino_ports[0] # Use the first found Arduino port
        pins = [2, 3, 4]
        trigger = ArduinoTrigger(device_port, pins)
        print(f"Arduino trigger initialized on port {device_port} with pins {pins}")
    else:
        print("No Arduino devices found.")