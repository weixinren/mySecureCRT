import serial
import serial.tools.list_ports
from PyQt5.QtCore import QObject, QThread, pyqtSignal


class SerialReadThread(QThread):
    data_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)

    def __init__(self, ser):
        super().__init__()
        self._serial = ser
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                if self._serial and self._serial.is_open:
                    waiting = self._serial.in_waiting
                    if waiting > 0:
                        data = self._serial.read(waiting)
                        if data:
                            self.data_received.emit(data)
                    else:
                        self.msleep(10)
                else:
                    break
            except Exception as e:
                if self._running:
                    self.error_occurred.emit(str(e))
                break

    def stop(self):
        self._running = False
        self.wait(100)


PARITY_MAP = {
    "None": serial.PARITY_NONE,
    "Even": serial.PARITY_EVEN,
    "Odd": serial.PARITY_ODD,
    "Mark": serial.PARITY_MARK,
    "Space": serial.PARITY_SPACE,
}

STOPBITS_MAP = {
    1: serial.STOPBITS_ONE,
    1.5: serial.STOPBITS_ONE_POINT_FIVE,
    2: serial.STOPBITS_TWO,
}


class SerialManager(QObject):
    data_received = pyqtSignal(bytes)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    bytes_sent = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial = None
        self._read_thread = None

    @property
    def is_connected(self):
        return self._serial is not None and self._serial.is_open

    def list_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def open(self, port, baudrate, databits, stopbits, parity, flowcontrol):
        self.close()
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=int(baudrate),
                bytesize=int(databits),
                stopbits=STOPBITS_MAP.get(stopbits, serial.STOPBITS_ONE),
                parity=PARITY_MAP.get(parity, serial.PARITY_NONE),
                xonxoff=(flowcontrol == "XON/XOFF"),
                rtscts=(flowcontrol == "RTS/CTS"),
                timeout=0.1,
            )
            self._read_thread = SerialReadThread(self._serial)
            self._read_thread.data_received.connect(self.data_received.emit)
            self._read_thread.error_occurred.connect(self._on_read_error)
            self._read_thread.start()
            self.connection_changed.emit(True)
        except Exception as e:
            self._serial = None
            self.error_occurred.emit(str(e))

    def close(self):
        if self._read_thread:
            self._read_thread.stop()
            self._read_thread = None
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self.connection_changed.emit(False)

    def write(self, data):
        if not self.is_connected:
            return
        try:
            self._serial.write(data)
            self.bytes_sent.emit(len(data))
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _on_read_error(self, msg):
        self.error_occurred.emit(msg)
        self.close()
