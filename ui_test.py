from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.rule import Rule

console = Console()

# --------------------------------------------------
# DEMO DATA
# These values are only for the UI prototype.
# --------------------------------------------------

station = "KDCA"
station_name = "WASHINGTON / REAGAN NATIONAL"
category = "VFR"
alerts = 1

temperature = "72°F"
dewpoint = "61°F"
wind = "180° / 08 KT"
visibility = "10+ SM"
ceiling = "CLR"
altimeter = "30.12"


# --------------------------------------------------
# COLORS
# --------------------------------------------------

BORDER = "bright_cyan"
LABEL = "grey62"
VALUE = "white"
ACCENT = "bright_cyan"


def flight_category(value):
    """Return a colored flight-category label."""

    colors = {
        "VFR": "bold bright_green",
        "MVFR": "bold bright_blue",
        "IFR": "bold bright_red",
        "LIFR": "bold magenta",
    }

    return Text(value, style=colors.get(value, "bold white"))


def build_header():

    title = Text(justify="center")
    title.append("BANDICUSS", style="bold bright_cyan")
    title.append("  WEATHER CENTER", style="bold white")

    subtitle = Text(
        "AVIATION • FORECAST • ALERTS • GRAPHICAL WEATHER",
        style="grey62",
        justify="center",
    )

    return Panel(
        Group(title, subtitle),
        border_style=BORDER,
        padding=(0, 1),
    )


def build_station_bar():

    table = Table.grid(expand=True)

    table.add_column(ratio=1)
    table.add_column(ratio=2)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    table.add_row(
        Text("STATION", style=LABEL),
        Text(station, style="bold white"),
        Text("FLIGHT CAT", style=LABEL),
        flight_category(category),
    )

    table.add_row(
        Text("LOCATION", style=LABEL),
        Text(station_name, style="white"),
        Text("NWS ALERTS", style=LABEL),
        Text(
            f"{alerts} ACTIVE",
            style="bold yellow" if alerts else "bold green",
        ),
    )

    return Panel(
        table,
        border_style="blue",
        padding=(0, 1),
    )


def build_conditions():

    table = Table.grid(expand=True)

    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    table.add_row(
        Text("TEMP", style=LABEL),
        Text(temperature, style=VALUE),
        Text("DEWPOINT", style=LABEL),
        Text(dewpoint, style=VALUE),
    )

    table.add_row(
        Text("WIND", style=LABEL),
        Text(wind, style=VALUE),
        Text("VISIBILITY", style=LABEL),
        Text(visibility, style=VALUE),
    )

    table.add_row(
        Text("CEILING", style=LABEL),
        Text(ceiling, style=VALUE),
        Text("ALTIMETER", style=LABEL),
        Text(altimeter, style=VALUE),
    )

    return Panel(
        table,
        title="[bold bright_cyan]CURRENT CONDITIONS[/]",
        border_style=BORDER,
        padding=(0, 1),
    )


def build_menu():

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
        border_style=BORDER,
        padding=(1, 1),
    )


def build_controls():

    controls = Text(justify="center")

    controls.append("[R]", style="bold bright_cyan")
    controls.append(" REFRESH     ", style="white")

    controls.append("[S]", style="bold bright_cyan")
    controls.append(" CHANGE STATION     ", style="white")

    controls.append("[Q]", style="bold bright_cyan")
    controls.append(" EXIT", style="white")

    return controls


# --------------------------------------------------
# DRAW INTERFACE
# --------------------------------------------------

console.clear()

console.print(build_header())
console.print(build_station_bar())
console.print(build_conditions())
console.print(build_menu())

console.print(build_controls())
console.print()

console.print(
    Rule(
        "[grey62]BANDICUSS WEATHER • v4 DEVELOPMENT[/]",
        style="grey35",
    )
)

console.print()

input(" SELECT OPTION: ")
