"""
Custom integration to integrate cFos Powerbrain with Home Assistant.

For more details about this integration, please refer to
https://github.com/mb-software/homeassistant-powerbrain
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PASSWORD
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.const import CONF_USERNAME
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN
from .powerbrain import Device
from .powerbrain import Powerbrain

_LOGGER = logging.getLogger(__name__)

# List the platforms that you want to support.
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH, Platform.SELECT]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        new = {**entry.data}
        new[CONF_USERNAME] = "admin"
        new[CONF_PASSWORD] = ""

        entry.version = 2
        hass.config_entries.async_update_entry(entry, data=new)

    _LOGGER.debug("Migrating to version %s successful", entry.version)

    return True


async def async_setup(hass: HomeAssistant, config):
    """Setup integration and services."""

    async def handle_enter_rfid(call):
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                dev_id = call.data.get("dev_id", "")
                hass.async_add_executor_job(
                    brain.enter_rfid, str(call.data.get("rfid")), dev_id
                )

    async def handle_set_meter(call):
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                dev_id = call.data.get("dev_id", "")
                data = {}
                if "power" in call.data:
                    data["power_va"] = call.data.get("power")
                if "voltage_l1" in call.data:
                    data["voltage"] = [
                        call.data.get("voltage_l1"),
                        call.data.get("voltage_l2", 230),
                        call.data.get("voltage_l3", 230),
                    ]
                if "current_l1" in call.data:
                    data["current"] = [
                        call.data.get("current_l1") * 1000,
                        call.data.get("current_l2", 0) * 1000,
                        call.data.get("current_l3", 0) * 1000,
                    ]
                if "import_energy" in call.data:
                    data["import_wh"] = call.data.get("import_energy") * 1000
                if "export_energy" in call.data:
                    data["export_wh"] = call.data.get("export_energy") * 1000
                if "is_va" in call.data:
                    data["is_va"] = call.data.get("is_va")
                if "soc" in call.data:
                    data["soc"] = call.data.get("soc")
                hass.async_add_executor_job(brain.devices[dev_id].set_value, data)

    async def handle_set_variable(call):
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                name = call.data.get("variable")
                value = call.data.get("value")
                hass.async_add_executor_job(brain.set_variable, name, value)

    async def handle_set_params(call):
        """Set global Charging Manager parameters."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                params = {
                    k: v
                    for k, v in call.data.items()
                    if k != "powerbrain_host"
                }
                hass.async_add_executor_job(brain.set_params, params)

    async def handle_set_charging_rules(call):
        """Set charging rules for a specific EVSE."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                dev_id = call.data.get("dev_id")
                rules = call.data.get("rules", [])
                if dev_id in brain.devices:
                    hass.async_add_executor_job(
                        brain.devices[dev_id].set_charging_rules, rules
                    )

    async def handle_update_charging_rule(call):
        """Update a single charging rule identified by its cmt label.

        Reads current rules, finds the rule with the matching cmt,
        applies the provided field updates, and writes all rules back.
        If no rule with that cmt exists, a new one is appended.
        """
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                dev_id = call.data.get("dev_id")
                cmt = call.data.get("cmt")
                updates = {k: v for k, v in call.data.items()
                           if k not in ("dev_id", "cmt", "powerbrain_host")}
                if dev_id not in brain.devices:
                    continue
                rules = await hass.async_add_executor_job(
                    brain.devices[dev_id].get_charging_rules
                )
                found = False
                new_rules = []
                for rule in rules:
                    if rule.get("cmt") == cmt:
                        new_rules.append({**rule, **updates})
                        found = True
                    else:
                        new_rules.append(rule)
                if not found:
                    new_rule = {
                        "cmt": cmt, "days": 127, "ctype": 0, "atype": 0,
                        "aexpr": 32000, "udur": 0, "flags": 16, "ena": True, "id": 0,
                    }
                    new_rule.update(updates)
                    new_rules.append(new_rule)
                    _LOGGER.info(
                        "update_charging_rule: rule '%s' not found in %s, appended new rule",
                        cmt, dev_id,
                    )
                await hass.async_add_executor_job(
                    brain.devices[dev_id].set_charging_rules, new_rules
                )
                _LOGGER.info(
                    "update_charging_rule: updated rule '%s' on %s: %s",
                    cmt, dev_id, updates,
                )

    async def handle_get_charging_rules(call):
        """Log current charging rules for a specific EVSE (debug helper)."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                dev_id = call.data.get("dev_id")
                if dev_id in brain.devices:
                    rules = await hass.async_add_executor_job(
                        brain.devices[dev_id].get_charging_rules
                    )
                    _LOGGER.info("Charging rules for %s: %s", dev_id, rules)

    async def handle_set_phase_mode(call):
        """Set phase mode for a specific EVSE (1 or 3 phases)."""
        entries = hass.config_entries.async_entries(DOMAIN)
        for entry in entries:
            brain = hass.data[DOMAIN][entry.entry_id]
            host = call.data.get("powerbrain_host", "")
            if host == "" or host == brain.host:
                dev_id = call.data.get("dev_id")
                phases = call.data.get("phases", 3)
                if dev_id in brain.devices:
                    hass.async_add_executor_job(
                        brain.devices[dev_id].set_phase_mode, phases
                    )

    hass.services.async_register(DOMAIN, "enter_rfid", handle_enter_rfid)
    hass.services.async_register(DOMAIN, "set_meter", handle_set_meter)
    hass.services.async_register(DOMAIN, "set_variable", handle_set_variable)
    hass.services.async_register(DOMAIN, "set_params", handle_set_params)
    hass.services.async_register(DOMAIN, "set_charging_rules", handle_set_charging_rules)
    hass.services.async_register(DOMAIN, "update_charging_rule", handle_update_charging_rule)
    hass.services.async_register(DOMAIN, "get_charging_rules", handle_get_charging_rules)
    hass.services.async_register(DOMAIN, "set_phase_mode", handle_set_phase_mode)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cFos Powerbrain from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Create Api instance
    brain = Powerbrain(
        entry.data[CONF_HOST], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )

    # Validate the API connection (and authentication)
    try:
        await hass.async_add_executor_job(brain.get_devices)
    except Exception as exc:
        raise ConfigEntryNotReady("Timeout while connecting to Powerbrain") from exc
    try:
        await hass.async_add_executor_job(brain.validate_auth)
    except Exception as exc:
        raise ConfigEntryAuthFailed("Authentification failed") from exc

    # Store an API object for your platforms to access
    hass.data[DOMAIN][entry.entry_id] = brain

    update_interval = entry.data[CONF_SCAN_INTERVAL]
    if entry.options.get(CONF_SCAN_INTERVAL):
        update_interval = entry.options.get(CONF_SCAN_INTERVAL)
    # listen for option updates
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Create the updatecoordinator instance
    coordinator = PowerbrainUpdateCoordinator(hass, brain, update_interval)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id + "_coordinator"] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass, entry):
    """Handle options update."""
    coordinator: PowerbrainUpdateCoordinator = hass.data[DOMAIN][
        entry.entry_id + "_coordinator"
    ]
    coordinator.update_interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL)
    )


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True


class PowerbrainUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from the powerbrain api."""

    def __init__(self, hass, brain: Powerbrain, update_interval: int):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Powerbrain Api data",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=update_interval),
        )
        self.brain = brain

    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            await self.hass.async_add_executor_job(self.brain.update_device_status)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


def get_entity_deviceinfo(device: Device) -> DeviceInfo:
    """Get Entity device info from Powerbrain device instance."""
    return {
        "identifiers": {
            # Serial numbers are unique identifiers within a specific domain
            (DOMAIN, f"{device.brain.attributes['vsn']['serialno']}_{device.dev_id}")
        },
        "name": device.name,
        "manufacturer": "cFos",
        "model": device.attributes["model"],
        "configuration_url": device.brain.host,
    }
