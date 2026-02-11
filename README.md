# rcal-xtb

`rcal-xtb` is a command-line tool that runs [xTB](https://github.com/grimme-lab/xtb) from Python and computes **P-type (hole)** and **N-type (electron)** reorganization energies from XYZ geometries.

## Features

- Runs xTB via Python `subprocess`
- Uses `GFN2-xTB` and `--opt tight`
- Computes strict 4-point `lambda_p` and `lambda_n`
- Writes results to CSV (eV)
- Accepts one XYZ input per run with a simple `--input` option
- Supports `--mode p|n` (`p` is the default)
- Can keep per-step xTB logs/workdirs for inspection

## Requirements

- Python `>=3.10`
- [uv](https://docs.astral.sh/uv/)
- **xTB installed separately** (this repository does not bundle xTB)

Install xTB using the official project resources:

- xTB GitHub repository: <https://github.com/grimme-lab/xtb>

This README assumes `xtb` is already available in your `PATH`.

## Installation (dev/local)

```bash
git clone <your-fork-or-repo-url>
cd rcal-xtb
uv sync
```

## Usage

### Recommended: run directly from GitHub with `uvx`

Use this GitHub repository as the source package:

```bash
uvx --from git+https://github.com/youthesame/rcal-xtb.git rcal-xtb --help
```

Single molecule:

```bash
uvx --from git+https://github.com/youthesame/rcal-xtb.git rcal-xtb \
  --mode p \
  --input "mols/AN3.xyz" \
  --output-csv "results/an3_lambda_p_ev.csv"
```

Single molecule (N-type):

```bash
uvx --from git+https://github.com/youthesame/rcal-xtb.git rcal-xtb \
  --mode n \
  --input "mols/AN3.xyz" \
  --output-csv "results/an3_lambda_n_ev.csv"
```

Multiple molecules (shell loop; one file per run, P-type):

```bash
for f in mols/*.xyz; do
  name=$(basename "$f" .xyz)
  uvx --from git+https://github.com/youthesame/rcal-xtb.git rcal-xtb \
    --mode p \
    --input "$f" \
    --output-csv "results/${name}_lambda_p_ev.csv"
done
```

### Alternative: run from a local checkout with `uv run`

```bash
uv run rcal-xtb --help
```

```bash
uv run rcal-xtb \
  --mode p \
  --input "mols/AN3.xyz" \
  --output-csv "results/lambda_p_ev.csv"
```

## Keeping xTB logs and intermediate files

By default, temporary working directories are removed.
To keep xTB step logs and intermediate structures:

```bash
uvx --from git+https://github.com/youthesame/rcal-xtb.git rcal-xtb \
  --mode p \
  --input "mols/AN3.xyz" \
  --output-csv "results/an3_lambda_p_ev.csv" \
  --keep-workdir \
  --work-root "output/AN3"
```
This repository is currently private, so GitHub authentication/authorization is required to execute the command successfully.

This keeps files under `output/AN3/<generated-workdir>/...`, including per-step `stdout.log` and `stderr.log`.

## CLI options

- `--mode`: Reorganization mode (`p` or `n`, default: `p`)
- `--input`: Path to a single input XYZ file (required)
- `--output-csv`: Output CSV path (default: `results/lambda_p_ev.csv` for mode `p`, `results/lambda_n_ev.csv` for mode `n`)
- `--keep-workdir`: Keep per-molecule temporary work directories
- `--work-root`: Optional root directory for temporary work directories
- `--xtb-maxcycle`: Optional xTB optimization max cycles (`--cycles INT`) for geometry optimization steps

## Output format

Mode `p` CSV columns:

- `molecule`
- `lambda_p_ev`
- `cation_relax_ev`
- `neutral_relax_ev`
- `xtb_total_wall_time_sec` (sum of xTB `total wall-time` over 4 steps, in seconds)
- `status` (`ok` or `failed`)
- `error`

Mode `n` CSV columns:

- `molecule`
- `lambda_n_ev`
- `anion_relax_ev`
- `neutral_relax_ev`
- `xtb_total_wall_time_sec` (sum of xTB `total wall-time` over 4 steps, in seconds)
- `status` (`ok` or `failed`)
- `error`

Exit code:

- `0`: run succeeded
- `1`: run failed, or xTB availability check failed

## Method (strict 4-point)

P-type uses:

- `R0`: optimized neutral geometry
- `R+`: optimized cation geometry
- `E0(Rx)`: neutral energy at geometry `Rx`
- `E+(Rx)`: cation energy at geometry `Rx`

Formula:

```text
lambda_p = [E+(R0) - E+(R+)] + [E0(R+) - E0(R0)]
```

N-type uses:

- `R0`: optimized neutral geometry
- `R-`: optimized anion geometry
- `E0(Rx)`: neutral energy at geometry `Rx`
- `E-(Rx)`: anion energy at geometry `Rx`

Formula:

```text
lambda_n = [E-(R0) - E-(R-)] + [E0(R-) - E0(R0)]
```

Internal energy is handled in Hartree and exported as eV.

## Development

Run checks:

```bash
uv sync
.venv/bin/ruff check .
.venv/bin/pytest -q
```

## References

- xTB GitHub: <https://github.com/grimme-lab/xtb>
- xTB documentation: <https://xtb-docs.readthedocs.io/>
- uv documentation: <https://docs.astral.sh/uv/>
