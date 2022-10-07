"""Number platform of powerbrain integration."""

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import PowerbrainUpdateCoordinator, get_entity_deviceinfo
from .const import DOMAIN
from .powerbrain import Evse, Powerbrain


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the number entities for powerbrain integration."""
    brain: Powerbrain = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device in brain.devices.values():
        if device.attributes["is_evse"]:
            entities.append(
                EvseLimitCurrentEntity(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"],
                    device,
                    "Current Limit Override",
                )
            )
    async_add_entities(entities)


class EvseLimitCurrentEntity(CoordinatorEntity, NumberEntity):
    """Number input for overriding current limit."""

    def __init__(
        self, coordinator: PowerbrainUpdateCoordinator, device: Evse, name: str
    ) -> None:
        """Initialize entity for charging current override."""
        super().__init__(coordinator)
        self.device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{self.device.dev_id}_{name}"
        self._attr_name = name
        self._attr_native_min_value = device.attributes["min_charging_cur"] / 1000
        self._attr_native_max_value = device.attributes["max_charging_cur"] / 1000
        self._attr_native_unit_of_measurement = "A"

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.hass.async_add_executor_job(
            self.device.override_current_limit, value * 1000
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = (
            self.device.attributes.get("ov_cur", self._attr_native_max_value * 1000)
            / 1000
        )
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)
