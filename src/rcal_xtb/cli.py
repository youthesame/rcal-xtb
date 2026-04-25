"""Command-line entry points for strict 4-point reorganization-energy runs."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Sequence

from rcal_xtb import xtb_runner

CSV_FIELDS_P = [
    "molecule",
    "engine",
    "lambda_p_ev",
    "cation_relax_ev",
    "neutral_relax_ev",
    "xtb_total_wall_time_sec",
    "status",
    "error",
]
CSV_FIELDS_N = [
    "molecule",
    "engine",
    "lambda_n_ev",
    "anion_relax_ev",
    "neutral_relax_ev",
    "xtb_total_wall_time_sec",
    "status",
    "error",
]


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``rcal-xtb`` CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser with mode, input path, output CSV, and xTB options.
    """
    parser = argparse.ArgumentParser(
        description=("Calculate strict 4-point P/N-type reorganization energy for a single XYZ file with xTB")
    )
    parser.add_argument(
        "--engine",
        choices=["gfn2", "gxtb"],
        default="gfn2",
        help="xTB engine: gfn2 (stock xTB with --gfn 2) or gxtb (modified xTB with --gxtb)",
    )
    parser.add_argument(
        "--mode",
        choices=["p", "n"],
        default="p",
        help="Reorganization mode: p (hole/cation) or n (electron/anion)",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a single input XYZ file",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help=("Output CSV path (default: results/lambda_p_ev.csv for mode p, results/lambda_n_ev.csv for mode n)"),
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Keep per-molecule temporary work directories",
    )
    parser.add_argument(
        "--work-root",
        default=None,
        help="Optional root directory to create temporary work directories",
    )
    parser.add_argument(
        "--xtb-maxcycle",
        type=int,
        default=None,
        help=("Optional xTB optimization max cycles (--cycles INT). Applied to optimization steps only."),
    )
    return parser


def _format_value(value: float | None, *, digits: int = 12) -> str:
    """Format an optional float value for CSV output.

    Parameters
    ----------
    value : float | None
        Value to format. ``None`` is converted to an empty string.
    digits : int, default=12
        Number of decimal digits for non-``None`` values.

    Returns
    -------
    str
        Decimal string for numeric values, or an empty string for ``None``.
    """
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def run(argv: Sequence[str] | None = None) -> int:
    """Execute one CLI run and write a single-row CSV result.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Argument list passed to ``argparse``. If ``None``, process arguments are
        used.

    Returns
    -------
    int
        Process exit code. ``0`` on success, ``1`` on validation or runtime
        failure.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1
    if input_path.suffix.lower() != ".xyz":
        print(f"Input must be an .xyz file: {input_path}", file=sys.stderr)
        return 1

    default_output_name = "lambda_p_ev.csv" if args.mode == "p" else "lambda_n_ev.csv"
    if args.output_csv:
        output_csv = Path(args.output_csv)
    elif args.engine == "gxtb":
        output_csv = Path("results") / "gxtb" / default_output_name
    else:
        output_csv = Path("results") / default_output_name
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    work_root: Path | None = None
    if args.work_root:
        work_root = Path(args.work_root)
        work_root.mkdir(parents=True, exist_ok=True)
    if args.xtb_maxcycle is not None and args.xtb_maxcycle < 1:
        print("--xtb-maxcycle must be >= 1", file=sys.stderr)
        return 1

    try:
        xtb_runner.ensure_xtb_available(args.engine)
    except Exception as exc:  # pragma: no cover - exercised by runtime only
        print(f"xTB availability check failed: {exc}", file=sys.stderr)
        return 1

    if args.mode == "p":
        fieldnames = CSV_FIELDS_P
        try:
            calc_kwargs = {
                "engine": args.engine,
                "work_root": work_root,
                "keep_workdir": args.keep_workdir,
            }
            if args.xtb_maxcycle is not None:
                calc_kwargs["xtb_maxcycle"] = args.xtb_maxcycle
            result = xtb_runner.calculate_lambda_p_for_xyz(
                input_path,
                **calc_kwargs,
            )
            row = {
                "molecule": result.molecule,
                "engine": args.engine,
                "lambda_p_ev": _format_value(result.lambda_p_ev),
                "cation_relax_ev": _format_value(result.cation_relax_ev),
                "neutral_relax_ev": _format_value(result.neutral_relax_ev),
                "xtb_total_wall_time_sec": _format_value(result.xtb_total_wall_time_sec, digits=6),
                "status": "ok",
                "error": "",
            }
            exit_code = 0
            print(
                f"{result.molecule}: lambda_p={result.lambda_p_ev:.6f} eV "
                f"(cation={result.cation_relax_ev:.6f}, neutral={result.neutral_relax_ev:.6f}) "
                f"[xtb_total_wall_time_sec={result.xtb_total_wall_time_sec:.6f}]"
            )
        except Exception as exc:
            elapsed_wall_time_sec = getattr(exc, "elapsed_wall_time_sec", None)
            row = {
                "molecule": input_path.name,
                "engine": args.engine,
                "lambda_p_ev": "",
                "cation_relax_ev": "",
                "neutral_relax_ev": "",
                "xtb_total_wall_time_sec": _format_value(elapsed_wall_time_sec, digits=6),
                "status": "failed",
                "error": str(exc),
            }
            exit_code = 1
            print(f"{input_path.name}: failed: {exc}", file=sys.stderr)
    else:
        fieldnames = CSV_FIELDS_N
        try:
            calc_kwargs = {
                "engine": args.engine,
                "work_root": work_root,
                "keep_workdir": args.keep_workdir,
            }
            if args.xtb_maxcycle is not None:
                calc_kwargs["xtb_maxcycle"] = args.xtb_maxcycle
            result = xtb_runner.calculate_lambda_n_for_xyz(
                input_path,
                **calc_kwargs,
            )
            row = {
                "molecule": result.molecule,
                "engine": args.engine,
                "lambda_n_ev": _format_value(result.lambda_n_ev),
                "anion_relax_ev": _format_value(result.anion_relax_ev),
                "neutral_relax_ev": _format_value(result.neutral_relax_ev),
                "xtb_total_wall_time_sec": _format_value(result.xtb_total_wall_time_sec, digits=6),
                "status": "ok",
                "error": "",
            }
            exit_code = 0
            print(
                f"{result.molecule}: lambda_n={result.lambda_n_ev:.6f} eV "
                f"(anion={result.anion_relax_ev:.6f}, neutral={result.neutral_relax_ev:.6f}) "
                f"[xtb_total_wall_time_sec={result.xtb_total_wall_time_sec:.6f}]"
            )
        except Exception as exc:
            elapsed_wall_time_sec = getattr(exc, "elapsed_wall_time_sec", None)
            row = {
                "molecule": input_path.name,
                "engine": args.engine,
                "lambda_n_ev": "",
                "anion_relax_ev": "",
                "neutral_relax_ev": "",
                "xtb_total_wall_time_sec": _format_value(elapsed_wall_time_sec, digits=6),
                "status": "failed",
                "error": str(exc),
            }
            exit_code = 1
            print(f"{input_path.name}: failed: {exc}", file=sys.stderr)

    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    print(f"Wrote CSV: {output_csv}")
    return exit_code


def main(argv: Sequence[str] | None = None) -> None:
    """Run the CLI and terminate the process.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Argument list passed to :func:`run`.

    Raises
    ------
    SystemExit
        Raised with the exit code returned by :func:`run`.
    """
    raise SystemExit(run(argv))
