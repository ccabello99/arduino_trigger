try:
    from serial import Serial, SerialException
except ImportError:
    Serial = None
    SerialException = None

import os
import re
import pyduinocli
import time
from typing import Optional
from serial.tools import list_ports
from qtpy import QtCore
from pyleco.utils.data_publisher import DataPublisher
from trigger_events import Pulse

def find_arduino_ports():
    ports = list_ports.comports()
    arduino_ports = {'ports': [], 'serial_numbers': []}

    for port in ports:
        if port.manufacturer == None:
            continue
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
        response_lines = []
        while self.arduino.in_waiting:
            line = self.arduino.readline().decode(errors='ignore').strip()
            if line:
                response_lines.append(line)
        return "\n".join(response_lines)

    def calculate_crc(self,data):
        crc = 0
        for char in data:
            crc ^= ord(char)
        return crc
        
    def write_to_device(self, signal: str):
        crc = self.calculate_crc(signal)
        signal = f"<{signal}{crc}>"
        self.arduino.write(signal.encode('utf-8'))
        QtCore.QThread.msleep(500)
        return self.read_response()
    
    def stop(self):
        response = self.write_to_device("STOP;")
        print(response)
        # Tell proxy server we have issued a command
        metadata = {"trigger_metadata": {}}
        metadata['trigger_metadata']['trigger_command'] = "STOP;"
        metadata['trigger_metadata']['response'] = response
        metadata['trigger_metadata']['message_type'] = "stop"
        metadata['trigger_metadata']['description'] = f"Stopped all events, set all pins to zero, and clear all planned events"
        
        if self.data_publisher is not None:
            self.data_publisher.send_data({self.data_publisher.full_name:
                                            {'metadata': metadata,
                                            'message_type': 'trigger',
                                            'serial_number': self.serial_number}})
        return response
    
    def createPulse(self, pin: int, width: int, delay: Optional[int] = None, timestamp: Optional[int] = None):
        if delay is None and timestamp is None:
            raise ValueError("Either 'delay' or 'timestamp' must be provided.")
        return Pulse(pin, width, delay, timestamp)
    
    def sendRisingEdge(self, event: str):
        response = self.write_to_device(event)
        print(response)

        match = re.match(r"\((\d+),(\d+),(\d+)\);", event)
        if match:
            pin = int(match.group(1))
            delay = int(match.group(2))

        metadata = {"trigger_metadata": {}}
        metadata['trigger_metadata']['trigger_command'] = event
        metadata['trigger_metadata']['response'] = response
        metadata['trigger_metadata']['message_type'] = "send_rising_edge"
        metadata['trigger_metadata']['description'] = f"Sending a rising edge to pin {pin} with delay of {delay} ms"
        
        if self.data_publisher is not None:
            self.data_publisher.send_data({self.data_publisher.full_name:
                                            {'metadata': metadata,
                                            'message_type': 'trigger',
                                            'serial_number': self.serial_number}})
        return response
    
    def sendFallingEdge(self, event: str):
        response = self.write_to_device(event)
        print(response)

        match = re.match(r"\((\d+),(\d+),(\d+)\);", event)
        if match:
            pin = int(match.group(1))
            delay = int(match.group(2))

        metadata = {"trigger_metadata": {}}
        metadata['trigger_metadata']['trigger_command'] = event
        metadata['trigger_metadata']['response'] = response
        metadata['trigger_metadata']['message_type'] = "send_falling_edge"
        metadata['trigger_metadata']['description'] = f"Sending a falling edge to pin {pin} with delay of {delay} ms"
        
        if self.data_publisher is not None:
            self.data_publisher.send_data({self.data_publisher.full_name:
                                            {'metadata': metadata,
                                            'message_type': 'trigger',
                                            'serial_number': self.serial_number}})
        return response

    def sendPulse(self, pulse: str):
        response = self.write_to_device(pulse)
        print(response)

        match = re.match(r"\((\d+),(\d+),1\);\(\d+,(\d+),0\);", pulse)
        if match:
            pin = int(match.group(1))
            delay = int(match.group(2))
            delay2 = int(match.group(3))
            width = delay2 - delay

        metadata = {"trigger_metadata": {}}
        metadata['trigger_metadata']['trigger_command'] = pulse
        metadata['trigger_metadata']['response'] = response
        metadata['trigger_metadata']['message_type'] = "send_pulse"
        metadata['trigger_metadata']['description'] = f"Sending a pulse to pin {pin} with delay of {delay} ms and pulse width of {width} ms"
        
        if self.data_publisher is not None:
            self.data_publisher.send_data({self.data_publisher.full_name:
                                            {'metadata': metadata,
                                            'message_type': 'trigger',
                                            'serial_number': self.serial_number}})
        return response

    def sendPulseSequence(self, sequence: str):
        response = self.write_to_device(sequence)
        print(response)


        # Regular expression to match each pair of ON and OFF events
        pattern = r"\((\d+),(\d+),1\);\(\d+?,(\d+),0\);"
        matches = re.findall(pattern, sequence)
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

        metadata = {"trigger_metadata": {}}
        metadata['trigger_metadata']['trigger_command'] = sequence
        metadata['trigger_metadata']['response'] = response
        metadata['trigger_metadata']['message_type'] = "send_pulse_sequence"
        metadata['trigger_metadata']['description'] = f"Sending a pulse sequence of {num_pulses} pulses to pin {pin} with delays of {delays} ms and pulse widths of {widths} ms"
        
        if self.data_publisher is not None:
            self.data_publisher.send_data({self.data_publisher.full_name:
                                            {'metadata': metadata,
                                            'message_type': 'trigger',
                                            'serial_number': self.serial_number}})
        return response

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
                cli.upload(sketch=os.path.dirname(self.compiledHexPath), fqbn="arduino:avr:uno", port=self._port)
                print("Upload successful.")
    
                if self.arduino:
                    self.arduino.setDTR(False)
                    time.sleep(0.5)
                    self.arduino.setDTR(True)
    
                    # Wait for Arduino to reboot
                    time.sleep(2)
    
                    # Optional: clear the input buffer to remove garbage
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
        trigger = None