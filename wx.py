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
        for k,v in feature["properties"].items():
            setattr(self, k, v)

    def __repr__(self):
        return f"Feature({self.id})"

class Alert(Feature):
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

        # Change required date strings to datetime objects
        for i in ("sent", "effective", "onset", "expires", "ends"):
            try:
                setattr(self, i, dt.datetime.fromisoformat(alert_feature["properties"][i]))
            except TypeError: # null
                setattr(self, i, None)

    def __repr__(self):
        return f"Alert({self.event})"

    @property
    def embed(self) -> discord.Embed:
        """ Chat embed """
        color = self._alert_colors.get((self.severity, self.urgency), None)
        description = ""
        instruction = None
        if self.urgency == "Immediate":
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

class Point(Feature):
    forecastZone: str
    def __init__(self, point_feature: dict):
        super().__init__(point_feature)
        zone_id = re.search(r"forecast/([A-Z0-9]{6})", self.forecastZone).groups(1)[0]
        self.zone = client.zones.forecast(zone_id)

class Zone(Feature):
    def __init__(self, zone_feature):
        super().__init__(zone_feature)

    def __repr__(self):
        return f"Zone({self.id})"

    def active_alerts(self):
        return client.alerts.active(zone=self.id)

class GovernmentOrganization:
    id: str
    name: str
    address: dict
    telephone: str
    faxNumber: str
    email: str
    sameAs: str
    nwsRegion: str
    parentOrganization: str
    responsibleCounties: list
    responsibleForecastZones: list
    responsibleFireZones: list
    responsibleObservationStations: list

    def __init__(self, gov_org):
        if gov_org.get("@type", None) == "GovernmentOrganization":
            for k,v in gov_org.items():
                if not k.startswith("@"):
                    setattr(self, k, v)
        else:
            raise TypeError("API returned a non-office object.")

    def __repr__(self):
        return f"GovernmentOrganization({self.name})"

class ClientAlerts:
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, alert_id: str = None):
        if alert_id:
            return Alert(self.parent.get(f"alerts/{alert_id}"))

    def active(self, **params):
        return FeatureCollection(self.parent.get(f"alerts/active", params=params))

class ClientOffice:
    def __init__(self, parent):
        self.parent = parent
        self.__cache = dict()

    def __call__(self, office_id: str = None):
        if not office_id in self.__cache:
            self.__cache[office_id] = GovernmentOrganization(self.parent.get(f"offices/{office_id.upper()}"))
        return self.__cache.get(office_id, None)

class ClientPoints:
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, lat: float, lon: float, **params):
        return Point(self.parent.get(f"points/{lat:.4f},{lon:.4f}"))

class ClientZones:
    def __init__(self, parent):
        self.parent = parent
        self.cache = dict()

    def __call__(self, *zone_ids) -> FeatureCollection | None:
        r = FeatureCollection()
        r.title = "Zone lookup"
        for zone_id in zone_ids:
            r.append(self.forecast(zone_id))
        return r

    def forecast(self, zone_id: str = None) -> Zone:
        cache_id = zone_id
        if self.cache.get(cache_id, None) is None:
            self.cache[cache_id] = self.parent.get(f"zones/forecast/{zone_id}")
        return Zone(self.cache[cache_id])

class Client:
    """ Basic client for querying weather.gov API."""
    def __init__(self, track_stats=True):
        self.headers = {"User-Agent": "python-requests | Discord weather bot"}
        self.session = requests.Session()
        self.get_count = 0
        self.alerts = ClientAlerts(self)
        self.office = ClientOffice(self)
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
