import datetime as dt
import discord
import requests
import re

severity_color = {("Severe", "Expected"): discord.Color.dark_gold(),
                  ("Severe", "Future"): discord.Color.dark_gold(),
                  ("Severe", "Immediate"): discord.Color.gold(),
                  ("Extreme", "Expected"): discord.Color.dark_red(),
                  ("Extreme", "Future"): discord.Color.dark_red(),
                  ("Extreme", "Immediate"): discord.Color.red()}

class Alert:
    def __init__(self, wxalert):
        """Alert object with only the required fields for the project."""
        self.areaDesc = wxalert["areaDesc"]
        self.description = wxalert["description"]
        self.discord_msg = None
        self.event = wxalert["event"]
        self.headline = wxalert["headline"]
        self.id = wxalert["id"]
        self.instruction = wxalert.get("instruction", None)
        self.nws_headline = wxalert["parameters"].get("NWSheadline", None)
        self.sent = dt.datetime.fromisoformat(wxalert["sent"])
        self.severity = wxalert["severity"]
        self.senderName = wxalert["senderName"]
        self.urgency = wxalert["urgency"]
        self.wmo = None

        # Get the office identifier if it is included
        try:
            self.wmo = wxalert["parameters"]["WMOidentifier"][0].split(" ")[1][1:]
        except KeyError:
            pass

        # Fold extra line breaks
        self.description = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.description)
        if self.instruction is not None:
            self.instruction = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.instruction)

    def __eq__(self, other):
        """ Really lazy compare """
        return type(other) == type(self) and other.id == self.id

    def __lt__(self, other):
        return self.sent < other.sent

    def __repr__(self):
        return f'Alert(event={self.event})'

    @property
    def embed(self) -> discord.Embed:
        """ Embed for the chat message """
        color = severity_color.get((self.severity, self.urgency), None)
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
            description += "\n".join([i.strip() for i in sorted(self.areaDesc.split(";"))])

        embed = discord.Embed(color=color,
                              title=self.event,
                              url=f"https://alerts.weather.gov/search?id={self.id}",
                              description=description,
                              timestamp=self.sent)
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)

        if instruction is not None:
            embed.add_field(name="Instructions", value=instruction, inline=False)

        embed.add_field(name="Severity", value=f"{self.severity} - {self.urgency}")

        return embed

    @property
    def embed_inactive(self):
        """ Embed for the chat message when the alert becomes inactive """
        embed = discord.Embed(title=self.event,
                              url=f"https://alerts.weather.gov/search?id={self.id}",
                              description="*This alert is no longer active.*")
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed

class Zone:
    def __init__(self, zone):
        self.id = zone["id"]
        self.type = zone["type"]
        self.name = zone["name"]
        self.state = zone["state"]
        self.grid_identifier = zone["gridIdentifier"]

    def __repr__(self):
        return f"<Zone:{self.id}, {self.name}>"

    @property
    def alerts(self):
        return client.alerts(zone=self.id)

    @property
    def alerts_active(self):
        return client.alerts.active(zone=self.id)

class Alerts:
    """ Alert API calls """
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, alert_id: str = None, **params) -> [Alert]:
        """ Returns all alerts if no alertID specified. """
        if alert_id:
            alerts = self.parent.get("alerts", params={"id": alert_id})["features"]
        else:
            alerts = self.parent.get("alerts", params=params)["features"]
        return [Alert(i["properties"]) for i in alerts]

    def active(self, **params):
        """ Alerts in the WeatherAlert class."""
        alerts = self.parent.get("alerts/active", params=params)["features"]
        return [Alert(i["properties"]) for i in alerts]

    def active_count(self, **params):
        """ Alerts in the WeatherAlert class."""
        alerts = self.parent.get("alerts/active/count", params=params)["features"]
        return [Alert(i["properties"]) for i in alerts]


class Zones:
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, zone_id:str = None, **params):
        """ Retrieve zone with specific zone ID. """
        if zone_id:
            params = {"id": zone_id}
        else:
            params = dict()
        zones =  self.parent.get("zones", params=params)["features"]
        return [Zone(i["properties"]) for i in zones]

    def land(self, **params):

        zones = self.parent.get("zones/land", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

    def marine(self, **params):
        zones = self.parent.get("zones/marine", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

    def forecast(self, **params):
        zones = self.parent.get("zones/forecast", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

    def public(self, **params):
        zones = self.parent.get("zones/public", params=params)
        return [i["properties"] for i in zones["features"]]

    def coastal(self, **params):
        zones = self.parent.get("zones/coastal", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

    def offshore(self, **params):
        zones = self.parent.get("zones/offshore", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

    def fire(self, **params):
        zones = self.parent.get("zones/fire", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

    def county(self, **params):
        zones = self.parent.get("zones/county", params=params)
        return [Zone(i["properties"]) for i in zones["features"]]

class Client:
    """ Basic client for querying weather.gov API."""

    def __init__(self, track_stats=True):
        self.base_url = "https://api.weather.gov"
        self.headers = {"User-Agent": "python-requests | Discord weather bot"}
        self.session = requests.Session()
        self.get_count = 0
        self.bytes_recvd = 0
        self.last_ok = None
        self._track_stats = track_stats

        self.alerts = Alerts(self)
        self.zones = Zones(self)

    def get(self, endpoint: str, raw=False, params: dict = None) -> dict:
        """ GET requests for API """
        if params is None:
            params = dict()

        url = f"{self.base_url}/{endpoint}"
        if raw:
            url = endpoint

        with self.session.get(url=url, headers=self.headers, params=params, timeout=5) as resp:
            if self._track_stats:
                self.get_count += 1
                self.bytes_recvd += len(resp.content)
            resp.raise_for_status()  # api error
            self.last_ok = dt.datetime.now()
            print(f"API GET:{resp.url} {resp.reason}")
            return resp.json()

    def ping(self):
            if self.get("") == {"status": "OK"}:
                return "OK"
            return None

    def stats(self):
        if self.last_ok is None:
            last_ok = "Never"
        else:
            diff = dt.datetime.now() - self.last_ok
            last_ok = f"{diff.seconds:,} seconds ago"

        return {"get_count": self.get_count,
                "bytes_recvd": f"{human_bytes(self.bytes_recvd)}",
                "last_ok": last_ok}

def human_bytes(nbytes: int):
    """ Human-readable byte count """
    d = {"B": 1, "kB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4}
    for k, v in d.items():
        if nbytes / v < 1000:
            return f"{nbytes / v:.1f} {k}"
    return f"{nbytes / v:.1f} {k}"

client = Client()
