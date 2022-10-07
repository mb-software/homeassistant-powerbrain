"""Constants for cFos Powerbrain."""
# Base component constants
NAME = "cFos Powerbrain"
DOMAIN = "powerbrain"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"

ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
ISSUE_URL = "https://github.com/mb-software/homeassistant-powerbrain/issues"

# Icons
ICON = "mdi:format-quote-close"


# Configuration and options


# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
