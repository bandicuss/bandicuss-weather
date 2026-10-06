"""Approved Horizon Observatory artwork adapted only for real acquisition state.

Based on the uConsole-approved prototype; standalone references are kept locally.
This module draws frames; it performs no network requests or terminal lifecycle work.
Pixel primitives are MIT licensed; see LICENSE-intros.
"""
from functools import lru_cache
import math
import bandicuss_intro as pixel
from bandicuss_intro_layout import position, resample

CYAN = (121, 206, 210)

WHITE = (229, 248, 239)

GREY = (146, 172, 190)

MINT = (104, 199, 166)

AMBER = (255, 174, 105)

def text_at(x, y, text, color=GREY):
    return position(x, y) + '\x1b[38;2;%d;%d;%dm' % color + text + '\x1b[0m'

def centered(text, y, columns, color=GREY):
    return text_at((columns - len(text)) // 2, y, text, color)

def render_pixels(data, x, y, width, rows):
    art = resample(data, pixel.WIDTH, pixel.HEIGHT, width, rows * 2)
    chunks = []
    for yy in range(rows):
        chunks.append(position(x, y + yy))
        previous = None
        for xx in range(width):
            pair = (art[(yy * 2) * width + xx], art[(yy * 2 + 1) * width + xx])
            if pair != previous:
                a, b = (pixel.PALETTE[index] for index in pair)
                chunks.append('\x1b[38;2;%d;%d;%d;48;2;%d;%d;%dm' % (*a, *b))
                previous = pair
            chunks.append('▀')
        chunks.append('\x1b[0m')
    return ''.join(chunks)

@lru_cache(maxsize=480)
def sky_color(y, blend):
    day = pixel.PALETTE[pixel.SKIES[0][min(15, y * 16 // 29)]]
    night = pixel.PALETTE[pixel.SKIES[3][min(15, y * 16 // 29)]]
    rgb = tuple(a + (b - a) * blend / 11 for a, b in zip(day, night))
    return min(range(len(pixel.PALETTE)),
               key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, pixel.PALETTE[i])))

def landscape(seconds, status, receiver=None):
    """Original acquisition composition using the intro's drawing primitives."""
    c = pixel.Canvas(0)
    # Cool skies settle gradually into aurora tones, without sudden scene cuts.
    night = max(0, min(1, (seconds - 6) / 5))
    for y in range(pixel.HEIGHT):
        index = sky_color(y, round(night * 11))
        c.pixels[y * pixel.WIDTH:(y + 1) * pixel.WIDTH] = bytes([index]) * pixel.WIDTH
    c.ellipse(59, 12, 5, 5, pixel.DAWN[0])
    for origin, level, scale in [(9, 7, .75), (42, 5, .55), (69, 10, .6)]:
        x = (origin + seconds * 1.1 + 12) % 102 - 12
        c.cloud(x, level, scale, pixel.DAWN[2], pixel.DAWN[3])
    if night:
        for x in range(78):
            yy = 5 + math.sin(x * .12 + seconds * .6) * 2
            c.dot(x, yy, pixel.NIGHT[1])
            c.dot(x, yy + 1, pixel.NIGHT[2])
    if status[1] == 'ACQUIRING':
        for i in range(22):
            x = (i * 19 - seconds * 9) % 78
            y = (i * 7 + seconds * 12) % 22
            c.dot(x, y, pixel.STORM[3])
    c.ridge([(0, 25), (12, 16), (24, 23), (36, 12), (49, 25), (64, 17), (78, 24)], pixel.DAWN[4])
    c.ridge([(0, 29), (17, 23), (31, 28), (46, 22), (60, 28), (78, 23)], pixel.DAWN[5])
    c.rect(0, 30, 78, 10, pixel.DAWN[6])
    for y in range(31, 40):
        for x in range(43, 72):
            if (x + y * 3 + int(seconds * 5)) % 11 < 3:
                c.dot(x + math.sin(seconds + y) * 2, y, pixel.DAWN[8 + y % 2])
    for x, y in [(3, 25), (9, 27), (74, 24)]:
        c.tree(x, y, 2, pixel.INK)
    if receiver is not None:
        receiver(c, seconds, status)
    else:
        # Field receiver and restrained outgoing pulse: decorative, not measured RF.
        c.rect(19, 25, 1, 9, pixel.NIGHT[7])
        c.rect(16, 33, 7, 2, pixel.INK)
        c.rect(16, 25, 7, 1, pixel.NIGHT[7])
        led = pixel.NIGHT[2] if status[0] == 'ACQUIRED' else pixel.DAWN[0]
        c.dot(19, 24, led)
        radius = 2 + (seconds * 3) % 10
        for angle in range(205, 336, 8):
            a = math.radians(angle)
            c.dot(19 + math.cos(a) * radius, 24 + math.sin(a) * radius, pixel.NIGHT[1])
    return bytes(c.pixels)

def layout(columns, rows):
    height = min(rows, 31)
    return (columns - 93) // 2, (rows - height) // 2, height

PRODUCTS = ('METAR', 'TAF', 'NWS ALERTS')

STYLES = {
    'PENDING': ('[WAIT]', GREY),
    'ACQUIRING': ('[>>>]', CYAN),
    'CHECKING': ('[>>>]', CYAN),
    'ACQUIRED': ('[OK]', MINT),
    'CHECKED': ('[OK]', MINT),
    'UNAVAILABLE': ('[--]', AMBER),
    'FAILED': ('[!!]', (239, 132, 123)),
    'SKIPPED': ('[--]', GREY),
}

def radar_dish(canvas, seconds, status):
    """Small parabolic receiver; decorative radio pulse, not live radar data."""
    # Gentle elevation scan, one back-and-forth cycle every twelve seconds.
    angle = -.55 + .13 * math.sin(seconds * math.tau / 12)
    cosine, sine = math.cos(angle), math.sin(angle)
    cx, cy = 19, 26

    def point(axial, transverse):
        return (cx + axial * cosine - transverse * sine,
                cy + axial * sine + transverse * cosine)

    # Low pedestal and dark base remain in the old receiver's footprint.
    canvas.rect(18, 29, 2, 5, pixel.NIGHT[7])
    canvas.rect(16, 33, 7, 2, pixel.INK)
    # A bright curved rim, with a darker backing to retain its silhouette.
    for i in range(-20, 21):
        transverse = i / 4
        axial = .14 * transverse * transverse - 2
        x, y = point(axial, transverse)
        canvas.dot(x - 1, y, pixel.INK)
        canvas.dot(x, y, pixel.NIGHT[7])
    # Feed arm projects into the open side of the bowl.
    for i in range(13):
        x, y = point(-2 + i * .5, 0)
        canvas.dot(x, y, pixel.NIGHT[7])
    x, y = point(4, 0)
    canvas.dot(x, y, pixel.NIGHT[2] if status[0] == 'ACQUIRED' else pixel.DAWN[0])
    # A narrow outward arc every four seconds, followed by a quiet interval.
    phase = seconds % 4
    if phase < 2.6:
        radius = 7 + phase * 3.2
        color = pixel.NIGHT[1] if phase < 1.8 else pixel.NIGHT[0]
        for i in range(-5, 6):
            direction = angle + i * .045
            canvas.dot(cx + math.cos(direction) * radius,
                       cy + math.sin(direction) * radius, color)

def frame(seconds, state, station, columns=97, rows=23):
    # Display arbitrary station input safely without changing the request value.
    station = ''.join(c if c.isascii() and c.isprintable() else '?'
                      for c in station)[:16]
    left, top, height = layout(columns, rows)
    chunks = [position(0, y) + '\x1b[0m\x1b[2K' for y in range(rows)]
    chunks.append(centered('BANDICUSS WEATHER CENTER', top, columns, WHITE))
    chunks.append(centered('STATION  ' + station + '  /  HORIZON OBSERVATORY', top + 1, columns, CYAN))
    chunks.append(centered('LIVE ACQUISITION / AVIATION WEATHER + NWS',
                           top + 2, columns, AMBER))
    active = next(((name, status) for name, status in zip(PRODUCTS, state)
                   if status in ('ACQUIRING', 'CHECKING')), None)
    if active:
        operation = '>>> NOW: ' + active[1] + ' ' + active[0] + ' <<<'
        color = CYAN
    elif 'FAILED' in state:
        operation = 'ACQUISITION FINISHED / SEE PRODUCT STATES BELOW'
        color = STYLES['FAILED'][1]
    elif all(status == 'PENDING' for status in state):
        operation = 'ACQUISITION READY / WAITING FOR METAR'
        color = MINT
    elif 'PENDING' in state:
        operation = 'STAGE COMPLETE / NEXT PRODUCT PENDING'
        color = MINT
    else:
        operation = 'ACQUISITION FINISHED / SEE PRODUCT STATES BELOW'
        color = MINT
    chunks.append(centered(operation, top + 3, columns, color))
    # Full landscape occupies 93x13 at 97x23; status strip remains separate.
    chunks.append(render_pixels(
        landscape(seconds, state, receiver=radar_dish),
        left, top + 4, 93, height - 10))
    for i, (name, status) in enumerate(zip(PRODUCTS, state)):
        x = left + i * 31
        marker, color = STYLES[status]
        label = ('>>> ' if status in ('ACQUIRING', 'CHECKING') else '    ') + name
        chunks.append(text_at(x + 3, top + height - 5, label, color))
        chunks.append(text_at(x + 3, top + height - 4, marker + ' ' + status, color))
    chunks.append(centered('BANDICUSS WEATHER / LIVE ACQUISITION / CTRL-C TO EXIT',
                                top + height - 2, columns))
    return ''.join(chunks)
