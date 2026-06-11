# cFos Powerbrain

[![GitHub Release][releases-shield]][releases]

[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

### Integration for Homeassistant to view and control devices (EV charging stations and powermeters) connected to a cFos Powerbrain charging controller or cFos charging manager

> **Fork by [guibrazlima](https://github.com/guibrazlima)** — extends the original integration with additional EVSE sensors and new services for programmatic control of charging rules and global parameters.

## Features

- Automatically discovers and creates devices (powermeters and charging stations) connected to a Powerbrain controller
- Creates sensors to read values from power meters (voltage, current, energy, ...)
- Creates switches to control charging stations (enable charging, enable charging rules, set charging current, ...)
- Adds a Homeassistant service to enter RFID/PIN codes into EVSE/wallboxes
- Adds a Homeassistant service to send power meter values to an HTTP input meter
- Adds a Homeassistant service to set global charging manager variables
- **[NEW]** Additional EVSE sensors (session energy, pause reason, CP/PP state, phases, ...)
- **[NEW]** Service to set global Charging Manager parameters (`set_params`)
- **[NEW]** Service to create/replace EVSE charging rules (`set_charging_rules`)
- **[NEW]** Service to update a single rule by label without affecting others (`update_charging_rule`)
- **[NEW]** Service to read current EVSE charging rules (`get_charging_rules`)

## Sensors

### Power Meter sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Power | W / VA | Current active power |
| Import | kWh | Total imported energy |
| Export | kWh | Total exported energy |
| Current L1/L2/L3 | A | Phase currents |
| Voltage L1/L2/L3 | V | Phase voltages |

### EVSE / Wallbox sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Charging Power | W | Current charging power |
| Total Charging Energy | kWh | Total energy charged (lifetime) |
| **Session Energy** | kWh | Energy charged in current session (resets on unplug) |
| State | — | Wallbox state: Standby / Car connected / Charging / Error / Offline |
| Current L1/L2/L3 | A | Phase charging currents |
| **Last Set Charging Current** | A | Last current commanded by the Charging Manager |
| **Used Phases** | — | Number of phases currently in use |
| **Pause Reason** | — | Why charging is paused: None / Current limit / Charging rules / Manual pause / Phase switch / Error |
| **Pause Time Remaining** | s | Seconds until end of minimum pause (0 = not paused) |
| **CP State** | — | Control Pilot state (e.g. "Vehicle detected") |
| **PP State** | — | Proximity Pilot state — cable detection (e.g. "no cable") |
| **Total Charging Duration** | s | Cumulative total charging time in seconds |

**Bold** = added in this fork.

## Services

### `powerbrain.enter_rfid`
Enter an RFID or PIN code into a charging station to authorize or stop charging.

| Field | Required | Description |
|-------|----------|-------------|
| `rfid` | ✅ | RFID or PIN (digits) |
| `dev_id` | — | EVSE device ID (e.g. `E1`). If omitted, auto-assigned. |
| `powerbrain_host` | — | Host address if multiple Powerbrain instances are configured |

---

### `powerbrain.set_meter`
Send power meter values to an HTTP input meter in the Charging Manager.

| Field | Required | Description |
|-------|----------|-------------|
| `dev_id` | ✅ | Meter device ID (e.g. `M1`) |
| `power` | — | Active power (W or VA) |
| `is_va` | — | True if power is in VA |
| `voltage_l1/l2/l3` | — | Phase voltages (V) |
| `current_l1/l2/l3` | — | Phase currents (A) |
| `import_energy` | — | Imported energy (kWh) |
| `export_energy` | — | Exported energy (kWh) |
| `powerbrain_host` | — | Host address if multiple instances |

---

### `powerbrain.set_variable`
Set the value of a Charging Manager variable.

| Field | Required | Description |
|-------|----------|-------------|
| `variable` | ✅ | Variable name |
| `value` | ✅ | Value to set |
| `powerbrain_host` | — | Host address if multiple instances |

---

### `powerbrain.set_params` *(new)*
Set global Charging Manager parameters. Only include the keys you want to change.

| Field | Required | Description |
|-------|----------|-------------|
| `min_pause_time` | — | Minimum pause between sessions (seconds, default 300) |
| `disable_policy` | — | On device disable: `0`=disable EVSE, `1`=use min. current, `-1`=free charging |
| `max_total_current` | — | Total installed power limit (mA) |
| `lb_enabled` | — | Enable/disable load balancing |
| `feed_in_tariff` | — | Feed-in tariff (currency/kWh) |
| `surplus_expr` | — | Expression to calculate surplus power |
| `powerbrain_host` | — | Host address if multiple instances |

Example automation — reduce minimum pause time to 60s:
```yaml
service: powerbrain.set_params
data:
  min_pause_time: 60
```

---

### `powerbrain.update_charging_rule` *(new)*
Update a single charging rule identified by its `cmt` label, without affecting other rules.

This is the recommended service for automation use-cases (e.g. EV smart charging) where only the start time or duration needs to change — other rules like solar-pause rules remain untouched.

If no rule with the given `cmt` label exists, a new rule is appended automatically.

| Field | Required | Description |
|-------|----------|-------------|
| `dev_id` | ✅ | EVSE device ID (e.g. `E1`) |
| `cmt` | ✅ | Label of the rule to update (must match exactly) |
| `time` | — | New start time in minutes since midnight (e.g. `1320` = 22:00) |
| `dur` | — | New duration in minutes |
| `aexpr` | — | New charging current in mA (for `atype=0` rules) |
| `ena` | — | Enable (`true`) or disable (`false`) the rule |
| `days` | — | New weekday bitfield (bit0=Mon … bit6=Sun, `127`=all) |
| `powerbrain_host` | — | Host address if multiple instances (optional) |

Example — update the EV overnight rule to start at 23:00 for 2 hours:
```yaml
service: powerbrain.update_charging_rule
data:
  dev_id: E1
  cmt: "EV Carregamento Nocturno"
  time: 1380   # 23:00 = 23 × 60
  dur: 120     # 2 hours
  ena: true
```

Example — disable the rule without deleting it:
```yaml
service: powerbrain.update_charging_rule
data:
  dev_id: E1
  cmt: "EV Carregamento Nocturno"
  ena: false
```

### `powerbrain.set_charging_rules` *(new)*
Replace the charging rules for a specific EVSE. All existing rules are overwritten.

Uses the native cFos `get_devices` / `set_device` API (same as the cFos web UI), which correctly persists rules across reboots.

| Field | Required | Description |
|-------|----------|-------------|
| `dev_id` | ✅ | EVSE device ID (e.g. `E1`) |
| `rules` | ✅ | Array of rule objects (see below) |
| `powerbrain_host` | — | Host address if multiple instances |

**Rule object fields (cFos native format):**

| Field | Type | Description |
|-------|------|-------------|
| `cmt` | str | Comment / label shown in the cFos UI |
| `days` | int | Weekday bitfield: bit0=Mon … bit6=Sun. `127` = all days |
| `ctype` | int | Condition type: `0`=none/time window, `1`=solar surplus, … |
| `atype` | int | Action type: `0`=set current (mA), `10`=pause |
| `aexpr` | int | Action value: current in mA for `atype=0`, `1` for `atype=10` |
| `time` | int | Start time in minutes after midnight (time-based rules) |
| `dur` | int | Duration in minutes |
| `udur` | int | Undercut duration in seconds |
| `flags` | int | `16`=normal, `18`=end-on-finish |
| `ena` | bool | `true` = rule enabled |
| `id` | int | Rule id; use `0` for auto-assign |
| `cexpr` | int | Condition threshold (e.g. solar power in W for `ctype=1`) |

Example — time-based rule: charge at 16A every night from 22:00 for 3 hours:
```yaml
service: powerbrain.set_charging_rules
data:
  dev_id: E1
  rules:
    - cmt: "Overnight cheap rate"
      days: 127       # all days
      ctype: 0        # no condition / time window
      atype: 0        # set current
      aexpr: 16000    # 16A in mA
      time: 1320      # 22:00 = 22 × 60 minutes
      dur: 180        # 3 hours
      udur: 0
      flags: 16
      ena: true
      id: 0
```

Example — pause rule: pause for 5 min if solar surplus < 3000W:
```yaml
service: powerbrain.set_charging_rules
data:
  dev_id: E1
  rules:
    - cmt: "Pause low solar"
      days: 127
      ctype: 1        # solar surplus condition
      atype: 10       # pause
      aexpr: 1
      cexpr: 3000     # threshold: 3000W
      udur: 300       # undercut duration 5 min
      flags: 18
      ena: true
      id: 0
```

Example — clear all rules (back to Charging Manager default behaviour):
```yaml
service: powerbrain.set_charging_rules
data:
  dev_id: E1
  rules: []
```

---

### `powerbrain.get_charging_rules` *(new)*
Retrieve and log the current charging rules for an EVSE. Rules are written to the Home Assistant log at INFO level — useful for debugging.

| Field | Required | Description |
|-------|----------|-------------|
| `dev_id` | ✅ | EVSE device ID (e.g. `E1`) |
| `powerbrain_host` | — | Host address if multiple instances |

---

## Installation using HACS (this fork)

To install this fork via HACS as a custom repository:

1. In HA go to **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/guibrazlima/homeassistant-powerbrain` as category **Integration**
3. Search for "cFos Powerbrain" and install
4. Restart Home Assistant

## Manual Installation

1. Open the directory for your HA configuration (where `configuration.yaml` is).
2. Create `custom_components/` if it doesn't exist.
3. Create `custom_components/powerbrain/` inside it.
4. Download all files from `custom_components/powerbrain/` in this repository.
5. Restart Home Assistant.
6. Go to **Settings → Integrations → Add** and search for "cFos Powerbrain".

## Configuration

Enter the host (IP address or URL) of your Powerbrain controller and the polling interval in seconds.

![config1img]
![config2img]

## Contributions are welcome!

Please read the [Contribution guidelines](CONTRIBUTING.md).

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/guibrazlima/homeassistant-powerbrain.svg?style=for-the-badge
[commits]: https://github.com/guibrazlima/homeassistant-powerbrain/commits/master
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[exampleimg]: doc/evse.png
[config1img]: doc/ConfigFlow.png
[config2img]: doc/device_discovery.png
[license-shield]: https://img.shields.io/github/license/guibrazlima/homeassistant-powerbrain.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/guibrazlima/homeassistant-powerbrain.svg?style=for-the-badge
[releases]: https://github.com/guibrazlima/homeassistant-powerbrain/releases
