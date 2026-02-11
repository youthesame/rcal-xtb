"""N-type (electron/anion) reorganization-energy formulas.

This module defines energy-term containers and computes strict 4-point
N-type reorganization energies in Hartree and eV.
"""

from __future__ import annotations

from dataclasses import dataclass

from rcal_xtb.reorg_p import HARTREE_TO_EV


@dataclass(frozen=True)
class NEnergyTermsEh:
    """Input energy terms for strict 4-point N-type calculation.

    Parameters
    ----------
    e0_r0 : float
        Neutral-state energy at neutral optimized geometry, ``E0(R0)`` in Eh.
    em_rminus : float
        Anion-state energy at anion optimized geometry, ``E-(R-)`` in Eh.
    em_r0 : float
        Anion-state energy at neutral optimized geometry, ``E-(R0)`` in Eh.
    e0_rminus : float
        Neutral-state energy at anion optimized geometry, ``E0(R-)`` in Eh.
    """

    e0_r0: float
    em_rminus: float
    em_r0: float
    e0_rminus: float


@dataclass(frozen=True)
class NReorganizationEnergy:
    """Computed N-type reorganization-energy components.

    Parameters
    ----------
    lambda_n_eh : float
        Total N-type reorganization energy in Eh.
    lambda_n_ev : float
        Total N-type reorganization energy in eV.
    anion_relax_eh : float
        Anion relaxation component in Eh, ``E-(R0) - E-(R-)``.
    anion_relax_ev : float
        Anion relaxation component in eV.
    neutral_relax_eh : float
        Neutral relaxation component in Eh, ``E0(R-) - E0(R0)``.
    neutral_relax_ev : float
        Neutral relaxation component in eV.
    """

    lambda_n_eh: float
    lambda_n_ev: float
    anion_relax_eh: float
    anion_relax_ev: float
    neutral_relax_eh: float
    neutral_relax_ev: float


def compute_n_reorganization_energy(terms: NEnergyTermsEh) -> NReorganizationEnergy:
    """Compute strict 4-point N-type reorganization energy.

    Parameters
    ----------
    terms : NEnergyTermsEh
        Input energies for ``R0`` and ``R-`` geometries.

    Returns
    -------
    NReorganizationEnergy
        Total and component energies in both Eh and eV.
    """
    anion_relax_eh = terms.em_r0 - terms.em_rminus
    neutral_relax_eh = terms.e0_rminus - terms.e0_r0
    lambda_n_eh = anion_relax_eh + neutral_relax_eh

    return NReorganizationEnergy(
        lambda_n_eh=lambda_n_eh,
        lambda_n_ev=lambda_n_eh * HARTREE_TO_EV,
        anion_relax_eh=anion_relax_eh,
        anion_relax_ev=anion_relax_eh * HARTREE_TO_EV,
        neutral_relax_eh=neutral_relax_eh,
        neutral_relax_ev=neutral_relax_eh * HARTREE_TO_EV,
    )
