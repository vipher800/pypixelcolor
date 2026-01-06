# -*- coding: utf-8 -*-
"""Scoreboard commands for team names and score.

This module provides two commands:

* ``set_scoreboard_teams``: draws two team names (left and right) vertically
    on the edges of the matrix using a fixed 3x5 bitmap font, with one blank
    row between characters.
* ``set_scoreboard_score``: draws the same team names on the sides and a
    large score ``"00:00"`` (16 pixels high) in the center of the matrix.

Both commands send the result as a static image using the same transport as
``send_image``.

- Each team name: up to 4 characters (A–Z, 0–9).
- Side font: 3 columns × 5 rows per character, vertical.
- Score font: 16 rows, wide digits in the center area only.
"""

from __future__ import annotations

from io import BytesIO
from logging import getLogger
from typing import Dict, List, Optional, Tuple

from PIL import Image

from ..lib.device_info import DeviceInfo
from .send_image import _build_send_plan

logger = getLogger(__name__)

_SCORE_CHAR_HEIGHT = 16
_SCORE_DIGIT_WIDTH = 8
_SCORE_COLON_WIDTH = 4


# 3x5 bitmap font: characters A–Z, 0–9
# Each glyph is a list of 5 strings of length 3, with '1' = LED on, '0' = off.
GLYPH_3X5: Dict[str, List[str]] = {
    # Digits
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
    # Uppercase letters
    "A": ["010", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["011", "100", "100", "100", "011"],
    "D": ["110", "101", "101", "101", "110"],
    "E": ["111", "100", "110", "100", "111"],
    "F": ["111", "100", "110", "100", "100"],
    "G": ["011", "100", "101", "101", "011"],
    "H": ["101", "101", "111", "101", "101"],
    "I": ["111", "010", "010", "010", "111"],
    "J": ["111", "001", "001", "101", "111"],
    "K": ["101", "110", "100", "110", "101"],
    "L": ["100", "100", "100", "100", "111"],
    "M": ["101", "111", "101", "101", "101"],
    "N": ["101", "111", "111", "111", "101"],
    "O": ["111", "101", "101", "101", "111"],
    "P": ["111", "101", "111", "100", "100"],
    "Q": ["111", "101", "101", "111", "011"],
    "R": ["111", "101", "111", "110", "101"],
    "S": ["111", "100", "111", "001", "111"],
    "T": ["111", "010", "010", "010", "010"],
    "U": ["101", "101", "101", "101", "111"],
    "V": ["101", "101", "101", "101", "010"],
    "W": ["101", "101", "111", "111", "101"],
    "X": ["101", "101", "010", "101", "101"],
    "Y": ["101", "101", "010", "010", "010"],
    "Z": ["111", "001", "010", "100", "111"],
}


# 16-pixel high font for score digits and colon.
# Each glyph is a list of 16 strings. Digits are 8 pixels wide,
# the colon is 4 pixels wide.
GLYPH_SCORE: Dict[str, List[str]] = {
    "0": [
        "00111100",
        "01100110",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "01100110",
        "00111100",
    ],
    "1": [
        "00011000",
        "00111000",
        "01111000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "00011000",
        "01111110",
        "01111110",
    ],
    "2": [
        "00111100",
        "01100110",
        "11000011",
        "00000011",
        "00000011",
        "00000110",
        "00001100",
        "00011000",
        "00110000",
        "01100000",
        "11000000",
        "11000000",
        "11000000",
        "11000000",
        "11111111",
        "11111111",
    ],
    "3": [
        "00111100",
        "01100110",
        "11000011",
        "00000011",
        "00000011",
        "00000110",
        "00011100",
        "00011100",
        "00000110",
        "00000011",
        "00000011",
        "00000011",
        "11000011",
        "01100110",
        "00111100",
        "00000000",
    ],
    "4": [
        "00000110",
        "00001110",
        "00011110",
        "00110110",
        "01100110",
        "11000110",
        "11000110",
        "11000110",
        "11111111",
        "11111111",
        "00000110",
        "00000110",
        "00000110",
        "00000110",
        "00000110",
        "00000000",
    ],
    "5": [
        "11111111",
        "11111111",
        "11000000",
        "11000000",
        "11000000",
        "11111100",
        "11111110",
        "00000111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "11000011",
        "01100110",
        "00111100",
        "00000000",
    ],
    "6": [
        "00111100",
        "01100110",
        "11000011",
        "11000000",
        "11000000",
        "11111100",
        "11111110",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "01100110",
        "00111100",
        "00000000",
    ],
    "7": [
        "11111111",
        "11111111",
        "00000011",
        "00000110",
        "00001100",
        "00011000",
        "00011000",
        "00110000",
        "00110000",
        "01100000",
        "01100000",
        "11000000",
        "11000000",
        "11000000",
        "11000000",
        "00000000",
    ],
    "8": [
        "00111100",
        "01100110",
        "11000011",
        "11000011",
        "11000011",
        "01100110",
        "00111100",
        "00111100",
        "01100110",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "01100110",
        "00111100",
        "00000000",
    ],
    "9": [
        "00111100",
        "01100110",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "01111111",
        "00111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "11000011",
        "01100110",
        "00111100",
        "00000000",
    ],
    ":": [
        "0000",
        "0000",
        "0110",
        "0110",
        "0110",
        "0110",
        "0000",
        "0000",
        "0000",
        "0000",
        "0110",
        "0110",
        "0110",
        "0110",
        "0000",
        "0000",
    ],
}


def _parse_color_hex(color: str) -> Tuple[int, int, int]:
    """Parse a 6-char hex color into an (R, G, B) tuple."""
    if not isinstance(color, str) or len(color) != 6 or not all(c in "0123456789abcdefABCDEF" for c in color):
        raise ValueError("Color must be a 6-character hexadecimal string, e.g. 'FF0000'.")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _compute_vertical_start(num_chars: int, matrix_height: int, char_height: int = 5, spacing: int = 1) -> int:
    """Compute the starting Y coordinate to vertically center num_chars characters."""
    if num_chars <= 0:
        return 0
    total_height = num_chars * char_height + (num_chars - 1) * spacing
    if total_height > matrix_height:
        # Not enough vertical space: draw from top and let it clip
        logger.warning(
            "Not enough vertical space for %d chars (needs %d, has %d)",
            num_chars,
            total_height,
            matrix_height,
        )
        return 0
    return (matrix_height - total_height) // 2


def _draw_glyph_3x5(
    img: Image.Image,
    glyph: List[str],
    x_offset: int,
    y_offset: int,
    color: Tuple[int, int, int],
) -> None:
    """Draw a single 3x5 glyph at (x_offset, y_offset)."""
    width, height = img.size
    r, g, b = color

    for row_idx, row in enumerate(glyph):
        y = y_offset + row_idx
        if y < 0 or y >= height:
            continue
        for col_idx, ch in enumerate(row):
            if ch != "1":
                continue
            x = x_offset + col_idx
            if 0 <= x < width:
                img.putpixel((x, y), (r, g, b))


def _draw_score_glyph(
    img: Image.Image,
    glyph: List[str],
    x_offset: int,
    y_offset: int,
    color: Tuple[int, int, int],
) -> None:
    """Draw a score glyph (16 rows) at (x_offset, y_offset)."""
    width, height = img.size
    r, g, b = color

    for row_idx, row in enumerate(glyph):
        y = y_offset + row_idx
        if y < 0 or y >= height:
            continue
        for col_idx, ch in enumerate(row):
            if ch != "1":
                continue
            x = x_offset + col_idx
            if 0 <= x < width:
                img.putpixel((x, y), (r, g, b))


def set_scoreboard_teams(
    team_left: str,
    team_right: str,
    color: str = "FFFFFF",
    device_info: Optional[DeviceInfo] = None,
):
    """Render two vertical team names on the left and right edges of the matrix.

    - Each name is drawn with a 3x5 font, one pixel of vertical spacing
      between characters.
    - Names are centered vertically when possible.
    - Only characters A–Z and 0–9 are supported; others are ignored.

    Args:
        team_left: Name of the left team (max 4 characters).
        team_right: Name of the right team (max 4 characters).
        color: Hex color for the text, e.g. "FF0000".
        device_info: Injected automatically; provides matrix width/height.
    """
    if device_info is None:
        raise ValueError("device_info is required for set_scoreboard_teams")

    width = int(device_info.width)
    height = int(device_info.height)

    if width < 6:
        raise ValueError("Matrix width must be at least 6 pixels (3 per side)")

    # Normalize and clamp team names
    team_left = (team_left or "").upper()[:4]
    team_right = (team_right or "").upper()[:4]

    # Filter unsupported characters (keep only those present in GLYPH_3X5)
    filtered_left = "".join(ch for ch in team_left if ch in GLYPH_3X5)
    filtered_right = "".join(ch for ch in team_right if ch in GLYPH_3X5)

    if not filtered_left:
        logger.warning("Left team name '%s' has no supported characters (A-Z, 0-9)", team_left)
    if not filtered_right:
        logger.warning("Right team name '%s' has no supported characters (A-Z, 0-9)", team_right)

    team_left = filtered_left
    team_right = filtered_right

    num_left = len(team_left)
    num_right = len(team_right)

    # Compute vertical start for each side
    spacing = 1
    char_h = 5
    y_start_left = _compute_vertical_start(num_left, height, char_h, spacing)
    y_start_right = _compute_vertical_start(num_right, height, char_h, spacing)

    text_color = _parse_color_hex(color)

    # Render base scoreboard (names only, no score)
    img = Image.new("RGB", (width, height), (0, 0, 0))

    # Left side: columns 0..2
    x_left = 0
    for idx, ch in enumerate(team_left):
        glyph = GLYPH_3X5.get(ch)
        if glyph is None:
            continue
        y_offset = y_start_left + idx * (char_h + spacing)
        _draw_glyph_3x5(img, glyph, x_left, y_offset, text_color)

    # Right side: last 3 columns
    x_right = width - 3
    for idx, ch in enumerate(team_right):
        glyph = GLYPH_3X5.get(ch)
        if glyph is None:
            continue
        y_offset = y_start_right + idx * (char_h + spacing)
        _draw_glyph_3x5(img, glyph, x_right, y_offset, text_color)

    # Convert image to PNG bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    # Reuse image send pipeline; static image = not a GIF
    return _build_send_plan(png_bytes, is_gif=False, plan_name="set_scoreboard_teams", save_slot=0)


def _parse_score(score: str) -> Tuple[str, str]:
    """Parse a score string like '00:00' or '00 : 00' into (left, right)."""
    if not isinstance(score, str):
        raise ValueError("score must be a string like '00:00'")

    s = score.strip().replace(" ", "")
    if ":" in s:
        left, right = s.split(":", 1)
    elif len(s) == 4 and s.isdigit():
        left, right = s[:2], s[2:]
    else:
        raise ValueError("Invalid score format. Use '00:00' or '0000'.")

    if len(left) != 2 or len(right) != 2 or not (left + right).isdigit():
        raise ValueError("Score must be two digits per side (e.g. '03:12').")

    return left, right


def set_scoreboard_score(
    team_left: str,
    team_right: str,
    score: str,
    color: str = "FFFFFF",
    device_info: Optional[DeviceInfo] = None,
):
    """Render team names on the sides and a 16-pixel-high score in the center.

    The names are drawn exactly like in ``set_scoreboard_teams`` (3x5 vertical
    on the edges). The score uses large digits (16 rows) in the center area,
    without overwriting the name columns.

    Args:
        team_left: Name of the left team (max 4 characters).
        team_right: Name of the right team (max 4 characters).
        score: Score string (e.g. "00:00" or "0000").
        color: Hex color for the text, e.g. "FF0000".
        device_info: Injected automatically; provides matrix width/height.
    """
    if device_info is None:
        raise ValueError("device_info is required for set_scoreboard_score")

    width = int(device_info.width)
    height = int(device_info.height)

    if height < _SCORE_CHAR_HEIGHT:
        raise ValueError(f"Matrix height must be at least {_SCORE_CHAR_HEIGHT} pixels for the score")
    if width < 6:
        raise ValueError("Matrix width must be at least 6 pixels (3 per side)")

    # Normalize and clamp team names
    team_left = (team_left or "").upper()[:4]
    team_right = (team_right or "").upper()[:4]

    # Filter unsupported characters (keep only those present in GLYPH_3X5)
    filtered_left = "".join(ch for ch in team_left if ch in GLYPH_3X5)
    filtered_right = "".join(ch for ch in team_right if ch in GLYPH_3X5)

    if not filtered_left:
        logger.warning("Left team name '%s' has no supported characters (A-Z, 0-9)", team_left)
    if not filtered_right:
        logger.warning("Right team name '%s' has no supported characters (A-Z, 0-9)", team_right)

    team_left = filtered_left
    team_right = filtered_right

    num_left = len(team_left)
    num_right = len(team_right)

    spacing = 1
    char_h = 5
    y_start_left = _compute_vertical_start(num_left, height, char_h, spacing)
    y_start_right = _compute_vertical_start(num_right, height, char_h, spacing)

    text_color = _parse_color_hex(color)

    # Create blank canvas
    img = Image.new("RGB", (width, height), (0, 0, 0))

    # Draw side names as in set_scoreboard_teams
    x_left = 0
    for idx, ch in enumerate(team_left):
        glyph = GLYPH_3X5.get(ch)
        if glyph is None:
            continue
        y_offset = y_start_left + idx * (char_h + spacing)
        _draw_glyph_3x5(img, glyph, x_left, y_offset, text_color)

    x_right = width - 3
    for idx, ch in enumerate(team_right):
        glyph = GLYPH_3X5.get(ch)
        if glyph is None:
            continue
        y_offset = y_start_right + idx * (char_h + spacing)
        _draw_glyph_3x5(img, glyph, x_right, y_offset, text_color)

    # Parse score
    left_score, right_score = _parse_score(score)

    # Compute center region (exclude 3 columns on each side)
    center_left = 3
    center_right = width - 4
    center_width = center_right - center_left + 1

    digit_w = _SCORE_DIGIT_WIDTH
    colon_w = _SCORE_COLON_WIDTH
    gap = 1

    total_score_width = digit_w * 4 + colon_w + gap * 2

    if total_score_width > center_width:
        logger.warning(
            "Score rendering too wide for center region (needed %d, available %d)",
            total_score_width,
            center_width,
        )

    start_x = center_left + max(0, (center_width - total_score_width) // 2)
    y_offset_score = 0  # full height

    # Helper to draw a 2-digit number
    def _draw_two_digits(value: str, x: int) -> int:
        if len(value) != 2 or not value.isdigit():
            raise ValueError("Each side score must be two digits (e.g. '03')")
        for ch in value:
            glyph = GLYPH_SCORE.get(ch)
            if glyph is None:
                raise ValueError(f"Unsupported score digit: {ch}")
            _draw_score_glyph(img, glyph, x, y_offset_score, text_color)
            x += digit_w
        return x

    x = start_x
    x = _draw_two_digits(left_score, x)

    # Draw colon
    colon_glyph = GLYPH_SCORE.get(":")
    if colon_glyph is None:
        raise ValueError("Colon glyph missing in score font")
    x += gap
    _draw_score_glyph(img, colon_glyph, x, y_offset_score, text_color)
    x += colon_w

    x += gap
    _draw_two_digits(right_score, x)

    # Convert image to PNG bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    return _build_send_plan(png_bytes, is_gif=False, plan_name="set_scoreboard_score", save_slot=0)


__all__ = ["set_scoreboard_teams", "set_scoreboard_score"]
