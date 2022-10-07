"""cFos Powerbrain http API interface."""

import requests

API_GET_PARAMS = "/cnf?cmd=get_params"
API_GET_DEV_INFO = "/cnf?cmd=get_dev_info"
API_OVERRIDE_DEVICE = "/cnf?cmd=override_device&dev_id="
API_OVERRIDE_FLAG_AMPS = "&mamps="
API_OVERRIDE_FLAGS = "&flags="


class Powerbrain:
    """Powerbrain charging controller class."""

    def __init__(self, host):
        """Initialize the Powerbrain instance."""
        self.host = host
        self.name = ""
        self.devices = {}
        self.attributes = {}

    def get_params(self):
        """Get powerbrain attributes and available devices."""

        dev_info = requests.get(self.host + API_GET_DEV_INFO, timeout=5).json()

        params = dev_info["params"]
        self.name = params["title"]
        self.attributes = params

        for device_attr in dev_info["devices"]:
            if device_attr["device_enabled"]:
                if device_attr["is_evse"]:
                    self.devices[device_attr["dev_id"]] = Evse(device_attr, self)
                else:
                    self.devices[device_attr["dev_id"]] = Device(device_attr, self)

    def update_device_status(self):
        """Update the device status."""
        dev_info = requests.get(self.host + API_GET_DEV_INFO, timeout=5).json()
        for k, device in self.devices.items():
            attr = next((x for x in dev_info["devices"] if x["dev_id"] == k), "")
            device.update_status(attr)


class Device:
    """Device connected via Powerbrain."""

    def __init__(self, attr, brain: Powerbrain):
        """Initialize the device instance."""
        self.name = attr["name"]
        self.dev_id = attr["dev_id"]
        self.attributes = attr
        self.brain = brain

    def update_status(self, attr):
        """Update attributes."""
        self.attributes = attr


class Evse(Device):
    """EVSE device."""

    def override_current_limit(self, value: float):
        """Override max charging current."""
        requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAG_AMPS}{value}",
            timeout=5,
        )

    def disable_charging(self, disable: bool):
        """Disable or enable charging."""
        requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAGS}{'C' if disable else 'c'}",
            timeout=5,
        )

    def disable_charging_rules(self, disable: bool):
        """Disable or enable charging rules."""
        requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAGS}{'E' if disable else 'e'}",
            timeout=5,
        )
