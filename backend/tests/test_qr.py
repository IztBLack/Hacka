"""Pruebas de la firma del QR: lo que impide la etiqueta fotocopiada."""

from __future__ import annotations

import pytest

from app.dominio.qr import (
    BYTES_FIRMA,
    FirmaInvalida,
    FormatoInvalido,
    PayloadBulto,
    firmar,
    verificar,
)

LLAVE = b"llave-de-prueba-del-cedis-32-bytes!!"
OTRA_LLAVE = b"llave-de-otro-cedis-cualquiera-xxxx"

ALFABETO_BASE32 = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")


@pytest.fixture
def payload() -> PayloadBulto:
    """El bulto del ejemplo de la propuesta."""
    return PayloadBulto(
        id_bulto="B00412",
        orden_compra="OC-88213",
        proveedor="PRV-0147",
        sucursal="SUC-14",
        sku="SKU-993201",
        cantidad=24,
        peso_kg=18.4,
        volumen_m3=0.42,
    )


def test_cadena_tiene_el_formato_del_documento(payload: PayloadBulto) -> None:
    cadena = firmar(payload, LLAVE)
    campos = cadena.split("|")

    assert len(campos) == 10
    assert campos[:9] == [
        "v1",
        "B00412",
        "OC-88213",
        "PRV-0147",
        "SUC-14",
        "SKU-993201",
        "24",
        "18.4",
        "0.42",
    ]


def test_ida_y_vuelta_devuelve_el_mismo_payload(payload: PayloadBulto) -> None:
    assert verificar(firmar(payload, LLAVE), LLAVE) == payload


def test_firma_es_base32_sin_relleno_y_en_mayusculas(payload: PayloadBulto) -> None:
    firma = firmar(payload, LLAVE).split("|")[-1]

    assert "=" not in firma
    assert firma == firma.upper()
    assert set(firma) <= ALFABETO_BASE32
    # 8 bytes en base32 son 13 caracteres (sin los 3 de relleno).
    assert len(firma) == 13
    assert BYTES_FIRMA == 8


def test_firma_es_determinista(payload: PayloadBulto) -> None:
    assert firmar(payload, LLAVE) == firmar(payload, LLAVE)


def test_un_solo_caracter_alterado_en_la_firma_se_rechaza(payload: PayloadBulto) -> None:
    cadena = firmar(payload, LLAVE)
    base, firma = cadena.rsplit("|", 1)
    # Se cambia el último carácter por otro del mismo alfabeto.
    alterada = firma[:-1] + ("A" if firma[-1] != "A" else "B")

    with pytest.raises(FirmaInvalida):
        verificar(f"{base}|{alterada}", LLAVE)


@pytest.mark.parametrize(
    "indice,valor_nuevo",
    [
        (1, "B00413"),  # otro bulto
        (5, "SKU-000001"),  # otro SKU
        (6, "25"),  # una pieza más: el excedente más barato de intentar
        (7, "180.4"),  # diez veces el peso
        (4, "SUC-99"),  # desvío a otra sucursal
    ],
    ids=["bulto", "sku", "cantidad", "peso", "sucursal"],
)
def test_alterar_un_dato_conservando_la_firma_se_rechaza(
    payload: PayloadBulto, indice: int, valor_nuevo: str
) -> None:
    campos = firmar(payload, LLAVE).split("|")
    campos[indice] = valor_nuevo

    with pytest.raises(FirmaInvalida):
        verificar("|".join(campos), LLAVE)


def test_etiqueta_de_otra_llave_se_rechaza(payload: PayloadBulto) -> None:
    """Una etiqueta emitida fuera del sistema (otro HMAC) no entra."""
    with pytest.raises(FirmaInvalida):
        verificar(firmar(payload, OTRA_LLAVE), LLAVE)


@pytest.mark.parametrize(
    "cadena",
    [
        "",
        "basura",
        "v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42",  # falta firma
        "v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42|AB|EXTRA",
        "v2|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42|ABCDEFGHIJKLM",
        "v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|x|18.4|0.42|ABCDEFGHIJKLM",
        "v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|0|18.4|0.42|ABCDEFGHIJKLM",
        "v1|B00412|OC-88213|PRV-0147|SUC-14|SKU-993201|24|18.4|0.42|",
    ],
    ids=[
        "vacia",
        "sin-separadores",
        "nueve-campos",
        "once-campos",
        "version-no-soportada",
        "cantidad-no-numerica",
        "cantidad-cero",
        "firma-vacia",
    ],
)
def test_formato_invalido_no_se_confunde_con_firma_invalida(cadena: str) -> None:
    """Distinguirlos importa: uno es etiqueta rota, el otro es fraude."""
    with pytest.raises(FormatoInvalido):
        verificar(cadena, LLAVE)


def test_decimales_equivalentes_producen_la_misma_firma() -> None:
    """18.40 y 18.4 son el mismo peso: no pueden dar firmas distintas."""
    uno = PayloadBulto("B1", "OC-1", "PRV-1", "SUC-1", "SKU-1", 1, 18.40, 0.420)
    otro = PayloadBulto("B1", "OC-1", "PRV-1", "SUC-1", "SKU-1", 1, 18.4, 0.42)

    assert firmar(uno, LLAVE) == firmar(otro, LLAVE)


def test_cantidad_negativa_no_construye_payload() -> None:
    with pytest.raises(ValueError):
        PayloadBulto("B1", "OC-1", "PRV-1", "SUC-1", "SKU-1", -1, 1.0, 0.1)


def test_separador_en_un_campo_no_construye_payload() -> None:
    """Si un dato trajera '|' podría inyectar campos falsos en la cadena."""
    with pytest.raises(ValueError):
        PayloadBulto("B1|B2", "OC-1", "PRV-1", "SUC-1", "SKU-1", 1, 1.0, 0.1)


def test_llave_vacia_no_firma(payload: PayloadBulto) -> None:
    with pytest.raises(ValueError):
        firmar(payload, b"")
