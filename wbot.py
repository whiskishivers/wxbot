#!/usr/bin/python3

import aiohttp
import asyncio
import discord
from discord.ext import commands, tasks
import os
import re
import wapi

class CustomBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_channel: discord.TextChannel | None = None
        self.cached_alerts = dict()
        self.check_interval = 5.0
        self.pause_alerts = False
        self.post_count = 0
        self.prune = False
        self.weather = wapi.client

    async def setup_hook(self) -> None:
        # start background task
        self.check_alerts.start()

    async def on_ready(self):
        # ready weather api client, sync commands
        await self.weather.initialize_session()
        await self.tree.sync()
        print("Bot ready")

    @tasks.loop(minutes=1.0)
    async def check_alerts(self):
        """ Loop for managing all alert messages """
        # Skip task if paused, no filter exists, or no alert channel set
        if self.pause_alerts or len(self.weather.alert_zones) == 0 or self.alert_channel is None:
            return

        print(f"Loop: {self.check_alerts.current_loop}. Total API calls: {self.weather.get_count}.")

        # Get active alerts
        try:
            alert_filter = {"zone": ",".join(self.weather.alert_zones), "status": "actual"}
            alerts = await self.weather.alerts.active(**alert_filter)
            alerts.sort(key=lambda x: x.sent)
        except wapi.RequestRateExceeded:
            print("Warning: Skipped alert check. Rate limit for NWS API has been exceeded.")
            return


        # Change task interval based on severity
        if len([i for i in alerts if i.severity == "Extreme"]) > 0:
            self.check_interval = 1.0
        else:
            self.check_interval = 5.0
        self.check_alerts.change_interval(minutes=self.check_interval)

        active_ids, posted_ids = set(i.id for i in alerts), set(self.cached_alerts.keys())

        # Edit or delete inactive alerts
        expired_ids = posted_ids - active_ids
        for i in expired_ids:
            if self.pause_alerts:
                break
            expired_alert: wapi.Alert = self.cached_alerts[i]

            # Pruning enabled - delete entire message
            if self.prune:
                try:
                    await expired_alert.discord_msg.delete()
                    print(f"Deleted: {expired_alert.event}")
                except discord.errors.NotFound as e:
                    print(f"ERROR: Could not delete alert. Code {e.code} {e.text}")
                finally:
                    self.cached_alerts.pop(i, None)
            else:
                # No pruning - update message with inactive embed
                content = f"Inactive: {expired_alert.event}"
                if expired_alert.is_active:
                    try:
                        expired_alert.is_active = False
                        await expired_alert.discord_msg.edit(content=content, embed=expired_alert.embed_inactive)
                        print(f"Edited: {expired_alert.event}")
                    except discord.errors.NotFound as e:
                        print(f"ERROR: Could not edit alert. Code {e.code} {e.text}")

        # Post new alerts
        new_ids = active_ids - posted_ids
        if len(new_ids):
            async with self.alert_channel.typing():
                await asyncio.sleep(2.0)
        for alert in alerts:
            if self.pause_alerts:
                break
            if alert.id in new_ids:
                try:
                    async with self.alert_channel.typing():
                        await asyncio.sleep(0.5)
                        alert.discord_msg = await self.alert_channel.send(content=f"**{alert.headline}**",                                                  embed=alert.embed)
                    self.cached_alerts[alert.id] = alert
                    self.post_count += 1
                    print(f"Posted: {alert.event}")
                except discord.errors.Forbidden:
                    print(f"ERROR: Forbidden error while posting alert {alert.id}")
                    break
                except discord.errors.NotFound:
                    print(f"ERROR: Not Found error while posting alert {alert.id}")
                    break
                new_ids.remove(alert.id)

intents = discord.Intents.default()

bot = CustomBot(intents=intents, command_prefix=".")

@bot.hybrid_group(name="w")
async def wxgrp(ctx):
    pass

@wxgrp.group(name="add")
async def wxadd(ctx):
    pass

@commands.guild_only()
@wxadd.command(name="point")
async def add_point(ctx: commands.Context, latitude: float, longitude: float):
    """ Include alerts from forecast and county zones associated with a given GPS coordinate """

    msg = ""
    zones = await bot.weather.points(latitude, longitude)
    for zone in zones:
        bot.weather.alert_zones.update([zone.id])
        msg += f"{zone.id} {zone.name} ({zone.type})\n"
    await ctx.send(f"✅ Zones added:\n{msg}", ephemeral=True)
    return

@commands.guild_only()
@wxadd.command(name="zone")
async def add_zone(ctx: commands.Context, zone_id: str):
    """ Include alerts from a specified forecast zone """
    valid_id = re.compile(r"^[0-9a-zA-Z,]+$")
    zone_id = zone_id.upper()

    if not valid_id.fullmatch(zone_id):
        await ctx.send("❌ Invalid zone ID. Letters, numbers, and commas only.", ephemeral=True)
        return

    split_ids = [i.strip() for i in zone_id.split(",")]

    try:
        zones = await bot.weather.zones(*split_ids)
    except aiohttp.ClientResponseError as e:
        await ctx.send(f"❌ Couldn't add zone. Check your syntax. Error:{e.status} {e.message}.", ephemeral=True)
        return

    bot.weather.alert_zones.update(split_ids)
    print(f"Zones added: {bot.weather.alert_zones}")
    zone_list = []
    for i in zones:
        zone_list.append(f"[{i.name}](https://forecast.weather.gov/MapClick.php?zoneid={i.id})")
    await ctx.send(f"✅ Zone set:\n{"\n".join(zone_list)}", ephemeral=True)

@commands.guild_only()
@wxgrp.command(name="clear")
async def clear(ctx: commands.Context):
    """ Delete all zone filters """
    bot.weather.alert_zones.clear()
    await ctx.send("Alert filters cleared.", ephemeral=True)

@commands.guild_only()
@wxgrp.command(name="force")
async def force(ctx: commands.Context):
    """ Immediately check for alerts """
    bot.pause_alerts = False
    bot.check_alerts.stop()
    bot.check_alerts.restart()
    await bot.change_presence(status=discord.Status.online)
    print("Alert check forced.")
    await ctx.send("✅ Alert check forced.", ephemeral=True)

@commands.guild_only()
@wxgrp.command(name="pause")
async def toggle_pause(ctx: commands.Context):
    """ Pause or resume alert checks """
    if bot.pause_alerts:
        # resume
        bot.pause_alerts = False
        await bot.change_presence(status=discord.Status.online)
        await ctx.send("✅ ▶️ Alert checking resumed.", ephemeral=True)
    else:
        # pause
        bot.pause_alerts = True
        await bot.change_presence(status=discord.Status.idle)
        await ctx.send("✅ ⏸️ Alert checking paused.", ephemeral=True)

@commands.guild_only()
@wxgrp.command(name="prune")
async def toggle_prune(ctx: commands.Context):
    """ Toggle removal of expired alerts """
    if bot.prune:
        bot.prune = False
        msg = f"Disabled alert pruning. Inactive alert messages will be edited."
    else:
        bot.prune = True
        msg = f"Enabled alert pruning. Inactive alert messages will be deleted."
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
        await ctx.send(f"✅ Alert channel set: {ctx.channel.mention}", ephemeral=True)
        bot.alert_channel = ctx.channel
    except discord.errors.Forbidden:
        await ctx.send(f"❌ Cannot post to {ctx.channel.mention}. Permission was denied.", ephemeral=True)

@commands.guild_only()
@wxgrp.command(name="status")
async def status(ctx: commands.Context):
    """ Display parameters and API stats """
    content = ""
    if bot.alert_channel is None or len(bot.weather.alert_zones) == 0:
        content += "⚠️ ** Setup is not complete!** ⚠️\n"
        if len(bot.weather.alert_zones) == 0:
            content += "**Set alert filters** using `/w add point` or `/w add zone`.\n"
        if bot.alert_channel is None:
            content += "**Set alert channel.** Use `/w subscribe` in the alert channel.\n\n"
    else:
        content += f"Alert channel: {bot.alert_channel.mention}.\n" \
                   f"Active: **{len(bot.cached_alerts)}**\n" \
                   f"Total posted: **{bot.post_count}**\n"
    content += f"Check interval: **{bot.check_alerts.minutes}** minutes.\n" \
               f"API GET count: **{bot.weather.get_count}** " \
               f"Latest request: {f"<t:{int(bot.weather.request_latest.timestamp()):}:R>" if bot.weather.request_latest else "Never"}\n" \
               f"Alert zones: `{",".join(bot.weather.alert_zones)}`\n" \
               f"Alert checks are {"**paused**" if bot.pause_alerts else "**running**"}.\n" \
               f"Expired alerts will be {"**deleted**" if bot.prune else "**edited**"}.\n" \
               f"Bot uptime: <t:{int(bot.weather.start_time.timestamp())}:R>.\n"
    await ctx.send(content, ephemeral=True)

if __name__ == '__main__':
    if os.environ.get("TOKEN"):
        bot.run(os.environ["TOKEN"])
    else:
        print("Discord TOKEN environment var not set.")
