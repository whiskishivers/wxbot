# Wx Bot
Wx bot utilizes the discord py framework and weather.gov API to post weather alerts to your discord server.

## Requirements
* Third party Python modules:
  * requests
  * discord

## Setup
1. Modify wx-bot.py and add your discord API token (scroll all the way down).
1. Run wx-bot.py.
1. Once the bot connects, be sure to secure command permissions in your Integrations page in server settings.
1. Run `/wx subscribe` in your alerts channel. The bot will confirm your choice.
1. Set your desired alert area with `/wx set area` or `/wx set zone`. See below.
1. Wait about five minutes. Any active alerts for your area will be posted.

The bot will check for alerts every 5 minutes. This interval will be shortened to 1 minute when immediate extreme alerts are active.

## Commands
`/wx pause` - Pause or resume alert checks (default: False)

`/wx purge` - Clear cache and delete all alert messages.

`/wx prune` - Enable or disable deletion of expired alert messages (default: True)

`/wx status` - Displays currently set options and API stats

`/wx subscribe` - Run this in a channel to have alerts posted there. Only one channel can subscribe at a time

`/wx set area` - Set the area(s) from which alerts should be posted. For more info, visit weather.gov

`/wx set zone` - Set the zone(s) from which alerts should be posted. For more info, visit weather.gov

## Area/Zone parameter examples
You can look up area and zone identifiers on the [NWS alerts page](https://alerts.weather.gov/). The commands can support multiple IDs when separated by commas.

Alerts for the entire state of California: `/wx set area CA`

Alerts for Hawaii coastal and land areas: `/wx set area HI,PH`

Alerts for Albany and Bronx counties in New York: `/wx set zone NYC001,NYC005`
