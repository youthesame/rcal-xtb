from __future__ import annotations

import pytest

from rcal_xtb.reorg_n import (
    NEnergyTermsEh,
    compute_n_reorganization_energy,
)
from rcal_xtb.reorg_p import HARTREE_TO_EV


def test_compute_n_reorganization_energy() -> None:
    terms = NEnergyTermsEh(
        e0_r0=-10.0,
        em_rminus=-10.3,
        em_r0=-10.1,
        e0_rminus=-9.9,
    )

    result = compute_n_reorganization_energy(terms)

    assert result.anion_relax_eh == pytest.approx(0.2)
    assert result.neutral_relax_eh == pytest.approx(0.1)
    assert result.lambda_n_eh == pytest.approx(0.3)
    assert result.lambda_n_ev == pytest.approx(0.3 * HARTREE_TO_EV)


def test_compute_n_reorganization_energy_ev_components() -> None:
    terms = NEnergyTermsEh(
        e0_r0=-100.0,
        em_rminus=-100.5,
        em_r0=-100.45,
        e0_rminus=-99.9,
    )

    result = compute_n_reorganization_energy(terms)

    assert result.anion_relax_ev == pytest.approx(
        (terms.em_r0 - terms.em_rminus) * HARTREE_TO_EV
    )
    assert result.neutral_relax_ev == pytest.approx(
        (terms.e0_rminus - terms.e0_r0) * HARTREE_TO_EV
    )
