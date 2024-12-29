# W Bot
Wx bot utilizes the discord.py framework and weather.gov API to post National Weather Service alerts to a channel in
your discord server.

## Requirements
* Third party Python modules:
  * requests
  * discord.py


## Features
- Checks for alerts every 5 minutes.
- Checks for alerts every minute while extreme alerts are active.
- Posts active alerts that are moderate, severe, extreme, or unknown in severity.
- Alert messages will contain a short description, list of affected zones and instructions.
- Alerts with immediate urgency will include the full description.
- Location filters can be applied using zone identifiers or GPS coordinates.

## Setup
1. Make a `TOKEN` environment variable that contains your discord API token.
2. Run wbot.py.
3. Set permissions for the commands in the Integrations section of your server settings.
4. Run `/w subscribe` in your alerts channel. The bot will confirm your choice.
5. Add at least one filter with `/w add point` or `/w add zone`.
6. Wait about five minutes or use `/w force`. Any active alerts for your area will be posted.

## Commands
`/w clear` - Clear all alert filters

`/w force` - Unpause and immediately check for alerts

`/w pause` - Toggle suspension of alert checks. The bot will appear idle or online to reflect this state

`/w purge` - Delete all alert messages and clear message cache

`/w prune` - Toggle between editing or deleting inactive alert messages (Default: edit)

`/w status` - Display counters and current filter

`/w subscribe` - Set the alert channel. Use it in the channel you want alerts in

`/w add point` - Add a forecast zone filter using GPS latitude and longitude.

`/w add zone` - Add a forecast zone filter using a zone identifier. See below.

## Examples
Visit the [NWS alerts page](https://alerts.weather.gov/) to look up zone identifiers. Multiple identifiers can be added
in one command if they are separated by a comma.

Alerts for the Gulf of Mexico marine zones near Pensacola, FL and Panama City, FL: `/w set zone GMZ750,GMZ634`

Alerts for Manhattan: `/w add point 40.6892 -74.0445`