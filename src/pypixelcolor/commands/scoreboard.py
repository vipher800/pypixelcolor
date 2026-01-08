# -*- coding: utf-8 -*-
"""Scoreboard command for team names and score.

This module provides one command:

* ``set_sb_score``: draws two team names on the sides and a
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

_SCORE_PANEL_HEIGHT = 16
_SCORE_PANEL_WIDTH = 64

_SCORE_DIGIT_WIDTH = 8
_SCORE_COLON_WIDTH = 4

# fixed X positions of various elements (all Y are 0)
_POSITION_T1_TEAMNAME_X = 0
_POSITION_T2_TEAMNAME_X = 59
_POSITION_T1_SET_X = 6
_POSITION_T2_SET_X = 55
_POSITION_T1_SCORE_X = 13
_POSITION_T2_SCORE_X = 34
_POSITION_SCORE_SEPARATOR_X = 30

_SCORE_GAP = 1  # gap between digits in the score display

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
    "A": ["111", "101", "111", "101", "101"],
    "B": ["110", "101", "110", "101", "110"],
    "C": ["111", "100", "100", "100", "111"],
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


# 16-pixel high font for score digits and colon (legacy 8-pixel-wide version).
# Each glyph is a list of 16 strings. Digits are 8 pixels wide,
# the colon is 4 pixels wide.
GLYPH_SCORE: Dict[str, List[str]] = {
    "0": [
        "01111110",
        "11111111",
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
        "11111111",
        "01111110"
    ],
    "1": [
        "00011000",
        "00011000",
        "00111000",
        "00111000",
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
        "00011000"
    ],
    "2": [
        "11111110",
        "11111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "01111111",
        "11111110",
        "11000000",
        "11000000",
        "11000000",
        "11000000", 
        "11000000",
        "11111111",
        "01111111"
    ],
    "3": [
        "11111110",
        "11111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "11111111",
        "11111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "11111111",
        "11111110"
    ],
    "4": [
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11111111",
        "01111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011"
    ],
    "5": [
        "11111111",
        "11111111",
        "11000000",
        "11000000",
        "11000000",
        "11000000", 
        "11000000",
        "11111110",
        "11111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "11111111",
        "11111110"
    ],
    "6": [
        "01111111",
        "11111111",
        "11000000",
        "11000000",
        "11000000",
        "11000000",
        "11000000",
        "11111110",
        "11111111",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11111111",
        "01111110"
    ],
    "7": [
        "11111111",
        "11111111",
        "00000011",
        "00000011",
        "00000110",
        "00000110",
        "00001100",
        "00001100",
        "00011000",
        "00011000",
        "00110000",
        "00110000",
        "01100000",
        "01100000",
        "11000000",
        "11000000"
    ],
    "8": [
        "01111110",
        "11111111",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11111111",
        "11111111",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11111111",
        "01111110"
    ],
    "9": [
        "01111110",
        "11111111",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11000011",
        "11111111",
        "01111111",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "00000011",
        "11111111",
        "11111110"
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
    "c": [
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
        "0110",
    ],
}


def _parse_color_hex(color: str) -> Tuple[int, int, int]:
    """Parse a 6-char hex color into an (R, G, B) tuple."""
    if not isinstance(color, str) or len(color) != 6 or not all(c in "0123456789abcdefABCDEF" for c in color):
        raise ValueError("Color must be a 6-character hexadecimal string, e.g. 'FF0000'.")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)



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


def _draw_glyph_3x5_rotated_ccw(
    img: Image.Image,
    glyph: List[str],
    x_offset: int,
    y_offset: int,
    color: Tuple[int, int, int],
) -> None:
    """Draw a 3x5 glyph rotated 90° counter-clockwise.

    The original glyph is 3 columns × 5 rows. After rotation it becomes
    5 columns × 3 rows. This is used for the left team name so letters
    are turned towards the center.
    """
    width, height = img.size
    r, g, b = color

    if not glyph:
        return

    glyph_h = len(glyph)  # 5
    glyph_w = len(glyph[0])  # 3

    for row_idx, row in enumerate(glyph):
        if len(row) != glyph_w:
            continue
        for col_idx, ch in enumerate(row):
            if ch != "1":
                continue
            # Rotate (col, row) -> (row, glyph_w - 1 - col)
            x = x_offset + row_idx
            y = y_offset + (glyph_w - 1 - col_idx)
            if 0 <= x < width and 0 <= y < height:
                img.putpixel((x, y), (r, g, b))


def _draw_glyph_3x5_rotated_cw(
    img: Image.Image,
    glyph: List[str],
    x_offset: int,
    y_offset: int,
    color: Tuple[int, int, int],
) -> None:
    """Draw a 3x5 glyph rotated 90° clockwise.

    After rotation the glyph is 5 columns × 3 rows. This is used for the
    right team name so letters are turned towards the center.
    """
    width, height = img.size
    r, g, b = color

    if not glyph:
        return

    glyph_h = len(glyph)  # 5
    glyph_w = len(glyph[0])  # 3

    for row_idx, row in enumerate(glyph):
        if len(row) != glyph_w:
            continue
        for col_idx, ch in enumerate(row):
            if ch != "1":
                continue
            # Rotate (col, row) -> (glyph_h - 1 - row, col)
            x = x_offset + (glyph_h - 1 - row_idx)
            y = y_offset + col_idx
            if 0 <= x < width and 0 <= y < height:
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


def _parse_sets(sets: str) -> Tuple[str, str]:
    """Parse a sets string like '1:2' or '12' into (left, right).

    Typically each side will be a single digit (0–9), but we also allow
    two digits per side when given without a colon (e.g. "12" -> ("1", "2")).
    """
    if not isinstance(sets, str):
        raise ValueError("sets must be a string like '1:2'")

    s = sets.strip().replace(" ", "")
    if not s:
        raise ValueError("sets string cannot be empty")

    if ":" in s:
        left, right = s.split(":", 1)
    elif len(s) == 2 and s.isdigit():
        left, right = s[0], s[1]
    else:
        raise ValueError("Invalid sets format. Use '1:2' or '12'.")

    if not left.isdigit() or not right.isdigit():
        raise ValueError("Sets must be numeric on both sides (e.g. '1:2').")

    return left, right


def set_sb_score(
    team_left: str,
    team_right: str,
    sets: str,
    score: str,
    color: str = "FFFFFF",
    device_info: Optional[DeviceInfo] = None,
):
    """Render team names on the sides and a 16-pixel-high score in the center.

    The names are drawn with a 3x5 font rotated on the edges
    (left side rotated 90° CCW, right side 90° CW). The score uses large
    digits (16 rows) in the center area,
    without overwriting the 5-column name regions.

    Additionally, a small number of sets for each team is displayed
    between the team name and the central score, using the same 3x5 font
    (not rotated). The sets are provided as a single string like
    ``"1:2"`` where the first number is the left team sets and the
    second is the right team sets.

    Args:
        team_left: Name of the left team (max 4 characters).
        team_right: Name of the right team (max 4 characters).
        sets: Sets string (e.g. "1:2" or "12").
        score: Score string (e.g. "00:00" or "0000").
        color: Hex color for the text, e.g. "FF0000".
        device_info: Injected automatically; provides matrix width/height.
    """
    if device_info is None:
        raise ValueError("device_info is required for set_sb_score")

    width = int(device_info.width)
    height = int(device_info.height)

    if height < _SCORE_PANEL_HEIGHT:
        raise ValueError(f"Matrix height must be at least {_SCORE_PANEL_HEIGHT} pixels for the score")
    # 5 columns per side for rotated glyphs
    if width < _SCORE_PANEL_WIDTH:
        raise ValueError(f"Matrix width must be at least {_SCORE_PANEL_WIDTH} pixels (5 per side)")

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

    # After rotation each glyph is 5x3 (width x height)
    spacing = 1
    char_h = 3
    # Fixed vertical anchors for team names (all at Y = 0)
    y_start_left = 0
    y_start_right = 0

    # Main color for team names and central score
    main_color = _parse_color_hex(color)

    # Create blank canvas
    img = Image.new("RGB", (width, height), (0, 0, 0))

    # Draw side names (3x5 font rotated towards the center)
    x_left = _POSITION_T1_TEAMNAME_X
    for idx, ch in enumerate(team_left):
        glyph = GLYPH_3X5.get(ch)
        if glyph is None:
            continue
        draw_idx = num_left - 1 - idx
        y_offset = y_start_left + draw_idx * (char_h + spacing)
        _draw_glyph_3x5_rotated_ccw(img, glyph, x_left, y_offset, main_color)

    x_right = _POSITION_T2_TEAMNAME_X
    for idx, ch in enumerate(team_right):
        glyph = GLYPH_3X5.get(ch)
        if glyph is None:
            continue
        y_offset = y_start_right + idx * (char_h + spacing)
        _draw_glyph_3x5_rotated_cw(img, glyph, x_right, y_offset, main_color)

    # --- Draw number of sets (between team name and score) ---
    def _normalize_sets(value: str, label: str) -> str:
        if value is None:
            return ""
        s = str(value).strip()
        if not s:
            return ""
        if not s.isdigit():
            logger.warning("%s sets value '%s' is not numeric; ignoring", label, value)
            return ""
        # Limit to at most 2 digits to keep it compact
        return s[:2]

    # Parse and normalize sets for each team
    try:
        raw_sets_left, raw_sets_right = _parse_sets(sets)
    except ValueError as e:
        raise ValueError(f"Invalid sets value: {e}") from e

    sets_left_str = _normalize_sets(raw_sets_left, "Left")
    sets_right_str = _normalize_sets(raw_sets_right, "Right")

    # Colors: green on the left, red on the right (used for sets and scores)
    left_sets_color = (0, 255, 0)
    right_sets_color = (255, 0, 0)

    # Unrotated 3x5 digits, centered vertically, placed in a 3-column band
    sets_char_h = 5
    sets_spacing = 1

    if sets_left_str:
        num = len(sets_left_str)
        x_sets_left = _POSITION_T1_SET_X  # fixed X for left sets
        y_start_sets_left = 0
        for idx, ch in enumerate(sets_left_str):
            glyph = GLYPH_3X5.get(ch)
            if glyph is None:
                continue
            y_offset = y_start_sets_left + idx * (sets_char_h + sets_spacing)
            _draw_glyph_3x5(img, glyph, x_sets_left, y_offset, left_sets_color)

    if sets_right_str:
        num = len(sets_right_str)
        x_sets_right = _POSITION_T2_SET_X  # fixed X for right sets
        y_start_sets_right = 0
        for idx, ch in enumerate(sets_right_str):
            glyph = GLYPH_3X5.get(ch)
            if glyph is None:
                continue
            y_offset = y_start_sets_right + idx * (sets_char_h + sets_spacing)
            _draw_glyph_3x5(img, glyph, x_sets_right, y_offset, right_sets_color)

    # Parse score
    left_score, right_score = _parse_score(score)

    # Fixed positions for score: left/right anchors (Y is 0)
    digit_w = _SCORE_DIGIT_WIDTH
    colon_w = _SCORE_COLON_WIDTH
    gap = 1  # gap around the colon
    inner_gap = 1  # second digit at X + _SCORE_DIGIT_WIDTH + _SCORE_GAP

    x_left_score = _POSITION_T1_SCORE_X
    x_right_score = _POSITION_T2_SCORE_X
    y_offset_score = 0

    # Helper to draw a 2-digit number with a small gap between digits
    def _draw_two_digits(value: str, x: int, color: Tuple[int, int, int]) -> int:
        if len(value) != 2 or not value.isdigit():
            raise ValueError("Each side score must be two digits (e.g. '03')")
        first, second = value[0], value[1]

        glyph = GLYPH_SCORE.get(first)
        if glyph is None:
            raise ValueError(f"Unsupported score digit: {first}")
        _draw_score_glyph(img, glyph, x, y_offset_score, color)
        x += digit_w + inner_gap

        glyph = GLYPH_SCORE.get(second)
        if glyph is None:
            raise ValueError(f"Unsupported score digit: {second}")
        _draw_score_glyph(img, glyph, x, y_offset_score, color)
        x += digit_w
        return x

    # Draw left score at fixed X
    _draw_two_digits(left_score, x_left_score, left_sets_color)

    # Dessiner le deux-points avec la police 8x16, positionné à une X fixe
    colon_glyph = GLYPH_SCORE.get(":")
    if colon_glyph is None:
        raise ValueError("Colon glyph missing in score font")
    _draw_score_glyph(img, colon_glyph, _POSITION_SCORE_SEPARATOR_X, y_offset_score, main_color)

    # Draw right score at fixed X
    _draw_two_digits(right_score, x_right_score, right_sets_color)

    # Convert image to PNG bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    return _build_send_plan(png_bytes, is_gif=False, plan_name="set_sb_score", save_slot=0)


__all__ = ["set_sb_score"]
