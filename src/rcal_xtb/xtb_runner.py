"""xTB execution helpers for strict 4-point reorganization-energy workflows."""

from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from rcal_xtb.energy_parser import (
    extract_total_energy_eh_from_text,
    extract_total_wall_time_sec_from_text,
)
from rcal_xtb.reorg_n import NEnergyTermsEh, compute_n_reorganization_energy
from rcal_xtb.reorg_p import PEnergyTermsEh, compute_p_reorganization_energy

XtbEngine = Literal["gfn2", "gxtb"]


@dataclass(frozen=True)
class PMoleculeResult:
    """Final P-type result for one input molecule.

    Parameters
    ----------
    molecule : str
        Input file name.
    lambda_p_ev : float
        Total P-type reorganization energy in eV.
    cation_relax_ev : float
        Cation relaxation component in eV.
    neutral_relax_ev : float
        Neutral relaxation component in eV.
    xtb_total_wall_time_sec : float
        Sum of xTB wall-times for all four steps.
    workdir : Path | None
        Preserved working directory path when ``keep_workdir=True``; otherwise
        ``None``.
    """

    molecule: str
    lambda_p_ev: float
    cation_relax_ev: float
    neutral_relax_ev: float
    xtb_total_wall_time_sec: float
    workdir: Path | None


@dataclass(frozen=True)
class NMoleculeResult:
    """Final N-type result for one input molecule.

    Parameters
    ----------
    molecule : str
        Input file name.
    lambda_n_ev : float
        Total N-type reorganization energy in eV.
    anion_relax_ev : float
        Anion relaxation component in eV.
    neutral_relax_ev : float
        Neutral relaxation component in eV.
    xtb_total_wall_time_sec : float
        Sum of xTB wall-times for all four steps.
    workdir : Path | None
        Preserved working directory path when ``keep_workdir=True``; otherwise
        ``None``.
    """

    molecule: str
    lambda_n_ev: float
    anion_relax_ev: float
    neutral_relax_ev: float
    xtb_total_wall_time_sec: float
    workdir: Path | None


@dataclass(frozen=True)
class _FourPointTermsEh:
    """Energy terms gathered from the four xTB steps.

    Parameters
    ----------
    e0_r0 : float
        Neutral-state energy at neutral optimized geometry in Eh.
    e_state_rstate : float
        Charged-state energy at charged optimized geometry in Eh.
    e_state_r0 : float
        Charged-state energy at neutral optimized geometry in Eh.
    e0_rstate : float
        Neutral-state energy at charged optimized geometry in Eh.
    xtb_total_wall_time_sec : float
        Sum of xTB wall-times from the four steps in seconds.
    """

    e0_r0: float
    e_state_rstate: float
    e_state_r0: float
    e0_rstate: float
    xtb_total_wall_time_sec: float


@dataclass(frozen=True)
class _XtbStepResult:
    """Result payload for one xTB command step.

    Parameters
    ----------
    energy_eh : float
        Parsed ``TOTAL ENERGY`` in Eh.
    optimized_xyz : Path | None
        ``xtbopt.xyz`` path for optimization steps, otherwise ``None``.
    wall_time_sec : float
        Parsed xTB wall-time in seconds for this step.
    """

    energy_eh: float
    optimized_xyz: Path | None
    wall_time_sec: float


class XtbCommandError(RuntimeError):
    """Error raised for xTB availability or execution failures.

    Parameters
    ----------
    message : str
        Human-readable error message.
    elapsed_wall_time_sec : float | None, optional
        Partial accumulated wall-time in seconds before the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        elapsed_wall_time_sec: float | None = None,
    ) -> None:
        super().__init__(message)
        self.elapsed_wall_time_sec = elapsed_wall_time_sec


def _module_load_command(engine: XtbEngine) -> str:
    if engine == "gxtb":
        return "module load g-xtb"
    return "module load xtb"


def _method_args(engine: XtbEngine) -> list[str]:
    if engine == "gxtb":
        return ["--gxtb"]
    return ["--gfn", "2"]


def ensure_xtb_available(engine: XtbEngine = "gfn2") -> None:
    """Verify that xTB can be loaded and executed in the shell environment.

    Parameters
    ----------
    engine : {"gfn2", "gxtb"}, default="gfn2"
        Engine environment to verify. ``"gxtb"`` uses ``module load g-xtb``
        and still expects the executable name to be ``xtb``.

    Raises
    ------
    XtbCommandError
        If ``module load xtb`` or basic xTB commands fail.
    """
    command = f"{_module_load_command(engine)} && which xtb && xtb --version"
    if engine == "gxtb":
        command = f"{command} && xtb --help"
    proc = subprocess.run(
        ["bash", "-lc", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise XtbCommandError(
            f"xTB is not available. Failed command: {command}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    if engine == "gxtb" and "--gxtb" not in f"{proc.stdout}\n{proc.stderr}":
        raise XtbCommandError(
            f"g-xTB support was not found in xtb --help. Failed command: {command}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )


def _run_xtb_step(
    *,
    input_xyz: Path,
    step_dir: Path,
    engine: XtbEngine,
    chrg: int,
    uhf: int,
    optimize: bool,
    xtb_maxcycle: int | None = None,
) -> _XtbStepResult:
    """Run one xTB optimization or single-point step.

    Parameters
    ----------
    input_xyz : Path
        Input geometry file.
    step_dir : Path
        Per-step working directory where logs and outputs are written.
    engine : {"gfn2", "gxtb"}
        xTB engine command style to use.
    chrg : int
        Charge passed to xTB as ``--chrg``.
    uhf : int
        UHF multiplicity control passed as ``--uhf``.
    optimize : bool
        If ``True``, run ``--opt tight`` and expect ``xtbopt.xyz``.
    xtb_maxcycle : int | None, optional
        Optional maximum optimization cycles (``--cycles``), used only when
        ``optimize=True``.

    Returns
    -------
    _XtbStepResult
        Parsed step energy, optional optimized geometry path, and wall-time.

    Raises
    ------
    XtbCommandError
        If command execution fails, wall-time/energy cannot be parsed, or an
        optimization output is missing.
    """
    step_dir.mkdir(parents=True, exist_ok=True)
    local_input = step_dir / "input.xyz"
    shutil.copy2(input_xyz, local_input)

    args = ["xtb", local_input.name]
    if optimize:
        args.extend(["--opt", "tight"])
        if xtb_maxcycle is not None:
            args.extend(["--cycles", str(xtb_maxcycle)])
    args.extend(_method_args(engine))
    args.extend(["--chrg", str(chrg), "--uhf", str(uhf)])

    xtb_cmd = " ".join(shlex.quote(arg) for arg in args)
    full_cmd = f"{_module_load_command(engine)} && {xtb_cmd}"

    proc = subprocess.run(
        ["bash", "-lc", full_cmd],
        cwd=step_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    stdout_path = step_dir / "stdout.log"
    stderr_path = step_dir / "stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    step_wall_time_sec: float | None = None
    try:
        step_wall_time_sec = extract_total_wall_time_sec_from_text(proc.stdout)
    except ValueError:
        step_wall_time_sec = None

    if proc.returncode != 0:
        raise XtbCommandError(
            "xTB command failed "
            f"(returncode={proc.returncode}, step={step_dir.name}). "
            f"stdout={stdout_path} stderr={stderr_path}",
            elapsed_wall_time_sec=step_wall_time_sec,
        )

    if step_wall_time_sec is None:
        raise XtbCommandError(
            f"total wall-time was not found in xTB output (step={step_dir.name}, stdout={stdout_path})"
        )

    try:
        energy_eh = extract_total_energy_eh_from_text(proc.stdout)
    except ValueError as exc:
        raise XtbCommandError(
            f"TOTAL ENERGY was not found in xTB output (step={step_dir.name}, stdout={stdout_path})",
            elapsed_wall_time_sec=step_wall_time_sec,
        ) from exc

    if not optimize:
        return _XtbStepResult(
            energy_eh=energy_eh,
            optimized_xyz=None,
            wall_time_sec=step_wall_time_sec,
        )

    optimized_xyz = step_dir / "xtbopt.xyz"
    if not optimized_xyz.exists():
        raise XtbCommandError(
            f"Optimization output not found: {optimized_xyz} (step={step_dir.name})",
            elapsed_wall_time_sec=step_wall_time_sec,
        )
    return _XtbStepResult(
        energy_eh=energy_eh,
        optimized_xyz=optimized_xyz,
        wall_time_sec=step_wall_time_sec,
    )


@contextmanager
def _molecule_workdir(
    *,
    xyz_path: Path,
    work_root: Path | None,
    keep_workdir: bool,
) -> Iterator[Path]:
    """Create and optionally clean up a per-molecule temporary working directory.

    Parameters
    ----------
    xyz_path : Path
        Source geometry path used to build the temp directory prefix.
    work_root : Path | None
        Parent directory for temp directory creation. Uses system temp directory
        when ``None``.
    keep_workdir : bool
        If ``True``, do not delete the generated work directory on exit.

    Yields
    ------
    Path
        Path to the temporary molecule work directory.
    """
    if work_root is not None:
        work_root.mkdir(parents=True, exist_ok=True)

    molecule_workdir = Path(
        tempfile.mkdtemp(
            prefix=f"{xyz_path.stem}_",
            dir=str(work_root) if work_root is not None else None,
        )
    )

    try:
        yield molecule_workdir
    finally:
        if not keep_workdir:
            shutil.rmtree(molecule_workdir, ignore_errors=True)


def _run_four_point_terms(
    *,
    input_xyz: Path,
    molecule_workdir: Path,
    engine: XtbEngine,
    state_label: str,
    state_charge: int,
    state_uhf: int,
    state_geom_name: str,
    xtb_maxcycle: int | None = None,
) -> _FourPointTermsEh:
    """Run the strict 4-point xTB workflow and collect energy terms.

    Parameters
    ----------
    input_xyz : Path
        Input geometry used as the starting point.
    molecule_workdir : Path
        Root work directory for all four xTB steps.
    engine : {"gfn2", "gxtb"}
        xTB engine command style to use.
    state_label : str
        Human-readable state label for directory naming (for example,
        ``"cation"`` or ``"anion"``).
    state_charge : int
        Charged-state ``--chrg`` value.
    state_uhf : int
        Charged-state ``--uhf`` value.
    state_geom_name : str
        Charged optimized geometry name used in output filenames (for example,
        ``"Rplus"`` or ``"Rminus"``).
    xtb_maxcycle : int | None, optional
        Optional maximum optimization cycles.

    Returns
    -------
    _FourPointTermsEh
        Four energy terms and summed xTB wall-time.

    Raises
    ------
    XtbCommandError
        If any xTB step fails or expected optimized geometry is missing.
    """
    total_wall_time_sec = 0.0

    def _run_step(*, input_xyz: Path, step_dir: Path, chrg: int, uhf: int, optimize: bool) -> _XtbStepResult:
        nonlocal total_wall_time_sec
        try:
            step_result = _run_xtb_step(
                input_xyz=input_xyz,
                step_dir=step_dir,
                engine=engine,
                chrg=chrg,
                uhf=uhf,
                optimize=optimize,
                xtb_maxcycle=xtb_maxcycle,
            )
        except XtbCommandError as exc:
            elapsed_wall_time_sec = total_wall_time_sec
            if exc.elapsed_wall_time_sec is not None:
                elapsed_wall_time_sec += exc.elapsed_wall_time_sec
            raise XtbCommandError(
                str(exc),
                elapsed_wall_time_sec=elapsed_wall_time_sec,
            ) from exc

        total_wall_time_sec += step_result.wall_time_sec
        return step_result

    step1_dir = molecule_workdir / "step1_neutral_opt"
    step1_result = _run_step(
        input_xyz=input_xyz,
        step_dir=step1_dir,
        chrg=0,
        uhf=0,
        optimize=True,
    )
    e0_r0 = step1_result.energy_eh
    r0_opt_in_step = step1_result.optimized_xyz
    if r0_opt_in_step is None:
        raise XtbCommandError(
            "R0 optimized structure was not produced",
            elapsed_wall_time_sec=total_wall_time_sec,
        )
    r0_opt_xyz = molecule_workdir / "R0_opt.xyz"
    shutil.copy2(r0_opt_in_step, r0_opt_xyz)

    step2_dir = molecule_workdir / f"step2_{state_label}_opt"
    step2_result = _run_step(
        input_xyz=r0_opt_xyz,
        step_dir=step2_dir,
        chrg=state_charge,
        uhf=state_uhf,
        optimize=True,
    )
    e_state_rstate = step2_result.energy_eh
    state_opt_in_step = step2_result.optimized_xyz
    if state_opt_in_step is None:
        raise XtbCommandError(
            f"{state_geom_name} optimized structure was not produced",
            elapsed_wall_time_sec=total_wall_time_sec,
        )
    state_opt_xyz = molecule_workdir / f"{state_geom_name}_opt.xyz"
    shutil.copy2(state_opt_in_step, state_opt_xyz)

    step3_dir = molecule_workdir / f"step3_{state_label}_sp_at_r0"
    step3_result = _run_step(
        input_xyz=r0_opt_xyz,
        step_dir=step3_dir,
        chrg=state_charge,
        uhf=state_uhf,
        optimize=False,
    )
    e_state_r0 = step3_result.energy_eh

    step4_dir = molecule_workdir / f"step4_neutral_sp_at_{state_geom_name.lower()}"
    step4_result = _run_step(
        input_xyz=state_opt_xyz,
        step_dir=step4_dir,
        chrg=0,
        uhf=0,
        optimize=False,
    )
    e0_rstate = step4_result.energy_eh

    return _FourPointTermsEh(
        e0_r0=e0_r0,
        e_state_rstate=e_state_rstate,
        e_state_r0=e_state_r0,
        e0_rstate=e0_rstate,
        xtb_total_wall_time_sec=total_wall_time_sec,
    )


def calculate_lambda_p_for_xyz(
    xyz_path: Path,
    *,
    engine: XtbEngine = "gfn2",
    work_root: Path | None = None,
    keep_workdir: bool = False,
    xtb_maxcycle: int | None = None,
) -> PMoleculeResult:
    """Calculate strict 4-point P-type reorganization energy for one ``.xyz``.

    Parameters
    ----------
    xyz_path : Path
        Path to the input ``.xyz`` file.
    engine : {"gfn2", "gxtb"}, default="gfn2"
        xTB engine command style to use.
    work_root : Path | None, optional
        Optional parent directory for temporary work directories.
    keep_workdir : bool, default=False
        Keep intermediate files and return the work directory path.
    xtb_maxcycle : int | None, optional
        Optional maximum optimization cycles for xTB optimization steps.

    Returns
    -------
    PMoleculeResult
        Computed P-type values in eV with total wall-time.

    Raises
    ------
    FileNotFoundError
        If ``xyz_path`` does not exist.
    XtbCommandError
        If xTB execution or output parsing fails.
    """
    if not xyz_path.exists():
        raise FileNotFoundError(f"Input XYZ not found: {xyz_path}")

    with _molecule_workdir(
        xyz_path=xyz_path,
        work_root=work_root,
        keep_workdir=keep_workdir,
    ) as molecule_workdir:
        terms = _run_four_point_terms(
            input_xyz=xyz_path,
            molecule_workdir=molecule_workdir,
            engine=engine,
            state_label="cation",
            state_charge=1,
            state_uhf=1,
            state_geom_name="Rplus",
            xtb_maxcycle=xtb_maxcycle,
        )
        p_energy = compute_p_reorganization_energy(
            PEnergyTermsEh(
                e0_r0=terms.e0_r0,
                ep_rplus=terms.e_state_rstate,
                ep_r0=terms.e_state_r0,
                e0_rplus=terms.e0_rstate,
            )
        )

        return PMoleculeResult(
            molecule=xyz_path.name,
            lambda_p_ev=p_energy.lambda_p_ev,
            cation_relax_ev=p_energy.cation_relax_ev,
            neutral_relax_ev=p_energy.neutral_relax_ev,
            xtb_total_wall_time_sec=terms.xtb_total_wall_time_sec,
            workdir=molecule_workdir if keep_workdir else None,
        )


def calculate_lambda_n_for_xyz(
    xyz_path: Path,
    *,
    engine: XtbEngine = "gfn2",
    work_root: Path | None = None,
    keep_workdir: bool = False,
    xtb_maxcycle: int | None = None,
) -> NMoleculeResult:
    """Calculate strict 4-point N-type reorganization energy for one ``.xyz``.

    Parameters
    ----------
    xyz_path : Path
        Path to the input ``.xyz`` file.
    engine : {"gfn2", "gxtb"}, default="gfn2"
        xTB engine command style to use.
    work_root : Path | None, optional
        Optional parent directory for temporary work directories.
    keep_workdir : bool, default=False
        Keep intermediate files and return the work directory path.
    xtb_maxcycle : int | None, optional
        Optional maximum optimization cycles for xTB optimization steps.

    Returns
    -------
    NMoleculeResult
        Computed N-type values in eV with total wall-time.

    Raises
    ------
    FileNotFoundError
        If ``xyz_path`` does not exist.
    XtbCommandError
        If xTB execution or output parsing fails.
    """
    if not xyz_path.exists():
        raise FileNotFoundError(f"Input XYZ not found: {xyz_path}")

    with _molecule_workdir(
        xyz_path=xyz_path,
        work_root=work_root,
        keep_workdir=keep_workdir,
    ) as molecule_workdir:
        terms = _run_four_point_terms(
            input_xyz=xyz_path,
            molecule_workdir=molecule_workdir,
            engine=engine,
            state_label="anion",
            state_charge=-1,
            state_uhf=1,
            state_geom_name="Rminus",
            xtb_maxcycle=xtb_maxcycle,
        )
        n_energy = compute_n_reorganization_energy(
            NEnergyTermsEh(
                e0_r0=terms.e0_r0,
                em_rminus=terms.e_state_rstate,
                em_r0=terms.e_state_r0,
                e0_rminus=terms.e0_rstate,
            )
        )

        return NMoleculeResult(
            molecule=xyz_path.name,
            lambda_n_ev=n_energy.lambda_n_ev,
            anion_relax_ev=n_energy.anion_relax_ev,
            neutral_relax_ev=n_energy.neutral_relax_ev,
            xtb_total_wall_time_sec=terms.xtb_total_wall_time_sec,
            workdir=molecule_workdir if keep_workdir else None,
        )
