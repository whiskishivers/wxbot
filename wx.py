import datetime as dt
import requests
import re


class Alert:
    def __init__(self, wxalert):
        """Alert object with only the required fields for the project."""
        self.description = wxalert["description"]
        self.event = wxalert["event"]
        self.expires = dt.datetime.fromisoformat(wxalert["expires"])
        self.headline = wxalert["headline"]
        self.id = wxalert["id"]
        self.messageType = wxalert["messageType"]
        self.references = wxalert["references"]
        self.response = wxalert["response"]
        self.sent = dt.datetime.fromisoformat(wxalert["sent"])
        self.severity = wxalert["severity"]
        self.senderName = wxalert["senderName"]
        self.urgency = wxalert["urgency"]

        # Instruction field is missing sometimes
        try:
            self.instruction = wxalert["instruction"]
        except KeyError:
            self.instruction = None

        # Get the office identifier if it is included
        try:
            wmo = wxalert["parameters"]["WMOidentifier"][0].split(" ")[1][1:]
        except KeyError:
            wmo = None
        self.__setattr__("wmo", wmo)

        # Remove un-needed line breaks in the description and instruction fields
        self.description = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.description)
        if self.instruction is not None:
            self.instruction = re.sub(r'(?<!\n)\n(?!\n)', ' ', self.instruction)

    def __repr__(self):
        return f'<Alert:{self.id}>'

    @property
    def reference_id(self):
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

    def active(self, **params):
        """ Returns all currently active alerts """
        return self.parent.get("alerts/active", params=params)

    def active_properties(self, **params):
        """ Get active alerts and wrap them into the Alert class."""
        alerts = self.active(**params)
        return [Alert(a["properties"]) for a in alerts["features"]]


class Client:
    """ Basic client for retrieving active alerts from weather.gov API."""

    def __init__(self, track_stats=True):
        self.base_url = "https://api.weather.gov"
        self.headers = {"User-Agent": "Discord weather bot | python-requests"}
        self.session = requests.Session()
        self.get_count = 0
        self.bytes_recvd = 0
        self.last_ok = None
        self._track_stats = track_stats

        self.alerts = Alerts(self)

    def get(self, endpoint: str, params: dict = None):
        """ Basic get for api endpoints"""
        with self.session.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params, timeout=5) as resp:
            if self._track_stats:
                self.get_count += 1
                self.bytes_recvd += len(resp.content)
            resp.raise_for_status()  # api error
            self.last_ok = dt.datetime.now()
            return resp.json()

    def stats(self):
        if self.last_ok is None:
            last_ok = "Never"
        else:
            diff = dt.datetime.now() - self.last_ok
            last_ok = f"{diff.seconds:,} seconds ago"

        return {"get_count": self.get_count,
                "bytes_recvd": f"{human_bytes(self.bytes_recvd)}",
                "last_ok": last_ok
                }


def human_bytes(nbytes: int):
    """ Returns a human-readable string from an integer representing a byte count"""
    d = {"B": 1, "kB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "TB": 1000 ** 4}
    for k, v in d.items():
        if nbytes / v < 1000:
            return f"{nbytes / v:.1f} {k}"
    return f"{nbytes / v:.1f} {k}"
