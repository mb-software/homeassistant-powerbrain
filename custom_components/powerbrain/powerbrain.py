"""cFos Powerbrain http API interface."""
import requests

API_GET_VALIDATE_AUTH = "/ui/en/sim.htm"
API_GET_PARAMS = "/cnf?cmd=get_params"
API_SET_PARAMS = "/cnf?cmd=set_params"
API_GET_DEV_INFO = "/cnf?cmd=get_dev_info"
API_GET_ENTER_RFID = "/cnf?cmd=enter_rfid&rfid="
API_GET_SET_VAR = "/cnf?cmd=set_cm_vars&name="
API_OVERRIDE_DEVICE = "/cnf?cmd=override_device&dev_id="
API_OVERRIDE_FLAG_AMPS = "&mamps="
API_OVERRIDE_FLAGS = "&flags="
API_DEV_ID = "&dev_id="
API_VAR_VAL = "&val="
API_SET_METER = "/cnf?cmd=set_ajax_meter"
API_GET_DEVICES_CFG = "/cnf?cmd=get_devices"
API_SET_DEVICE_CFG = "/cnf?cmd=set_device"


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
        """Set value of a charging manager variable."""
        requests.get(
            f"{self.host}{API_GET_SET_VAR}{name}{API_VAR_VAL}{value}",
            timeout=5,
            auth=(self.username, self.password),
        )

    def set_params(self, params: dict):
        """Set global Charging Manager parameters via POST.

        Supported keys include: min_pause_time, disable_policy, max_total_current,
        reserve_current, lb_enabled, feed_in_tariff, price_model, surplus_expr, etc.
        """
        response = requests.post(
            self.host + API_SET_PARAMS,
            json=params,
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()

    def get_charging_rules(self, dev_id: str) -> list:
        """Get current charging rules for a device via get_devices (full config).

        Returns list of rule dicts with cFos native format:
            ctype   (int)   condition type (0=always/time, 1=solar surplus, ...)
            atype   (int)   action type (0=set current, 10=pause)
            aexpr   (int)   action value (current in mA, or 1 for pause)
            days    (int)   weekday bitfield (bit0=Mon...bit6=Sun, 127=all)
            time    (int)   start time in minutes since midnight
            dur     (int)   duration in minutes
            udur    (int)   undercut duration in seconds
            flags   (int)   rule flags (16=normal, 18=end-on-finish)
            ena     (bool)  rule enabled
            cmt     (str)   comment/name for the rule
            id      (int)   rule id (0 = auto-assigned)
        """
        response = requests.get(
            self.host + API_GET_DEVICES_CFG,
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()
        devices_cfg = response.json()
        device = next(
            (d for d in devices_cfg if d["dev_id"] == dev_id), None
        )
        if device is None:
            raise ValueError(f"Device {dev_id} not found")
        crule_set = device.get("crule_set") or {}
        rule_set = crule_set.get("rule_set") or {}
        return rule_set.get("", [])

    def set_charging_rules(self, dev_id: str, rules: list):
        """Set charging rules for a specific device via set_device (full config).

        Reads current device config via get_devices, replaces crule_set.rule_set['']
        with the provided rules list, and POSTs to cmd=set_device.

        Each rule is a dict with cFos native format (see get_charging_rules).
        Common rule templates:

        Time-based charging rule (e.g. 22:00-07:00 at 16A every day):
            {
                'cmt': 'Overnight',
                'days': 127,
                'ctype': 0,       # 0 = no condition / time window
                'atype': 0,       # 0 = set to value (current in mA)
                'aexpr': 16000,   # 16A
                'time': 1320,     # 22:00 = 22*60
                'dur': 540,       # 9h = 540 min
                'udur': 0,
                'flags': 16,
                'ena': True,
                'id': 0,
            }

        Pause rule (e.g. pause for 5 min if solar < 3000W):
            {
                'cmt': 'Pause low solar',
                'days': 127,
                'ctype': 1,       # 1 = solar surplus condition
                'atype': 10,      # 10 = pause
                'aexpr': 1,
                'cexpr': 3000,    # threshold in W
                'udur': 300,
                'flags': 18,
                'ena': True,
                'id': 0,
            }
        """
        import json as _json
        # Fetch full device config
        response = requests.get(
            self.host + API_GET_DEVICES_CFG,
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()
        devices_cfg = response.json()
        device = next(
            (d for d in devices_cfg if d["dev_id"] == dev_id), None
        )
        if device is None:
            raise ValueError(f"Device {dev_id} not found")

        # Ensure crule_set structure exists
        if not device.get("crule_set"):
            device["crule_set"] = {"rule_set": {"": []}, "selected_id": ""}
        if "rule_set" not in device["crule_set"]:
            device["crule_set"]["rule_set"] = {"": []}
        if "" not in device["crule_set"]["rule_set"]:
            device["crule_set"]["rule_set"][""] = []

        device["crule_set"]["rule_set"][""] = rules

        # POST updated device config (UI format: '{ "devices": [<dev>]}')
        payload = '{ "devices": [' + _json.dumps(device) + ']}'
        response = requests.post(
            self.host + API_SET_DEVICE_CFG,
            data=payload,
            headers={"Content-Type": "application/json"},
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()

    def set_phase_mode(self, dev_id: str, phases: int):
        """Set phase mode for an EVSE.

        phases: 1 = single-phase (L1 only), 3 = three-phase (L1+L2+L3).
        Uses Modbus register 8044 via device=meter1 (built-in EVSE Modbus alias).
        Value: 1 = L1 only, 7 = L1+L2+L3.
        Note: used_phases in get_dev_info reflects active phases during charging;
        the register value is the configured target applied on next session start.
        """
        value = 1 if phases == 1 else 7
        response = requests.get(
            f"{self.host}/cnf?cmd=modbus&device=meter1&write=8044&value={value}",
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()

    def get_phase_mode(self) -> int:
        """Read current phase mode from Modbus register 8044 (device=meter1).

        Returns 1 for single-phase or 7 for three-phase.
        """
        response = requests.get(
            f"{self.host}/cnf?cmd=modbus&device=meter1&read=8044",
            timeout=5,
            auth=(self.username, self.password),
        )
        response.raise_for_status()
        return int(response.json())


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

    def get_charging_rules(self) -> list:
        """Get current charging rules for this EVSE."""
        return self.brain.get_charging_rules(self.dev_id)

    def set_charging_rules(self, rules: list):
        """Set charging rules for this EVSE. See Powerbrain.set_charging_rules for rule format."""
        self.brain.set_charging_rules(self.dev_id, rules)

    def set_phase_mode(self, phases: int):
        """Set phase mode: 1 = single-phase, 3 = three-phase."""
        self.brain.set_phase_mode(self.dev_id, phases)

    def get_phase_mode(self) -> int:
        """Read current configured phase mode from register 8044. Returns 1 or 7."""
        return self.brain.get_phase_mode()


class Meter(Device):
    """Energy meter device"""

    def set_value(self, data):
        """Send values to an HTTP input meter.

        Supported keys (see cFos HTTP API docs):
            power_va        (int)   Active power in W or VA
            import_wh       (int)   Imported energy in Wh
            export_wh       (int)   Exported energy in Wh
            voltage         (list)  [v1, v2, v3] in V
            current         (list)  [c1, c2, c3] in mA
            is_va           (bool)  True if power is in VA
            soc             (int)   State of charge 0-100% (storage meters only)
        """
        response = requests.post(
            f"{self.brain.host}{API_SET_METER}{API_DEV_ID}{self.dev_id}",
            json=data,
            timeout=5,
            auth=(self.brain.username, self.brain.password),
        )
        response.raise_for_status()


