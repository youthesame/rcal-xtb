from __future__ import annotations

import pytest

from rcal_xtb.energy_parser import (
    extract_total_energy_eh_from_text,
    extract_total_wall_time_sec_from_text,
)


def test_extract_total_energy_supports_upper_and_lower_case() -> None:
    text = """
      :: total energy             -35.022101092550 Eh    ::
      | TOTAL ENERGY              -35.022201092550 Eh   |
    """
    assert extract_total_energy_eh_from_text(text) == pytest.approx(-35.022201092550)


def test_extract_total_energy_raises_when_missing() -> None:
    with pytest.raises(ValueError, match="TOTAL ENERGY"):
        extract_total_energy_eh_from_text("no energy line")


def test_extract_total_wall_time_from_total_section() -> None:
    text = """
total:
 * wall-time:     0 d,  1 h,  2 min,  3.500 sec
 *  cpu-time:     0 d,  1 h,  3 min, 40.000 sec
SCF:
 * wall-time:     0 d,  0 h,  0 min, 11.111 sec
"""
    assert extract_total_wall_time_sec_from_text(text) == pytest.approx(3723.5)


def test_extract_total_wall_time_raises_when_total_section_missing() -> None:
    text = """
SCF:
 * wall-time:     0 d,  0 h,  0 min,  1.000 sec
"""
    with pytest.raises(ValueError, match="total section"):
        extract_total_wall_time_sec_from_text(text)


def test_extract_total_wall_time_raises_when_missing() -> None:
    text = """
total:
 * cpu-time:      0 d,  0 h,  0 min,  2.000 sec
"""
    with pytest.raises(ValueError, match="wall-time"):
        extract_total_wall_time_sec_from_text(text)
