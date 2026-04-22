import os
import json
import copy


DEFAULT_CONFIG = {
    "serial": {
        "port": "",
        "baudrate": 115200,
        "databits": 8,
        "stopbits": 1,
        "parity": "None",
        "flowcontrol": "None",
    },
    "display": {
        "mode": "text",
    },
    "window": {
        "width": 900,
        "height": 600,
        "x": 100,
        "y": 100,
    },
}


class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".mySecureCRT")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, "config.json")
        self._path = config_path
        self._data = copy.deepcopy(DEFAULT_CONFIG)

    def load(self):
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self._merge(self._data, saved)
        except (json.JSONDecodeError, IOError):
            pass

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, dotted_key):
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return None
        return node

    def set(self, dotted_key, value):
        keys = dotted_key.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node:
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    def get_all(self):
        return copy.deepcopy(self._data)

    @staticmethod
    def _merge(base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._merge(base[k], v)
            else:
                base[k] = v
