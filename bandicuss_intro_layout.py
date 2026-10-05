# Adapted from theNeighborrr/bandicuss-weather-intros, revision c1640f3.
# Copyright (c) 2026 theNeighborrr. MIT license; see LICENSE-intros.
"""Proportional terminal layout shared by both intros. No terminal font changes."""
import math


def fit_canvas(columns, rows, width, height, captions=2, pixel=False):
    """Return (left, top, artwork width, artwork height) in cells/pixels.

    Pixel artwork uses two vertical pixels per terminal row. Keep captions at
    the user's font size and reserve a blank border where the window permits.
    """
    available_width = max(1, columns - (2 if columns >= 81 else 1))
    available_rows = max(1, rows - (2 if rows >= 26 else 0) - captions)
    vertical = 2 if pixel else 1
    scale = min(available_width / width, available_rows * vertical / height)
    target_width = max(1, min(available_width, math.floor(width * scale + 1e-9)))
    target_height = max(vertical, math.floor(height * scale / vertical + 1e-9) * vertical)
    used_rows = target_height // vertical + captions
    return ((columns - target_width) // 2, (rows - used_rows) // 2,
            target_width, target_height)


def resample(data, source_width, source_height, width, height, stride=1):
    """Nearest-neighbor sampling preserves the palette and ASCII character set."""
    xs = [min(source_width - 1, x * source_width // width) for x in range(width)]
    output = bytearray()
    for y in range(height):
        row = min(source_height - 1, y * source_height // height) * source_width
        for x in xs:
            start = (row + x) * stride
            output.extend(data[start:start + stride])
    return bytes(output)


def position(left, top):
    return "\x1b[%d;%dH" % (top + 1, left + 1)


def caption(text, columns, row, color=(146, 172, 190)):
    return (position(max(0, (columns - len(text)) // 2), row)
            + "\x1b[0m\x1b[38;2;%d;%d;%dm" % color
            + text + "\x1b[0m\x1b[K")
