import aiohttp
import datetime as dt
import discord
import re


class FeatureCollection(list):
    """ Default object from API """
    updated: dt.datetime

    def __init__(self, fcoll=dict()):
        super().__init__()
        self.title = fcoll.get("title", None)
        updated = fcoll.get("updated", None)
        if updated:
            self.updated = dt.datetime.fromisoformat(updated)
        if len(fcoll) == 0:
            return
        for feature in fcoll["features"]:
            match feature["properties"]["@type"]:
                case "wx:Alert":
                    self.append(Alert(feature))
                case "wx:Point":
                    continue #self.append(Point(feature))
                case "wx:Zone":
                    self.append(Zone(feature))
                case _:
                    self.append(Feature(feature))

    def __repr__(self):
        return f"FeatureCollection({self.title})"


class Feature:
    id: str = None

    def __init__(self, feature):
        for k, v in feature["properties"].items():
            setattr(self, k, v)

    def __repr__(self):
        return f"Feature({self.id})"


class Alert(Feature):
    affectedZones: list
    areaDesc: str = ""
    description: str = ""
    discord_msg: discord.Message = None
    effective: dt.datetime = None
    ends: dt.datetime = None
    event: str = ""
    expires: dt.datetime = None
    instruction: str = ""
    parameters: dict = dict()
    senderName: str = ""
    sent: dt.datetime = None
    onset: dt.datetime = None
    severity: str = ""
    urgency: str = ""
    wmo: str | None
    zones: FeatureCollection
    _alert_colors = {("Severe", "Expected"): discord.Color.dark_gold(),
                     ("Severe", "Future"): discord.Color.dark_gold(),
                     ("Severe", "Immediate"): discord.Color.gold(),
                     ("Extreme", "Expected"): discord.Color.dark_red(),
                     ("Extreme", "Future"): discord.Color.dark_red(),
                     ("Extreme", "Immediate"): discord.Color.red()}

    def __init__(self, alert_feature):
        super().__init__(alert_feature)

        # pull out required parameters
        self.nws_headline = self.parameters.get("NWSheadline", None)
        try:
            self.wmo = self.parameters["WMOidentifier"][0].split(" ")[1][-3:]
        except (KeyError, TypeError):
            self.wmo = None

        # Fold extra line breaks
        if self.description is not None:
            self.description = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.description)
        if self.instruction is not None:
            self.instruction = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.instruction)
        # Change required date strings to datetime objects
        for i in ("sent", "effective", "onset", "expires", "ends"):
            try:
                setattr(self, i, dt.datetime.fromisoformat(alert_feature["properties"][i]))
            except TypeError:  # null
                setattr(self, i, None)

    def __repr__(self):
        return f"Alert({self.event})"

    @property
    def embed(self) -> discord.Embed:
        """ Discord message embed """
        color = self._alert_colors.get((self.severity, self.urgency), None)
        description = ""
        if self.severity == "Extreme" or self.urgency == "Immediate":
            description += self.description[:4096]

        # Use short headline and zone list for non-urgent alerts
        elif self.nws_headline:
            description += f"{"\n".join(self.nws_headline)}\n\n"
            description += self.areaDesc

        embed = discord.Embed(color=color,
                              title=self.event,
                              url=f"https://alerts.weather.gov/search?id={self.id}",
                              description=description,
                              timestamp=self.sent)
        if self.instruction:
            instruction = self.instruction[:1024]
            embed.add_field(name="Instructions", value=instruction, inline=False)
        embed.add_field(name="Severity", value=f"{self.severity} - {self.urgency}")
        if self.onset is not None:
            embed.add_field(name="Onset", value = f"<t:{int(self.onset.timestamp())}:R>")
        if self.ends is not None:
            embed.add_field(name="Ends", value = f"<t:{int(self.ends.timestamp())}:R>")
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed

    @property
    def embed_inactive(self) -> discord.Embed:
        """ Discord message embed for inactive alerts """
        embed = discord.Embed(title=self.event, url=f"https://alerts.weather.gov/search?id={self.id}",
                              description="*This alert is no longer active.*")
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed


class Point(Feature):
    forecastZone: str

    @property
    def forecast_zone(self):
        return self.forecast_zone


class Zone(Feature):
    def __repr__(self):
        return f"Zone({self.id})"

class ClientAlerts:
    def __init__(self, parent):
        self.parent = parent

    async def __call__(self, alert_id: str = None):
        if alert_id:
            return Alert(await self.parent.get(f"alerts/{alert_id}"))

    async def active(self, **params):
        return FeatureCollection(await self.parent.get(f"alerts/active", params=params))

class ClientPoints:
    def __init__(self, parent):
        self.parent = parent

    async def __call__(self, latitude: float, longitude: float):
        lat, lon = f"{latitude:.4f}", f"{longitude:.4f}"
        point = Point(await self.parent.get(f"points/{lat},{lon}"))
        zone = await client.zones.raw(point.forecastZone)
        return zone

class ClientZones:
    def __init__(self, parent):
        self.parent = parent
        self._cache = dict()

    async def __call__(self, *zone_ids) -> [Zone]:
        """ Return list of zone objects. Query API for non-cached zones. """
        param_ids = [i for i in zone_ids if i not in self._cache.keys()]
        if len(param_ids) > 0:
            params = {"id": ",".join(param_ids)}
            new_zones = FeatureCollection(await client.get("zones/forecast", params=params))
            for i in new_zones:
                self._cache[i.id] = i
        return [self._cache[i] for i in zone_ids]

    async def raw(self, zone_url: str) -> Zone:
        if self._cache.get(zone_url, None) is None:
            resp = await client.get(zone_url, raw=True)
            self._cache[zone_url] = resp
        return Zone(self._cache[zone_url])

class Client:
    def __init__(self):
        self.start_time = dt.datetime.now()
        self.headers = {"User-Agent": "python-aiohttp | Discord weather bot"}
        self.session = None
        self.alert_zones = set()
        self.get_count = 0
        self.get_last = None
        self.alerts = ClientAlerts(self)
        self.points = ClientPoints(self)
        self.zones = ClientZones(self)

    async def initialize_session(self):
        """Initializes the session."""
        self.session = aiohttp.ClientSession()

    async def get(self, endpoint, params=None, raw=False):
        if self.session is None:
            await self.initialize_session()
        url = f"{endpoint}" if raw else f"https://api.weather.gov/{endpoint}"
        try:
            async with self.session.get(url, params=params, headers=self.headers) as resp:
                self.get_count += 1
                self.get_last = dt.datetime.now()
                print(f"{resp.status} {resp.url}")
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            print(f"Error during GET request: {endpoint}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

client = Client()
