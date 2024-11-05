#!/usr/bin/python3

from asyncio import sleep as sleep
import discord
from discord.ext import commands, tasks
import os
import re
import requests
import wx


class CustomBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_channel: discord.TextChannel | None = None
        self.alert_params = None
        self.cached_alerts = dict()
        self.check_interval = 5.0
        self.pause_alerts = False
        self.post_count = 0
        self.prune = False

    async def setup_hook(self) -> None:
        # start background task
        self.check_alerts.start()

    async def on_ready(self):
        await self.tree.sync()
        print("Bot ready")

    @tasks.loop(minutes=1.0)
    async def check_alerts(self):
        # Skip task if paused, no parameters set, or no alert channel set
        try:
            if self.pause_alerts or len(bot.alert_params) == 0 or self.alert_channel is None:
                return
        except TypeError:
            return

        # Get active alerts

        alerts = sorted(w_client.alerts.active(**self.alert_params), key=lambda x: x.sent)

        # Set lower task interval when big bad alerts exist
        if len([i for i in alerts if i.severity == "Extreme" and i.urgency == "Immediate"]) > 0:
            self.check_interval = 1.0
        else:
            self.check_interval = 5.0
        self.check_alerts.change_interval(minutes=self.check_interval)

        # Sets for determining new/expired alerts
        active_ids, posted_ids = set(i.id for i in alerts), set(self.cached_alerts.keys())

        # Edit or delete inactive alerts
        expired_ids = posted_ids - active_ids
        for i in expired_ids:
            if self.pause_alerts:
                break
            expired_alert: wx.WeatherAlert = self.cached_alerts[i]

            # Pruning enabled - delete entire message
            if self.prune:
                try:
                    await expired_alert.discord_msg.delete()
                    print(f"Pruned: {expired_alert.event}")
                except discord.errors.NotFound as e:
                    print(f"ERROR: Could not delete alert. Code {e.code} {e.text}")
                finally:
                    self.cached_alerts.pop(i, None)

            # No pruning - update message with inactive embed
            else:
                content = f"Inactive: {expired_alert.event}"
                try:
                    await expired_alert.discord_msg.edit(content=content, embed=expired_alert.embed_inactive)
                    print(f"Edited: {expired_alert.event}")
                except discord.errors.NotFound as e:
                    print(f"ERROR: Could not edit alert. Code {e.code} {e.text}")
                finally:
                    self.cached_alerts.pop(i, None)

        # Post new alerts
        new_ids = active_ids - posted_ids
        for alert in alerts:
            if self.pause_alerts:
                break
            if alert.id in new_ids:
                try:
                    alert.discord_msg = await self.alert_channel.send(content=f"**{alert.headline}**",
                                                                      embed=alert.embed)
                    self.cached_alerts[alert.id] = alert
                    self.post_count += 1
                    print(f"Posted: {alert.event}")
                except discord.errors.Forbidden:
                    print(f"ERROR: Permission error while posting alert {alert.id}")
                    break
                except discord.errors.NotFound:
                    print(f"ERROR: Not Found error while posting alert {alert.id}")
                    break

                new_ids.remove(alert.id)

        print(
            f"Queries: {w_client.get_count}. Interval: {self.check_interval}. Cached: {len(self.cached_alerts)}.")


intents = discord.Intents.default()
bot = CustomBot(intents=intents, command_prefix=".")


@bot.hybrid_group(name="wx")
async def wxgrp(ctx):
    pass


@wxgrp.group(name="set")
async def wxset(ctx):
    pass


@commands.guild_only()
@wxset.command(name="area")
async def set_area(ctx: commands.Context, area_id: str):
    """ Set the area(s) from which alerts will be posted """
    valid_id = re.compile(r"^[0-9a-zA-Z,]+$")

    if not valid_id.fullmatch(area_id.upper()):
        await ctx.send("Invalid area ID. Letters, numbers, and commas only.", ephemeral=True)
        return

    try:
        resp = w_client.alerts.active(area=area_id.upper())
    except requests.exceptions.HTTPError as e:
        await ctx.send(f"weather.gov api returned {e.response.status_code} {e.response.reason}. Cannot set area",
                       ephemeral=True)
        return
    bot.alert_params = {"area": area_id}
    print(f"Params set: {bot.alert_params}")
    await ctx.send("✅ Area set!", ephemeral=True)


@commands.guild_only()
@wxset.command(name="zone")
async def set_zone(ctx: commands.Context, zone_id: str):
    """ Set the zone(s) from which alerts will be posted """
    valid_id = re.compile(r"^[0-9a-zA-Z,]+$")

    if not valid_id.fullmatch(zone_id.upper()):
        print(zone_id)
        await ctx.send("Invalid zone ID. Letters, numbers, and commas only.", ephemeral=True)
        return

    try:
        resp = w_client.alerts.active(zone=zone_id.upper())
    except requests.exceptions.HTTPError as e:
        await ctx.send(f"weather.gov api returned {e.response.status_code} {e.response.reason}. Cannot set zone.",
                       ephemeral=True)
        return
    bot.alert_params = {"zone": zone_id}
    print(f"Params set: {bot.alert_params}")
    await ctx.send("✅ Zone set!", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="pause")
async def toggle_pause(ctx: commands.Context):
    """ Pause or resume alert checks """
    if bot.pause_alerts:
        # Toggle resume
        bot.pause_alerts = False
        await bot.change_presence(status=discord.Status.online)
        await ctx.send("✅ ▶️ Alert checking resumed.", ephemeral=True)
    else:
        # Toggle pause
        bot.pause_alerts = True
        await bot.change_presence(status=discord.Status.idle)
        await ctx.send("✅ ⏸️ Alert checking paused.", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="prune")
async def toggle_pruning(ctx: commands.Context):
    """ Toggle removal of expired alerts """
    if bot.prune:
        bot.prune = False
        msg = f"Disabled alert pruning."
    else:
        bot.prune = True
        msg = f"Enabled alert pruning."
    await ctx.send(f"✅ {msg}", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="purge")
async def purge(ctx: commands.Context):
    """ Clear cache and delete all alerts """
    if bot.alert_channel is None:
        return
    all_alerts = bot.cached_alerts.items()
    async with ctx.typing(ephemeral=True):
        for alert_id, alert in all_alerts:
            try:
                await alert.discord_msg.delete()
                await sleep(0.8)
                print(f"Removed: {alert.event}")
            except discord.errors.NotFound as e:
                print(f"ERROR: Could not delete alert. Code {e.code} {e.text}")
        bot.cached_alerts.clear()
        await ctx.send(f"All alerts cleared.", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="subscribe")
async def subscribe(ctx: commands.Context):
    """ Tells the bot where to post. Use it in the channel you want alerts in """
    if ctx.channel is None:
        return
    try:
        test_post = await ctx.channel.send("Weather alerts will be posted here.")
        await test_post.delete()
        await ctx.send(f"✅ Alerts will be posted to {ctx.channel.mention}", ephemeral=True)
        bot.alert_channel = ctx.channel
    except discord.errors.Forbidden:
        await ctx.send(f"Error! The bot is not allowed to post here. Check bot permissions.", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="status")
async def wx_status(ctx: commands.Context):
    """ Display parameters and API stats """
    stats = w_client.stats()
    content = ""

    if bot.alert_params is None:
        content += "⚠️ **Alert filters are not set.** Use `/wx set area (area_id)` or `/wx set zone (zone_id)`.\n"

    if bot.alert_channel is None:
        content += "⚠️ **Alert channel is not set.** Use `/wx subscribe` in the alert channel to set it.\n"
    else:
        content += f"Alert channel: {bot.alert_channel.mention}\n"

    content += f"Alerts: *{bot.post_count} posted. {len(bot.cached_alerts)} cached.*\n" \
               f"Current interval: *{bot.check_alerts.minutes} minutes*\n" \
               f"Filter parameters: `{bot.alert_params}`\n" \
               f"Paused: *{bot.pause_alerts}*\n" \
               f"Pruning: *{bot.prune}*\n" \
               f"API calls: *{stats['get_count']} ({stats['bytes_recvd']})*\n" \
               f"API last good call: *{stats['last_ok']}*"

    await ctx.send(content, ephemeral=True)


if __name__ == '__main__':
    w_client = wx.Client()
    ping = w_client.ping()
    print(f"Client loaded. Ping: {ping}")
    bot.run(os.environ["TOKEN"])
