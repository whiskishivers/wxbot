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
`/wx force` - Unpause and immediately check for alerts

`/wx pause` - Toggle suspension of alert checks. The bot will appear idle or online to reflect this state.

`/wx purge` - Delete all alert messages and clear message cache.

`/wx prune` - Toggle between editing or deleting inactive alert messages (Default: edit)

`/wx status` - Display parameters and API stats

`/wx subscribe` - Set the alert channel. Use it in the channel you want alerts in

`/wx set area` - Set the area(s) from which alerts should be posted. See examples below

`/wx set point` - Provide a GPS coordinate. Alerts from the matching zone will be posted

`/wx set zone` - Set the zone(s) from which alerts should be posted. See examples below

## Area/Zone parameter examples
Visit the [NWS alerts page](https://alerts.weather.gov/) to look up zone and area identifiers. If you are only
interested in a very specific geographical location, it is best to use the area or zone that most closely defines it.

The bot filters on one type at a time (area or zone). Multiple areas/zones must be comma separated.

Alerts for the entire state of California: `/wx set area CA`

Alerts for Hawaii coastal and land areas: `/wx set area HI,PH`

Alerts for the Gulf of Mexico marine zones near Pensacola, FL and Panama City, FL: `/wx set zone GMZ750,GMZ634`
