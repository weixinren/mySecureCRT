from datetime import datetime


class DataLogger:
    def __init__(self):
        self._file = None
        self._active = False

    @property
    def is_active(self):
        return self._active

    def start(self, file_path):
        self.stop()
        self._file = open(file_path, "a", encoding="utf-8")
        self._active = True
        self._file.write(f"--- Log started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        self._file.flush()

    def stop(self):
        if self._file:
            self._file.write(f"--- Log stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            self._file.flush()
            self._file.close()
            self._file = None
        self._active = False

    def log(self, direction, data):
        if not self._active or not self._file:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            text = data.decode("utf-8", errors="replace")
        except AttributeError:
            text = str(data)
        hex_str = " ".join(f"{b:02X}" for b in data) if isinstance(data, (bytes, bytearray)) else ""
        self._file.write(f"[{timestamp}] {direction}: {text}")
        if hex_str:
            self._file.write(f"  | HEX: {hex_str}")
        self._file.write("\n")
        self._file.flush()
