from __future__ import annotations

import csv
from pathlib import Path

from rcal_xtb import cli
from rcal_xtb.xtb_runner import NMoleculeResult, PMoleculeResult, XtbCommandError


def _write_dummy_xyz(path: Path) -> None:
    path.write_text("1\nH\nH 0.0 0.0 0.0\n", encoding="utf-8")


def test_cli_writes_failed_row_for_single_input_failure_p_mode(monkeypatch, tmp_path: Path) -> None:
    xyz_path = tmp_path / "bad.xyz"
    _write_dummy_xyz(xyz_path)
    output_csv = tmp_path / "results" / "out.csv"

    monkeypatch.setattr(cli.xtb_runner, "ensure_xtb_available", lambda: None)

    def fake_calculate_lambda_p_for_xyz(
        xyz_path: Path,
        *,
        work_root: Path | None = None,
        keep_workdir: bool = False,
    ) -> PMoleculeResult:
        raise XtbCommandError(
            "simulated xtb failure",
            elapsed_wall_time_sec=3.5,
        )

    monkeypatch.setattr(
        cli.xtb_runner,
        "calculate_lambda_p_for_xyz",
        fake_calculate_lambda_p_for_xyz,
    )

    exit_code = cli.run(
        [
            "--input",
            str(xyz_path),
            "--output-csv",
            str(output_csv),
        ]
    )

    assert exit_code == 1
    rows = list(csv.DictReader(output_csv.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    assert row["molecule"] == "bad.xyz"
    assert row["status"] == "failed"
    assert row["xtb_total_wall_time_sec"] == "3.500000"
    assert "simulated xtb failure" in row["error"]


def test_cli_writes_ok_row_for_single_input_success(monkeypatch, tmp_path: Path) -> None:
    xyz_path = tmp_path / "good.xyz"
    _write_dummy_xyz(xyz_path)
    output_csv = tmp_path / "results" / "out.csv"

    monkeypatch.setattr(cli.xtb_runner, "ensure_xtb_available", lambda: None)

    def fake_calculate_lambda_p_for_xyz(
        xyz_path: Path,
        *,
        work_root: Path | None = None,
        keep_workdir: bool = False,
    ) -> PMoleculeResult:
        return PMoleculeResult(
            molecule=xyz_path.name,
            lambda_p_ev=0.123,
            cation_relax_ev=0.045,
            neutral_relax_ev=0.078,
            xtb_total_wall_time_sec=9.876543,
            workdir=None,
        )

    monkeypatch.setattr(
        cli.xtb_runner,
        "calculate_lambda_p_for_xyz",
        fake_calculate_lambda_p_for_xyz,
    )

    exit_code = cli.run(
        [
            "--input",
            str(xyz_path),
            "--output-csv",
            str(output_csv),
        ]
    )

    assert exit_code == 0
    rows = list(csv.DictReader(output_csv.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    assert row["molecule"] == "good.xyz"
    assert row["status"] == "ok"
    assert row["lambda_p_ev"] != ""
    assert row["xtb_total_wall_time_sec"] == "9.876543"


def test_cli_writes_failed_row_for_single_input_failure_n_mode(monkeypatch, tmp_path: Path) -> None:
    xyz_path = tmp_path / "bad_n.xyz"
    _write_dummy_xyz(xyz_path)
    output_csv = tmp_path / "results" / "out_n.csv"

    monkeypatch.setattr(cli.xtb_runner, "ensure_xtb_available", lambda: None)

    def fake_calculate_lambda_n_for_xyz(
        xyz_path: Path,
        *,
        work_root: Path | None = None,
        keep_workdir: bool = False,
    ) -> NMoleculeResult:
        raise XtbCommandError(
            "simulated n-type xtb failure",
            elapsed_wall_time_sec=7.25,
        )

    monkeypatch.setattr(
        cli.xtb_runner,
        "calculate_lambda_n_for_xyz",
        fake_calculate_lambda_n_for_xyz,
    )

    exit_code = cli.run(
        [
            "--mode",
            "n",
            "--input",
            str(xyz_path),
            "--output-csv",
            str(output_csv),
        ]
    )

    assert exit_code == 1
    rows = list(csv.DictReader(output_csv.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    assert row["molecule"] == "bad_n.xyz"
    assert row["status"] == "failed"
    assert row["lambda_n_ev"] == ""
    assert row["anion_relax_ev"] == ""
    assert row["xtb_total_wall_time_sec"] == "7.250000"
    assert "simulated n-type xtb failure" in row["error"]


def test_cli_writes_ok_row_for_single_input_success_n_mode(monkeypatch, tmp_path: Path) -> None:
    xyz_path = tmp_path / "good_n.xyz"
    _write_dummy_xyz(xyz_path)
    output_csv = tmp_path / "results" / "out_n.csv"

    monkeypatch.setattr(cli.xtb_runner, "ensure_xtb_available", lambda: None)

    def fake_calculate_lambda_n_for_xyz(
        xyz_path: Path,
        *,
        work_root: Path | None = None,
        keep_workdir: bool = False,
    ) -> NMoleculeResult:
        return NMoleculeResult(
            molecule=xyz_path.name,
            lambda_n_ev=0.321,
            anion_relax_ev=0.111,
            neutral_relax_ev=0.210,
            xtb_total_wall_time_sec=4.5,
            workdir=None,
        )

    monkeypatch.setattr(
        cli.xtb_runner,
        "calculate_lambda_n_for_xyz",
        fake_calculate_lambda_n_for_xyz,
    )

    exit_code = cli.run(
        [
            "--mode",
            "n",
            "--input",
            str(xyz_path),
            "--output-csv",
            str(output_csv),
        ]
    )

    assert exit_code == 0
    rows = list(csv.DictReader(output_csv.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    assert row["molecule"] == "good_n.xyz"
    assert row["status"] == "ok"
    assert row["lambda_n_ev"] != ""
    assert row["xtb_total_wall_time_sec"] == "4.500000"
