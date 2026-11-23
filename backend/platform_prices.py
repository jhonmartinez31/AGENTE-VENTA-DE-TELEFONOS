"""
Catálogo Financiero Multi-Plataforma Oficial de CEL RED (Actualización Noviembre 2026)
Contiene los precios exactos de contado, desembolso y cuotas iniciales por plataforma para Android e iPhone:
1. ADDI / SISTECRÉDITO: Precio de desembolso directo.
2. CONFIA / BANCO DE BOGOTÁ: Precio de desembolso directo.
3. KREDIYA (Android): Precio en plataforma + Cuotas Iniciales aprobadas (30%, 40%, 45%, 50%).
4. CREDIMÓVIL (Android): Precio en plataforma + Cuota Inicial al 10% y al 15%
   (Incluye PROMOCIONES DE NOVIEMBRE CREDIMÓVIL | CELRED con vigencia hasta nueva orden).
5. RENTING (Exclusivo iPhone — para clientes con poco historial crediticio o reportados):
   Valor plataforma + Cuota Inicial aprobada al 20% y al 30%.
"""

from typing import Dict, Any, Optional


def _fmt_cop(val: int) -> str:
    return f"${val:,.0f}".replace(",", ".")


# Promociones Oficiales de Noviembre Credimóvil | Cel Red (Vigencia hasta nueva orden)
PROMOCIONES_NOVIEMBRE_CREDIMOVIL = [
    {"sku": "AND-HON-400S-256", "referencia": "Honor 400 Smart (256GB / 6GB RAM)", "inicial_10": 66000, "inicial_15": 114000},
    {"sku": "AND-RED-17-256", "referencia": "Redmi 17 (256GB / 4GB RAM)", "inicial_10": 50000, "inicial_15": 90000},
    {"sku": "AND-SAM-A07-128", "referencia": "Samsung Galaxy A07 (128GB / 6GB RAM)", "inicial_10": 30000, "inicial_15": 60000},
    {"sku": "AND-SAM-A17-256", "referencia": "Samsung Galaxy A17 (256GB / 8GB RAM)", "inicial_10": 50000, "inicial_15": 70000},
    {"sku": "AND-RED-15-256", "referencia": "Redmi 15 (256GB / 8GB RAM)", "inicial_10": 50000, "inicial_15": 90000},
    {"sku": "AND-INF-HOT60PP-256", "referencia": "Infinix Hot 60 Pro Plus (256GB / 8GB RAM)", "inicial_10": 90000, "inicial_15": 150000},
    {"sku": "AND-INF-HOT70-256", "referencia": "Infinix Hot 70 (256GB / 4GB RAM)", "inicial_10": 70000, "inicial_15": 121700},
    {"sku": "AND-RED-15C-256", "referencia": "Redmi 15C (256GB / 8GB RAM)", "inicial_10": 70000, "inicial_15": 113500},
    {"sku": "AND-TEC-SP50-256", "referencia": "Tecno Spark 50 (256GB / 4GB RAM)", "inicial_10": 60000, "inicial_15": 115500},
]


# Mapa maestro indexado por SKU oficial de Cel Red
PLATAFORMAS_POR_SKU: Dict[str, Dict[str, Any]] = {
    # =================================================================
    # ANDROID NUEVOS (CONTADO + PLATAFORMAS DE CRÉDITO + PROMO NOVIEMBRE CREDIMÓVIL)
    # =================================================================
    "AND-INF-HOT70-256": {
        "contado": 675000,
        "addi_sistecredito": 1055000,
        "banco_bogota": 1055000,
        "krediya": {
            "facturar": 930000,
            "plataforma": 1150000,
            "inicial_30": 125000,
            "inicial_40": 240000,
            "inicial_45": 297500,
            "inicial_50": 355000,
        },
        "credimovil": {
            "plataforma": 950000,
            "inicial_10": 70000,
            "inicial_15": 121700,
            "promo_noviembre": True,
            "inicial_10_normal": 95000,
            "inicial_15_normal": 142500,
        },
    },
    "AND-INF-HOT60PP-256": {
        "contado": 870000,
        "addi_sistecredito": 1270000,
        "banco_bogota": 1220000,
        "krediya": {
            "facturar": 1100000,
            "plataforma": 1400000,
            "inicial_30": 120000,
            "inicial_40": 260000,
            "inicial_45": 330000,
            "inicial_50": 400000,
        },
        "credimovil": {
            "plataforma": 1130000,
            "inicial_10": 90000,
            "inicial_15": 150000,
            "promo_noviembre": True,
            "inicial_10_normal": 113000,
            "inicial_15_normal": 169500,
        },
    },
    "AND-INF-H60P-256": {
        "contado": None,
        "addi_sistecredito": 1060000,
        "banco_bogota": 1030000,
        "krediya": {
            "facturar": 875000,
            "plataforma": 1089000,
            "inicial_30": 112700,
            "inicial_40": 221600,
            "inicial_45": 276050,
            "inicial_50": 330500,
        },
        "credimovil": {"plataforma": 945000, "inicial_10": 94500, "inicial_15": 141750},
    },
    "AND-INF-H60I-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 790000,
            "plataforma": 1045000,
            "inicial_30": 58500,
            "inicial_40": 163000,
            "inicial_45": 215250,
            "inicial_50": 267500,
        },
        "credimovil": {"plataforma": 820000, "inicial_10": 82000, "inicial_15": 123000},
    },
    "AND-INF-SM10-256": {
        "contado": None,
        "addi_sistecredito": 860000,
        "banco_bogota": 810000,
        "krediya": {
            "facturar": 680000,
            "plataforma": 850000,
            "inicial_30": 85000,
            "inicial_40": 170000,
            "inicial_45": 212500,
            "inicial_50": 255000,
        },
        "credimovil": {"plataforma": 730000, "inicial_10": 73000, "inicial_15": 109500},
    },
    "AND-INF-NOTEEDGE": {
        "contado": 1020000,
        "addi_sistecredito": 1520000,
        "banco_bogota": 1370000,
        "krediya": {
            "facturar": 1220000,
            "plataforma": 1420000,
            "inicial_30": 226000,
            "inicial_40": 368000,
            "inicial_45": 439000,
            "inicial_50": 510000,
        },
    },
    "AND-HON-400S-256": {
        "contado": 700000,
        "addi_sistecredito": 1100000,
        "banco_bogota": 1050000,
        "krediya": {
            "facturar": 930000,
            "plataforma": 1200000,
            "inicial_30": 90000,
            "inicial_40": 210000,
            "inicial_45": 270000,
            "inicial_50": 330000,
        },
        "credimovil": {
            "plataforma": 960000,
            "inicial_10": 66000,
            "inicial_15": 114000,
            "promo_noviembre": True,
            "inicial_10_normal": 96000,
            "inicial_15_normal": 144000,
        },
    },
    "AND-SAM-A05-128": {
        "contado": 350000,
        "addi_sistecredito": 710000,
        "banco_bogota": 650000,
        "krediya": {
            "facturar": 590000,
            "plataforma": 770000,
            "inicial_30": 51000,
            "inicial_40": 128000,
            "inicial_45": 166500,
            "inicial_50": 205000,
        },
        "credimovil": {"plataforma": 600000, "inicial_10": 60000, "inicial_15": 90000},
    },
    "AND-SAM-A07-128": {
        "contado": 520000,
        "addi_sistecredito": 890000,
        "banco_bogota": 820000,
        "krediya": {
            "facturar": 720000,
            "plataforma": 900000,
            "inicial_30": 90000,
            "inicial_40": 180000,
            "inicial_45": 225000,
            "inicial_50": 270000,
        },
        "credimovil": {
            "plataforma": 740000,
            "inicial_10": 30000,
            "inicial_15": 60000,
            "promo_noviembre": True,
            "inicial_10_normal": 74000,
            "inicial_15_normal": 111000,
        },
    },
    "AND-SAM-A16-128": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 775000,
            "plataforma": 1050000,
            "inicial_30": 40000,
            "inicial_40": 145000,
            "inicial_45": 197500,
            "inicial_50": 250000,
        },
    },
    "AND-SAM-A17-256": {
        "contado": 850000,
        "addi_sistecredito": 1170000,
        "banco_bogota": 1070000,
        "krediya": {
            "facturar": 960000,
            "plataforma": 1154000,
            "inicial_30": 152200,
            "inicial_40": 267600,
            "inicial_45": 325300,
            "inicial_50": 383000,
        },
        "credimovil": {
            "plataforma": 1050000,
            "inicial_10": 50000,
            "inicial_15": 70000,
            "promo_noviembre": True,
            "inicial_10_normal": 105000,
            "inicial_15_normal": 157500,
        },
    },
    "AND-SAM-A26-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 1170000,
            "plataforma": 1550000,
            "inicial_30": 85000,
            "inicial_40": 240000,
            "inicial_45": 317500,
            "inicial_50": 395000,
        },
    },
    "AND-SAM-A36-256": {
        "contado": None,
        "addi_sistecredito": 1650000,
        "banco_bogota": 1550000,
        "krediya": {
            "facturar": 1427000,
            "plataforma": 1800000,
            "inicial_30": 167000,
            "inicial_40": 347000,
            "inicial_45": 437000,
            "inicial_50": 527000,
        },
    },
    "AND-SAM-A37-256": {
        "contado": 1160000,
        "addi_sistecredito": 1860000,
        "banco_bogota": 1510000,
        "krediya": {
            "facturar": 1420000,
            "plataforma": 1800000,
            "inicial_30": 160000,
            "inicial_40": 340000,
            "inicial_45": 430000,
            "inicial_50": 520000,
        },
    },
    "AND-SAM-A56-256": {
        "contado": None,
        "addi_sistecredito": 2070000,
        "banco_bogota": 1920000,
        "krediya": {
            "facturar": 1790000,
            "plataforma": 2300000,
            "inicial_30": 180000,
            "inicial_40": 410000,
            "inicial_45": 525000,
            "inicial_50": 640000,
        },
    },
    "NEW-SAM-A57-256": {
        "contado": 1990000,
        "addi_sistecredito": 2490000,
        "banco_bogota": 2390000,
    },
    "NEW-SAM-S25U-256": {
        "contado": 2950000,
        "addi_sistecredito": 3650000,
        "banco_bogota": 3350000,
    },
    "NEW-SAM-S25U-512": {
        "contado": 3150000,
        "addi_sistecredito": 3850000,
        "banco_bogota": 3550000,
    },
    "NEW-SAM-S26U-256": {
        "contado": 3350000,
        "addi_sistecredito": 4050000,
        "banco_bogota": 3750000,
    },
    "NEW-SAM-S26U-512": {
        "contado": 3800000,
        "addi_sistecredito": 4500000,
        "banco_bogota": 4200000,
    },
    "AND-OPP-A5X-128": {
        "contado": 510000,
        "addi_sistecredito": 880000,
        "banco_bogota": 760000,
        "krediya": {
            "facturar": 753000,
            "plataforma": 990000,
            "inicial_30": 60000,
            "inicial_40": 159000,
            "inicial_45": 208500,
            "inicial_50": 258000,
        },
    },
    "AND-OPP-A5-256": {
        "contado": None,
        "addi_sistecredito": 1030000,
        "banco_bogota": 890000,
        "krediya": {
            "facturar": 880000,
            "plataforma": 1094900,
            "inicial_30": 113570,
            "inicial_40": 223060,
            "inicial_45": 277805,
            "inicial_50": 332550,
        },
    },
    "AND-OPP-A60-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 945500,
            "plataforma": 1265000,
            "inicial_30": 60000,
            "inicial_40": 186500,
            "inicial_45": 249750,
            "inicial_50": 313000,
        },
    },
    "AND-OPP-A80-256": {
        "contado": 910000,
        "addi_sistecredito": 1110000,
        "banco_bogota": 1110000,
        "krediya": {
            "facturar": 1125500,
            "plataforma": 1485000,
            "inicial_30": 86000,
            "inicial_40": 234500,
            "inicial_45": 308750,
            "inicial_50": 383000,
        },
    },
    "AND-POC-F8P-256": {
        "contado": 1860000,
        "addi_sistecredito": 2350000,
        "banco_bogota": 2350000,
    },
    "AND-POC-X8PM-256": {
        "contado": 1820000,
    },
    "AND-POC-X8P-512": {
        "contado": None,
        "addi_sistecredito": 1800000,
        "banco_bogota": 1700000,
    },
    "AND-POC-X8PM-512": {
        "contado": 1960000,
        "addi_sistecredito": 2440000,
        "banco_bogota": 2310000,
    },
    "AND-RED-A5-128": {
        "contado": 350000,
        "addi_sistecredito": 700000,
        "banco_bogota": 600000,
        "krediya": {
            "facturar": 584100,
            "plataforma": 763000,
            "inicial_30": 50000,
            "inicial_40": 126300,
            "inicial_45": 164450,
            "inicial_50": 202600,
        },
    },
    "AND-RED-A7P-128": {
        "contado": 460000,
        "addi_sistecredito": 810000,
        "banco_bogota": 710000,
        "krediya": {
            "facturar": 690000,
            "plataforma": 594000,
            "inicial_30": 274200,
            "inicial_40": 333600,
            "inicial_45": 363300,
            "inicial_50": 393000,
        },
        "credimovil": {"plataforma": 740000, "inicial_10": 74000, "inicial_15": 111000},
    },
    "AND-RED-14C-128": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 765000,
            "plataforma": 850000,
            "inicial_30": 170000,
            "inicial_40": 255000,
            "inicial_45": 297500,
            "inicial_50": 340000,
        },
    },
    "AND-RED-15C-256": {
        "contado": 620000,
        "addi_sistecredito": 1020000,
        "banco_bogota": 920000,
        "krediya": {
            "facturar": 850000,
            "plataforma": 913000,
            "inicial_30": 210900,
            "inicial_40": 302200,
            "inicial_45": 347850,
            "inicial_50": 393500,
        },
        "credimovil": {
            "plataforma": 980000,
            "inicial_10": 70000,
            "inicial_15": 113500,
            "promo_noviembre": True,
            "inicial_10_normal": 98000,
            "inicial_15_normal": 147000,
        },
    },
    "AND-RED-15-256": {
        "contado": 680000,
        "addi_sistecredito": 1080000,
        "banco_bogota": 980000,
        "krediya": {
            "facturar": 910000,
            "plataforma": 1150000,
            "inicial_30": 105000,
            "inicial_40": 220000,
            "inicial_45": 277500,
            "inicial_50": 335000,
        },
        "credimovil": {
            "plataforma": 980000,
            "inicial_10": 50000,
            "inicial_15": 90000,
            "promo_noviembre": True,
            "inicial_10_normal": 98000,
            "inicial_15_normal": 147000,
        },
    },
    "AND-RED-17-256": {
        "contado": 670000,
        "addi_sistecredito": 1070000,
        "banco_bogota": 1020000,
        "krediya": {
            "facturar": 898000,
            "plataforma": 1100000,
            "inicial_30": 128000,
            "inicial_40": 238000,
            "inicial_45": 293000,
            "inicial_50": 348000,
        },
        "credimovil": {
            "plataforma": 948000,
            "inicial_10": 50000,
            "inicial_15": 90000,
            "promo_noviembre": True,
            "inicial_10_normal": 94800,
            "inicial_15_normal": 142200,
        },
    },
    "AND-RED-N14-256": {
        "contado": None,
        "addi_sistecredito": 890000,
        "banco_bogota": 1040000,
        "krediya": {
            "facturar": 920000,
            "plataforma": 1100000,
            "inicial_30": 150000,
            "inicial_40": 260000,
            "inicial_45": 315000,
            "inicial_50": 370000,
        },
    },
    "AND-RED-N14P-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 1310000,
            "plataforma": 1600000,
            "inicial_30": 190000,
            "inicial_40": 350000,
            "inicial_45": 430000,
            "inicial_50": 510000,
        },
    },
    "AND-RED-N15-256": {
        "contado": 780000,
        "addi_sistecredito": 1180000,
        "banco_bogota": 1130000,
        "krediya": {
            "facturar": 1000000,
            "plataforma": 1214000,
            "inicial_30": 150200,
            "inicial_40": 271600,
            "inicial_45": 332300,
            "inicial_50": 393000,
        },
        "credimovil": {"plataforma": 1050000, "inicial_10": 105000, "inicial_15": 157500},
    },
    "AND-RED-N15P-256": {
        "contado": 970000,
        "addi_sistecredito": 1420000,
        "banco_bogota": 1270000,
        "krediya": {
            "facturar": 1440000,
            "plataforma": 1800000,
            "inicial_30": 180000,
            "inicial_40": 360000,
            "inicial_45": 450000,
            "inicial_50": 540000,
        },
    },
    "AND-RED-N15PP-5G": {
        "contado": 1450000,
    },
    "AND-RED-N17-256-6": {
        "contado": 750000,
        "addi_sistecredito": 1130000,
        "banco_bogota": 1100000,
        "credimovil": {"plataforma": 1030000, "inicial_10": 103000, "inicial_15": 154500},
    },
    "AND-RED-N17-256-8": {
        "contado": 820000,
        "addi_sistecredito": 1200000,
        "banco_bogota": 1170000,
        "krediya": {
            "facturar": 1100000,
            "plataforma": 1430000,
            "inicial_30": 99000,
            "inicial_40": 242000,
            "inicial_45": 313500,
            "inicial_50": 385000,
        },
        "credimovil": {"plataforma": 1100000, "inicial_10": 110000, "inicial_15": 165000},
    },
    "AND-RED-N17P-512": {
        "contado": 1360000,
    },
    "AND-RLM-C75-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 920000,
            "plataforma": 1150000,
            "inicial_30": 115000,
            "inicial_40": 230000,
            "inicial_45": 287500,
            "inicial_50": 345000,
        },
    },
    "AND-RLM-N60X-128": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 620000,
            "plataforma": 820000,
            "inicial_30": 46000,
            "inicial_40": 128000,
            "inicial_45": 169000,
            "inicial_50": 210000,
        },
    },
    "AND-RLM-N70-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 764500,
            "plataforma": 935000,
            "inicial_30": 110000,
            "inicial_40": 203500,
            "inicial_45": 250250,
            "inicial_50": 297000,
        },
    },
    "AND-TEC-POP5G-16": {
        "contado": None,
        "addi_sistecredito": 200000,
        "banco_bogota": 400000,
    },
    "AND-TEC-SPGO2-128": {
        "contado": 360000,
        "addi_sistecredito": 710000,
        "banco_bogota": 560000,
        "krediya": {
            "facturar": 600000,
            "plataforma": 616000,
            "inicial_30": 168800,
            "inicial_40": 230400,
            "inicial_45": 261200,
            "inicial_50": 292000,
        },
        "credimovil": {"plataforma": 630000, "inicial_10": 63000, "inicial_15": 94500},
    },
    "AND-TEC-SPGO3-128": {
        "contado": 420000,
        "addi_sistecredito": 780000,
        "banco_bogota": 620000,
        "krediya": {
            "facturar": 640000,
            "plataforma": 726000,
            "inicial_30": 131800,
            "inicial_40": 204400,
            "inicial_45": 240700,
            "inicial_50": 277000,
        },
        "credimovil": {"plataforma": 690000, "inicial_10": 69000, "inicial_15": 103500},
    },
    "AND-TEC-SP40-256": {
        "contado": 550000,
        "addi_sistecredito": 930000,
        "banco_bogota": 750000,
        "krediya": {
            "facturar": 745000,
            "plataforma": 817000,
            "inicial_30": 173100,
            "inicial_40": 254800,
            "inicial_45": 295650,
            "inicial_50": 336500,
        },
        "credimovil": {"plataforma": 825000, "inicial_10": 82500, "inicial_15": 123750},
    },
    "AND-TEC-SP40PP-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {
            "facturar": 1080000,
            "plataforma": 1300000,
            "inicial_30": 170000,
            "inicial_40": 300000,
            "inicial_45": 365000,
            "inicial_50": 430000,
        },
        "credimovil": {"plataforma": 1080000, "inicial_10": 108000, "inicial_15": 162000},
    },
    "AND-TEC-SP50-256": {
        "contado": 690000,
        "addi_sistecredito": 1090000,
        "banco_bogota": 1040000,
        "krediya": {
            "facturar": 930000,
            "plataforma": 1138000,
            "inicial_30": 133400,
            "inicial_40": 247200,
            "inicial_45": 304100,
            "inicial_50": 361000,
        },
        "credimovil": {
            "plataforma": 970000,
            "inicial_10": 60000,
            "inicial_15": 115500,
            "promo_noviembre": True,
            "inicial_10_normal": 97000,
            "inicial_15_normal": 145500,
        },
    },
    "AND-TEC-POVAC2": {
        "contado": 1040000,
        "addi_sistecredito": 1470000,
        "banco_bogota": 1440000,
        "krediya": {
            "facturar": 1305000,
            "plataforma": 1500000,
            "inicial_30": 255000,
            "inicial_40": 405000,
            "inicial_45": 480000,
            "inicial_50": 555000,
        },
    },
    "AND-TEC-CAM50P-256": {
        "contado": 1250000,
        "addi_sistecredito": 1650000,
        "banco_bogota": 1600000,
        "krediya": {
            "facturar": 1450000,
            "plataforma": 1300000,
            "inicial_30": 540000,
            "inicial_40": 670000,
            "inicial_45": 735000,
            "inicial_50": 800000,
        },
    },
    "AND-TEC-CAM50U-256": {
        "contado": 1280000,
        "addi_sistecredito": 1780000,
        "banco_bogota": 1630000,
        "krediya": {
            "facturar": 1500000,
            "plataforma": 1635000,
            "inicial_30": 355500,
            "inicial_40": 519000,
            "inicial_45": 600750,
            "inicial_50": 682500,
        },
    },
    "AND-ITE-A100C-128": {
        "contado": 370000,
        "addi_sistecredito": 750000,
        "banco_bogota": 720000,
        "credimovil": {"plataforma": 700000, "inicial_10": 70000, "inicial_15": 105000},
    },

    # =================================================================
    # IPHONE NUEVOS Y APPLE ECOSISTEMA (DESDE IPHONE 13 HASTA IPHONE 17)
    # =================================================================
    "NEW-APL-IP13-128": {
        "contado": 1840000,
        "addi_sistecredito": 2470000,
        "banco_bogota": 2240000,
        "renting": {"plataforma": 2450000, "inicial_20": 490000, "inicial_30": 735000},
        "obsequio": "Estuche y Vidrio templado",
    },
    "NEW-APL-IP14-128": {
        "contado": 2100000,
        "addi_sistecredito": 2730000,
        "banco_bogota": 2500000,
        "renting": {"plataforma": 2750000, "inicial_20": 550000, "inicial_30": 825000},
    },
    "NEW-APL-IP15-128": {
        "contado": 2300000,
        "addi_sistecredito": 2950000,
        "banco_bogota": 2700000,
        "renting": {"plataforma": 3100000, "inicial_20": 620000, "inicial_30": 930000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "NEW-APL-IP16-128": {
        "contado": 2650000,
        "addi_sistecredito": 3330000,
        "banco_bogota": 3050000,
        "renting": {"plataforma": 3500000, "inicial_20": 700000, "inicial_30": 1050000},
        "obsequio": "COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods)",
    },
    "NEW-APL-IP17-256": {
        "contado": 3380000,
        "addi_sistecredito": 4250000,
        "banco_bogota": 3830000,
        "renting": {"plataforma": 4100000, "inicial_20": 820000, "inicial_30": 1230000},
    },
    "NEW-APL-IP17P-256": {
        "contado": 4120000,
        "addi_sistecredito": 4970000,
        "banco_bogota": 4570000,
    },
    "NEW-APL-IP17PM-256-AN": {
        "contado": 4300000,
        "addi_sistecredito": 5250000,
        "banco_bogota": 4750000,
        "renting": {"plataforma": 5200000, "inicial_20": 1040000, "inicial_30": 1560000},
    },
    "NEW-APL-IP17PM-256-SIL": {
        "contado": 4350000,
        "addi_sistecredito": 5300000,
        "banco_bogota": 4800000,
        "renting": {"plataforma": 5200000, "inicial_20": 1040000, "inicial_30": 1560000},
    },
    "NEW-APL-MACNEO-256": {
        "contado": 2480000,
        "addi_sistecredito": 3080000,
        "banco_bogota": 2930000,
    },
    "NEW-APL-IPADA16-128": {
        "contado": 1550000,
        "addi_sistecredito": 2050000,
        "banco_bogota": 2000000,
    },

    # =================================================================
    # IPHONE OPEN BOX — SEMINUEVOS (DESDE IPHONE 13 HASTA IPHONE 17)
    # =================================================================
    "OBX-APL-IP13-128": {
        "contado": 1150000,
        "addi_sistecredito": 1850000,
        "banco_bogota": 1600000,
        "renting": {"plataforma": 1850000, "inicial_20": 370000, "inicial_30": 555000},
        "obsequio": "Estuche y Vidrio templado",
    },
    "OBX-APL-IP13P-128": {
        "contado": 1590000,
        "addi_sistecredito": 2330000,
        "banco_bogota": 2030000,
        "renting": {"plataforma": 2300000, "inicial_20": 460000, "inicial_30": 690000},
    },
    "OBX-APL-IP13P-256": {
        "contado": 1680000,
        "addi_sistecredito": 2370000,
        "banco_bogota": 2070000,
        "renting": {"plataforma": 2500000, "inicial_20": 500000, "inicial_30": 750000},
    },
    "OBX-APL-IP13PM-128": {
        "contado": 1890000,
        "addi_sistecredito": 2640000,
        "banco_bogota": 2240000,
        "renting": {"plataforma": 2650000, "inicial_20": 530000, "inicial_30": 795000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP13PM-256": {
        "contado": 1990000,
        "addi_sistecredito": 2740000,
        "banco_bogota": 2340000,
        "renting": {"plataforma": 2950000, "inicial_20": 590000, "inicial_30": 885000},
    },
    "OBX-APL-IP14-128": {
        "contado": 1320000,
        "addi_sistecredito": 2080000,
        "banco_bogota": 1730000,
        "renting": {"plataforma": 2250000, "inicial_20": 450000, "inicial_30": 675000},
    },
    "OBX-APL-IP14-256": {
        "contado": 1390000,
        "addi_sistecredito": 2190000,
        "banco_bogota": 1940000,
        "renting": {"plataforma": 2400000, "inicial_20": 480000, "inicial_30": 720000},
    },
    "OBX-APL-IP14P-128": {
        "contado": 1750000,
        "addi_sistecredito": 2520000,
        "banco_bogota": 2140000,
        "renting": {"plataforma": 2000000, "inicial_20": 400000, "inicial_30": 600000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP14P-256": {
        "contado": 1900000,
        "addi_sistecredito": 2650000,
        "banco_bogota": 2300000,
        "renting": {"plataforma": 2700000, "inicial_20": 540000, "inicial_30": 810000},
    },
    "OBX-APL-IP14PM-128": {
        "contado": 1980000,
        "addi_sistecredito": 2780000,
        "banco_bogota": 2380000,
        "renting": {"plataforma": 2900000, "inicial_20": 580000, "inicial_30": 870000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP14PM-256": {
        "contado": 2350000,
        "addi_sistecredito": 3050000,
        "banco_bogota": 2650000,
        "renting": {"plataforma": 3150000, "inicial_20": 630000, "inicial_30": 945000},
    },
    "OBX-APL-IP15-128": {
        "contado": 1780000,
        "addi_sistecredito": 2630000,
        "banco_bogota": 2280000,
        "renting": {"plataforma": 2500000, "inicial_20": 500000, "inicial_30": 750000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP15P-128": {
        "contado": 2080000,
        "addi_sistecredito": 2940000,
        "banco_bogota": 2590000,
        "renting": {"plataforma": 3000000, "inicial_20": 600000, "inicial_30": 900000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP15P-256": {
        "contado": 2200000,
        "addi_sistecredito": 3090000,
        "banco_bogota": 2690000,
        "renting": {"plataforma": 3250000, "inicial_20": 650000, "inicial_30": 975000},
    },
    "OBX-APL-IP15PM-256": {
        "contado": 2480000,
        "addi_sistecredito": 3380000,
        "banco_bogota": 2980000,
        "renting": {"plataforma": 3500000, "inicial_20": 700000, "inicial_30": 1050000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP16-128": {
        "contado": 2180000,
        "addi_sistecredito": 3170000,
        "banco_bogota": 2820000,
        "renting": {"plataforma": 3200000, "inicial_20": 640000, "inicial_30": 960000},
        "obsequio": "COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods)",
    },
    "OBX-APL-IP16P-128": {
        "contado": 2580000,
        "addi_sistecredito": 3490000,
        "banco_bogota": 3140000,
        "renting": {"plataforma": 3600000, "inicial_20": 720000, "inicial_30": 1080000},
        "obsequio": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
    },
    "OBX-APL-IP16P-256": {
        "contado": 2650000,
        "addi_sistecredito": 3650000,
        "banco_bogota": 3300000,
        "renting": {"plataforma": 3700000, "inicial_20": 740000, "inicial_30": 1110000},
        "obsequio": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
    },
    "OBX-APL-IP16PM-256": {
        "contado": 2930000,
        "addi_sistecredito": 4040000,
        "banco_bogota": 3640000,
        "renting": {"plataforma": 4200000, "inicial_20": 840000, "inicial_30": 1260000},
        "obsequio": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
    },
    "OBX-APL-IP17-256": {
        "contado": 3000000,
        "addi_sistecredito": 3250000,
        "banco_bogota": 3000000,
    },
    "OBX-APL-IP17P-256": {
        "contado": 3520000,
        "addi_sistecredito": 4370000,
        "banco_bogota": 3970000,
        "renting": {"plataforma": 4500000, "inicial_20": 900000, "inicial_30": 1350000},
    },
    "OBX-APL-IP17PM-256": {
        "contado": 4000000,
        "addi_sistecredito": 4800000,
        "banco_bogota": 4450000,
        "renting": {"plataforma": 5200000, "inicial_20": 1040000, "inicial_30": 1560000},
    },
}

# Alias de compatibilidad para SKUs de Infinix
PLATAFORMAS_POR_SKU["AND-INF-H70-256"] = PLATAFORMAS_POR_SKU["AND-INF-HOT70-256"]
PLATAFORMAS_POR_SKU["AND-INF-H60PP-256"] = PLATAFORMAS_POR_SKU["AND-INF-HOT60PP-256"]
PLATAFORMAS_POR_SKU["AND-INF-NEDGE"] = PLATAFORMAS_POR_SKU["AND-INF-NOTEEDGE"]


def get_platform_info(sku: str) -> Dict[str, Any]:
    return PLATAFORMAS_POR_SKU.get(sku, {})


def format_credimovil_november_promos_markdown() -> str:
    """
    Devuelve la tabla oficial de Promociones de Noviembre de Credimóvil | Cel Red.
    """
    lines = [
        "🔥 **PROMOCIONES DE NOVIEMBRE CREDIMÓVIL | CEL RED *(Vigencia hasta nueva orden)*:**",
        "- **Honor 400 Smart (256/6):** **10% Inicial: $66.000** | **15% Inicial: $114.000**",
        "- **Redmi 17 (256/4):** **10% Inicial: $50.000** | **15% Inicial: $90.000**",
        "- **Samsung Galaxy A07 (128/6):** **10% Inicial: $30.000** | **15% Inicial: $60.000**",
        "- **Samsung Galaxy A17 (256/8):** **10% Inicial: $50.000** | **15% Inicial: $70.000**",
        "- **Redmi 15 (256/8):** **10% Inicial: $50.000** | **15% Inicial: $90.000**",
        "- **Infinix Hot 60 Pro Plus (256/8):** **10% Inicial: $90.000** | **15% Inicial: $150.000**",
        "- **Infinix Hot 70 (256/4):** **10% Inicial: $70.000** | **15% Inicial: $121.700**",
        "- **Redmi 15C (256/8):** **10% Inicial: $70.000** | **15% Inicial: $113.500**",
        "- **Tecno Spark 50 (256/4):** **10% Inicial: $60.000** | **15% Inicial: $115.500**",
    ]
    return "\n".join(lines)


def format_platform_summary_markdown(sku: str, filtro_plataforma: Optional[str] = None) -> str:
    """
    Devuelve el desglose formateado en Markdown de los precios de desembolso y cuotas iniciales
    para un SKU dado según las tablas actualizadas de Noviembre 2026 y Promociones Credimóvil.
    """
    info = get_platform_info(sku)
    if not info:
        return ""

    lines = []
    addi = info.get("addi_sistecredito")
    bog = info.get("banco_bogota")
    kred = info.get("krediya")
    cred = info.get("credimovil")
    rent = info.get("renting")

    if addi:
        lines.append(f"  - **Addi o Sistecrédito (Valor de desembolso):** **{_fmt_cop(addi)}**")
    if bog:
        lines.append(f"  - **Confia / Banco de Bogotá (Valor de desembolso):** **{_fmt_cop(bog)}**")
    if kred:
        plat = kred["plataforma"]
        ini30 = kred["inicial_30"]
        ini40 = kred.get("inicial_40")
        ini45 = kred.get("inicial_45")
        ini50 = kred.get("inicial_50")
        extra_kred = ""
        if ini40 and ini45 and ini50:
            extra_kred = f" | *40%: {_fmt_cop(ini40)}* | *45%: {_fmt_cop(ini45)}* | *50%: {_fmt_cop(ini50)}*"
        lines.append(
            f"  - **Krediya:** Valor plataforma **{_fmt_cop(plat)}** | "
            f"**Inicial aprobada al 30%: {_fmt_cop(ini30)}**{extra_kred}"
        )
    if cred:
        plat = cred["plataforma"]
        ini10 = cred["inicial_10"]
        ini15 = cred["inicial_15"]
        if cred.get("promo_noviembre"):
            norm10 = cred.get("inicial_10_normal")
            norm15 = cred.get("inicial_15_normal")
            nota_norm = (
                f" *(Precio normal sin promo: 10% {_fmt_cop(norm10)} / 15% {_fmt_cop(norm15)})*"
                if norm10 and norm15 else ""
            )
            lines.append(
                f"  - **🔥 Credimóvil (PROMO NOVIEMBRE):** Valor plataforma **{_fmt_cop(plat)}** | "
                f"**Inicial 10% Promo: {_fmt_cop(ini10)}** | **Inicial 15% Promo: {_fmt_cop(ini15)}**{nota_norm}"
            )
        else:
            lines.append(
                f"  - **Credimóvil:** Valor plataforma **{_fmt_cop(plat)}** | "
                f"**Inicial al 10%: {_fmt_cop(ini10)}** | **Inicial al 15%: {_fmt_cop(ini15)}**"
            )
    if rent:
        plat = rent["plataforma"]
        ini20 = rent["inicial_20"]
        ini30 = rent["inicial_30"]
        lines.append(
            f"  - **Renting iPhone *(Ideal para reportados o con poco historial crediticio)*:** "
            f"Valor plataforma **{_fmt_cop(plat)}** | **Inicial al 20%: {_fmt_cop(ini20)}** | **Inicial al 30%: {_fmt_cop(ini30)}**"
        )

    if not lines:
        return ""
    return "\n".join(lines)
