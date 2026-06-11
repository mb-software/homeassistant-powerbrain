"""Select platform for cFos Powerbrain — phase mode selection."""
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import get_entity_deviceinfo
from .__init__ import PowerbrainUpdateCoordinator
from .const import DOMAIN
from .powerbrain import Evse
from .powerbrain import Powerbrain

PHASE_OPTIONS = ["1 phase", "3 phases"]
PHASE_TO_INT = {"1 phase": 1, "3 phases": 7}
# Register 8044: 1 = L1 only (1 phase), 7 = L1+L2+L3 (3 phases)
PHASE_REG_TO_OPTION = {
    1: "1 phase",
    7: "3 phases",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the select entities for powerbrain integration."""
    brain: Powerbrain = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for device in brain.devices.values():
        if device.attributes["is_evse"]:
            entities.append(
                EvsePhaseSelectEntity(
                    hass.data[DOMAIN][entry.entry_id + "_coordinator"],
                    device,
                    "Phase Mode",
                )
            )
    async_add_entities(entities)


class EvsePhaseSelectEntity(CoordinatorEntity, SelectEntity):
    """Select entity for EVSE phase mode (1-phase / 3-phase)."""

    def __init__(
        self,
        coordinator: PowerbrainUpdateCoordinator,
        device: Evse,
        name: str,
    ) -> None:
        """Initialize phase select entity."""
        super().__init__(coordinator)
        self.device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = (
            f"{coordinator.brain.attributes['vsn']['serialno']}"
            f"_{self.device.dev_id}_{name}"
        )
        self._attr_name = name
        self._attr_options = PHASE_OPTIONS
        self._attr_icon = "mdi:sine-wave"

    @callback
    def _handle_coordinator_update(self) -> None:
        # Read register 8044 via Modbus — this is the configured phase mode, not the active one
        # We cache the last known value to avoid blocking calls in the callback
        if hasattr(self, "_phase_reg_value"):
            self._attr_current_option = PHASE_REG_TO_OPTION.get(
                self._phase_reg_value, "3 phases"
            )
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Read initial phase mode from register 8044 when entity is added."""
        await super().async_added_to_hass()
        self._phase_reg_value = await self.hass.async_add_executor_job(
            self.device.get_phase_mode
        )
        self._attr_current_option = PHASE_REG_TO_OPTION.get(
            self._phase_reg_value, "3 phases"
        )

    async def async_select_option(self, option: str) -> None:
        """Change phase mode."""
        phases = PHASE_TO_INT.get(option, 7)
        await self.hass.async_add_executor_job(self.device.set_phase_mode, phases)
        self._phase_reg_value = phases
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)
