"""Reparto de piezas en bultos (dominio puro)."""

from app.dominio.desglose import LineaPendiente, planear_desglose

SUCS = ["SUC-01", "SUC-02", "SUC-03"]


def test_las_piezas_cuadran_exacto_por_sku():
    lineas = [LineaPendiente("A", "a", 480), LineaPendiente("B", "b", 240)]
    plan = planear_desglose(lineas, 148, SUCS)
    assert len(plan) == 148
    assert sum(b.piezas for b in plan if b.sku == "A") == 480
    assert sum(b.piezas for b in plan if b.sku == "B") == 240
    assert all(b.piezas > 0 for b in plan)


def test_reparto_proporcional_y_un_sku_por_bulto():
    plan = planear_desglose(
        [LineaPendiente("A", "a", 300), LineaPendiente("B", "b", 100)], 40, SUCS
    )
    assert sum(1 for b in plan if b.sku == "A") == 30
    assert sum(1 for b in plan if b.sku == "B") == 10


def test_cada_linea_recibe_al_menos_un_bulto():
    plan = planear_desglose(
        [LineaPendiente("A", "a", 1000), LineaPendiente("B", "b", 1)], 2, SUCS
    )
    assert {b.sku for b in plan} == {"A", "B"}


def test_no_hay_mas_bultos_que_piezas():
    plan = planear_desglose([LineaPendiente("A", "a", 5)], 50, SUCS)
    assert len(plan) == 5
    assert all(b.piezas == 1 for b in plan)


def test_sucursal_rota_y_secuencia_consecutiva():
    plan = planear_desglose([LineaPendiente("A", "a", 10)], 5, SUCS)
    assert [b.sucursal for b in plan] == ["SUC-01", "SUC-02", "SUC-03", "SUC-01", "SUC-02"]
    assert [b.secuencia for b in plan] == [1, 2, 3, 4, 5]


def test_sin_pendiente_no_hay_bultos():
    assert planear_desglose([LineaPendiente("A", "a", 0)], 10, SUCS) == []
    assert planear_desglose([LineaPendiente("A", "a", 10)], 10, []) == []
