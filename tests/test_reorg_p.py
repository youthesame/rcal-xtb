from __future__ import annotations

import pytest

from rcal_xtb.reorg_p import (
    HARTREE_TO_EV,
    PEnergyTermsEh,
    compute_p_reorganization_energy,
)


def test_compute_p_reorganization_energy() -> None:
    terms = PEnergyTermsEh(
        e0_r0=-10.0,
        ep_rplus=-9.7,
        ep_r0=-9.6,
        e0_rplus=-9.8,
    )

    result = compute_p_reorganization_energy(terms)

    assert result.cation_relax_eh == pytest.approx(0.1)
    assert result.neutral_relax_eh == pytest.approx(0.2)
    assert result.lambda_p_eh == pytest.approx(0.3)
    assert result.lambda_p_ev == pytest.approx(0.3 * HARTREE_TO_EV)


def test_compute_p_reorganization_energy_ev_components() -> None:
    terms = PEnergyTermsEh(
        e0_r0=-100.0,
        ep_rplus=-99.5,
        ep_r0=-99.45,
        e0_rplus=-99.9,
    )

    result = compute_p_reorganization_energy(terms)

    assert result.cation_relax_ev == pytest.approx(
        (terms.ep_r0 - terms.ep_rplus) * HARTREE_TO_EV
    )
    assert result.neutral_relax_ev == pytest.approx(
        (terms.e0_rplus - terms.e0_r0) * HARTREE_TO_EV
    )
