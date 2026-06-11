"""Sensor platform."""
import logging
import types
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import get_entity_deviceinfo
from .__init__ import PowerbrainUpdateCoordinator
from .const import DOMAIN
from .powerbrain import Device
from .powerbrain import Powerbrain

_LOGGER = logging.getLogger(__name__)

PAUSE_REASON_MAP = {
    0: "None",
    1: "Current limit",
    2: "Charging rules",
    3: "Manual pause",
    4: "Phase switch",
    5: "Error",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Config entry example."""
    brain: Powerbrain = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device in brain.devices.values():
        if not device.attributes["is_evse"]:
            entities.extend(
                create_meter_entities(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"], device
                )
            )
        else:
            entities.extend(
                create_evse_entities(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"], device
                )
            )

    async_add_entities(entities)


class PowerbrainDeviceSensor(CoordinatorEntity, SensorEntity):
    """Powerbrain device sensors."""

    def __init__(
        self,
        coordinator: PowerbrainUpdateCoordinator,
        device: Device,
        attr: str,
        name: str,
        unit: str = None,
        deviceclass: str = None,
        stateclass: str = None,
        state_modifier: Any = None,
        nested_path: list = None,
    ) -> None:
        """Initialize sensor attributes."""
        super().__init__(coordinator)
        self.device = device
        self.attribute = attr
        self.state_modifier = state_modifier
        self.nested_path = nested_path  # e.g. ["evse", "cp_state"]
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{self.device.dev_id}_{name}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = deviceclass
        self._attr_state_class = stateclass

    def _get_raw_value(self):
        """Get raw value from device attributes, supporting nested paths."""
        if self.nested_path:
            value = self.device.attributes
            for key in self.nested_path:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        return self.device.attributes.get(self.attribute)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        raw = self._get_raw_value()
        if raw is None:
            return

        new_value = 0
        if self.state_modifier is None:
            new_value = raw
        elif isinstance(self.state_modifier, types.LambdaType):
            new_value = self.state_modifier(raw)
        else:
            new_value = raw * self.state_modifier

        if (
            self._attr_native_value is None
            or new_value >= self._attr_native_value
            or self._attr_state_class != SensorStateClass.TOTAL_INCREASING
        ):
            self._attr_native_value = new_value
            self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)


def create_meter_entities(coordinator: PowerbrainUpdateCoordinator, device: Device):
    """Create the entities for a powermeter device."""
    ret = []

    power_unit = "W"
    if "is_va" in device.attributes:
        if device.attributes["is_va"]:
            power_unit = "VA"
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "power_w" if coordinator.brain.version >= 1.2 else "power",
            "Power", power_unit, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "import", "Import", "kWh",
            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "export", "Export", "kWh",
            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "current_l1", "Current L1", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "current_l2", "Current L2", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "current_l3", "Current L3", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "voltage_l1", "Voltage L1", "V",
            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "voltage_l2", "Voltage L2", "V",
            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "voltage_l3", "Voltage L3", "V",
            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT,
        )
    )
    return ret


def create_evse_entities(coordinator: PowerbrainUpdateCoordinator, device: Device):
    """Create the entities for an evse device."""
    ret = []

    # ── Existing sensors ──────────────────────────────────────────────────────

    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device,
            "power_w" if coordinator.brain.version >= 1.2 else "cur_charging_power",
            "Charging Power", "W", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "total_energy", "Total Charging Energy", "kWh",
            SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "state", "State",
            state_modifier=lambda s: {
                1: "1: Standby",
                2: "2: Car connected",
                3: "3: Charging",
                4: "4: Charging/vent",
                5: "5: Error",
                6: "6: Offline",
            }.get(s, f"Unknown ({s})"),
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "current_l1", "Current L1", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "current_l2", "Current L2", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "current_l3", "Current L3", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )

    # ── New sensors ───────────────────────────────────────────────────────────

    # Session energy (Wh → kWh). Resets each charging session.
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "ta_en", "Session Energy", "kWh",
            SensorDeviceClass.ENERGY, SensorStateClass.MEASUREMENT, 0.001,
        )
    )

    # Last commanded charging current (mA → A)
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "last_set_charging_cur", "Last Set Charging Current", "A",
            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, 0.001,
        )
    )

    # Number of phases currently in use
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "used_phases", "Used Phases",
            None, None, SensorStateClass.MEASUREMENT,
        )
    )

    # Pause reason (human-readable)
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "pause_reason", "Pause Reason",
            state_modifier=lambda r: PAUSE_REASON_MAP.get(r, f"Unknown ({r})"),
        )
    )

    # Pause remaining time in seconds (0 when not paused)
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "pause_time", "Pause Time Remaining", "s",
            SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT,
        )
    )

    # CP (Control Pilot) state — from nested evse object
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "cp_state", "CP State",
            nested_path=["evse", "cp_state"],
        )
    )

    # PP (Proximity Pilot) state — cable detection
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "pp_state", "PP State",
            nested_path=["evse", "pp_state"],
        )
    )

    # Total cumulative charging duration in seconds
    ret.append(
        PowerbrainDeviceSensor(
            coordinator, device, "charging_dur", "Total Charging Duration", "s",
            SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING,
        )
    )

    return ret
