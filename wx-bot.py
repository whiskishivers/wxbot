#!/usr/bin/python3

import discord
from discord.ext import commands, tasks

import re
import requests
import wx
from asyncio import sleep as sleep

severity_color = {("Severe", "Immediate"): discord.Color.gold(),
                  ("Severe", "Future"): discord.Color.gold(),
                  ("Extreme", "Future"): discord.Color.gold(),
                  ("Extreme", "Immediate"): discord.Color.red()}


class CustomBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_channel = None
        self.alert_params = None
        self.cached_alerts = dict()
        self.check_interval = 5.0
        self.paused = False
        self.prune = True

    async def setup_hook(self) -> None:
        # start the task to run in the background
        self.check_alerts.start()

    async def on_ready(self):
        await self.tree.sync()
        print("Bot ready")

    @tasks.loop(minutes=1.0)
    async def check_alerts(self):
        print("Task started.")
        try:
            if self.paused or len(bot.alert_params) == 0 or self.alert_channel is None:
                print("Skipped task.")
                return
        except TypeError:
            print("Skipped task.")
            return

        # Get active alerts
        alerts = sorted(w_client.alerts.active_properties(**self.alert_params), key=lambda x: x.sent)

        # Set lower task interval when extreme alerts exist
        if len([i for i in alerts if i.severity == "Extreme" and i.urgency == "Immediate"]) > 0:
            self.check_alerts.change_interval(minutes=1.0)
        else:
            self.check_alerts.change_interval(minutes=5.0)

        # Make id sets for logic
        active_ids, posted_ids = set(i.id for i in alerts), set(self.cached_alerts.keys())

        # Delete expired alerts
        if self.prune:
            expired_ids = posted_ids - active_ids
            for i in expired_ids:
                await self.cached_alerts[i].delete()
                await sleep(0.8)
                self.cached_alerts.pop(i, None)
                print(f"Removed: {i}")

        # Post new alerts
        new_ids = active_ids - posted_ids
        for alert in alerts:
            if self.paused:
                return

            if alert.id in new_ids:
                color = severity_color.get((alert.severity, alert.urgency), None)
                embed = discord.Embed(color=color,
                                      title=alert.event,
                                      url=f"https://alerts.weather.gov/search?id={alert.id}",
                                      description=alert.description[:4096],
                                      timestamp=alert.sent)
                if alert.instruction is not None:
                    embed.add_field(name="Instructions", value=alert.instruction[:1024], inline=False)
                embed.add_field(name="Urgency", value=alert.urgency)
                embed.add_field(name="Severity", value=alert.severity)
                embed.add_field(name="Response", value=alert.response)

                if alert.wmo:
                    author_url = f"https://www.weather.gov/{alert.wmo.lower()}"
                    embed.set_author(name=alert.senderName, url=author_url)

                try:
                    self.cached_alerts[alert.id] = await self.alert_channel.send(content=f"### {alert.headline}",
                                                                                 embed=embed)
                    print(f"Posted: {alert.headline}")
                except discord.errors.Forbidden:
                    print(f"ERROR: No permission to post alert {alert.id}")
                    break
                except discord.errors.NotFound:
                    print(f"ERROR: Channel not found. Could not post {alert.id}")
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
    """ Set the area from which alerts will be posted """
    valid_id = re.compile(r"^[0-9a-zA-Z,]+$")

    if not valid_id.fullmatch(area_id.upper()):
        print(area_id)
        await ctx.send("Invalid area ID. Letters, numbers, and commas only.", ephemeral=True)
        return

    try:
        resp = w_client.alerts.active_properties(area=area_id.upper())
    except requests.exceptions.HTTPError as e:
        await ctx.send(f"weather.gov api returned {e.response.status_code} {e.response.reason}. Check your syntax?",
                       ephemeral=True)
        return
    bot.alert_params = {"area": area_id}
    await ctx.send("✅ Area set!", ephemeral=True)


@commands.guild_only()
@wxset.command(name="zone")
async def set_zone(ctx: commands.Context, zone_id: str):
    """ Set the zone from which alerts will be posted """
    valid_id = re.compile(r"^[0-9a-zA-Z,]+$")

    if not valid_id.fullmatch(zone_id.upper()):
        print(zone_id)
        await ctx.send("Invalid area ID. Letters, numbers, and commas only.", ephemeral=True)
        return

    try:
        resp = w_client.alerts.active_properties(zone=zone_id.upper())
    except requests.exceptions.HTTPError as e:
        await ctx.send(f"weather.gov api returned {e.response.status_code} {e.response.reason}. Check your syntax?",
                       ephemeral=True)
        return
    bot.alert_params = {"zone": zone_id}
    print(f"Params set: {bot.alert_params}")
    await ctx.send("✅ Zone set!", ephemeral=True)


@commands.guild_only()
@wxset.command(name="pause")
async def set_pause(ctx: commands.Context, pause: bool):
    """ Pause or resume alert checks """
    bot.paused = pause
    await ctx.send(f"✅ Bot paused: {bot.paused}", ephemeral=True)


@commands.guild_only()
@wxset.command(name="prune")
async def set_prune(ctx: commands.Context, prune: bool):
    """ Enable or disable deletion of expired alerts """
    bot.prune = prune
    await ctx.send(f"✅ Pruning: {bot.prune}", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="subscribe")
async def subscribe(ctx: commands.Context):
    """ Run this command in the alert channel so the bot knows where to post """
    if ctx.channel is None:
        return
    try:
        test_post = await ctx.channel.send("Weather alerts will be posted here.")
        await test_post.delete()
        await ctx.send(f"✅ Alerts will be posted to {ctx.channel.mention}", ephemeral=True)
        bot.alert_channel = ctx.channel
    except discord.errors.Forbidden:
        await ctx.send(f"Error! The bot needs permission to send messages here.", ephemeral=True)


@commands.guild_only()
@wxgrp.command(name="status")
async def wx_status(ctx: commands.Context):
    """ Shows bot options and stats. """
    stats = w_client.stats()
    content = "## Bot status:\n"

    if bot.alert_params is None:
        content += "⚠️ **Alert area or zone has not been set**. Use `/wx set area (area_id)` or `/wx set zone (zone_id)`.\n"

    if bot.alert_channel is None:
        content += "⚠️ **Alert channel has not set**. Use `/wx subscribe` in the alert channel" \
                   " to set it.\n"
    else:
        content += f"Alert channel: {bot.alert_channel.mention}\n"

    content += f"Cached alerts: {len(bot.cached_alerts)}\n" \
               f"Current parameters: {bot.alert_params}\n" \
               f"Current interval: {bot.check_alerts.minutes} minutes\n" \
               f"Paused: {bot.paused}\n" \
               f"Pruning: {bot.prune}\n" \
               f"API calls: {stats['get_count']}\n" \
               f"API bytes received: {stats['bytes_recvd']}\n" \
               f"API last good call: {stats['last_ok']}"

    await ctx.send(content, ephemeral=True)


if __name__ == '__main__':
    # weather.gov api client
    w_client = wx.Client()

    bot.run("discord bot token goes here")
