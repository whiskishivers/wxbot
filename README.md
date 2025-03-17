# Wx Bot
Wx bot utilizes the discord.py framework and weather.gov API to post National Weather Service alerts to a channel in
your discord server.

## Requirements
* Third party Python modules:
  * discord.py

## Features
- Updates your specified alert channel every 5 minutes, or every minute during extreme weather.
- Posts all active alerts including test messages.
  - Alerts of immediate urgency contain the full description.
  - Other alerts contain a summary headline and a list of affected zones in your filter.
  - Severe alerts are colored yellow. Extreme alerts are colored red.
- Alerts can be filtered using forecast zone IDs or GPS coordinates.
- Expired or canceled alert messages are automatically handled.

## Setup
1. Make a `TOKEN` environment variable that contains your discord API token.
2. Run wbot.py.
3. Set permissions for the commands in the Integrations section of your server settings.
4. Run `/w subscribe` in your alerts channel. The bot will confirm your choice.
5. Add at least one filter with `/w add point` or `/w add zone`.
6. Wait about five minutes or use `/w force`. Any active alerts for your area will be posted.

## Commands
`/w clear` Clear alert filter

`/w force` Unpause and immediately check for alerts

`/w pause` Toggle suspension of alert checks. The bot will appear idle or online to reflect this state

`/w purge` Delete all active alert messages

`/w prune` Toggle between editing or deleting inactive alert messages (Default: edit)

`/w status` Display counters and current filter

`/w subscribe` Set alert channel by running this command in it

`/w add point` Add a forecast zone using GPS latitude and longitude.

`/w add zone` Add a forecast zone using a zone identifier. See below.

## Examples
Visit the [NWS alerts page](https://alerts.weather.gov/) to look up zone IDs. The bot currently supports forecast zones
only. Multiple identifiers can be added in one command if they are separated by a comma.

### Zone IDs
Alerts for Pensacola, Pensacola Bay and adjacent ocean zones in the Gulf: `/w add zone GMZ634,FLZ202,GMZ655,GMZ650`

### GPS coordinate
Alerts for Manhattan, NY: `/w add point 40.6892 -74.0445`

GPS points are not stored or displayed after the zone in which they reside in are determined.