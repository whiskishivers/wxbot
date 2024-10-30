# Wx Bot
Wx bot utilizes the discord py framework and weather.gov API to post weather alerts to your discord server.

## Requirements
* Third party Python modules:
  * requests
  * discord.py

## Setup
1. Make a `DISCORDTOKEN` environment variable that contains your bot's API token.
2. Run wx-bot.py.
3. Use the Integrations page under Server Settings in your server to set permissions for the commands.
4. Run `/wx subscribe` in your alerts channel. The bot will confirm your choice.
5. Set your desired filter with `/wx set area` or `/wx set zone`. See example section for more info.
6. Wait about five minutes. Any active alerts for your area will be posted.

The API query interval is 5 minutes and will reduce to 1 minute when extreme weather alerts are active.

## Commands
`/wx pause` - Pause or resume alert checks

`/wx purge` - Clear cache and delete all alerts. Note: This is sluggish due to API rate limiting

`/wx prune` - Toggle removal of expired alerts (Default: enabled)

`/wx status` - Display parameters and API stats

`/wx subscribe` - Tells the bot where to post. Use it in the channel you want alerts in.

`/wx set area` - Set the area(s) from which alerts should be posted. See examples below.

`/wx set zone` - Set the zone(s) from which alerts should be posted. See examples below.

## Area/Zone parameter examples
The [NWS alerts page](https://alerts.weather.gov/) contains every zone and area identifier you can use. An area contains many zones. Example: All states are areas, all counties are zones. If you are using the bot for a very specific geographical location, it is best to specify a zone so that only relevant alerts are posted.

The bot filters one type only (area or zone). Multiple areas/zones must be comma separated.

Alerts for the entire state of California: `/wx set area CA`

Alerts for Hawaii coastal and land areas: `/wx set area HI,PH`

Alerts for the Gulf of Mexico marine zones near Pensacola, FL and Panama City, FL: `/wx set zone GMZ750,GMZ634`
