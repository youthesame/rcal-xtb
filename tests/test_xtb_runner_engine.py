from __future__ import annotations

import subprocess
from pathlib import Path

from rcal_xtb import xtb_runner

XTB_STDOUT = """
 | TOTAL ENERGY              -1.000000000000 Eh   |
total:
 * wall-time:     0 d,  0 h,  0 min,  1.500 sec
"""


def _write_dummy_xyz(path: Path) -> None:
    path.write_text("1\nH\nH 0.0 0.0 0.0\n", encoding="utf-8")


def test_ensure_xtb_available_uses_gxtb_module(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_run(args, *, capture_output, text, check):
        seen["args"] = args
        seen["capture_output"] = capture_output
        seen["text"] = text
        seen["check"] = check
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="/path/to/xtb\n--gxtb\n", stderr="")

    monkeypatch.setattr(xtb_runner.subprocess, "run", fake_run)

    xtb_runner.ensure_xtb_available("gxtb")

    assert seen["args"] == ["bash", "-lc", "module load g-xtb && which xtb && xtb --version && xtb --help"]
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["check"] is False


def test_run_xtb_step_uses_gxtb_flag_without_gfn2(monkeypatch, tmp_path: Path) -> None:
    input_xyz = tmp_path / "input.xyz"
    _write_dummy_xyz(input_xyz)
    seen: dict[str, object] = {}

    def fake_run(args, *, cwd, capture_output, text, check):
        seen["args"] = args
        seen["cwd"] = cwd
        seen["capture_output"] = capture_output
        seen["text"] = text
        seen["check"] = check
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=XTB_STDOUT, stderr="")

    monkeypatch.setattr(xtb_runner.subprocess, "run", fake_run)

    result = xtb_runner._run_xtb_step(
        input_xyz=input_xyz,
        step_dir=tmp_path / "step",
        engine="gxtb",
        chrg=-1,
        uhf=1,
        optimize=False,
    )

    command = seen["args"][2]
    assert "module load g-xtb" in command
    assert "--gxtb" in command
    assert "--gfn 2" not in command
    assert "--chrg -1" in command
    assert "--uhf 1" in command
    assert result.energy_eh == -1.0
    assert result.wall_time_sec == 1.5


def test_run_xtb_step_preserves_opt_tight_and_cycles_for_gxtb(monkeypatch, tmp_path: Path) -> None:
    input_xyz = tmp_path / "input.xyz"
    _write_dummy_xyz(input_xyz)
    seen: dict[str, object] = {}

    def fake_run(args, *, cwd, capture_output, text, check):
        seen["args"] = args
        Path(cwd, "xtbopt.xyz").write_text("1\nH\nH 0.0 0.0 0.0\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=XTB_STDOUT, stderr="")

    monkeypatch.setattr(xtb_runner.subprocess, "run", fake_run)

    result = xtb_runner._run_xtb_step(
        input_xyz=input_xyz,
        step_dir=tmp_path / "step",
        engine="gxtb",
        chrg=1,
        uhf=1,
        optimize=True,
        xtb_maxcycle=123,
    )

    command = seen["args"][2]
    assert "--opt tight" in command
    assert "--cycles 123" in command
    assert "--gxtb" in command
    assert result.optimized_xyz == tmp_path / "step" / "xtbopt.xyz"
