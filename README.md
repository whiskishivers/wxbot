# Wx Bot
Wx bot utilizes the discord py framework and weather.gov API to post severe and extreme weather alerts to a channel in
your discord server.

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
6. Wait about five minutes. Any active alerts for your area will be posted.

The bot checks active alerts every 5 minutes, or every 1 minute when extreme, immediate alerts exist.

The bot handles only alerts that have **severe** and **extreme** severity with **future** or **immediate** urgency.

Alerts that have **immediate** urgency will be posted with the full alert description. Other alerts will contain only the
areas that are affected. For these alerts, the user must click the alert link to view the full description.

Chat messages containing alerts that have expired or are considered "inactive" by the API will be edited to reflect that
change.

## Commands
`/wx pause` - Pause or resume alert checks. The bot will indicate this state with Discord's idle/online status.

`/wx purge` - Clear cache and delete all alerts. Note: This is sluggish due to API rate limiting

`/wx prune` - Toggle pruning. Expired alerts will be deleted from the channel instead of edited. (Default: disabled)

`/wx status` - Display parameters and API stats

`/wx subscribe` - Tells the bot where to post. Use it in the channel you want alerts in.

`/wx set area` - Set the area(s) from which alerts should be posted. See examples below.

`/wx set zone` - Set the zone(s) from which alerts should be posted. See examples below.

## Area/Zone parameter examples
The [NWS alerts page](https://alerts.weather.gov/) contains every zone and area identifier you can use. An area contains many zones. For example,
a land area can be a state or county. If you are using the bot for a very specific geographical location, it is best
to use the area or zone that most closely encompasses the location you are interested in.

The bot filters one type only (area or zone). Multiple areas/zones must be comma separated.

Alerts for the entire state of California: `/wx set area CA`

Alerts for Hawaii coastal and land areas: `/wx set area HI,PH`

Alerts for the Gulf of Mexico marine zones near Pensacola, FL and Panama City, FL: `/wx set zone GMZ750,GMZ634`
