# rcal-xtb

`rcal-xtb` is a command-line tool that runs [xTB](https://github.com/grimme-lab/xtb) from Python and computes **P-type (hole)** and **N-type (electron)** reorganization energies from XYZ geometries.

## Features

- Runs xTB via Python `subprocess`
- Uses `GFN2-xTB` and `--opt tight`
- Supports g-xTB via a modified `xtb` binary with `--gxtb`
- Computes strict 4-point `lambda_p` and `lambda_n`
- Writes results to CSV (eV)
- Accepts one XYZ input per run with a simple `--input` option
- Supports `--mode p|n` (`p` is the default)
- Can keep per-step xTB logs/workdirs for inspection

## Requirements

- Python `>=3.10`
- [uv](https://docs.astral.sh/uv/)
- **xTB installed separately** (this repository does not bundle xTB)
- **g-xTB installed separately** if using `--engine gxtb`

Install xTB using the official project resources:

- xTB GitHub repository: <https://github.com/grimme-lab/xtb>

This README assumes `xtb` is already available in your `PATH`.
For g-xTB, this project expects the g-xTB environment to provide a modified
`xtb` binary that accepts `--gxtb`.

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
  --engine gfn2 \
  --mode p \
  --input "mols/AN3.xyz" \
  --output-csv "results/lambda_p_ev.csv"
```

Run with g-xTB:

```bash
uv run rcal-xtb \
  --engine gxtb \
  --mode p \
  --input "mols/AN3.xyz" \
  --output-csv "results/gxtb/AN3_p.csv" \
  --keep-workdir \
  --work-root "output/gxtb/AN3"
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

- `--engine`: xTB engine (`gfn2` or `gxtb`, default: `gfn2`)
- `--mode`: Reorganization mode (`p` or `n`, default: `p`)
- `--input`: Path to a single input XYZ file (required)
- `--output-csv`: Output CSV path (default: `results/lambda_p_ev.csv` / `results/lambda_n_ev.csv` for `gfn2`, `results/gxtb/lambda_p_ev.csv` / `results/gxtb/lambda_n_ev.csv` for `gxtb`)
- `--keep-workdir`: Keep per-molecule temporary work directories
- `--work-root`: Optional root directory for temporary work directories
- `--xtb-maxcycle`: Optional xTB optimization max cycles (`--cycles INT`) for geometry optimization steps

## Output format

Mode `p` CSV columns:

- `molecule`
- `engine`
- `lambda_p_ev`
- `cation_relax_ev`
- `neutral_relax_ev`
- `xtb_total_wall_time_sec` (sum of xTB `total wall-time` over 4 steps, in seconds)
- `status` (`ok` or `failed`)
- `error`

Mode `n` CSV columns:

- `molecule`
- `engine`
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

## Benchmark: Comparison with Literature

The following tables compare reorganization energies computed by `rcal-xtb`
(GFN2-xTB and g-xTB / `--opt tight` / strict 4-point) with literature values from
R. Flores *et al.*, *Theor. Chem. Acc.* **2025**, 144, 37.
([DOI: 10.1007/s00214-025-03187-4](https://doi.org/10.1007/s00214-025-03187-4)).

Detailed computed results are available in:

- [results/benchmark_gfn2_gxtb.csv](results/benchmark_gfn2_gxtb.csv)
- [results/gxtb/](results/gxtb/)
- [results/gfn2/](results/gfn2/)

### Experimental cation reorganization energies λ+ vs computed λ_p (meV)

Note: Experimental values are λ+ (cation relaxation component only), while
computed λ_p is the total reorganization energy (λ+ + λ0).

| Molecule | Exp. λ+ (meV) | GFN2-xTB λ_p (meV) | g-xTB λ_p (meV) |
| -------- | ------------: | ------------------: | ---------------: |
| AN3      |          69.7 |              1045.8 |            205.0 |
| TTA      |          58.8 |              1158.7 |            193.5 |
| PEN      |    49.6 ; 44  |               449.6 |            188.2 |
| PFP      |   124 ; 112   |               706.4 |            416.7 |
| TL85     |           720 |               639.0 |            457.5 |

### Theoretical total reorganization energy λ vs computed λ_p (meV)

| Molecule | QD-NEVPT2/cc-pVTZ | OO-RI-SCS-MP2/cc-pVTZ | IP-EOM-CCSD/cc-pVDZ | GFN2-xTB | g-xTB |
| -------- | ----------------: | ---------------------: | ------------------: | -------: | ----: |
| TL85     |             781.8 |                  690.5 |                   — |    639.0 | 457.5 |
| PhNMe₂   |             346.5 |                  348.9 |                   — |    785.7 | 402.3 |
| PhCOH    |             325.6 |                  233.9 |                   — |   1337.6 | 175.6 |
| RBH₂     |             524.3 |                  560.6 |                 440 |   1057.9 | 658.4 |
| RCOH     |             558.7 |                  568.0 |                 450 |    903.1 | 676.4 |
| RCN      |             534.6 |                  544.0 |                 420 |    869.7 | 664.2 |

## References

- R. Flores *et al.*, *Theor. Chem. Acc.* **2025**, 144, 37.
  [DOI: 10.1007/s00214-025-03187-4](https://doi.org/10.1007/s00214-025-03187-4)
- xTB GitHub: <https://github.com/grimme-lab/xtb>
- g-xTB GitHub: <https://github.com/grimme-lab/g-xtb>
- xTB documentation: <https://xtb-docs.readthedocs.io/>
- uv documentation: <https://docs.astral.sh/uv/>
