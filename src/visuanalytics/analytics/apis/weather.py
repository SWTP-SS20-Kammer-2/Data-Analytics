"""
Dieses Modul enthält die Funktionalität zum Beziehen der Wettervorhersage-Daten von der Weatherbit-API.
"""

import json
import requests

from visuanalytics.analytics.util import resources
from visuanalytics.analytics.util import config_manager

CITIES = ["Kiel", "Berlin", "Dresden", "Hannover", "Bremen", "Düsseldorf", "Frankfurt", "Nürnberg", "Stuttgart",
          "München", "Saarbrücken", "Schwerin", "Hamburg", "Gießen", "Konstanz", "Magdeburg", "Leipzig", "Mainz",
          "Regensburg"]
"""
list: Städte, für die wir die Wettervorhersage von der Weatherbit-API beziehen.
"""

WEATHERBIT_URL = "https://api.weatherbit.io/v2.0/forecast/daily?"

WEATHERBIT_API_KEY = config_manager.get_private()["api_keys"]["weatherbit"]


def get_forecasts(single=False, cityname="Giessen"):
    # TODO (David): Die Städtenamen als Parameter übergeben statt eine globale Konstante zu verwenden
    """
    Bezieht die 16-Tage-Wettervorhersage für 15 Städte Deutschlands und bündelt sie in einer Liste.

    Jede JSON-Antwort wird mittels json.loads() in ein dictionary konvertiert und in einer Liste gespeichert.

    :returns: Eine Liste von Dictionaries, welche je eine JSON-Response der API repräsentieren.
    :rtype: dict

    :raises:
        ValueError: Wenn der Response-Code eine andere Nummer als 200 enthält. Dies kann vor allem bei einem fehlenden
        oder ungültigen API-Key vorkommen.
        socket.gaierror: Wenn keine Verbindung zum Internet besteht.
    """
    json_data = []
    if single:
        json_data.append(_fetch(requests.get(_forecast_request(cityname))))
    else:
        for c in CITIES:
            json_data.append(_fetch(requests.get(_forecast_request(c))))
    return json_data


def _fetch(response):
    if response.status_code != 200:
        raise ValueError("Response-Code: " + str(response.status_code))
    return json.loads(response.content)


def _forecast_request(location):
    return WEATHERBIT_URL + "city=" + location + "&key=" + WEATHERBIT_API_KEY


def get_example(single=False):
    """
    Bezieht die 16-Tage-Wettervorhersage für 15 Städte Deutschlands (aus der examples/weather.json)  und bündelt sie in einer Liste.

    :return: Eine Liste von Dictionaries, welche je eine JSON-Response der API repräsentieren ( aus der json datein gelesen)
    :rtype: dict

    """
    if single:
        with resources.open_resource("exampledata/example_single_weather.json", "r") as json_file:
            return json.load(json_file)
    with resources.open_resource("exampledata/example_weather.json", "r") as json_file:
        return json.load(json_file)
