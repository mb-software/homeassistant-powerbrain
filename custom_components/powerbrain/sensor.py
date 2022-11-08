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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Config entry example."""
    # assuming API object stored here by __init__.py
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
    ) -> None:
        """Initialize sensor attributes."""
        super().__init__(coordinator)
        self.device = device
        self.attribute = attr
        self.state_modifier = state_modifier
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{self.device.dev_id}_{name}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = deviceclass
        self._attr_state_class = stateclass

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        new_value = 0
        if self.state_modifier is None:
            new_value = self.device.attributes[self.attribute]
        elif isinstance(self.state_modifier, types.LambdaType):
            new_value = self.state_modifier(self.device.attributes[self.attribute])
        else:
            new_value = self.device.attributes[self.attribute] * self.state_modifier

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

    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "power",
            "Power",
            "VA" if device.attributes["is_va"] else "W",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "import",
            "Import",
            "kWh",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "export",
            "Export",
            "kWh",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "current_l1",
            "Current L1",
            "A",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "current_l2",
            "Current L2",
            "A",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "current_l3",
            "Current L3",
            "A",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "voltage_l1",
            "Voltage L1",
            "V",
            SensorDeviceClass.VOLTAGE,
            SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "voltage_l2",
            "Voltage L2",
            "V",
            SensorDeviceClass.VOLTAGE,
            SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "voltage_l3",
            "Voltage L3",
            "V",
            SensorDeviceClass.VOLTAGE,
            SensorStateClass.MEASUREMENT,
        )
    )
    return ret


def create_evse_entities(coordinator: PowerbrainUpdateCoordinator, device: Device):
    """Create the entities for an evse device."""
    ret = []

    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "cur_charging_power",
            "Charging Power",
            "W",
            SensorDeviceClass.POWER,
            SensorStateClass.MEASUREMENT,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "total_energy",
            "Total Charging Energy",
            "kWh",
            SensorDeviceClass.ENERGY,
            SensorStateClass.TOTAL_INCREASING,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "state",
            "State",
            state_modifier=lambda s: {
                1: "1: Standby",
                2: "2: Car connected",
                3: "3: Charging",
                4: "4: Charging/vent",
                5: "5: Error",
                6: "6: Offline",
            }[s],
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "current_l1",
            "Current L1",
            "A",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "current_l2",
            "Current L2",
            "A",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            0.001,
        )
    )
    ret.append(
        PowerbrainDeviceSensor(
            coordinator,
            device,
            "current_l3",
            "Current L3",
            "A",
            SensorDeviceClass.CURRENT,
            SensorStateClass.MEASUREMENT,
            0.001,
        )
    )
    return ret
