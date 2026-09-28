import urllib.request
import urllib.parse
import urllib.error
import json
import os
import math
import textwrap
import subprocess
import time
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
    "Bandicuss-Weather/4.0 "
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
    console.clear()

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    title_text = Text(justify="center")
    title_text.append("BANDICUSS", style="bold bright_cyan")
    title_text.append("  METAR / CURRENT CONDITIONS", style="bold white")

    subtitle = Text(
        f"{station} • OBSERVATION • AVIATION IMPACTS",
        style="grey62",
        justify="center",
    )

    console.print(
        Panel(
            Group(title_text, subtitle),
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # VALUES
    # ------------------------------------------------------

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

    flight_cat = wx.get("fltCat", "N/A")
    weather = wx.get("wxString")
    clouds = wx.get("clouds", []) or []

    raw_metar = wx.get(
        "rawOb",
        "METAR unavailable",
    )

    rh = relative_humidity(
        temp_c,
        dew_c,
    )

    wc = wind_chill(
        temp_f,
        wind_speed,
    )

    hi = heat_index(
        temp_f,
        rh,
    )

    # ------------------------------------------------------
    # AVIATION IMPACT COLORS
    # ------------------------------------------------------

    def ceiling_style(base):
        if base is None:
            return "white"

        if base < 500:
            return "bold magenta"

        if base < 1000:
            return "bold bright_red"

        if base <= 3000:
            return "bold bright_blue"

        return "bold bright_green"

    def visibility_style(vis):
        if vis is None:
            return "white"

        try:
            vis = float(vis)
        except (TypeError, ValueError):
            return "white"

        if vis < 1:
            return "bold magenta"

        if vis < 3:
            return "bold bright_red"

        if vis <= 5:
            return "bold bright_blue"

        return "bold bright_green"

    # ------------------------------------------------------
    # STATION STATUS
    # ------------------------------------------------------

    station_table = Table.grid(expand=True)
    station_table.add_column(ratio=1)
    station_table.add_column(ratio=2)
    station_table.add_column(ratio=1)
    station_table.add_column(ratio=1)

    station_table.add_row(
        Text("STATION", style=RICH_LABEL),
        Text(station, style="bold white"),
        Text("FLIGHT CATEGORY", style=RICH_LABEL),
        rich_flight_category(flight_cat),
    )

    station_table.add_row(
        Text("LOCATION", style=RICH_LABEL),
        Text(
            station_location(wx, station),
            style="white",
        ),
        Text("VISIBILITY", style=RICH_LABEL),
        Text(
            f"{visibility} SM"
            if visibility is not None
            else "N/A",
            style=visibility_style(visibility),
        ),
    )

    console.print(
        Panel(
            station_table,
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # TEMPERATURE / MOISTURE
    # ------------------------------------------------------

    temp_table = Table.grid(expand=True)
    temp_table.add_column(ratio=1)
    temp_table.add_column(ratio=2)
    temp_table.add_column(ratio=1)
    temp_table.add_column(ratio=2)

    temp_table.add_row(
        Text("TEMPERATURE", style=RICH_LABEL),
        Text(
            f"{temp_f:.1f}°F / {temp_c:.1f}°C"
            if temp_c is not None
            else "N/A",
            style=RICH_VALUE,
        ),
        Text("DEWPOINT", style=RICH_LABEL),
        Text(
            f"{dew_f:.1f}°F / {dew_c:.1f}°C"
            if dew_c is not None
            else "N/A",
            style=RICH_VALUE,
        ),
    )

    temp_table.add_row(
        Text("REL HUMIDITY", style=RICH_LABEL),
        Text(
            f"{rh:.0f}%"
            if rh is not None
            else "N/A",
            style=RICH_VALUE,
        ),
        Text("WIND CHILL", style=RICH_LABEL),
        Text(
            f"{wc:.1f}°F"
            if wc is not None
            else "N/A",
            style=RICH_VALUE,
        ),
    )

    temp_table.add_row(
        Text("HEAT INDEX", style=RICH_LABEL),
        Text(
            f"{hi:.1f}°F"
            if hi is not None
            else "N/A",
            style=RICH_VALUE,
        ),
        Text("PRESENT WX", style=RICH_LABEL),
        Text(
            str(weather)
            if weather
            else "NONE REPORTED",
            style="white",
        ),
    )

    console.print(
        Panel(
            temp_table,
            title="[bold bright_cyan]TEMPERATURE / MOISTURE[/]",
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # WIND / PRESSURE
    # ------------------------------------------------------

    if wind_speed is None:
        wind_text = "N/A"

    elif wind_dir is None:
        wind_text = (
            f"VARIABLE AT {wind_speed:.0f} KT"
        )

    else:
        direction = wind_cardinal(wind_dir)

        wind_text = (
            f"{wind_dir:03.0f}° ({direction}) "
            f"AT {wind_speed:.0f} KT"
        )

    if wind_gust is not None:
        wind_text += (
            f" GUSTING {wind_gust:.0f} KT"
        )

    pressure_table = Table.grid(expand=True)
    pressure_table.add_column(ratio=1)
    pressure_table.add_column(ratio=2)
    pressure_table.add_column(ratio=1)
    pressure_table.add_column(ratio=2)

    pressure_table.add_row(
        Text("WIND", style=RICH_LABEL),
        Text(wind_text, style=RICH_VALUE),
        Text("VISIBILITY", style=RICH_LABEL),
        Text(
            f"{visibility} SM"
            if visibility is not None
            else "N/A",
            style=visibility_style(visibility),
        ),
    )

    pressure_table.add_row(
        Text("ALTIMETER", style=RICH_LABEL),
        Text(
            f"{hpa_to_inhg(alt_hpa):.2f} inHg"
            if alt_hpa is not None
            else "N/A",
            style=RICH_VALUE,
        ),
        Text("SEA LEVEL PRESS", style=RICH_LABEL),
        Text(
            f"{slp:.1f} hPa"
            if slp is not None
            else "N/A",
            style=RICH_VALUE,
        ),
    )

    console.print(
        Panel(
            pressure_table,
            title="[bold bright_cyan]WIND / VISIBILITY / PRESSURE[/]",
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # CLOUD LAYERS
    # ------------------------------------------------------

    cloud_table = Table.grid(expand=True)
    cloud_table.add_column(
        width=12,
        justify="center",
    )
    cloud_table.add_column(
        width=18,
        justify="right",
    )
    cloud_table.add_column(ratio=1)

    cloud_table.add_row(
        Text("COVER", style=RICH_LABEL),
        Text("BASE", style=RICH_LABEL),
        Text(" AVIATION IMPACT", style=RICH_LABEL),
    )

    if clouds:
        for cloud_layer in clouds:
            cover = str(
                cloud_layer.get(
                    "cover",
                    "",
                )
            ).upper()

            base = cloud_layer.get("base")

            is_ceiling = (
                cover in (
                    "BKN",
                    "OVC",
                    "VV",
                )
            )

            if base is not None:
                base_text = f"{base} FT"
            else:
                base_text = "NOT REPORTED"

            if is_ceiling and base is not None:
                style = ceiling_style(base)

                if base < 500:
                    impact = "LIFR CEILING"

                elif base < 1000:
                    impact = "IFR CEILING"

                elif base <= 3000:
                    impact = "MVFR CEILING"

                else:
                    impact = "VFR CEILING"

            elif is_ceiling:
                style = "white"
                impact = "CEILING"

            else:
                style = "white"
                impact = "NON-CEILING LAYER"

            cloud_table.add_row(
                Text(cover or "N/A", style=style),
                Text(base_text, style=style),
                Text(f" {impact}", style=style),
            )

    else:
        cloud_table.add_row(
            Text("NONE", style="white"),
            Text("—", style="grey62"),
            Text(
                "NO CLOUD LAYERS REPORTED",
                style="grey62",
            ),
        )

    console.print(
        Panel(
            cloud_table,
            title="[bold bright_cyan]CLOUD LAYERS[/]",
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # RAW METAR
    # ------------------------------------------------------

    console.print(
        Panel(
            Text(
                str(raw_metar),
                style="bold white",
            ),
            title="[bold bright_cyan]RAW METAR[/]",
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------

    controls = Text(justify="center")
    controls.append(
        "[ENTER]",
        style="bold bright_cyan",
    )
    controls.append(
        " RETURN TO WEATHER CENTER",
        style="white",
    )

    console.print(controls)
    console.print()

    console.print(
        Rule(
            "[grey62]BANDICUSS WEATHER • METAR / CONDITIONS • v4.0[/]",
            style="grey35",
        )
    )

    console.print()

    input(" Press ENTER to return...")


# ==========================================================
# TAF DISPLAY
# ==========================================================

def display_taf(station, taf):
    console.clear()

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    title_text = Text(justify="center")
    title_text.append("BANDICUSS", style="bold bright_cyan")
    title_text.append("  TERMINAL FORECAST", style="bold white")

    subtitle = Text(
        f"{station} • TAF • FORECAST AVIATION IMPACTS",
        style="grey62",
        justify="center",
    )

    console.print(
        Panel(
            Group(title_text, subtitle),
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # NO TAF AVAILABLE
    # ------------------------------------------------------

    if not taf:
        console.print(
            Panel(
                Text(
                    f"No TAF is available for {station}.",
                    style="bold yellow",
                    justify="center",
                ),
                title="[bold bright_cyan]TAF STATUS[/]",
                border_style="yellow",
                padding=(1, 1),
            )
        )

        controls = Text(justify="center")
        controls.append("[ENTER]", style="bold bright_cyan")
        controls.append(
            " RETURN TO WEATHER CENTER",
            style="white",
        )

        console.print(controls)
        console.print()
        console.print(
            Rule(
                "[grey62]BANDICUSS WEATHER • TERMINAL FORECAST • v4.0[/]",
                style="grey35",
            )
        )
        console.print()

        input(" Press ENTER to return...")
        return

    # ------------------------------------------------------
    # TAF DATA
    # ------------------------------------------------------

    raw_taf = taf.get("rawTAF")

    if raw_taf is None:
        raw_taf = taf.get("rawOb")

    raw_taf = raw_taf or "TAF unavailable"

    issue_time = taf.get("issueTime")

    # ------------------------------------------------------
    # IMPACT HELPERS
    # ------------------------------------------------------

    def ceiling_style(base):
        if base < 500:
            return "bold magenta", "LIFR"

        if base < 1000:
            return "bold bright_red", "IFR"

        if base <= 3000:
            return "bold bright_blue", "MVFR"

        return "bold bright_green", "VFR"

    def visibility_style(vis):
        if vis < 1:
            return "bold magenta", "LIFR"

        if vis < 3:
            return "bold bright_red", "IFR"

        if vis <= 5:
            return "bold bright_blue", "MVFR"

        return "bold bright_green", "VFR"

    def impact_rank(category):
        ranks = {
            "VFR": 0,
            "MVFR": 1,
            "IFR": 2,
            "LIFR": 3,
        }
        return ranks.get(category, -1)

    def category_style(category):
        styles = {
            "VFR": "bold bright_green",
            "MVFR": "bold bright_blue",
            "IFR": "bold bright_red",
            "LIFR": "bold magenta",
        }
        return styles.get(category, "white")

    # ------------------------------------------------------
    # TAF GROUP PARSING
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # FORECAST INFORMATION
    # ------------------------------------------------------

    info_table = Table.grid(expand=True)
    info_table.add_column(ratio=1)
    info_table.add_column(ratio=2)
    info_table.add_column(ratio=1)
    info_table.add_column(ratio=2)

    info_table.add_row(
        Text("STATION", style=RICH_LABEL),
        Text(station, style="bold white"),
        Text("ISSUE TIME", style=RICH_LABEL),
        Text(
            str(issue_time) if issue_time else "N/A",
            style="white",
        ),
    )

    info_table.add_row(
        Text("FORECAST GROUPS", style=RICH_LABEL),
        Text(str(len(groups)), style="bold white"),
        Text("TAF STATUS", style=RICH_LABEL),
        Text("AVAILABLE", style="bold green"),
    )

    console.print(
        Panel(
            info_table,
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # FORECAST GROUPS
    # ------------------------------------------------------

    for index, group in enumerate(groups):

        if not group:
            continue

        if index == 0:
            group_name = "BASE"
            marker_style = "bold bright_cyan"
            forecast_words = group

        else:
            marker = group[0]

            if marker.startswith("FM"):
                group_name = marker
                marker_style = "bold bright_green"

            elif marker == "TEMPO":
                group_name = marker
                marker_style = "bold yellow"

            elif marker.startswith("PROB"):
                group_name = marker
                marker_style = "bold magenta"

            elif marker == "BECMG":
                group_name = marker
                marker_style = "bold bright_blue"

            else:
                group_name = marker
                marker_style = "bold white"

            forecast_words = group[1:]

        # --------------------------------------------------
        # IDENTIFY CEILING / VISIBILITY IMPACTS
        # --------------------------------------------------

        ceiling_impacts = []
        visibility_impacts = []

        lowest_ceiling = None
        lowest_visibility = None

        for word in forecast_words:
            token = word.upper()

            # ----------------------------------------------
            # CEILING: BKN / OVC / VV
            # ----------------------------------------------

            if (
                token.startswith("BKN")
                or token.startswith("OVC")
                or token.startswith("VV")
            ):
                if token.startswith("VV"):
                    height_text = token[2:5]
                else:
                    height_text = token[3:6]

                if height_text.isdigit():
                    base = int(height_text) * 100

                    style, category = ceiling_style(base)

                    ceiling_impacts.append(
                        (
                            token,
                            base,
                            style,
                            category,
                        )
                    )

                    if (
                        lowest_ceiling is None
                        or base < lowest_ceiling
                    ):
                        lowest_ceiling = base

            # ----------------------------------------------
            # VISIBILITY
            # ----------------------------------------------

            vis_value = None

            if token.endswith("SM"):
                vis_token = token[:-2]

                try:
                    if "/" in vis_token:
                        numerator, denominator = vis_token.split("/", 1)

                        vis_value = (
                            float(numerator)
                            / float(denominator)
                        )

                    else:
                        vis_value = float(vis_token)

                except (ValueError, ZeroDivisionError):
                    vis_value = None

            if vis_value is not None:
                style, category = visibility_style(
                    vis_value
                )

                visibility_impacts.append(
                    (
                        token,
                        vis_value,
                        style,
                        category,
                    )
                )

                if (
                    lowest_visibility is None
                    or vis_value < lowest_visibility
                ):
                    lowest_visibility = vis_value

        # --------------------------------------------------
        # DETERMINE GROUP IMPACT
        # --------------------------------------------------

        group_category = None

        if lowest_ceiling is not None:
            _, ceiling_category = ceiling_style(
                lowest_ceiling
            )
            group_category = ceiling_category

        if lowest_visibility is not None:
            _, visibility_category = visibility_style(
                lowest_visibility
            )

            if (
                group_category is None
                or impact_rank(visibility_category)
                > impact_rank(group_category)
            ):
                group_category = visibility_category

        # --------------------------------------------------
        # GROUP HEADER
        # --------------------------------------------------

        group_header = Text()
        group_header.append(
            group_name,
            style=marker_style,
        )

        if group_category:
            group_header.append(
                "   •   ",
                style="grey62",
            )
            group_header.append(
                group_category,
                style=category_style(group_category),
            )

        # --------------------------------------------------
        # COLOR FORECAST TOKENS
        # --------------------------------------------------

        forecast_line = Text()

        for word_index, word in enumerate(forecast_words):

            token = word.upper()
            token_style = "white"

            for (
                ceiling_token,
                _,
                style,
                _,
            ) in ceiling_impacts:
                if token == ceiling_token:
                    token_style = style
                    break

            for (
                vis_token,
                _,
                style,
                _,
            ) in visibility_impacts:
                if token == vis_token:
                    token_style = style
                    break

            if word_index:
                forecast_line.append(" ")

            forecast_line.append(
                word,
                style=token_style,
            )

        # --------------------------------------------------
        # IMPACT SUMMARY
        # --------------------------------------------------

        impact_table = Table.grid(expand=True)
        impact_table.add_column(ratio=1)
        impact_table.add_column(ratio=2)
        impact_table.add_column(ratio=1)
        impact_table.add_column(ratio=2)

        if lowest_ceiling is not None:
            ceiling_color, ceiling_category = ceiling_style(
                lowest_ceiling
            )

            ceiling_text = Text(
                f"{lowest_ceiling} FT • {ceiling_category}",
                style=ceiling_color,
            )

        else:
            ceiling_text = Text(
                "NO CEILING RESTRICTION",
                style="grey62",
            )

        if lowest_visibility is not None:
            vis_color, vis_category = visibility_style(
                lowest_visibility
            )

            visibility_text = Text(
                f"{lowest_visibility:g} SM • {vis_category}",
                style=vis_color,
            )

        else:
            visibility_text = Text(
                "NOT RESTRICTED / NOT REPORTED",
                style="grey62",
            )

        impact_table.add_row(
            Text("CEILING", style=RICH_LABEL),
            ceiling_text,
            Text("VISIBILITY", style=RICH_LABEL),
            visibility_text,
        )

        group_contents = Group(
            forecast_line,
            Text(""),
            impact_table,
        )

        console.print(
            Panel(
                group_contents,
                title=group_header,
                border_style=(
                    category_style(group_category)
                    if group_category
                    else "blue"
                ),
                padding=(0, 1),
            )
        )

    # ------------------------------------------------------
    # RAW TAF
    # ------------------------------------------------------

    raw_taf_renderables = []

    for index, group in enumerate(groups):
        group_text = Text()

        if index == 0:
            group_text.append(
                "BASE  ",
                style="bold bright_cyan",
            )
            taf_words = group

        else:
            marker = group[0]

            if marker.startswith("FM"):
                marker_style = "bold bright_green"

            elif marker == "TEMPO":
                marker_style = "bold yellow"

            elif marker.startswith("PROB"):
                marker_style = "bold magenta"

            elif marker == "BECMG":
                marker_style = "bold bright_blue"

            else:
                marker_style = "bold white"

            group_text.append(
                f"{marker}  ",
                style=marker_style,
            )

            taf_words = group[1:]

        group_text.append(
            " ".join(taf_words),
            style="white",
        )

        raw_taf_renderables.append(group_text)

    if raw_taf_renderables:
        raw_taf_display = Group(
            *raw_taf_renderables
        )
    else:
        raw_taf_display = Text(
            "TAF unavailable",
            style="yellow",
        )

    console.print(
        Panel(
            raw_taf_display,
            title="[bold bright_cyan]RAW TAF[/]",
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------

    controls = Text(justify="center")
    controls.append(
        "[ENTER]",
        style="bold bright_cyan",
    )
    controls.append(
        " RETURN TO WEATHER CENTER",
        style="white",
    )

    console.print(controls)
    console.print()

    console.print(
        Rule(
            "[grey62]BANDICUSS WEATHER • TERMINAL FORECAST • v4.0[/]",
            style="grey35",
        )
    )

    console.print()

    input(" Press ENTER to return...")


# ==========================================================
# QUICK AVIATION SUMMARY
# ==========================================================

def display_summary(station, wx, taf):
    console.clear()

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    title_text = Text(justify="center")
    title_text.append("BANDICUSS", style="bold bright_cyan")
    title_text.append("  AVIATION SUMMARY", style="bold white")

    subtitle = Text(
        f"{station} • CURRENT CONDITIONS • METAR • TAF",
        style="grey62",
        justify="center",
    )

    console.print(
        Panel(
            Group(title_text, subtitle),
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # WEATHER VALUES
    # ------------------------------------------------------

    temp_c = wx.get("temp")
    dew_c = wx.get("dewp")

    temp_f = c_to_f(temp_c)
    dew_f = c_to_f(dew_c)

    wind_dir = wx.get("wdir")
    wind_speed = wx.get("wspd")
    wind_gust = wx.get("wgst")

    visibility = wx.get("visib")
    alt_hpa = wx.get("altim")

    flight_cat = wx.get("fltCat", "N/A")
    clouds = wx.get("clouds", []) or []

    ceiling = None

    for cloud_layer in clouds:
        if cloud_layer.get("cover") in ("BKN", "OVC", "VV"):
            base = cloud_layer.get("base")

            if base is not None:
                if ceiling is None or base < ceiling:
                    ceiling = base

    # ------------------------------------------------------
    # STATION STATUS
    # ------------------------------------------------------

    station_table = Table.grid(expand=True)
    station_table.add_column(ratio=1)
    station_table.add_column(ratio=2)
    station_table.add_column(ratio=1)
    station_table.add_column(ratio=1)

    station_table.add_row(
        Text("STATION", style=RICH_LABEL),
        Text(station, style="bold white"),
        Text("FLIGHT CATEGORY", style=RICH_LABEL),
        rich_flight_category(flight_cat),
    )

    station_table.add_row(
        Text("LOCATION", style=RICH_LABEL),
        Text(station_location(wx, station), style="white"),
        Text("TAF STATUS", style=RICH_LABEL),
        Text(
            "AVAILABLE" if taf else "NOT AVAILABLE",
            style="bold green" if taf else "bold yellow",
        ),
    )

    console.print(
        Panel(
            station_table,
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # CURRENT CONDITIONS
    # ------------------------------------------------------

    if temp_f is not None:
        temp_text = f"{temp_f:.0f}°F / {temp_c:.0f}°C"
    else:
        temp_text = "N/A"

    if dew_f is not None:
        dew_text = f"{dew_f:.0f}°F / {dew_c:.0f}°C"
    else:
        dew_text = "N/A"

    if wind_speed is None:
        wind_text = "N/A"

    elif wind_dir is None:
        wind_text = f"VRB / {wind_speed:.0f} KT"

    else:
        wind_text = f"{wind_dir:03.0f}° / {wind_speed:.0f} KT"

    if wind_gust is not None:
        wind_text += f" G{wind_gust:.0f}"

    if visibility is not None:
        visibility_text = f"{visibility} SM"
    else:
        visibility_text = "N/A"

    if alt_hpa is not None:
        altimeter_text = f"{hpa_to_inhg(alt_hpa):.2f} inHg"
    else:
        altimeter_text = "N/A"

    if ceiling is not None:
        ceiling_text = f"{ceiling} FT"
    else:
        ceiling_text = "CLR / NONE"

    conditions = Table.grid(expand=True)
    conditions.add_column(ratio=1)
    conditions.add_column(ratio=2)
    conditions.add_column(ratio=1)
    conditions.add_column(ratio=2)

    conditions.add_row(
        Text("TEMPERATURE", style=RICH_LABEL),
        Text(temp_text, style=RICH_VALUE),
        Text("DEWPOINT", style=RICH_LABEL),
        Text(dew_text, style=RICH_VALUE),
    )

    conditions.add_row(
        Text("WIND", style=RICH_LABEL),
        Text(wind_text, style=RICH_VALUE),
        Text("VISIBILITY", style=RICH_LABEL),
        Text(visibility_text, style=RICH_VALUE),
    )

    conditions.add_row(
        Text("CEILING", style=RICH_LABEL),
        Text(ceiling_text, style=RICH_VALUE),
        Text("ALTIMETER", style=RICH_LABEL),
        Text(altimeter_text, style=RICH_VALUE),
    )

    console.print(
        Panel(
            conditions,
            title="[bold bright_cyan]CURRENT CONDITIONS[/]",
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # METAR
    # ------------------------------------------------------

    raw_metar = wx.get(
        "rawOb",
        "METAR unavailable",
    )

    console.print(
        Panel(
            Text(
                str(raw_metar),
                style="bold white",
            ),
            title="[bold bright_cyan]METAR[/]",
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # TAF
    # ------------------------------------------------------

    if taf:
        raw_taf = taf.get("rawTAF")

        if raw_taf is None:
            raw_taf = taf.get("rawOb")

        raw_taf = raw_taf or "TAF unavailable"

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

        taf_renderables = []

        for index, group in enumerate(groups):
            group_text = Text()

            if index == 0:
                group_text.append(
                    "BASE  ",
                    style="bold bright_cyan",
                )
                forecast_words = group

            else:
                marker = group[0]

                if marker.startswith("FM"):
                    marker_style = "bold bright_green"

                elif marker == "TEMPO":
                    marker_style = "bold yellow"

                elif marker.startswith("PROB"):
                    marker_style = "bold magenta"

                elif marker == "BECMG":
                    marker_style = "bold bright_blue"

                else:
                    marker_style = "bold white"

                group_text.append(
                    f"{marker}  ",
                    style=marker_style,
                )

                forecast_words = group[1:]

            group_text.append(
                " ".join(forecast_words),
                style="white",
            )

            taf_renderables.append(group_text)

        if taf_renderables:
            taf_display = Group(*taf_renderables)
        else:
            taf_display = Text(
                "TAF unavailable",
                style="yellow",
            )

    else:
        taf_display = Text(
            "TAF NOT AVAILABLE",
            style="bold yellow",
        )

    console.print(
        Panel(
            taf_display,
            title="[bold bright_cyan]TERMINAL AERODROME FORECAST[/]",
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------

    controls = Text(justify="center")
    controls.append("[ENTER]", style="bold bright_cyan")
    controls.append(" RETURN TO WEATHER CENTER", style="white")

    console.print(controls)
    console.print()

    console.print(
        Rule(
            "[grey62]BANDICUSS WEATHER • AVIATION SUMMARY • v4.0[/]",
            style="grey35",
        )
    )

    console.print()

    input(" Press ENTER to return...")


# ==========================================================
def display_alerts(
    station,
    wx,
    cached_alerts=None
):
    console.clear()

    # ------------------------------------------------------
    # HEADER
    # ------------------------------------------------------

    title_text = Text(justify="center")
    title_text.append(
        "BANDICUSS",
        style="bold bright_cyan",
    )
    title_text.append(
        "  NWS ALERTS",
        style="bold white",
    )

    subtitle = Text(
        f"{station} • WATCHES • WARNINGS • ADVISORIES",
        style="grey62",
        justify="center",
    )

    console.print(
        Panel(
            Group(title_text, subtitle),
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    lat = wx.get("lat")
    lon = wx.get("lon")

    # ------------------------------------------------------
    # RETURN CONTROL
    # ------------------------------------------------------

    def alerts_footer():
        controls = Text(justify="center")
        controls.append(
            "[ENTER]",
            style="bold bright_cyan",
        )
        controls.append(
            " RETURN TO WEATHER CENTER",
            style="white",
        )

        console.print(controls)
        console.print()

        console.print(
            Rule(
                "[grey62]BANDICUSS WEATHER • NWS ALERTS • v4.0[/]",
                style="grey35",
            )
        )

        console.print()

        input(" Press ENTER to return...")

    # ------------------------------------------------------
    # SEVERITY COLORS
    # ------------------------------------------------------

    def severity_style(severity):
        severity = str(
            severity or "Unknown"
        ).upper()

        styles = {
            "EXTREME": "bold magenta",
            "SEVERE": "bold bright_red",
            "MODERATE": "bold yellow",
            "MINOR": "bold bright_cyan",
        }

        return styles.get(
            severity,
            "bold white",
        )

    # ------------------------------------------------------
    # COORDINATE CHECK
    # ------------------------------------------------------

    if lat is None or lon is None:
        console.print(
            Panel(
                Text(
                    "Station coordinates are unavailable.",
                    style="bold yellow",
                    justify="center",
                ),
                title="[bold yellow]ALERT DATA UNAVAILABLE[/]",
                border_style="yellow",
                padding=(1, 1),
            )
        )

        alerts_footer()
        return

    # ------------------------------------------------------
    # RETRIEVE ALERTS
    # ------------------------------------------------------

    if cached_alerts is None:
        console.print(
            Text(
                " Retrieving active NWS alerts...",
                style="grey62",
            )
        )

        try:
            alerts = fetch_nws_alerts(
                lat,
                lon,
            )

        except Exception as error:
            console.print()

            console.print(
                Panel(
                    Group(
                        Text(
                            "Unable to retrieve NWS alerts.",
                            style="bold bright_red",
                        ),
                        Text(""),
                        Text(
                            str(error),
                            style="white",
                        ),
                    ),
                    title="[bold bright_red]NWS ALERT ERROR[/]",
                    border_style="bright_red",
                    padding=(1, 1),
                )
            )

            alerts_footer()
            return

        console.clear()

        console.print(
            Panel(
                Group(title_text, subtitle),
                border_style=RICH_BORDER,
                padding=(0, 1),
            )
        )

    else:
        alerts = cached_alerts

    # ------------------------------------------------------
    # NO ACTIVE ALERTS
    # ------------------------------------------------------

    if not alerts:
        status_table = Table.grid(expand=True)
        status_table.add_column(ratio=1)
        status_table.add_column(ratio=2)
        status_table.add_column(ratio=1)
        status_table.add_column(ratio=2)

        status_table.add_row(
            Text("STATION", style=RICH_LABEL),
            Text(station, style="bold white"),
            Text("ACTIVE ALERTS", style=RICH_LABEL),
            Text("0", style="bold bright_green"),
        )

        console.print(
            Panel(
                status_table,
                border_style="blue",
                padding=(0, 1),
            )
        )

        console.print(
            Panel(
                Text(
                    "No active NWS watches, warnings, or advisories "
                    "were found for this location.",
                    style="bold bright_green",
                    justify="center",
                ),
                title="[bold bright_green]NO ACTIVE ALERTS[/]",
                border_style="bright_green",
                padding=(1, 1),
            )
        )

        alerts_footer()
        return

    # ------------------------------------------------------
    # ALERT STATUS
    # ------------------------------------------------------

    status_table = Table.grid(expand=True)
    status_table.add_column(ratio=1)
    status_table.add_column(ratio=2)
    status_table.add_column(ratio=1)
    status_table.add_column(ratio=2)

    status_table.add_row(
        Text("STATION", style=RICH_LABEL),
        Text(station, style="bold white"),
        Text("ACTIVE ALERTS", style=RICH_LABEL),
        Text(
            str(len(alerts)),
            style="bold yellow",
        ),
    )

    console.print(
        Panel(
            status_table,
            border_style="blue",
            padding=(0, 1),
        )
    )

    # ------------------------------------------------------
    # ALERT PANELS
    # ------------------------------------------------------

    for number, alert in enumerate(
        alerts,
        start=1,
    ):
        properties = alert.get(
            "properties",
            {},
        )

        event = properties.get(
            "event",
            "Weather Alert",
        )

        severity = properties.get(
            "severity",
            "Unknown",
        )

        urgency = properties.get(
            "urgency",
            "Unknown",
        )

        certainty = properties.get(
            "certainty",
            "Unknown",
        )

        headline = properties.get(
            "headline",
        )

        area = properties.get(
            "areaDesc",
        )

        effective = properties.get(
            "effective",
        )

        expires = properties.get(
            "expires",
        )

        description = properties.get(
            "description",
        )

        instruction = properties.get(
            "instruction",
        )

        alert_style = severity_style(
            severity
        )

        # --------------------------------------------------
        # ALERT SUMMARY
        # --------------------------------------------------

        alert_info = Table.grid(expand=True)
        alert_info.add_column(ratio=1)
        alert_info.add_column(ratio=2)
        alert_info.add_column(ratio=1)
        alert_info.add_column(ratio=2)

        alert_info.add_row(
            Text("SEVERITY", style=RICH_LABEL),
            Text(
                str(severity).upper(),
                style=alert_style,
            ),
            Text("URGENCY", style=RICH_LABEL),
            Text(
                str(urgency).upper(),
                style="white",
            ),
        )

        alert_info.add_row(
            Text("CERTAINTY", style=RICH_LABEL),
            Text(
                str(certainty).upper(),
                style="white",
            ),
            Text("ALERT", style=RICH_LABEL),
            Text(
                f"{number} OF {len(alerts)}",
                style="white",
            ),
        )

        alert_info.add_row(
            Text("EFFECTIVE", style=RICH_LABEL),
            Text(
                friendly_time(effective),
                style="white",
            ),
            Text("EXPIRES", style=RICH_LABEL),
            Text(
                friendly_time(expires),
                style="white",
            ),
        )

        console.print(
            Panel(
                alert_info,
                title=Text(
                    str(event).upper(),
                    style=alert_style,
                ),
                border_style=alert_style,
                padding=(0, 1),
            )
        )

        # --------------------------------------------------
        # AREA / HEADLINE
        # --------------------------------------------------

        overview_items = []

        if area:
            area_text = Text()
            area_text.append(
                "AREA\n",
                style=RICH_LABEL,
            )
            area_text.append(
                str(area),
                style="white",
            )
            overview_items.append(
                area_text
            )

        if headline:
            if overview_items:
                overview_items.append(
                    Text("")
                )

            headline_text = Text()
            headline_text.append(
                "HEADLINE\n",
                style=RICH_LABEL,
            )
            headline_text.append(
                str(headline),
                style="bold white",
            )
            overview_items.append(
                headline_text
            )

        if overview_items:
            console.print(
                Panel(
                    Group(
                        *overview_items
                    ),
                    title="[bold bright_cyan]ALERT OVERVIEW[/]",
                    border_style="blue",
                    padding=(0, 1),
                )
            )

        # --------------------------------------------------
        # DESCRIPTION
        # --------------------------------------------------

        if description:
            console.print(
                Panel(
                    Text(
                        str(description),
                        style="white",
                    ),
                    title="[bold bright_cyan]DESCRIPTION[/]",
                    border_style="blue",
                    padding=(0, 1),
                )
            )

        # --------------------------------------------------
        # INSTRUCTIONS
        # --------------------------------------------------

        if instruction:
            console.print(
                Panel(
                    Text(
                        str(instruction),
                        style="bold white",
                    ),
                    title="[bold yellow]SAFETY / INSTRUCTIONS[/]",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )

    # ------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------

    alerts_footer()


# ==========================================================
# NWS FORECAST
# ==========================================================

def display_nws_forecast(station, wx):
    console.clear()

    title_text = Text(justify="center")
    title_text.append("BANDICUSS", style="bold bright_cyan")
    title_text.append("  NWS FORECAST", style="bold white")

    subtitle = Text(
        f"{station} • NATIONAL WEATHER SERVICE",
        style="grey62",
        justify="center",
    )

    header = Panel(
        Group(title_text, subtitle),
        border_style=RICH_BORDER,
        padding=(0, 1),
    )

    console.print(header)

    lat = wx.get("lat")
    lon = wx.get("lon")

    def forecast_footer():
        console.print()

        controls = Text(justify="center")
        controls.append("[ENTER]", style="bold bright_cyan")
        controls.append(
            " RETURN TO WEATHER CENTER",
            style="white",
        )

        console.print(controls)
        console.print()

        console.print(
            Rule(
                "[grey62]BANDICUSS WEATHER • "
                "NWS FORECAST • v4.0[/]",
                style="grey35",
            )
        )

        console.print()
        input(" Press ENTER to return...")

    if lat is None or lon is None:
        console.print(
            Panel(
                Text(
                    "Station coordinates are unavailable.",
                    style="bold yellow",
                    justify="center",
                ),
                title="[bold yellow]FORECAST DATA UNAVAILABLE[/]",
                border_style="yellow",
                padding=(1, 1),
            )
        )

        forecast_footer()
        return

    console.print(
        Text(
            " Retrieving NWS forecast...",
            style="grey62",
        )
    )

    try:
        forecast = fetch_nws_forecast(
            lat,
            lon,
        )

    except urllib.error.HTTPError as error:
        console.print()

        error_text = Text(justify="center")
        error_text.append(
            "NWS forecast is not available "
            "for this location.\n",
            style="bold yellow",
        )
        error_text.append(
            f"HTTP ERROR: {error.code}",
            style="white",
        )

        console.print(
            Panel(
                error_text,
                title="[bold yellow]FORECAST UNAVAILABLE[/]",
                border_style="yellow",
                padding=(1, 1),
            )
        )

        forecast_footer()
        return

    except Exception as error:
        console.print()

        error_text = Text()
        error_text.append(
            "Unable to retrieve NWS forecast.\n\n",
            style="bold bright_red",
        )
        error_text.append(
            str(error),
            style="white",
        )

        console.print(
            Panel(
                error_text,
                title="[bold bright_red]NWS FORECAST ERROR[/]",
                border_style="bright_red",
                padding=(1, 1),
            )
        )

        forecast_footer()
        return

    if not forecast:
        console.print()

        console.print(
            Panel(
                Text(
                    "Forecast unavailable.",
                    style="bold yellow",
                    justify="center",
                ),
                title="[bold yellow]FORECAST UNAVAILABLE[/]",
                border_style="yellow",
                padding=(1, 1),
            )
        )

        forecast_footer()
        return

    periods = forecast.get(
        "properties",
        {},
    ).get(
        "periods",
        [],
    )

    console.clear()
    console.print(header)

    if not periods:
        console.print(
            Panel(
                Text(
                    "No forecast periods were returned.",
                    style="bold yellow",
                    justify="center",
                ),
                title="[bold yellow]FORECAST UNAVAILABLE[/]",
                border_style="yellow",
                padding=(1, 1),
            )
        )

        forecast_footer()
        return

    status_table = Table.grid(expand=True)
    status_table.add_column(ratio=1)
    status_table.add_column(ratio=2)
    status_table.add_column(ratio=1)
    status_table.add_column(ratio=2)

    status_table.add_row(
        Text("STATION", style=RICH_LABEL),
        Text(station, style="bold white"),
        Text("PERIODS", style=RICH_LABEL),
        Text(
            str(min(len(periods), 8)),
            style="bold bright_cyan",
        ),
    )

    status_table.add_row(
        Text("SOURCE", style=RICH_LABEL),
        Text(
            "NATIONAL WEATHER SERVICE",
            style="white",
        ),
        Text("DISPLAY", style=RICH_LABEL),
        Text(
            "NEXT 8 PERIODS",
            style="white",
        ),
    )

    console.print(
        Panel(
            status_table,
            border_style="blue",
            padding=(0, 1),
        )
    )

    for number, period in enumerate(
        periods[:8],
        start=1,
    ):
        name = period.get(
            "name",
            "Forecast",
        )

        temperature = period.get(
            "temperature",
        )

        unit = period.get(
            "temperatureUnit",
            "F",
        )

        short = period.get(
            "shortForecast",
            "",
        )

        detailed = period.get(
            "detailedForecast",
            "",
        )

        wind_speed = period.get(
            "windSpeed",
            "",
        )

        wind_direction = period.get(
            "windDirection",
            "",
        )

        is_daytime = period.get(
            "isDaytime",
        )

        if is_daytime is True:
            period_style = "bold bright_yellow"
            border_style = "yellow"
            period_type = "DAY"

        elif is_daytime is False:
            period_style = "bold bright_blue"
            border_style = "blue"
            period_type = "NIGHT"

        else:
            period_style = "bold bright_cyan"
            border_style = RICH_BORDER
            period_type = "PERIOD"

        summary_table = Table.grid(expand=True)
        summary_table.add_column(ratio=1)
        summary_table.add_column(ratio=2)
        summary_table.add_column(ratio=1)
        summary_table.add_column(ratio=2)

        if temperature is not None:
            temperature_text = (
                f"{temperature}°{unit}"
            )
        else:
            temperature_text = "N/A"

        if wind_speed:
            wind_text = " ".join(
                part
                for part in (
                    str(wind_direction),
                    str(wind_speed),
                )
                if part
            )
        else:
            wind_text = "N/A"

        summary_table.add_row(
            Text("TEMP", style=RICH_LABEL),
            Text(
                temperature_text,
                style="bold white",
            ),
            Text("WIND", style=RICH_LABEL),
            Text(
                wind_text,
                style="white",
            ),
        )

        summary_table.add_row(
            Text("PERIOD", style=RICH_LABEL),
            Text(
                f"{number} OF "
                f"{min(len(periods), 8)}",
                style="white",
            ),
            Text("TYPE", style=RICH_LABEL),
            Text(
                period_type,
                style=period_style,
            ),
        )

        period_items = [summary_table]

        if short:
            period_items.append(Text(""))

            short_text = Text()
            short_text.append(
                "SUMMARY\n",
                style=RICH_LABEL,
            )
            short_text.append(
                str(short),
                style="bold white",
            )

            period_items.append(short_text)

        if detailed:
            period_items.append(Text(""))

            detail_text = Text()
            detail_text.append(
                "DETAILS\n",
                style=RICH_LABEL,
            )
            detail_text.append(
                str(detailed),
                style="white",
            )

            period_items.append(detail_text)

        console.print(
            Panel(
                Group(*period_items),
                title=Text(
                    str(name).upper(),
                    style=period_style,
                ),
                border_style=border_style,
                padding=(0, 1),
            )
        )

    forecast_footer()


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
        console.clear()

        title_text = Text(justify="center")
        title_text.append(
            "BANDICUSS",
            style="bold bright_cyan",
        )
        title_text.append(
            "  GRAPHICAL WEATHER",
            style="bold white",
        )

        subtitle = Text(
            "RADAR • SATELLITE • CONVECTIVE • "
            "FORECAST • TROPICAL",
            style="grey62",
            justify="center",
        )

        console.print(
            Panel(
                Group(title_text, subtitle),
                border_style=RICH_BORDER,
                padding=(0, 1),
            )
        )

        info = Text(justify="center")
        info.append(
            "Select a product below to open it in Chromium.",
            style="grey70",
        )

        console.print(
            Panel(
                info,
                border_style="blue",
                padding=(0, 1),
            )
        )

        products = Table.grid(expand=True)

        products.add_column(
            width=6,
            justify="center",
        )
        products.add_column(ratio=1)

        products.add_row(
            Text("[1]", style="bold bright_cyan"),
            Group(
                Text(
                    "NWS RADAR",
                    style="bold white",
                ),
                Text(
                    "National radar imagery and "
                    "precipitation monitoring",
                    style="grey62",
                ),
            ),
        )

        products.add_row(
            Text(""),
            Text(""),
        )

        products.add_row(
            Text("[2]", style="bold bright_cyan"),
            Group(
                Text(
                    "GOES SATELLITE",
                    style="bold white",
                ),
                Text(
                    "Geostationary satellite imagery "
                    "and atmospheric monitoring",
                    style="grey62",
                ),
            ),
        )

        products.add_row(
            Text(""),
            Text(""),
        )

        products.add_row(
            Text("[3]", style="bold bright_cyan"),
            Group(
                Text(
                    "SPC CONVECTIVE OUTLOOKS",
                    style="bold white",
                ),
                Text(
                    "Severe thunderstorm and "
                    "convective outlook products",
                    style="grey62",
                ),
            ),
        )

        products.add_row(
            Text(""),
            Text(""),
        )

        products.add_row(
            Text("[4]", style="bold bright_cyan"),
            Group(
                Text(
                    "WPC FORECAST PRODUCTS",
                    style="bold white",
                ),
                Text(
                    "National forecast, precipitation, "
                    "and analysis products",
                    style="grey62",
                ),
            ),
        )

        products.add_row(
            Text(""),
            Text(""),
        )

        products.add_row(
            Text("[5]", style="bold bright_cyan"),
            Group(
                Text(
                    "NHC / TROPICAL WEATHER",
                    style="bold white",
                ),
                Text(
                    "Tropical cyclone and hurricane "
                    "forecast products",
                    style="grey62",
                ),
            ),
        )

        console.print(
            Panel(
                products,
                title="[bold bright_cyan]"
                "GRAPHICAL PRODUCTS[/]",
                border_style=RICH_BORDER,
                padding=(1, 1),
            )
        )

        controls = Text(justify="center")
        controls.append(
            "[1-5]",
            style="bold bright_cyan",
        )
        controls.append(
            " OPEN PRODUCT     ",
            style="white",
        )
        controls.append(
            "[Q]",
            style="bold bright_cyan",
        )
        controls.append(
            " BACK TO WEATHER CENTER",
            style="white",
        )

        console.print(controls)
        console.print()

        console.print(
            Rule(
                "[grey62]BANDICUSS WEATHER • "
                "GRAPHICAL WEATHER • v4.0[/]",
                style="grey35",
            )
        )

        console.print()

        choice = input(
            " SELECT PRODUCT: "
        ).strip().lower()

        if choice == "1":
            launch_browser(
                NWS_RADAR_URL,
                "NWS RADAR",
            )
            pause()

        elif choice == "2":
            launch_browser(
                GOES_URL,
                "GOES SATELLITE",
            )
            pause()

        elif choice == "3":
            launch_browser(
                SPC_URL,
                "SPC CONVECTIVE OUTLOOKS",
            )
            pause()

        elif choice == "4":
            launch_browser(
                WPC_URL,
                "WPC FORECAST PRODUCTS",
            )
            pause()

        elif choice == "5":
            launch_browser(
                NHC_URL,
                "NHC / TROPICAL WEATHER",
            )
            pause()

        elif choice == "q":
            return

        else:
            console.print()
            console.print(
                Text(
                    " Invalid selection.",
                    style="bold yellow",
                )
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

        elif choice == "2":
            display_metar(station, metar)

        elif choice == "3":
            display_taf(station, taf)

        elif choice == "4":
            display_alerts(station, metar, alerts)

        elif choice == "5":
            display_nws_forecast(station, metar)

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

def startup_animation():
    """Short animated Bandicuss Weather boot screen."""

    cloud = [
        "      .--.      ",
        "   .-(    ).    ",
        "  (___.__)__)   ",
    ]

    scene_width = 78

    # Four clouds with slightly different movement.
    # Each tuple contains the horizontal position
    # for one cloud during that frame.
    frames = [
        (3, 47, 20, 61),
        (5, 45, 22, 59),
        (7, 43, 24, 57),
        (9, 41, 26, 55),
        (11, 39, 28, 53),
        (13, 37, 30, 51),
        (15, 35, 32, 49),
    ]

    def make_cloud_row(positions, styles):
        lines = []

        for cloud_row in range(len(cloud)):
            canvas = [" "] * scene_width

            for position, style_number in zip(
                positions,
                styles,
            ):
                cloud_part = cloud[cloud_row]

                for index, character in enumerate(
                    cloud_part
                ):
                    target = position + index

                    if (
                        0 <= target < scene_width
                        and character != " "
                    ):
                        canvas[target] = (
                            character,
                            style_number,
                        )

            rendered = Text()

            for item in canvas:
                if isinstance(item, tuple):
                    character, style_number = item

                    if style_number == 1:
                        style = "bold bright_cyan"
                    else:
                        style = "bold white"

                    rendered.append(
                        character,
                        style=style,
                    )

                else:
                    rendered.append(item)

            lines.append(rendered)

        return lines

    for cloud_one, cloud_two, cloud_three, cloud_four in frames:
        console.clear()

        console.print()

        # Upper cloud level
        upper_lines = make_cloud_row(
            (
                cloud_one,
                cloud_two,
            ),
            (
                1,
                2,
            ),
        )

        for cloud_line in upper_lines:
            console.print(
                cloud_line,
                justify="center",
            )

        # Space between cloud levels
        console.print()

        # Lower cloud level
        lower_lines = make_cloud_row(
            (
                cloud_three,
                cloud_four,
            ),
            (
                2,
                1,
            ),
        )

        for cloud_line in lower_lines:
            console.print(
                cloud_line,
                justify="center",
            )

        console.print()

        boot_title = Text()

        title_text = "BANDICUSS  WEATHER CENTER"
        title_padding = max(
            0,
            (scene_width - len(title_text)) // 2,
        )

        boot_title.append(
            " " * title_padding,
        )
        boot_title.append(
            "BANDICUSS",
            style="bold bright_cyan",
        )
        boot_title.append(
            "  WEATHER CENTER",
            style="bold white",
        )

        console.print(
            boot_title,
            justify="center",
        )

        system_text = "FIELD WEATHER SYSTEM"
        system_padding = max(
            0,
            (scene_width - len(system_text)) // 2,
        )

        system_line = Text()
        system_line.append(
            " " * system_padding,
        )
        system_line.append(
            system_text,
            style="grey62",
        )

        console.print(
            system_line,
            justify="center",
        )

        version_text = "v4.0"
        version_padding = max(
            0,
            (scene_width - len(version_text)) // 2,
        )

        version_line = Text()
        version_line.append(
            " " * version_padding,
        )
        version_line.append(
            version_text,
            style="bold bright_cyan",
        )

        console.print(
            version_line,
            justify="center",
        )

        time.sleep(0.20)

    time.sleep(0.45)


def draw_startup_screen(station):
    """Draw the v4 station-selection screen."""

    console.clear()

    title_text = Text(justify="center")
    title_text.append(
        "BANDICUSS",
        style="bold bright_cyan",
    )
    title_text.append(
        "  WEATHER CENTER",
        style="bold white",
    )

    subtitle = Text(
        "AVIATION • FORECAST • ALERTS • GRAPHICAL WEATHER",
        style="grey62",
        justify="center",
    )

    console.print(
        Panel(
            Group(
                title_text,
                subtitle,
            ),
            border_style=RICH_BORDER,
            padding=(0, 1),
        )
    )

    system_table = Table.grid(expand=True)
    system_table.add_column(ratio=1)
    system_table.add_column(ratio=2)
    system_table.add_column(ratio=1)
    system_table.add_column(ratio=2)

    system_table.add_row(
        Text(
            "SYSTEM",
            style=RICH_LABEL,
        ),
        Text(
            "FIELD WEATHER",
            style="bold white",
        ),
        Text(
            "VERSION",
            style=RICH_LABEL,
        ),
        Text(
            "v4.0",
            style="bold bright_cyan",
        ),
    )

    system_table.add_row(
        Text(
            "DEFAULT",
            style=RICH_LABEL,
        ),
        Text(
            DEFAULT_STATION,
            style="bold white",
        ),
        Text(
            "STATUS",
            style=RICH_LABEL,
        ),
        Text(
            "READY",
            style="bold bright_green",
        ),
    )

    console.print(
        Panel(
            system_table,
            border_style="blue",
            padding=(0, 1),
        )
    )

    station_info = Group(
        Text(
            "SELECT AVIATION WEATHER STATION",
            style="bold white",
            justify="center",
        ),
        Text(""),
        Text(
            "Enter a four-letter ICAO airport identifier.",
            style="white",
            justify="center",
        ),
        Text(
            "Press ENTER to use the default station.",
            style="grey62",
            justify="center",
        ),
        Text(""),
        Text(
            "KDCA    KADW    KBWI    KJFK    EGLL",
            style="bold bright_cyan",
            justify="center",
        ),
    )

    console.print(
        Panel(
            station_info,
            title="[bold bright_cyan]STATION SELECTION[/]",
            border_style=RICH_BORDER,
            padding=(1, 1),
        )
    )

    controls = Text(justify="center")
    controls.append(
        "[ENTER]",
        style="bold bright_cyan",
    )
    controls.append(
        f" USE {station}",
        style="white",
    )
    controls.append(
        "     ",
    )
    controls.append(
        "[ICAO]",
        style="bold bright_cyan",
    )
    controls.append(
        " CHANGE STATION",
        style="white",
    )

    console.print(controls)
    console.print()

    console.print(
        Rule(
            "[grey62]BANDICUSS WEATHER • v4.0[/]",
            style="grey35",
        )
    )

    console.print()


def main():
    station = DEFAULT_STATION

    startup_animation()

    draw_startup_screen(
        station
    )

    selected = input(
        f" ICAO STATION [{station}]: "
    ).strip().upper()

    if selected:
        station = selected

    weather_menu(
        station
    )

    console.clear()


if __name__ == "__main__":
    main()
