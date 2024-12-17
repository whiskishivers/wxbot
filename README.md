# Wx Bot
Wx bot utilizes the discord py framework and weather.gov API to post weather alerts to a discord channel.

## Requirements
* Third party Python modules:
  * requests
  * discord.py

## Setup
1. Make a `TOKEN` environment variable that contains your API token.
2. Run wx-bot.py.
3. Use the Integrations page under Server Settings in your server to set permissions for the commands.
4. Run `/wx subscribe` in your alerts channel. The bot will confirm your choice.
5. Set your desired filter with `/wx set area` or `/wx set zone`. See example section for more info.
6. Wait about five minutes or use `/wx force`. Any active alerts for your area will be posted.


## Features
- The bot posts alerts with **unknown, moderate, severe, or extreme** severity. Other alerts are ignored.
- Alert checks run every 5 minutes. When **immediate** alerts are found with **extreme** severity, the interval drops
to 1 minute.
- Alerts with **immediate** urgency include the full description. Other alerts will include the NWS headline and a
list of affected zones.

## Commands
`/wx clear` - Clear alert filter.

`/wx force` - Unpause and immediately check for alerts

`/wx pause` - Toggle suspension of alert checks. The bot will appear idle or online to reflect this state.

`/wx purge` - Delete all alert messages and clear message cache.

`/wx prune` - Toggle between editing or deleting inactive alert messages (Default: edit)

`/wx status` - Display parameters and API stats

`/wx subscribe` - Set the alert channel. Use it in the channel you want alerts in

`/wx add point` - Add a forecast zone filter using GPS latitude and longitude.

`/wx add zone` - Add a forecast zone filter using a zone identifer. See below.

## Examples
Visit the [NWS alerts page](https://alerts.weather.gov/) to look up zone identifiers. Multiple identifiers can be added
in one command if they are separated by a comma.

Alerts for the Gulf of Mexico marine zones near Pensacola, FL and Panama City, FL: `/wx set zone GMZ750,GMZ634`

When using `add point`, the GPS coordinates are used to retrieve the zone identifier the point resides in. The accuracy
needs to be no more than four decimal places (~100 meters).