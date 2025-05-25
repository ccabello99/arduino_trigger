try:
    from serial import Serial, SerialException
except ImportError:
    Serial = None
    SerialException = None

import os
import numpy as np
import pyduinocli
import time
from serial.tools import list_ports
from qtpy import QtCore

def find_arduino_ports():
    ports = list_ports.comports()
    arduino_ports = []

    for port in ports:
        if port.manufacturer == None:
            continue
        if "Arduino" in port.manufacturer:
            arduino_ports.append(port.device)

    return arduino_ports
            

class ArduinoTrigger:
    def __init__(self, device_port, pins):
        self.device_port = device_port
        self.pins = pins
        self.arduino = Serial(device_port, 115200, timeout=1, rtscts=False, dsrdtr=False)
        self.shotNumber = 0
    
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
        return response

    def sendPulse(self, pulse: str):
        response = self.write_to_device(pulse)
        print(response)
        return response

    def sendPulseSequence(self, sequence: str):
        response = self.write_to_device(sequence)
        print(response)
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