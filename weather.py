import urllib.request
import urllib.parse
import urllib.error
import json
import os
import math
import textwrap
import subprocess
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule

WIDTH = 58
DEFAULT_STATION = "KDCA"

METAR_URL = "https://aviationweather.gov/api/data/metar"
TAF_URL = "https://aviationweather.gov/api/data/taf"

NWS_API = "https://api.weather.gov"

NWS_RADAR_URL = "https://radar.weather.gov/"
GOES_URL = "https://www.star.nesdis.noaa.gov/GOES/"
SPC_URL = "https://www.spc.noaa.gov/products/outlook/"
WPC_URL = "https://www.wpc.ncep.noaa.gov/"
NHC_URL = "https://www.nhc.noaa.gov/"

USER_AGENT = (
    "Bandicuss-Field-Console/3.0 "
    "(personal weather console)"
)


# Rich v4 interface
console = Console()
RICH_BORDER = "bright_cyan"
RICH_LABEL = "grey62"
RICH_VALUE = "white"


# ==========================================================
# BASIC DISPLAY
# ==========================================================

def clear():
    os.system("clear")


def line(char="="):
    print(char * WIDTH)


def title(text):
    line("=")
    print(text.center(WIDTH))
    line("=")


def pause():
    print()
    input(" Press ENTER to continue...")


def wrapped(text, indent=" "):
    if not text:
        print(f"{indent}Not available")
        return

    for paragraph in str(text).splitlines():

        pieces = textwrap.wrap(
            paragraph,
            width=WIDTH - len(indent),
            break_long_words=False,
            break_on_hyphens=False,
        )

        if not pieces:
            print()
        else:
            for piece in pieces:
                print(indent + piece)


def formatted_taf(raw_taf):
    if not raw_taf:
        print(" TAF unavailable")
        return

    words = str(raw_taf).split()
    groups = []
    current = []

    for word in words:

        is_change_group = (
            word.startswith("FM")
            or word == "BECMG"
            or word == "TEMPO"
            or word == "PROB30"
            or word == "PROB40"
        )

        if is_change_group and current:
            groups.append(current)
            current = []

        current.append(word)

    if current:
        groups.append(current)

    for index, group in enumerate(groups):

        if index > 0:
            print()

        wrapped(
            " ".join(group),
            " "
        )


# ==========================================================
# CONVERSIONS / CALCULATIONS
# ==========================================================

def c_to_f(temp_c):
    if temp_c is None:
        return None

    return (temp_c * 9 / 5) + 32


def hpa_to_inhg(hpa):
    if hpa is None:
        return None

    return hpa * 0.0295299830714


def relative_humidity(temp_c, dew_c):
    if temp_c is None or dew_c is None:
        return None

    try:
        a = 17.625
        b = 243.04

        numerator = math.exp(
            (a * dew_c) / (b + dew_c)
        )

        denominator = math.exp(
            (a * temp_c) / (b + temp_c)
        )

        return 100 * (
            numerator / denominator
        )

    except Exception:
        return None


def wind_chill(temp_f, wind_kt):
    if temp_f is None or wind_kt is None:
        return None

    mph = wind_kt * 1.15078

    if temp_f > 50 or mph < 3:
        return None

    return (
        35.74
        + (0.6215 * temp_f)
        - (35.75 * (mph ** 0.16))
        + (
            0.4275
            * temp_f
            * (mph ** 0.16)
        )
    )


def heat_index(temp_f, rh):
    if temp_f is None or rh is None:
        return None

    if temp_f < 80 or rh < 40:
        return None

    t = temp_f
    r = rh

    return (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * r
        - 0.22475541 * t * r
        - 0.00683783 * t * t
        - 0.05481717 * r * r
        + 0.00122874 * t * t * r
        + 0.00085282 * t * r * r
        - 0.00000199 * t * t * r * r
    )


def wind_cardinal(degrees):
    if degrees is None:
        return ""

    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]

    index = round(
        degrees / 22.5
    ) % 16

    return directions[index]


# ==========================================================
# INTERNET / API FUNCTIONS
# ==========================================================

def fetch_json_url(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/geo+json, "
                "application/json"
            )
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=15
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def fetch_aviation_json(base_url, station):
    query = urllib.parse.urlencode({
        "ids": station,
        "format": "json"
    })

    request = urllib.request.Request(
        f"{base_url}?{query}",
        headers={
            "User-Agent": USER_AGENT
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=12
    ) as response:

        return json.loads(
            response.read().decode("utf-8")
        )


def fetch_metar(station):
    data = fetch_aviation_json(
        METAR_URL,
        station
    )

    if not data:
        return None

    return data[0]


def fetch_taf(station):
    data = fetch_aviation_json(
        TAF_URL,
        station
    )

    if not data:
        return None

    return data[0]


# ==========================================================
# NWS PRODUCTS
# ==========================================================

def fetch_nws_point(lat, lon):
    url = (
        f"{NWS_API}/points/"
        f"{lat:.4f},{lon:.4f}"
    )

    return fetch_json_url(url)


def fetch_nws_alerts(lat, lon):
    query = urllib.parse.urlencode({
        "point": f"{lat:.4f},{lon:.4f}",
        "status": "actual"
    })

    url = (
        f"{NWS_API}/alerts/active?"
        f"{query}"
    )

    data = fetch_json_url(url)

    return data.get(
        "features",
        []
    )


def fetch_nws_forecast(lat, lon):
    point_data = fetch_nws_point(
        lat,
        lon
    )

    properties = point_data.get(
        "properties",
        {}
    )

    forecast_url = properties.get(
        "forecast"
    )

    if not forecast_url:
        return None

    return fetch_json_url(
        forecast_url
    )


def get_alert_count(wx):
    lat = wx.get("lat")
    lon = wx.get("lon")

    if lat is None or lon is None:
        return None, []

    try:
        alerts = fetch_nws_alerts(
            lat,
            lon
        )

        return len(alerts), alerts

    except Exception:
        return None, []


# ==========================================================
# TIME FORMATTING
# ==========================================================

def friendly_time(value):
    if not value:
        return "N/A"

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )

        return parsed.strftime(
            "%Y-%m-%d %H:%M %Z"
        )

    except Exception:
        return str(value)


# ==========================================================
# METAR DISPLAY
# ==========================================================

def display_metar(station, wx):
    clear()

    title(
        f"CURRENT CONDITIONS - {station}"
    )

    temp_c = wx.get("temp")
    dew_c = wx.get("dewp")

    temp_f = c_to_f(temp_c)
    dew_f = c_to_f(dew_c)

    wind_dir = wx.get("wdir")
    wind_speed = wx.get("wspd")
    wind_gust = wx.get("wgst")

    visibility = wx.get("visib")
    alt_hpa = wx.get("altim")
    slp = wx.get("slp")

    flight_cat = wx.get(
        "fltCat",
        "N/A"
    )

    weather = wx.get(
        "wxString"
    )

    clouds = wx.get(
        "clouds",
        []
    )

    raw_metar = wx.get(
        "rawOb",
        "METAR unavailable"
    )

    rh = relative_humidity(
        temp_c,
        dew_c
    )

    wc = wind_chill(
        temp_f,
        wind_speed
    )

    hi = heat_index(
        temp_f,
        rh
    )

    print()

    print(
        f" FLIGHT CATEGORY : "
        f"{flight_cat}"
    )

    if temp_c is not None:
        print(
            f" TEMPERATURE     : "
            f"{temp_f:.1f} F / "
            f"{temp_c:.1f} C"
        )

    if dew_c is not None:
        print(
            f" DEWPOINT        : "
            f"{dew_f:.1f} F / "
            f"{dew_c:.1f} C"
        )

    if rh is not None:
        print(
            f" REL HUMIDITY    : "
            f"{rh:.0f}%"
        )

    if wc is not None:
        print(
            f" WIND CHILL      : "
            f"{wc:.1f} F"
        )

    if hi is not None:
        print(
            f" HEAT INDEX      : "
            f"{hi:.1f} F"
        )

    print()

    if wind_speed is not None:

        if wind_dir is None:
            wind_text = (
                f"Variable at "
                f"{wind_speed:.0f} kt"
            )

        else:
            direction = wind_cardinal(
                wind_dir
            )

            wind_text = (
                f"{wind_dir:03.0f} deg "
                f"({direction}) at "
                f"{wind_speed:.0f} kt"
            )

        if wind_gust is not None:
            wind_text += (
                f", gusting "
                f"{wind_gust:.0f} kt"
            )

        print(
            f" WIND            : "
            f"{wind_text}"
        )

    if visibility is not None:
        print(
            f" VISIBILITY      : "
            f"{visibility} SM"
        )

    if alt_hpa is not None:
        print(
            f" ALTIMETER       : "
            f"{hpa_to_inhg(alt_hpa):.2f} "
            f"inHg"
        )

    if slp is not None:
        print(
            f" SEA LEVEL PRESS : "
            f"{slp:.1f} hPa"
        )

    print()
    print(" WEATHER:")

    if weather:
        wrapped(
            weather,
            "   "
        )
    else:
        print(
            "   No significant "
            "weather reported"
        )

    print()
    print(" CLOUD LAYERS:")

    if clouds:

        for cloud_layer in clouds:

            cover = cloud_layer.get(
                "cover",
                ""
            )

            base = cloud_layer.get(
                "base"
            )

            if base is not None:
                print(
                    f"   {cover:<4} "
                    f"{base:>6} ft"
                )
            else:
                print(
                    f"   {cover}"
                )

    else:
        print(
            "   No cloud layers reported"
        )

    print()
    line("-")
    print(" RAW METAR")
    line("-")
    print()

    wrapped(raw_metar)

    print()
    line("=")


# ==========================================================
# TAF DISPLAY
# ==========================================================

def display_taf(station, taf):
    clear()

    title(
        f"TERMINAL FORECAST - {station}"
    )

    print()

    if not taf:
        print(
            " No TAF is available "
            "for this station."
        )

        print()
        line("=")

        return

    raw_taf = taf.get(
        "rawTAF"
    )

    if raw_taf is None:
        raw_taf = taf.get(
            "rawOb"
        )

    if raw_taf is None:
        raw_taf = (
            "TAF unavailable"
        )

    issue_time = taf.get(
        "issueTime"
    )

    if issue_time:
        print(
            f" ISSUE TIME: "
            f"{issue_time}"
        )

        print()

    print(" RAW TAF:")
    print()

    formatted_taf(
        raw_taf
    )

    print()
    line("=")


# ==========================================================
# QUICK AVIATION SUMMARY
# ==========================================================

def display_summary(station, wx, taf):
    clear()

    title(
        f"AVIATION WEATHER - {station}"
    )

    temp_c = wx.get("temp")
    dew_c = wx.get("dewp")

    temp_f = c_to_f(temp_c)
    dew_f = c_to_f(dew_c)

    wind_dir = wx.get("wdir")
    wind_speed = wx.get("wspd")
    wind_gust = wx.get("wgst")

    visibility = wx.get("visib")
    alt_hpa = wx.get("altim")

    flight_cat = wx.get(
        "fltCat",
        "N/A"
    )

    clouds = wx.get(
        "clouds",
        []
    )

    print()

    print(
        f" FLIGHT CATEGORY : "
        f"{flight_cat}"
    )

    if (
        temp_c is not None
        and dew_c is not None
    ):
        print(
            f" TEMP / DEWPOINT : "
            f"{temp_f:.0f}/"
            f"{dew_f:.0f} F "
            f"({temp_c:.0f}/"
            f"{dew_c:.0f} C)"
        )

    elif temp_c is not None:
        print(
            f" TEMPERATURE     : "
            f"{temp_f:.0f} F "
            f"({temp_c:.0f} C)"
        )

    print()

    if wind_speed is not None:

        if wind_dir is None:
            wind_text = (
                f"VRB "
                f"{wind_speed:.0f} KT"
            )

        else:
            wind_text = (
                f"{wind_dir:03.0f} "
                f"{wind_speed:.0f} KT"
            )

        if wind_gust is not None:
            wind_text += (
                f" G{wind_gust:.0f}"
            )

        print(
            f" WIND            : "
            f"{wind_text}"
        )

    if visibility is not None:
        print(
            f" VISIBILITY      : "
            f"{visibility} SM"
        )

    if alt_hpa is not None:
        print(
            f" ALTIMETER       : "
            f"{hpa_to_inhg(alt_hpa):.2f} "
            f"inHg"
        )

    ceiling = None

    for cloud_layer in clouds:

        if cloud_layer.get(
            "cover"
        ) in (
            "BKN",
            "OVC",
            "VV"
        ):

            base = cloud_layer.get(
                "base"
            )

            if base is not None:

                if (
                    ceiling is None
                    or base < ceiling
                ):
                    ceiling = base

    if ceiling is not None:
        print(
            f" CEILING         : "
            f"{ceiling} ft"
        )
    else:
        print(
            " CEILING         : "
            "None reported"
        )

    print()

    if taf:
        print(
            " TAF             : "
            "AVAILABLE"
        )
    else:
        print(
            " TAF             : "
            "NOT AVAILABLE"
        )

    print()
    line("-")
    print(" METAR")
    line("-")
    print()

    wrapped(
        wx.get(
            "rawOb",
            "METAR unavailable"
        )
    )

    if taf:

        print()
        line("-")
        print(" TAF")
        line("-")
        print()

        raw_taf = taf.get(
            "rawTAF"
        )

        if raw_taf is None:
            raw_taf = taf.get(
                "rawOb"
            )

        formatted_taf(
            raw_taf
            or "TAF unavailable"
        )

    print()
    line("=")


# ==========================================================
# NWS ALERT DISPLAY
# ==========================================================

def display_alerts(
    station,
    wx,
    cached_alerts=None
):
    clear()

    title(
        f"ACTIVE NWS ALERTS - {station}"
    )

    lat = wx.get("lat")
    lon = wx.get("lon")

    print()

    if lat is None or lon is None:
        print(
            " Station coordinates "
            "are unavailable."
        )

        print()
        line("=")

        return

    if cached_alerts is None:

        print(
            " Retrieving active "
            "NWS alerts..."
        )

        try:
            alerts = fetch_nws_alerts(
                lat,
                lon
            )

        except Exception as error:

            print()
            print(
                " Unable to retrieve "
                "NWS alerts."
            )

            print()

            wrapped(
                str(error),
                " "
            )

            print()
            line("=")

            return

    else:
        alerts = cached_alerts

    clear()

    title(
        f"ACTIVE NWS ALERTS - {station}"
    )

    print()

    if not alerts:

        print(
            " No active NWS watches, "
            "warnings, or advisories "
            "were found for this location."
        )

        print()
        line("=")

        return

    print(
        f" ACTIVE ALERTS: "
        f"{len(alerts)}"
    )

    print()

    for number, alert in enumerate(
        alerts,
        start=1
    ):

        properties = alert.get(
            "properties",
            {}
        )

        event = properties.get(
            "event",
            "Weather Alert"
        )

        severity = properties.get(
            "severity",
            "Unknown"
        )

        urgency = properties.get(
            "urgency",
            "Unknown"
        )

        certainty = properties.get(
            "certainty",
            "Unknown"
        )

        headline = properties.get(
            "headline"
        )

        area = properties.get(
            "areaDesc"
        )

        effective = properties.get(
            "effective"
        )

        expires = properties.get(
            "expires"
        )

        description = properties.get(
            "description"
        )

        instruction = properties.get(
            "instruction"
        )

        line("-")

        print(
            f" ALERT {number}: "
            f"{event}"
        )

        line("-")
        print()

        print(
            f" SEVERITY : "
            f"{severity}"
        )

        print(
            f" URGENCY  : "
            f"{urgency}"
        )

        print(
            f" CERTAINTY: "
            f"{certainty}"
        )

        print()

        if area:
            print(" AREA:")

            wrapped(
                area,
                "   "
            )

            print()

        if headline:
            print(" HEADLINE:")

            wrapped(
                headline,
                "   "
            )

            print()

        print(
            f" EFFECTIVE: "
            f"{friendly_time(effective)}"
        )

        print(
            f" EXPIRES  : "
            f"{friendly_time(expires)}"
        )

        if description:
            print()
            print(" DESCRIPTION:")

            wrapped(
                description,
                "   "
            )

        if instruction:
            print()
            print(" INSTRUCTIONS:")

            wrapped(
                instruction,
                "   "
            )

        print()

    line("=")


# ==========================================================
# NWS FORECAST
# ==========================================================

def display_nws_forecast(station, wx):
    clear()

    title(
        f"NWS FORECAST - {station}"
    )

    lat = wx.get("lat")
    lon = wx.get("lon")

    print()

    if lat is None or lon is None:
        print(
            " Station coordinates "
            "are unavailable."
        )

        print()
        line("=")

        return

    print(
        " Retrieving NWS forecast..."
    )

    try:
        forecast = fetch_nws_forecast(
            lat,
            lon
        )

    except urllib.error.HTTPError as error:

        print()
        print(
            " NWS forecast is not "
            "available for this location."
        )

        print(
            f" HTTP ERROR: "
            f"{error.code}"
        )

        print()
        line("=")

        return

    except Exception as error:

        print()
        print(
            " Unable to retrieve "
            "NWS forecast."
        )

        print()

        wrapped(
            str(error),
            " "
        )

        print()
        line("=")

        return

    if not forecast:
        print()
        print(
            " Forecast unavailable."
        )

        print()
        line("=")

        return

    periods = forecast.get(
        "properties",
        {}
    ).get(
        "periods",
        []
    )

    clear()

    title(
        f"NWS FORECAST - {station}"
    )

    print()

    if not periods:
        print(
            " No forecast periods "
            "were returned."
        )

        print()
        line("=")

        return

    for period in periods[:8]:

        name = period.get(
            "name",
            "Forecast"
        )

        temperature = period.get(
            "temperature"
        )

        unit = period.get(
            "temperatureUnit",
            "F"
        )

        short = period.get(
            "shortForecast",
            ""
        )

        detailed = period.get(
            "detailedForecast",
            ""
        )

        wind_speed = period.get(
            "windSpeed",
            ""
        )

        wind_direction = period.get(
            "windDirection",
            ""
        )

        line("-")
        print(
            f" {name.upper()}"
        )
        line("-")
        print()

        if temperature is not None:
            print(
                f" TEMP : "
                f"{temperature} {unit}"
            )

        if wind_speed:
            print(
                f" WIND : "
                f"{wind_direction} "
                f"{wind_speed}"
            )

        if short:
            print()
            wrapped(
                short,
                " "
            )

        if detailed:
            print()
            wrapped(
                detailed,
                " "
            )

        print()

    line("=")


# ==========================================================
# GRAPHICAL PRODUCTS
# ==========================================================

def launch_browser(url, product_name):
    clear()

    title(product_name)

    print()
    print(
        " Launching graphical product "
        "on the uConsole..."
    )
    print()

    try:

        subprocess.Popen(
            [
                "chromium",
                "--new-window",
                url
            ],
            env={
                **os.environ,
                "DISPLAY": ":0"
            },
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        print(
            " Product launched in Chromium."
        )

        print()
        print(
            " Close Chromium when finished."
        )

    except Exception as error:

        print(
            " Unable to launch Chromium."
        )

        print()

        wrapped(
            str(error),
            " "
        )

    print()
    line("=")


def graphical_weather_menu():
    while True:

        clear()

        title(
            "GRAPHICAL WEATHER"
        )

        print()
        print(
            " [1] NWS RADAR"
        )
        print(
            " [2] GOES SATELLITE"
        )
        print(
            " [3] SPC CONVECTIVE OUTLOOKS"
        )
        print(
            " [4] WPC FORECAST PRODUCTS"
        )
        print(
            " [5] NHC / TROPICAL WEATHER"
        )
        print(
            " [Q] BACK TO WEATHER CENTER"
        )

        print()
        line("=")

        choice = input(
            " SELECT: "
        ).strip().lower()

        if choice == "1":

            launch_browser(
                NWS_RADAR_URL,
                "NWS RADAR"
            )

            pause()

        elif choice == "2":

            launch_browser(
                GOES_URL,
                "GOES SATELLITE"
            )

            pause()

        elif choice == "3":

            launch_browser(
                SPC_URL,
                "SPC CONVECTIVE OUTLOOKS"
            )

            pause()

        elif choice == "4":

            launch_browser(
                WPC_URL,
                "WPC FORECAST PRODUCTS"
            )

            pause()

        elif choice == "5":

            launch_browser(
                NHC_URL,
                "NHC / TROPICAL WEATHER"
            )

            pause()

        elif choice == "q":
            return

        else:
            print()
            print(
                " Invalid selection."
            )

            pause()


# ==========================================================
# STATION DATA
# ==========================================================

def load_station(station):
    clear()

    title(
        "BANDICUSS WEATHER"
    )

    print()

    print(
        f" Retrieving aviation weather "
        f"for {station}..."
    )

    print()

    try:

        metar = fetch_metar(
            station
        )

        if metar is None:

            print(
                f" No METAR data found "
                f"for {station}."
            )

            pause()

            return None, None

    except Exception as error:

        print(
            " Unable to retrieve "
            "METAR data."
        )

        print()

        wrapped(
            str(error),
            " "
        )

        pause()

        return None, None

    try:
        taf = fetch_taf(
            station
        )

    except Exception:
        taf = None

    return metar, taf


# ==========================================================
# RICH V4 WEATHER CENTER DISPLAY
# ==========================================================

def rich_flight_category(value):
    value = str(value or "N/A").upper()
    colors = {
        "VFR": "bold bright_green",
        "MVFR": "bold bright_blue",
        "IFR": "bold bright_red",
        "LIFR": "bold magenta",
    }
    return Text(value, style=colors.get(value, "bold white"))


def station_location(wx, station):
    for key in ("name", "site", "stationName"):
        value = wx.get(key)
        if value:
            return str(value).upper()
    return station


def dashboard_ceiling(wx):
    ceiling = None
    for cloud_layer in wx.get("clouds", []) or []:
        if cloud_layer.get("cover") in ("BKN", "OVC", "VV"):
            base = cloud_layer.get("base")
            if base is not None and (ceiling is None or base < ceiling):
                ceiling = base
    return ceiling


def dashboard_wind(wx):
    speed = wx.get("wspd")
    direction = wx.get("wdir")
    gust = wx.get("wgst")

    if speed is None:
        return "N/A"

    if direction is None:
        text = f"VRB / {speed:.0f} KT"
    else:
        text = f"{direction:03.0f}° / {speed:.0f} KT"

    if gust is not None:
        text += f" G{gust:.0f}"

    return text


def build_v4_header():
    title_text = Text(justify="center")
    title_text.append("BANDICUSS", style="bold bright_cyan")
    title_text.append("  WEATHER CENTER", style="bold white")

    subtitle = Text(
        "AVIATION • FORECAST • ALERTS • GRAPHICAL WEATHER",
        style="grey62",
        justify="center",
    )

    return Panel(
        Group(title_text, subtitle),
        border_style=RICH_BORDER,
        padding=(0, 1),
    )


def build_v4_station_bar(station, wx, alert_count):
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=2)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    if alert_count is None:
        alert_text = Text("UNAVAILABLE", style="bold yellow")
    elif alert_count:
        alert_text = Text(f"{alert_count} ACTIVE", style="bold yellow")
    else:
        alert_text = Text("0 ACTIVE", style="bold green")

    table.add_row(
        Text("STATION", style=RICH_LABEL),
        Text(station, style="bold white"),
        Text("FLIGHT CAT", style=RICH_LABEL),
        rich_flight_category(wx.get("fltCat", "N/A")),
    )

    table.add_row(
        Text("LOCATION", style=RICH_LABEL),
        Text(station_location(wx, station), style="white"),
        Text("NWS ALERTS", style=RICH_LABEL),
        alert_text,
    )

    return Panel(table, border_style="blue", padding=(0, 1))


def build_v4_conditions(wx):
    temp_c = wx.get("temp")
    dew_c = wx.get("dewp")
    temp_f = c_to_f(temp_c)
    dew_f = c_to_f(dew_c)
    visibility = wx.get("visib")
    alt_hpa = wx.get("altim")
    ceiling = dashboard_ceiling(wx)

    temp_text = f"{temp_f:.0f}°F" if temp_f is not None else "N/A"
    dew_text = f"{dew_f:.0f}°F" if dew_f is not None else "N/A"
    vis_text = f"{visibility} SM" if visibility is not None else "N/A"
    ceiling_text = f"{ceiling} FT" if ceiling is not None else "CLR / NONE"
    alt_text = f"{hpa_to_inhg(alt_hpa):.2f}" if alt_hpa is not None else "N/A"

    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    table.add_row(
        Text("TEMP", style=RICH_LABEL),
        Text(temp_text, style=RICH_VALUE),
        Text("DEWPOINT", style=RICH_LABEL),
        Text(dew_text, style=RICH_VALUE),
    )
    table.add_row(
        Text("WIND", style=RICH_LABEL),
        Text(dashboard_wind(wx), style=RICH_VALUE),
        Text("VISIBILITY", style=RICH_LABEL),
        Text(vis_text, style=RICH_VALUE),
    )
    table.add_row(
        Text("CEILING", style=RICH_LABEL),
        Text(ceiling_text, style=RICH_VALUE),
        Text("ALTIMETER", style=RICH_LABEL),
        Text(alt_text, style=RICH_VALUE),
    )

    return Panel(
        table,
        title="[bold bright_cyan]CURRENT CONDITIONS[/]",
        border_style=RICH_BORDER,
        padding=(0, 1),
    )


def build_v4_menu():
    menu = Table.grid(expand=True)
    menu.add_column(width=6, justify="center")
    menu.add_column(ratio=1)
    menu.add_column(width=6, justify="center")
    menu.add_column(ratio=1)

    menu.add_row(
        Text("[1]", style="bold bright_cyan"),
        Text("AVIATION SUMMARY", style="white"),
        Text("[4]", style="bold bright_cyan"),
        Text("NWS ALERTS", style="white"),
    )
    menu.add_row(
        Text("[2]", style="bold bright_cyan"),
        Text("METAR / CONDITIONS", style="white"),
        Text("[5]", style="bold bright_cyan"),
        Text("NWS FORECAST", style="white"),
    )
    menu.add_row(
        Text("[3]", style="bold bright_cyan"),
        Text("TAF / TERMINAL FORECAST", style="white"),
        Text("[6]", style="bold bright_cyan"),
        Text("GRAPHICAL WEATHER", style="white"),
    )

    return Panel(
        menu,
        title="[bold bright_cyan]WEATHER PRODUCTS[/]",
        border_style=RICH_BORDER,
        padding=(1, 1),
    )


def build_v4_controls():
    controls = Text(justify="center")
    controls.append("[R]", style="bold bright_cyan")
    controls.append(" REFRESH     ", style="white")
    controls.append("[S]", style="bold bright_cyan")
    controls.append(" CHANGE STATION     ", style="white")
    controls.append("[Q]", style="bold bright_cyan")
    controls.append(" EXIT", style="white")
    return controls


def draw_v4_dashboard(station, wx, alert_count):
    console.clear()
    console.print(build_v4_header())
    console.print(build_v4_station_bar(station, wx, alert_count))
    console.print(build_v4_conditions(wx))
    console.print(build_v4_menu())
    console.print(build_v4_controls())
    console.print()
    console.print(
        Rule(
            "[grey62]BANDICUSS WEATHER • v4.0[/]",
            style="grey35",
        )
    )
    console.print()


# ==========================================================
# WEATHER CENTER
# ==========================================================

def weather_menu(station):
    metar, taf = load_station(station)

    if metar is None:
        return station

    alert_count, alerts = get_alert_count(metar)

    while True:
        draw_v4_dashboard(station, metar, alert_count)

        choice = input(" SELECT OPTION: ").strip().lower()

        if choice == "1":
            display_summary(station, metar, taf)
            pause()

        elif choice == "2":
            display_metar(station, metar)
            pause()

        elif choice == "3":
            display_taf(station, taf)
            pause()

        elif choice == "4":
            display_alerts(station, metar, alerts)
            pause()

        elif choice == "5":
            display_nws_forecast(station, metar)
            pause()

        elif choice == "6":
            graphical_weather_menu()

        elif choice == "r":
            new_metar, new_taf = load_station(station)

            if new_metar is not None:
                metar = new_metar
                taf = new_taf
                alert_count, alerts = get_alert_count(metar)

        elif choice == "s":
            new_station = input(
                "\n Enter ICAO station: "
            ).strip().upper()

            if new_station:
                new_metar, new_taf = load_station(new_station)

                if new_metar is not None:
                    station = new_station
                    metar = new_metar
                    taf = new_taf
                    alert_count, alerts = get_alert_count(metar)

        elif choice == "q":
            return station

        else:
            print()
            print(" Invalid selection.")
            pause()


# ==========================================================
# MAIN
# ==========================================================

def main():
    station = DEFAULT_STATION

    clear()

    title(
        "BANDICUSS WEATHER MODULE"
    )

    print()

    print(
        f" Default station: "
        f"{DEFAULT_STATION}"
    )

    print()

    print(
        " Enter an ICAO airport identifier."
    )

    print(
        " Examples: "
        "KDCA  KADW  KBWI  KJFK  EGLL"
    )

    print()

    selected = input(
        f" ICAO station "
        f"[{station}]: "
    ).strip().upper()

    if selected:
        station = selected

    weather_menu(
        station
    )

    clear()


if __name__ == "__main__":
    main()
