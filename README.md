# cFos Powerbrain

[![GitHub Release][releases-shield]][releases]

[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

<a href="https://www.buymeacoffee.com/mbsoftware"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=mbsoftware&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" /></a>

\*\*This component will set up devices (EV charging stations and powermeters) connected to a cFos Powerbrain controller using the local http API

## Features

- Automatically discovers and creates devices (powermeters and charging stations) connected to a Powerbrain controller
- Creates sensors to read values from power meters (voltage, current, energy, ...)
- Creates switches to control charging stations (enable charging, enable charging rules, set charging current, ...)
- ...More to come...

\*\*Please note that this integration is still in an early stage and functionality will likely be extended in the future. If you experience any issues or bugs, please raise an issue on Github. If you want to contribute, please also read the [Contribution guidelines](CONTRIBUTING.md) .




![example][exampleimg]


## Installation using HACS

Simply install this repository as a custom repository for integrations in HACS following the guide here:
https://hacs.xyz/docs/faq/custom_repositories .

Then you can simply download and update the integration using HACS

## Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `powerbrain`.
4. Download _all_ the files from the `custom_components/powerbrain/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "cFos Powerbrain"


## Configuration is done in the UI

Simply enter the host (IP address) of your powerbrain controller in the local network and choose the update intervall [seconds] the integration uses to poll the sensor values.

![config1img]
![config2img]

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/mb-software
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/mb-software/homeassistant-powerbrain.svg?style=for-the-badge
[commits]: https://github.com/mb-software/homeassistant-powerbrain/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: doc/evse.png
[config1img]: doc/ConfigFlow.png
[config2img]: doc/device_discovery.png
[license-shield]: https://img.shields.io/github/license/mb-software/homeassistant-powerbrain.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40mb-software-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/mb-software/homeassistant-powerbrain.svg?style=for-the-badge
[releases]: https://github.com/mb-software/homeassistant-powerbrain/releases
[user_profile]: https://github.com/mb-software
