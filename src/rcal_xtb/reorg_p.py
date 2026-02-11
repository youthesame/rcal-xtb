"""P-type (hole/cation) reorganization-energy formulas.

This module defines energy-term containers and computes strict 4-point
P-type reorganization energies in Hartree and eV.
"""

from __future__ import annotations

from dataclasses import dataclass

HARTREE_TO_EV = 27.211386245988


@dataclass(frozen=True)
class PEnergyTermsEh:
    """Input energy terms for strict 4-point P-type calculation.

    Parameters
    ----------
    e0_r0 : float
        Neutral-state energy at neutral optimized geometry, ``E0(R0)`` in Eh.
    ep_rplus : float
        Cation-state energy at cation optimized geometry, ``E+(R+)`` in Eh.
    ep_r0 : float
        Cation-state energy at neutral optimized geometry, ``E+(R0)`` in Eh.
    e0_rplus : float
        Neutral-state energy at cation optimized geometry, ``E0(R+)`` in Eh.
    """

    e0_r0: float
    ep_rplus: float
    ep_r0: float
    e0_rplus: float


@dataclass(frozen=True)
class PReorganizationEnergy:
    """Computed P-type reorganization-energy components.

    Parameters
    ----------
    lambda_p_eh : float
        Total P-type reorganization energy in Eh.
    lambda_p_ev : float
        Total P-type reorganization energy in eV.
    cation_relax_eh : float
        Cation relaxation component in Eh, ``E+(R0) - E+(R+)``.
    cation_relax_ev : float
        Cation relaxation component in eV.
    neutral_relax_eh : float
        Neutral relaxation component in Eh, ``E0(R+) - E0(R0)``.
    neutral_relax_ev : float
        Neutral relaxation component in eV.
    """

    lambda_p_eh: float
    lambda_p_ev: float
    cation_relax_eh: float
    cation_relax_ev: float
    neutral_relax_eh: float
    neutral_relax_ev: float


def compute_p_reorganization_energy(terms: PEnergyTermsEh) -> PReorganizationEnergy:
    """Compute strict 4-point P-type reorganization energy.

    Parameters
    ----------
    terms : PEnergyTermsEh
        Input energies for ``R0`` and ``R+`` geometries.

    Returns
    -------
    PReorganizationEnergy
        Total and component energies in both Eh and eV.
    """
    cation_relax_eh = terms.ep_r0 - terms.ep_rplus
    neutral_relax_eh = terms.e0_rplus - terms.e0_r0
    lambda_p_eh = cation_relax_eh + neutral_relax_eh

    return PReorganizationEnergy(
        lambda_p_eh=lambda_p_eh,
        lambda_p_ev=lambda_p_eh * HARTREE_TO_EV,
        cation_relax_eh=cation_relax_eh,
        cation_relax_ev=cation_relax_eh * HARTREE_TO_EV,
        neutral_relax_eh=neutral_relax_eh,
        neutral_relax_ev=neutral_relax_eh * HARTREE_TO_EV,
    )
