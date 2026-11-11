"""
Generador de Documento Oficial de Conocimiento RAG — CEL RED (Tienda de Celulares y Accesorios)
Crea el manual comercial y catálogo oficial de precios y obsequios en PDF (`catalogo_y_politicas_celred.pdf`)
para su indexación semántica en PostgreSQL + pgvector (`celred_db`), sin requerir librerías externas.
"""

import os


def _build_minimal_pdf(lines: list[str]) -> bytes:
    """Construye un archivo PDF 1.4 estándar válido con las líneas de texto comerciales de Cel Red."""
    stream_lines = ["BT", "/F1 9 Tf", "45 750 Td", "13 TL"]
    for line in lines:
        safe = (
            line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )
        stream_lines.append(f"({safe}) '")
    stream_lines.append("ET")
    content_bytes = "\n".join(stream_lines).encode("latin-1")

    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode("latin-1") + content_bytes + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for obj in objs:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets:
        pdf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1")
    )
    return bytes(pdf)


def generate_celred_pdf():
    data_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(data_dir, "catalogo_y_politicas_celred.pdf")

    # Eliminar cualquier PDF antiguo de otros proyectos si existiera
    old_pdf = os.path.join(data_dir, "protocolos_emergencia.pdf")
    if os.path.exists(old_pdf):
        try:
            os.remove(old_pdf)
        except Exception:
            pass

    lineas = [
        "CATALOGO OFICIAL DE PRECIOS DE CONTADO Y OBSEQUIOS - TIENDA CEL RED",
        "",
        "1. POLITICA COMERCIAL DE EQUIPOS APPLE (DESDE IPHONE 13 EN ADELANTE):",
        "En Cel Red comercializamos equipos iPhone unicamente desde el iPhone 13 en adelante (se omiten iPhone 11 y 12).",
        "Manejamos dos lineas oficiales: Equipos Nuevos (Activos / Sellados) y Equipos Open Box (Seminuevos Garantizados).",
        "Los equipos Open Box son seminuevos verificados tecnica y esteticamente, por lo que su valor de contado es menor.",
        "",
        "2. TABLA OFICIAL DE OBSEQUIOS Y COMBOS POR COMPRA DE IPHONE:",
        "- iPhone 13 de 128GB ($1.150.000 Open Box / $1.840.000 Nuevo): Incluye de obsequio ESTUCHE Y VIDRIO.",
        "- iPhone 13 Pro Max 128GB ($1.890.000 Open Box): Incluye COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "- iPhone 14 Pro 128GB ($1.820.000 Open Box): Incluye COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "- iPhone 14 Pro Max 128GB ($1.980.000 Open Box): Incluye COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "- iPhone 15 de 128GB ($1.790.000 Open Box / $2.200.000 Nuevo): Incluye COMBO 2 o COMBO 3 (AirPods).",
        "- iPhone 15 Pro de 128GB ($2.050.000 Open Box): Incluye COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods).",
        "- iPhone 15 Pro Max de 256GB ($2.530.000 Open Box): Incluye COMBO 2 o COMBO 3 (AirPods).",
        "- iPhone 16 de 128GB ($2.180.000 Open Box / $2.600.000 Nuevo): Incluye COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods).",
        "- iPhone 16 Pro 128GB ($2.580.000 Open Box): Incluye COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche).",
        "- iPhone 16 Pro 256GB ($2.650.000 Open Box): Incluye COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche).",
        "- iPhone 16 Pro Max 256GB ($2.950.000 Open Box): Incluye COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche).",
        "",
        "3. RESUMEN DE PRECIOS ANDROID NUEVOS DE CONTADO (29 REFERENCIAS):",
        "- Samsung: A05 128/4 ($350.000), A07 128/6 ($470.000), A17 256/8 ($720.000), A37 5G 256/8 ($1.160.000), A57 5G ($1.990.000),",
        "  S25 Ultra 256/12 ($2.980.000), S25 Ultra 512/12 ($3.300.000), S26 Ultra 256/12 ($3.340.000), S26 Ultra 512/12 ($3.800.000).",
        "- Xiaomi Redmi y POCO: Redmi A5 ($350.000), Redmi A7 Pro ($460.000), Redmi 15C ($620.000), Redmi 17 ($670.000), Redmi 15 ($680.000),",
        "  Note 17 256/6 ($750.000), Note 15 ($780.000), Note 17 256/8 ($820.000), Note 15 Pro ($970.000),",
        "  POCO F8 Pro 256/12 ($1.860.000), POCO X8 Pro Max 512/12 ($1.960.000).",
        "- Tecno, Infinix, Oppo, Honor e Itel: Tecno Spark Go2 ($360.000), Itel A100C ($370.000), Spark Go3 ($420.000),",
        "  Oppo A5X ($510.000), Spark 40 ($550.000), Infinix Hot 70 ($675.000), Spark 50 ($690.000), Honor 400 Smart ($700.000),",
        "  Infinix Hot 60 Pro Plus ($870.000), Oppo A80 5G ($910.000), Infinix Note Edge ($1.020.000), Tecno Pova Curve 2 ($1.040.000),",
        "  Tecno Camon 50 Pro ($1.250.000), Tecno Camon 50 Ultra ($1.280.000).",
        "",
        "4. SISTEMA DE SEPARADOS, FINANCIACION Y GARANTIAS CEL RED:",
        "- Plan Separado: Abono inicial minimo del 20%, congela el precio y reserva el IMEI hasta por 45 dias sin intereses.",
        "- Plataformas de Credito: Addi, Sistecredito, Banco de Bogota, Krediya (inicial 20%/30%), Credimovil (inicial 10%/15%) y Renting iPhone.",
        "- Garantia: 12 meses en equipos Nuevos y 6 meses en equipos Open Box Seminuevos con factura legal en SysCafe.",
        "",
        "5. DIRECTORIO OFICIAL DE LAS 14 SEDES DE CEL RED:",
        "- 1. Puerto Asis / Putumayo: CALLE 10 NO 24 - 18 BARRIO EL CARMEN",
        "- 2. Mocoa / Putumayo: CRA 9 # 10 - 30 AVENIDA COLOMBIA",
        "- 3. La Hormiga - Valle del Guamuez: BARRIO CENTRAL LAS AMERICAS CARRERA 5 - #7-16 A UN COSTADO DE LA ALCALDIA MUNICIPAL",
        "- 4. Orito / Putumayo: CALLE 8 # 10 - 47 BARRIO MARCO FIDEL SUAREZ AL LADO DE DISTRISUR",
        "- 5, 6 y 7. Ipiales / Narino: CRA 6 NO 13-05 ESQUINA ED MARKUS | CRA 6 NO 11-51 CC ZAFIRO LOCAL 123 | CRA 7 NO 9-56 CC VICTORIA PLAZA LOCAL 101A",
        "- 8, 9 y 10. Pasto / Narino: CALLE 16 NO 23-82 LOCAL 1 CENTRO | CALLE 17 # 26-60 CC PASAJE EL LICEO LOCAL 103 | CC SEBASTIAN DE BELALCAZAR LOCAL 6A",
        "- 11. Tuquerres / Narino: CRA 14 - CLL 20 ESQUINA - TUQUERRES",
        "- 12. Medellin / Antioquia: CENTRO COMERCIAL PREMIUM PLAZA LOCAL 1301",
        "- 13. Neiva / Huila: CRA.2 # 6 - 26 - LOCAL 5 - CENTRO",
        "- 14. La Union / Narino: CRA 1 # 11- 81 - FRENTE AL PARQUE CUEVAS LEIVA",
    ]

    pdf_bytes = _build_minimal_pdf(lineas)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"[OK] PDF comercial oficial de Cel Red generado en: {pdf_path}")


if __name__ == "__main__":
    generate_celred_pdf()
