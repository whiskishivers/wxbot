import datetime as dt
import discord
import requests
import re

severity_color = {("Severe", "Future"): discord.Color.dark_gold(),
                  ("Severe", "Immediate"): discord.Color.gold(),
                  ("Extreme", "Future"): discord.Color.dark_red(),
                  ("Extreme", "Immediate"): discord.Color.red()}

class WeatherAlert:
    def __init__(self, wxalert):
        """Alert object with only the required fields for the project."""
        self.areaDesc = wxalert["areaDesc"]
        self.description = wxalert["description"]
        self.discord_msg = None
        self.event = wxalert["event"]
        self.expires = dt.datetime.fromisoformat(wxalert["expires"])
        self.headline = wxalert["headline"]
        self.id = wxalert["id"]
        self.instruction = wxalert.get("instruction", None)
        self.messageType = wxalert["messageType"]
        self.nws_headline = wxalert["parameters"].get("NWSheadline", None)
        self.references = wxalert["references"]
        self.response = wxalert["response"]
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

    def __repr__(self):
        return f'<Alert:{self.id}>'

    @property
    def embed(self) -> discord.Embed:
        """ Embed for chat response """
        color = severity_color.get((self.severity, self.urgency), None)
        instruction = None

        # Non-urgent alerts only include area descriptions. Immediate alerts include full description.
        if self.urgency == "Immediate":
            description = self.description[:4096]
            if self.instruction:
                instruction = self.instruction[:1024]
        else:
            description = self.areaDesc

        embed = discord.Embed(color=color,
                              title=self.event,
                              url=f"https://alerts.weather.gov/search?id={self.id}",
                              description=description,
                              timestamp=self.sent)

        if instruction is not None:
            embed.add_field(name="Instructions", value=instruction, inline=False)

        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed

    @property
    def embed_inactive(self):
        """ Discord chat response embed to use when the alert becomes inactive."""
        embed = discord.Embed(title= self.event,
                              url=f"https://alerts.weather.gov/search?id={self.id}",
                              description="*This alert is no longer active.*")
        if self.wmo:
            author_url = f"https://www.weather.gov/{self.wmo.lower()}"
            embed.set_author(name=self.senderName, url=author_url)
        return embed


    @property
    def reference_id(self) -> str:
        """The latest alert that is being updated. Returns None if no references exist."""
        try:
            return self.references[-1]['identifier']
        except (IndexError, TypeError):
            return None

class Alerts:
    """ Class for retrieving alert info """
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, alertID: str = None, **params):
        """ Returns all alerts if no alertID specified. """
        if alertID:
            return self.parent.get(f"alerts/{alertID}", params=params)
        return self.parent.get(f'alerts', params=params)

    def active(self, **params) -> list[WeatherAlert]:
        """ Alerts in the WeatherAlert class."""
        params["urgency"] = "Future,Immediate"
        alerts = self.parent.get("alerts/active", params=params)
        return [WeatherAlert(a["properties"]) for a in alerts["features"]]

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

    def get(self, endpoint: str, params: dict = None) -> dict:
        """ Basic get for api endpoints """
        with self.session.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params, timeout=5) as resp:
            if self._track_stats:
                self.get_count += 1
                self.bytes_recvd += len(resp.content)
            resp.raise_for_status()  # api error
            self.last_ok = dt.datetime.now()
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
