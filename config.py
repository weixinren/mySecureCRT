import os
import json
import copy
import uuid


DEFAULT_CONFIG = {
    "sessions": [],
    "active_session": "",
    "window": {
        "width": 900,
        "height": 600,
        "x": 100,
        "y": 100,
    },
}

DEFAULT_SESSION = {
    "id": "",
    "name": "新会话",
    "renamed": False,
    "serial": {
        "port": "",
        "baudrate": 115200,
        "databits": 8,
        "stopbits": 1,
        "parity": "None",
        "flowcontrol": "None",
    },
    "display": {
        "mode": "terminal",
        "font_size": 14,
    },
}


def new_session_config(name="新会话"):
    """Create a new session config dict with a unique ID."""
    session = copy.deepcopy(DEFAULT_SESSION)
    session["id"] = uuid.uuid4().hex[:8]
    session["name"] = name
    return session


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
        except (json.JSONDecodeError, IOError):
            return

        if "sessions" not in saved:
            saved = self._migrate_v1(saved)

        self._merge(self._data, saved)

    def save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, dotted_key, default=None):
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
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
    def _migrate_v1(old_config):
        """Migrate V1 single-session config to V2 multi-session format."""
        serial_cfg = old_config.get("serial", {})
        display_cfg = old_config.get("display", {})
        port = serial_cfg.get("port", "")
        session = copy.deepcopy(DEFAULT_SESSION)
        session["id"] = uuid.uuid4().hex[:8]
        session["name"] = port if port else "新会话"
        session["renamed"] = False
        session["serial"] = {**DEFAULT_SESSION["serial"], **serial_cfg}
        session["display"] = {**DEFAULT_SESSION["display"], **display_cfg}
        return {
            "sessions": [session],
            "active_session": session["id"],
            "window": old_config.get("window", copy.deepcopy(DEFAULT_CONFIG["window"])),
        }

    @staticmethod
    def _merge(base, override):
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                ConfigManager._merge(base[k], v)
            else:
                base[k] = v
