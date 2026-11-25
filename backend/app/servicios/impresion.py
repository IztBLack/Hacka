"""Generación de etiquetas ZPL y documentos imprimibles.

El ZPL se genera aquí, en el backend, no en el driver de la impresora: así la
etiqueta sale idéntica desde el portal del proveedor, desde el kiosco de la
caseta y desde la reimpresión en recibo.

La conversión a PDF usa Playwright headless (HTML -> PDF). Este módulo entrega
el HTML listo y deja la conversión al adaptador que corre con el navegador
instalado; si no está, lo dice en claro en lugar de devolver un PDF vacío.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from app.dominio.qr import PayloadBulto

__all__ = [
    "ErrorImpresion",
    "generar_zpl_etiqueta",
    "generar_html_etiqueta",
    "generar_html_relacion_embarque",
    "html_a_pdf",
]

# Etiqueta 4x6" a 203 dpi (Zebra ZT411): 812 x 1218 puntos.
PUNTOS_POR_PULGADA = 203
ANCHO_ETIQUETA = 4 * PUNTOS_POR_PULGADA
ALTO_ETIQUETA = 6 * PUNTOS_POR_PULGADA


class ErrorImpresion(RuntimeError):
    """No se pudo generar el documento solicitado."""


def generar_zpl_etiqueta(
    payload: PayloadBulto, cadena_qr: str, folio_reimpresion: str | None = None
) -> str:
    """ZPL II de la etiqueta 4x6 con QR versión 7 y corrección nivel M.

    `^BQN,2,10,M` = QR modelo 2, factor de magnificación 10 (módulo ~0.5 mm a
    203 dpi) y corrección M, que es lo que permite leer a 30-40 cm con el
    motor SE4710 incluso con la etiqueta algo sucia.
    """
    marca_reimpresion = ""
    if folio_reimpresion:
        # La reimpresión se marca en la etiqueta: nadie puede alegar que no sabía.
        marca_reimpresion = (
            f"^FO30,1120^A0N,28,28^FDREIMPRESION {folio_reimpresion}^FS\n"
        )

    return (
        "^XA\n"
        f"^PW{ANCHO_ETIQUETA}^LL{ALTO_ETIQUETA}^LH0,0^CI28\n"
        f"^FO30,30^A0N,70,70^FD{payload.sucursal}^FS\n"
        f"^FO30,110^A0N,40,40^FDBulto {payload.id_bulto}^FS\n"
        f"^FO30,160^A0N,34,34^FD{payload.orden_compra}  {payload.proveedor}^FS\n"
        f"^FO30,210^A0N,34,34^FDSKU {payload.sku}^FS\n"
        f"^FO30,255^A0N,50,50^FDCANT {payload.cantidad}^FS\n"
        f"^FO30,315^A0N,30,30^FD{payload.peso_kg} kg   {payload.volumen_m3} m3^FS\n"
        f"^FO120,380^BQN,2,10,M^FDLM,{cadena_qr}^FS\n"
        f"{marca_reimpresion}"
        f"^FO30,1160^A0N,24,24^FD{cadena_qr[:60]}^FS\n"
        "^XZ\n"
    )


def generar_html_etiqueta(payload: PayloadBulto, cadena_qr: str) -> str:
    """HTML de la etiqueta para la vista previa del portal y para el PDF."""
    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        "<style>@page{size:4in 6in;margin:0}"
        "body{font:14px/1.4 system-ui;margin:0;padding:12px}"
        ".suc{font-size:42px;font-weight:700}.qr{margin-top:12px;font:11px monospace;"
        "word-break:break-all}</style></head><body>"
        f"<div class=\"suc\">{escape(payload.sucursal)}</div>"
        f"<div>Bulto <b>{escape(payload.id_bulto)}</b></div>"
        f"<div>{escape(payload.orden_compra)} &middot; {escape(payload.proveedor)}</div>"
        f"<div>SKU {escape(payload.sku)}</div>"
        f"<div style=\"font-size:28px\">CANT {payload.cantidad}</div>"
        f"<div>{payload.peso_kg} kg &middot; {payload.volumen_m3} m&sup3;</div>"
        f"<div class=\"qr\">{escape(cadena_qr)}</div>"
        "</body></html>"
    )


def generar_html_relacion_embarque(
    folio: str,
    sucursal: str,
    clase_unidad: str,
    tarimas: list[str],
    peso_kg: float,
    volumen_m3: float,
    ocupacion: float,
    qr_maestro: str,
    sello_seguridad: str | None,
    km_salida: int | None,
    operador: str | None,
    generado_en: datetime | None = None,
) -> str:
    """Relación de Embarque: el documento que viaja con la unidad.

    Lleva sello de seguridad y kilometraje de salida, que la v1 omitía y son
    control antirrobo básico.
    """
    momento = generado_en or datetime.now()
    filas = "".join(f"<tr><td>{i}</td><td>{escape(t)}</td></tr>" for i, t in enumerate(tarimas, 1))
    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        f"<title>Relacion de Embarque {escape(folio)}</title>"
        "<style>body{font:12px/1.5 system-ui;padding:24px}"
        "table{border-collapse:collapse;width:100%;margin-top:12px}"
        "td,th{border:1px solid #999;padding:4px 6px;text-align:left}"
        ".firma{margin-top:48px;border-top:1px solid #000;width:260px}</style>"
        "</head><body>"
        f"<h1>Relacion de Embarque {escape(folio)}</h1>"
        f"<p><b>Sucursal:</b> {escape(sucursal)} &middot; "
        f"<b>Unidad:</b> {escape(clase_unidad)} &middot; "
        f"<b>Ocupacion:</b> {ocupacion * 100:.1f}%</p>"
        f"<p><b>Tarimas:</b> {len(tarimas)} &middot; <b>Peso:</b> {peso_kg:.0f} kg "
        f"&middot; <b>Volumen:</b> {volumen_m3:.2f} m&sup3;</p>"
        f"<p><b>Sello de seguridad:</b> {escape(sello_seguridad or 'PENDIENTE')} &middot; "
        f"<b>Km de salida:</b> {km_salida if km_salida is not None else 'PENDIENTE'}</p>"
        f"<p><b>Generado:</b> {momento:%Y-%m-%d %H:%M}</p>"
        f"<table><thead><tr><th>#</th><th>Folio de tarima</th></tr></thead>"
        f"<tbody>{filas}</tbody></table>"
        f"<p style=\"font:11px monospace;word-break:break-all\">QR maestro: "
        f"{escape(qr_maestro)}</p>"
        f"<div class=\"firma\">{escape(operador or '')}<br>Firma del operador</div>"
        "</body></html>"
    )


def html_a_pdf(html: str) -> bytes:
    """Convierte HTML a PDF con Playwright headless.

    Adaptador aislado a propósito: es la única parte del backend que necesita
    un navegador instalado (`playwright install chromium`). Si no está, falla
    con un mensaje claro en lugar de entregar un PDF corrupto.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ErrorImpresion(
            "Playwright no está instalado: ejecute "
            "'pip install playwright && playwright install chromium'"
        ) from exc

    with sync_playwright() as p:  # pragma: no cover - requiere navegador
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page()
            pagina.set_content(html, wait_until="load")
            return pagina.pdf(print_background=True)
        finally:
            navegador.close()
