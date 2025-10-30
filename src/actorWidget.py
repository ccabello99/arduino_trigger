from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QSpinBox, QApplication, QLabel
)
from PyQt5.QtCore import pyqtSignal, Qt
import logging
import sys

from trigger import find_arduino_ports
from trigger_actor import ArduinoActor

logger = logging.getLogger(__name__)


class ActorInitDialog(QDialog):
    """Dialog to input parameters for ArduinoActor initialization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Initialize ArduinoActor")
        self.setModal(True)

        layout = QFormLayout(self)

        self.name_input = QLineEdit("shooter")
        self.publisher_input = QLineEdit("shooter")
        self.host_ip_input = QLineEdit("192.168.178.15")
        self.proxy_ip_input = QLineEdit("192.168.178.15")
        self.host_port_input = QSpinBox()
        self.host_port_input.setRange(1, 65535)
        self.host_port_input.setValue(12300)
        self.proxy_port_input = QSpinBox()
        self.proxy_port_input.setRange(1, 65535)
        self.proxy_port_input.setValue(11100)

        layout.addRow("Actor Name:", self.name_input)
        layout.addRow("Publisher Name:", self.publisher_input)
        layout.addRow("Host Address:", self.host_ip_input)
        layout.addRow("Proxy Address:", self.proxy_ip_input)
        layout.addRow("Host Port:", self.host_port_input)
        layout.addRow("Proxy Port:", self.proxy_port_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {
            "name": self.name_input.text().strip(),
            "publisher_name": self.publisher_input.text().strip(),
            "host": self.host_ip_input.text().strip(),
            "port": int(self.host_port_input.value()),
            "proxy_address": self.proxy_ip_input.text().strip(),
            "proxy_port": int(self.proxy_port_input.value())
        }


class ActorWidget(QWidget):
    """Widget that allows initializing and connecting ArduinoActor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.actor = None
        self.connected = False  # track connection state

        layout = QVBoxLayout(self)

        self.title = QLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setText("Actor name: ")
        layout.addWidget(self.title, alignment=Qt.AlignCenter)

        # LED indicator
        self.led = QLabel()
        self.led.setFixedSize(20, 20)
        self.led.setAlignment(Qt.AlignCenter)
        self.update_led()  # start as red
        layout.addWidget(self.led, alignment=Qt.AlignCenter)

        # Pins display
        self.pins_label = QLabel()
        self.pins_label.setAlignment(Qt.AlignCenter)
        self.pins_label.setFixedSize(80, 80)
        self.pins_label.setWordWrap(True)
        self.update_pins_display()  # show placeholder at start
        layout.addWidget(self.pins_label, alignment=Qt.AlignCenter)        

        # Buttons
        self.init_button = QPushButton("Connect Actor")
        self.init_button.clicked.connect(self.open_actor_init_dialog)

        self.uninit_button = QPushButton("Disconnect Actor")
        self.uninit_button.clicked.connect(self.close_actor)

        layout.addWidget(self.init_button)
        layout.addWidget(self.uninit_button)
        self.setLayout(layout)

    def update_led(self):
        """Update LED color based on self.connected"""
        color = "green" if self.connected else "red"
        self.led.setStyleSheet(
            f"background-color: {color}; border-radius: 10px; border: 1px solid black;"
        )

    def update_pins_display(self):
        """Update label to show actor pins dictionary"""
        if self.actor and hasattr(self.actor, "pins"):
            text = ", ".join(f"{k}: {v}" for k, v in self.actor.pins.items())
            self.pins_label.setText(f"Pins → {text}")
        else:
            self.pins_label.setText("Pins → (no actor connected)")        

    def open_actor_init_dialog(self):
        dialog = ActorInitDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            try:
                devices = find_arduino_ports()
                pins = {"Shutter": 0, "Detectors": 1, "SDI": 2, "DSCAN": 3, "Aux.": 4}
                device_info = {'port': devices['ports'][0], 'serial_number': devices['serial_numbers'][0], 'pins': pins}
                self.actor = ArduinoActor(device_info=device_info, **values)
                self.actor.start_listening()
                self.connected = True
                self.update_led()
                self.update_pins_display()
                msg = f"ArduinoActor initialized and listening"
                self.title.setText(f"Actor name: {self.actor.name}")
                logger.info(msg)
                QMessageBox.information(self, "Success", msg)
            except Exception as e:
                self.connected = False
                self.update_led()
                self.update_pins_display()
                msg = f"Failed to initialize ArduinoActor: {e}"
                logger.error(msg)
                QMessageBox.critical(self, "Error", msg)

    def close_actor(self):
        try:
            if self.actor:
                self.actor.stop_listening()
            self.actor = None
            self.connected = False
            self.update_led()
            self.update_pins_display()
            msg = f"ArduinoActor uninitialized and stopped listening"
            self.title.setText(f"Actor name: ")
            logger.info(msg)
            QMessageBox.information(self, "Success", msg)
        except Exception as e:
            msg = f"Failed to uninitialize ArduinoActor: {e}"
            logger.error(msg)
            QMessageBox.critical(self, "Error", msg)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    widget = ActorWidget()
    widget.setWindowTitle("ArduinoActor Connector")
    widget.resize(300, 150)
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
