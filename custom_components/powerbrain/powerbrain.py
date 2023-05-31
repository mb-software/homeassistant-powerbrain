"""cFos Powerbrain http API interface."""
import requests

API_GET_VALIDATE_AUTH = "/ui/en/sim.htm"
API_GET_PARAMS = "/cnf?cmd=get_params"
API_GET_DEV_INFO = "/cnf?cmd=get_dev_info"
API_GET_ENTER_RFID = "/cnf?cmd=enter_rfid&rfid="
API_GET_SET_VAR = "/cnf?cmd=set_cm_vars&name="
API_OVERRIDE_DEVICE = "/cnf?cmd=override_device&dev_id="
API_OVERRIDE_FLAG_AMPS = "&mamps="
API_OVERRIDE_FLAGS = "&flags="
API_DEV_ID = "&dev_id="
API_VAR_VAL = "&val="
API_SET_METER = "/cnf?cmd=set_ajax_meter"


class Powerbrain:
    """Powerbrain charging controller class."""

    def __init__(self, host, username, password):
        """Initialize the Powerbrain instance."""
        self.host = host
        self.username = username
        self.password = password
        self.name = ""
        self.devices = {}
        self.attributes = {}
        self.version = 0.0

    def validate_auth(self):
        """Make a request to check if given admin username and password are valid."""
        response = requests.get(
            self.host + API_GET_VALIDATE_AUTH,
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()

    def get_devices(self):
        """Get powerbrain attributes and available devices."""

        dev_info = requests.get(self.host + API_GET_DEV_INFO, timeout=5).json()

        params = dev_info["params"]
        self.name = params["title"]
        self.attributes = params
        version_list = params["version"].split(".")
        self.version = float(version_list[0] + "." + version_list[1])

        for device_attr in dev_info["devices"]:
            if device_attr["device_enabled"]:
                if device_attr["is_evse"]:
                    self.devices[device_attr["dev_id"]] = Evse(device_attr, self)
                else:
                    self.devices[device_attr["dev_id"]] = Meter(device_attr, self)

    def update_device_status(self):
        """Update the device status."""
        dev_info = requests.get(self.host + API_GET_DEV_INFO, timeout=5).json()
        for k, device in self.devices.items():
            attr = next((x for x in dev_info["devices"] if x["dev_id"] == k), "")
            device.update_status(attr)

    def enter_rfid(self, rfid, dev=""):
        """Enter RFID or PIN code."""
        dev_id = ""
        if dev != "":
            dev_id = API_DEV_ID + dev
        requests.get(self.host + API_GET_ENTER_RFID + rfid + dev_id, timeout=5)

    def set_variable(self, name, value):
        """Set value of a charging manager variable"""
        requests.get(
            f"{self.host}{API_GET_SET_VAR}{name}{API_VAR_VAL}{value}",
            timeout=5,
            auth=(self.username, self.password),
        )


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
        response = requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAG_AMPS}{value}",
            timeout=5,
            auth=(self.brain.username, self.brain.password),
        )
        response.raise_for_status()

    def disable_charging(self, disable: bool):
        """Disable or enable charging."""
        response = requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAGS}{'C' if disable else 'c'}",
            timeout=5,
            auth=(self.brain.username, self.brain.password),
        )
        response.raise_for_status()

    def disable_charging_rules(self, disable: bool):
        """Disable or enable evse charging rules."""
        response = requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAGS}{'E' if disable else 'e'}",
            timeout=5,
            auth=(self.brain.username, self.brain.password),
        )
        response.raise_for_status()

    def disable_user_rules(self, disable: bool):
        """Disable or enable user charging rules."""
        response = requests.get(
            f"{self.brain.host}{API_OVERRIDE_DEVICE}{self.dev_id}{API_OVERRIDE_FLAGS}{'U' if disable else 'u'}",
            timeout=5,
            auth=(self.brain.username, self.brain.password),
        )
        response.raise_for_status()


class Meter(Device):
    """Energy meter device"""

    def set_value(self, data):
        """send values of httpinput meter"""
        response = requests.post(
            f"{self.brain.host}{API_SET_METER}{API_DEV_ID}{self.dev_id}",
            json=data,
            timeout=5,
            auth=(self.brain.username, self.brain.password),
        )
        response.raise_for_status()
