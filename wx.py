import datetime as dt
import discord
import requests
import re

class FeatureCollection:
    """ Default object from API"""
    def __init__(self, fcoll):
        self.title = fcoll.get("title", None)
        self.features = []
        for feature in fcoll["features"]:
            match feature["properties"]["@type"]:
                case "wx:Alert":
                    self.features.append(Alert(feature))
                case "wx:Zone":
                    self.features.append(Zone(feature))
                case _:
                    self.features.append(Feature(feature))

    def __iter__(self):
        return self.features.__iter__()

    def sort(self,**params):
        return self.features.sort(**params)

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
    ends: dt.datetime = None
    event: str = ""
    expires: dt.datetime | None = None
    instruction: str = ""
    parameters: dict = dict()
    senderName: str = ""
    sent: dt.datetime | None = None
    severity: str = ""
    urgency: str = ""
    wmo: str
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
        except:
            self.wmo = None

        # Fold extra line breaks
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
        """ Embed for the chat message """
        color = self._alert_colors.get((self.severity, self.urgency), None)
        instruction = None
        description = ""
        # Non-urgent alerts only include area descriptions. Immediate alerts include full description.
        if self.urgency == "Immediate":
            description += self.description[:4096]
            if self.instruction:
                instruction = self.instruction[:1024]
        else:
            if self.nws_headline:
                description += f"{"\n".join(self.nws_headline)}\n\n"
                areas = self.areaDesc.split(";")
                areas = [i.strip() for i in areas]
                areas.sort()
                description += "\n".join(areas)

        embed = discord.Embed(color=color, title=self.event, url=f"https://alerts.weather.gov/search?id={self.id}",
                              description=description, timestamp=self.sent)
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        if instruction is not None:
            embed.add_field(name="Instructions", value=instruction, inline=False)

        embed.add_field(name="Severity", value=f"{self.severity} - {self.urgency}")
        return embed

    @property
    def embed_inactive(self) -> discord.Embed:
        """ Embed for editing inactive chat messages """
        if self.ends:
            timestamp = self.expires
        else:
            timestamp = self.sent

        embed = discord.Embed(title=self.event, url=f"https://alerts.weather.gov/search?id={self.id}",
                              description="*This alert is no longer active.*", timestamp=timestamp)
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed

class Zone(Feature):
    def __init__(self, zone_feature):
        super().__init__(zone_feature)

    def __repr__(self):
        return f"Zone({self.id})"

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

    def __call__(self, office_id: str = None):
        if office_id:
            return GovernmentOrganization(self.parent.get(f"offices/{office_id.upper()}"))

class ClientZones:
    def __init__(self, parent):
        self.parent = parent
    def __call__(self, zone_id: str = None, **params):
        if zone_id:
            params["id"] = zone_id
            return FeatureCollection(self.parent.get(f"zones", params=params))



class Client:
    """ Basic client for querying weather.gov API."""
    def __init__(self, track_stats=True):
        self.headers = {"User-Agent": "python-requests | Discord weather bot"}
        self.session = requests.Session()
        self.alerts = ClientAlerts(self)
        self.office = ClientOffice(self)
        self.zones = ClientZones(self)

    def get(self, endpoint: str, raw=False, params: dict = None) -> dict:
        """ GET requests  """
        if params is None:
            params = dict()
        url = f"https://api.weather.gov/{endpoint}"
        if raw:
            url = endpoint
        with self.session.get(url=url, headers=self.headers, params=params, timeout=5) as resp:
            print(f"API GET: {resp.status_code} {resp.url}")
            resp.raise_for_status()  # api error
            return resp.json()

client = Client()
