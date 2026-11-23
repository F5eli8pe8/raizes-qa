from datetime import date

import pytest

from app.domain.cupom import Cupom
from app.domain.erros import CupomInvalido

HOJE = date(2026, 11, 20)


@pytest.mark.unit
def test_cupom_valido_aplica_o_desconto_percentual():
    cupom = Cupom("PROMO10", percentual=10, validade=date(2026, 12, 31))
    assert cupom.desconto_sobre(5000, "recife-centro", HOJE) == 500


@pytest.mark.unit
def test_cupom_vale_no_ultimo_dia_de_validade():
    cupom = Cupom("PROMO10", percentual=10, validade=HOJE)
    assert cupom.desconto_sobre(5000, "recife-centro", HOJE) == 500


@pytest.mark.unit
def test_ct10_cupom_expirado_e_rejeitado():
    cupom = Cupom("PROMO10", percentual=10, validade=date(2026, 11, 19))
    with pytest.raises(CupomInvalido, match="Cupom inválido ou expirado."):
        cupom.desconto_sobre(5000, "recife-centro", HOJE)


@pytest.mark.unit
def test_ct10_cupom_de_outra_unidade_e_rejeitado():
    cupom = Cupom(
        "SALVADOR5", percentual=5, validade=date(2026, 12, 31), unidade_id="salvador-pituba"
    )
    with pytest.raises(CupomInvalido, match="Cupom inválido ou expirado."):
        cupom.desconto_sobre(5000, "recife-centro", HOJE)


@pytest.mark.unit
def test_desconto_e_arredondado_para_baixo_em_centavos():
    cupom = Cupom("PROMO10", percentual=10, validade=date(2026, 12, 31))
    assert cupom.desconto_sobre(1999, "recife-centro", HOJE) == 199


@pytest.mark.unit
@pytest.mark.parametrize("percentual", [0, 101])
def test_percentual_fora_do_intervalo_e_rejeitado(percentual):
    with pytest.raises(ValueError):
        Cupom("X", percentual=percentual, validade=date(2026, 12, 31))