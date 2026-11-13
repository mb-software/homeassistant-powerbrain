"""Select platform of powerbrain integration."""
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .__init__ import get_entity_deviceinfo
from .__init__ import PowerbrainUpdateCoordinator
from .const import DOMAIN
from .powerbrain import Evse
from .powerbrain import Powerbrain

OWN_RULE_SET_NAME = "Own rule set"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the select entities for powerbrain integration."""
    brain: Powerbrain = hass.data[DOMAIN][entry.entry_id]

    evses = [d for d in brain.devices.values() if d.attributes["is_evse"]]
    if not evses:
        return

    try:
        rule_sets = await hass.async_add_executor_job(brain.get_rule_sets)
    except Exception as exc:
        raise ConfigEntryNotReady("Could not read charging rule sets") from exc

    entities = [
        EvseRuleSetSelectEntity(
            hass.data[DOMAIN][entry.entry_id + "_coordinator"],
            device,
            "Charging Rule Set",
            rule_sets,
        )
        for device in evses
    ]
    async_add_entities(entities)


class EvseRuleSetSelectEntity(CoordinatorEntity, SelectEntity):
    """Select entity to switch the active charging rule set of an evse."""

    def __init__(
        self,
        coordinator: PowerbrainUpdateCoordinator,
        device: Evse,
        name: str,
        rule_sets: list[dict],
    ) -> None:
        """Initialize entity for the charging rule set."""
        super().__init__(coordinator)
        self.device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.brain.attributes['vsn']['serialno']}_{self.device.dev_id}_{name}"
        self._attr_name = name
        self._attr_icon = "mdi:format-list-checks"

        # option label -> set_id; the "own rule set" of the evse has an empty id
        self._options: dict[str, str] = {}
        for rule_set in rule_sets:
            label = rule_set["name"]
            if label in self._options:
                label = f"{label} ({rule_set['set_id']})"
            self._options[label] = rule_set["set_id"]
        if "" not in self._options.values():
            self._options[OWN_RULE_SET_NAME] = ""
        self._attr_options = list(self._options)

    async def async_select_option(self, option: str) -> None:
        """Switch the charging rule set."""
        set_id = self._options[option]
        await self.hass.async_add_executor_job(self.device.switch_rule_set, set_id)
        self.async_write_ha_state()
        # The charging manager reports "ok" even if the credentials are wrong
        # (it then changes the user rule set instead), so verify the result.
        if self.device.overrides.get("rule_set_id") != set_id:
            raise HomeAssistantError(
                "Charging rule set was not changed, please check the admin credentials"
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        """Information of the parent device."""
        return get_entity_deviceinfo(self.device)

    @property
    def current_option(self) -> str | None:
        """Currently active rule set."""
        set_id = self.device.overrides.get("rule_set_id")
        return next((k for k, v in self._options.items() if v == set_id), None)
