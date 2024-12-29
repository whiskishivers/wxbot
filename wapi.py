import datetime as dt
import discord
import requests
import re


class FeatureCollection(list):
    """ Default object from API """

    def __init__(self, fcoll=dict()):
        super().__init__()
        self.title = fcoll.get("title", None)
        if len(fcoll) == 0:
            return
        for feature in fcoll["features"]:
            match feature["properties"]["@type"]:
                case "wx:Alert":
                    self.append(Alert(feature))
                case "wx:Point":
                    self.append(Point(feature))
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
    discord_msg: discord.Message | None = None
    effective: dt.datetime | None = None
    ends: dt.datetime = None
    event: str = ""
    expires: dt.datetime | None = None
    instruction: str = ""
    parameters: dict = dict()
    senderName: str = ""
    sent: dt.datetime | None = None
    onset: dt.datetime | None = None
    severity: str = ""
    urgency: str = ""
    wmo: str | None
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

        # Cache affected zones
        for i in self.affectedZones.copy():
            self.affectedZones.remove(i)
            self.affectedZones.append(client.zones.raw(i))

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
        """ Chat embed """
        color = self._alert_colors.get((self.severity, self.urgency), None)
        description = ""
        if self.severity == "Extreme" or self.urgency == "Immediate":
            description += self.description[:4096]
        # Use short headline and area list for non-urgent alerts
        elif self.nws_headline:
            description += f"{"\n".join(self.nws_headline)}\n\n"
            areas = self.areaDesc.split(";")
            areas = [i.strip() for i in areas]
            areas.sort()
            description += "\n".join(areas)

        embed = discord.Embed(color=color,
                              title=self.event,
                              url=f"https://alerts.weather.gov/search?id={self.id}",
                              description=description,
                              timestamp=self.onset)

        if self.instruction:
            instruction = self.instruction[:1024]
            embed.add_field(name="Instructions", value=instruction, inline=False)
        embed.add_field(name="Severity", value=f"{self.severity}")
        embed.add_field(name="Urgency", value=self.urgency)

        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)

        return embed

    @property
    def embed_inactive(self) -> discord.Embed:
        """ Embed for editing inactive chat messages """
        embed = discord.Embed(title=self.event, url=f"https://alerts.weather.gov/search?id={self.id}",
                              description="*This alert is no longer active.*")
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed


class Zone(Feature):
    def __init__(self, zone_feature):
        super().__init__(zone_feature)

    def __repr__(self):
        return f"Zone({self.id})"

    def active_alerts(self):
        return client.alerts.active(zone=self.id)


class Point(Feature):
    zone: Zone
    gridX: float
    gridY: float

    def __init__(self, point_feature: dict):
        super().__init__(point_feature)
        self.zone = client.zones.raw(self.forecastZone)

    def __repr__(self):
        return f"Point({self.gridX},{self.gridY})"


class ClientAlerts:
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, alert_id: str = None):
        if alert_id:
            return Alert(self.parent.get(f"alerts/{alert_id}"))

    def active(self, **params):
        return FeatureCollection(self.parent.get(f"alerts/active", params=params))


class ClientPoints:
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, lat: float, lon: float, **params):
        return Point(self.parent.get(f"points/{lat:.4f},{lon:.4f}"))


class ClientZones:
    def __init__(self, parent):
        self.parent = parent
        self._cache = dict()

    def __call__(self, *zone_ids) -> FeatureCollection | None:
        r = FeatureCollection()
        r.title = "Zone lookup"
        [r.append(self.forecast(i)) for i in zone_ids]
        return r

    def forecast(self, zone_id: str = None) -> Zone:
        if self._cache.get(zone_id, None) is None:
            self._cache[zone_id] = self.parent.get(f"zones/forecast/{zone_id}")
        return Zone(self._cache[zone_id])

    def raw(self, zone_url: str) -> Zone:
        if self._cache.get(zone_url, None) is None:
            resp = client.get(zone_url, raw=True)
            self._cache[zone_url] = resp
        return Zone(self._cache[zone_url])


class Client:
    """ Basic client for querying weather.gov API."""

    def __init__(self, track_stats=True):
        self.headers = {"User-Agent": "python-requests | Discord weather bot"}
        self.session = requests.Session()
        self.get_count = 0
        self.alerts = ClientAlerts(self)
        self.points = ClientPoints(self)
        self.zones = ClientZones(self)

    def get(self, endpoint: str, raw=False, params: dict = None) -> dict:
        """ GET requests  """
        if params is None:
            params = dict()
        url = f"https://api.weather.gov/{endpoint}"
        if raw:
            url = endpoint
        with self.session.get(url=url, headers=self.headers, params=params, timeout=5) as resp:
            self.get_count += 1
            print(f"API GET: {resp.status_code} {resp.url}")
            resp.raise_for_status()  # api error
            return resp.json()

client = Client()