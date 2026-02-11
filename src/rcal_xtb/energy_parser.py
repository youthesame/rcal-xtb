"""Parsers for extracting energy and wall-time from xTB logs."""

from __future__ import annotations

import re
from pathlib import Path

TOTAL_ENERGY_PATTERN = re.compile(r"(?i)(?:TOTAL ENERGY|total energy)\s+(-?\d+(?:\.\d+)?)\s+Eh")
TOTAL_SECTION_PATTERN = re.compile(r"(?ims)^\s*total:\s*$\n(?P<body>.*?)(?=^\s*[A-Za-z][A-Za-z0-9 _/+.-]*:\s*$|\Z)")
WALL_TIME_PATTERN = re.compile(
    r"(?im)^\s*\*\s*wall-time:\s*(?P<days>\d+)\s*d,\s*"
    r"(?P<hours>\d+)\s*h,\s*(?P<minutes>\d+)\s*min,\s*"
    r"(?P<seconds>\d+(?:\.\d+)?)\s*sec\s*$"
)


def extract_total_energy_eh_from_text(text: str) -> float:
    """Extract the last ``TOTAL ENERGY`` value from xTB text output.

    Parameters
    ----------
    text : str
        Raw standard output text produced by xTB.

    Returns
    -------
    float
        The last matched total energy value in Eh.

    Raises
    ------
    ValueError
        If no ``TOTAL ENERGY`` line is found.
    """
    matches = TOTAL_ENERGY_PATTERN.findall(text)
    if not matches:
        raise ValueError("TOTAL ENERGY was not found in xTB output")
    return float(matches[-1])


def extract_total_energy_eh_from_file(path: Path) -> float:
    """Extract ``TOTAL ENERGY`` from a UTF-8-decoded log file.

    Parameters
    ----------
    path : Path
        Path to an xTB output log file.

    Returns
    -------
    float
        The last matched total energy value in Eh.

    Raises
    ------
    ValueError
        If no ``TOTAL ENERGY`` line is found in the file contents.
    """
    return extract_total_energy_eh_from_text(path.read_text(encoding="utf-8", errors="replace"))


def extract_total_wall_time_sec_from_text(text: str) -> float:
    """Extract total wall-time from the ``total:`` section of xTB output.

    Parameters
    ----------
    text : str
        Raw standard output text produced by xTB.

    Returns
    -------
    float
        Wall-time in seconds.

    Raises
    ------
    ValueError
        If the ``total:`` section or ``wall-time`` row is missing.
    """
    total_section_match = TOTAL_SECTION_PATTERN.search(text)
    if total_section_match is None:
        raise ValueError("total section was not found in xTB output")

    wall_time_match = WALL_TIME_PATTERN.search(total_section_match.group("body"))
    if wall_time_match is None:
        raise ValueError("total wall-time was not found in xTB output")

    days = int(wall_time_match.group("days"))
    hours = int(wall_time_match.group("hours"))
    minutes = int(wall_time_match.group("minutes"))
    seconds = float(wall_time_match.group("seconds"))
    return (days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60) + seconds


def extract_total_wall_time_sec_from_file(path: Path) -> float:
    """Extract total wall-time from a UTF-8-decoded log file.

    Parameters
    ----------
    path : Path
        Path to an xTB output log file.

    Returns
    -------
    float
        Wall-time in seconds.

    Raises
    ------
    ValueError
        If the required wall-time information is not found.
    """
    return extract_total_wall_time_sec_from_text(path.read_text(encoding="utf-8", errors="replace"))
