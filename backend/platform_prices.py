"""
 Catálogo Financiero Multi-Plataforma Oficial de CEL RED (`editada.xlsx`)
Contiene los precios exactos de desembolso y cuotas iniciales por plataforma para Android e iPhone:
1. ADDI / SISTECRÉDITO: Precio de desembolso directo.
2. BANCO DE BOGOTÁ: Precio de desembolso directo.
3. KREDIYA (Android): Precio en plataforma + Cuota Inicial aprobada al 30% (y referencia al 20%).
4. CREDIMÓVIL (Android): Precio en plataforma + Cuota Inicial al 10% (0.1) y al 15% (0.15).
5. RENTING (Exclusivo iPhone — para clientes con poco historial crediticio o reportados):
   Valor plataforma + Cuota Inicial aprobada al 20% y al 30%.
"""

from typing import Dict, Any, Optional


def _fmt_cop(val: int) -> str:
    return f"${val:,.0f}".replace(",", ".")


# Mapa maestro indexado por SKU oficial de Cel Red
PLATAFORMAS_POR_SKU: Dict[str, Dict[str, Any]] = {
    # =================================================================
    # ANDROID NUEVOS (CONTADO + PLATAFORMAS DE CRÉDITO)
    # =================================================================
    "AND-INF-H70-256": {
        "contado": 675000,
        "addi_sistecredito": 1055000,
        "banco_bogota": 1055000,
        "krediya": {"plataforma": 1150000, "inicial_30": 120000},
        "credimovil": {"plataforma": 945000, "inicial_10": 94500, "inicial_15": 141750},
    },
    "AND-INF-H60PP-256": {
        "contado": 870000,
        "addi_sistecredito": 1270000,
        "banco_bogota": 1220000,
        "krediya": {"plataforma": 1400000, "inicial_30": 120000},
        "credimovil": {"plataforma": 1130000, "inicial_10": 113000, "inicial_15": 169500},
    },
    "AND-INF-H60P-256": {
        "contado": None,
        "addi_sistecredito": 1060000,
        "banco_bogota": 1030000,
        "krediya": {"plataforma": 1089000, "inicial_30": 112700},
        "credimovil": {"plataforma": 945000, "inicial_10": 94500, "inicial_15": 141750},
    },
    "AND-INF-H60I-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1045000, "inicial_30": 58500},
        "credimovil": {"plataforma": 820000, "inicial_10": 82000, "inicial_15": 123000},
    },
    "AND-INF-SM10-256": {
        "contado": None,
        "addi_sistecredito": 860000,
        "banco_bogota": 810000,
        "krediya": {"plataforma": 850000, "inicial_30": 85000},
        "credimovil": {"plataforma": 730000, "inicial_10": 73000, "inicial_15": 109500},
    },
    "AND-INF-NEDGE": {
        "contado": 1020000,
        "addi_sistecredito": 1520000,
        "banco_bogota": 1370000,
        "krediya": {"plataforma": 1420000, "inicial_30": 226000},
    },
    "AND-HON-400S-256": {
        "contado": 700000,
        "addi_sistecredito": 1100000,
        "banco_bogota": 1050000,
        "krediya": {"plataforma": 1200000, "inicial_30": 90000},
        "credimovil": {"plataforma": 960000, "inicial_10": 96000, "inicial_15": 144000},
    },
    "AND-SAM-A05-128": {
        "contado": 350000,
        "addi_sistecredito": 710000,
        "banco_bogota": 650000,
        "krediya": {"plataforma": 770000, "inicial_30": 51000},
        "credimovil": {"plataforma": 600000, "inicial_10": 60000, "inicial_15": 90000},
    },
    "AND-SAM-A07-128": {
        "contado": 470000,
        "addi_sistecredito": 890000,
        "banco_bogota": 820000,
        "krediya": {"plataforma": 900000, "inicial_30": 60000},
        "credimovil": {"plataforma": 710000, "inicial_10": 71000, "inicial_15": 106500},
    },
    "AND-SAM-A16-128": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1050000, "inicial_30": 40000},
    },
    "AND-SAM-A17-256": {
        "contado": 720000,
        "addi_sistecredito": 1170000,
        "banco_bogota": 1070000,
        "krediya": {"plataforma": 1154000, "inicial_30": 132200},
        "credimovil": {"plataforma": 1030000, "inicial_10": 103000, "inicial_15": 154500},
    },
    "AND-SAM-A26-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1550000, "inicial_30": 85000},
    },
    "AND-SAM-A36-256": {
        "contado": None,
        "addi_sistecredito": 1650000,
        "banco_bogota": 1550000,
        "krediya": {"plataforma": 1800000, "inicial_30": 167000},
    },
    "AND-SAM-A37-256": {
        "contado": 1160000,
        "addi_sistecredito": 1860000,
        "banco_bogota": 1510000,
        "krediya": {"plataforma": 1800000, "inicial_30": 160000},
    },
    "AND-SAM-A56-256": {
        "contado": None,
        "addi_sistecredito": 2070000,
        "banco_bogota": 1920000,
        "krediya": {"plataforma": 2300000, "inicial_30": 180000},
    },
    "NEW-SAM-A57-256": {
        "contado": 1990000,
        "addi_sistecredito": 2490000,
        "banco_bogota": 2390000,
    },
    "NEW-SAM-S25U-256": {
        "contado": 2980000,
        "addi_sistecredito": 3680000,
        "banco_bogota": 3380000,
    },
    "NEW-SAM-S25U-512": {
        "contado": 3300000,
        "addi_sistecredito": 4000000,
        "banco_bogota": 3700000,
    },
    "NEW-SAM-S26U-256": {
        "contado": 3340000,
        "addi_sistecredito": 4040000,
        "banco_bogota": 3740000,
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
        "krediya": {"plataforma": 990000, "inicial_30": 60000},
    },
    "AND-OPP-A5-256": {
        "contado": None,
        "addi_sistecredito": 1030000,
        "banco_bogota": 890000,
        "krediya": {"plataforma": 1094900, "inicial_30": 113570},
    },
    "AND-OPP-A60-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1265000, "inicial_30": 60000},
    },
    "AND-OPP-A80-256": {
        "contado": 910000,
        "addi_sistecredito": 1110000,
        "banco_bogota": 1110000,
        "krediya": {"plataforma": 1485000, "inicial_30": 86000},
    },
    "AND-POC-F8P-256": {
        "contado": 1860000,
        "addi_sistecredito": 2350000,
        "banco_bogota": 2350000,
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
        "krediya": {"plataforma": 763000, "inicial_30": 50000},
    },
    "AND-RED-A7P-128": {
        "contado": 460000,
        "addi_sistecredito": 810000,
        "banco_bogota": 710000,
        "krediya": {"plataforma": 594000, "inicial_30": 274200},
        "credimovil": {"plataforma": 740000, "inicial_10": 74000, "inicial_15": 111000},
    },
    "AND-RED-14C-128": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 850000, "inicial_30": 170000},
    },
    "AND-RED-15C-256": {
        "contado": 620000,
        "addi_sistecredito": 1020000,
        "banco_bogota": 920000,
        "krediya": {"plataforma": 913000, "inicial_30": 170900},
        "credimovil": {"plataforma": 890000, "inicial_10": 89000, "inicial_15": 133500},
    },
    "AND-RED-15-256": {
        "contado": 680000,
        "addi_sistecredito": 1080000,
        "banco_bogota": 980000,
        "krediya": {"plataforma": 1150000, "inicial_30": 105000},
        "credimovil": {"plataforma": 980000, "inicial_10": 98000, "inicial_15": 147000},
    },
    "AND-RED-17-256": {
        "contado": 670000,
        "addi_sistecredito": 1070000,
        "banco_bogota": 1020000,
        "krediya": {"plataforma": 1100000, "inicial_30": 128000},
        "credimovil": {"plataforma": 948000, "inicial_10": 94800, "inicial_15": 142200},
    },
    "AND-RED-N14-256": {
        "contado": None,
        "addi_sistecredito": 890000,
        "banco_bogota": 1040000,
        "krediya": {"plataforma": 1100000, "inicial_30": 150000},
    },
    "AND-RED-N14P-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1600000, "inicial_30": 190000},
    },
    "AND-RED-N15-256": {
        "contado": 780000,
        "addi_sistecredito": 1180000,
        "banco_bogota": 1130000,
        "krediya": {"plataforma": 1214000, "inicial_30": 150200},
        "credimovil": {"plataforma": 1030000, "inicial_10": 103000, "inicial_15": 154500},
    },
    "AND-RED-N15P-256": {
        "contado": 970000,
        "addi_sistecredito": 1420000,
        "banco_bogota": 1270000,
        "krediya": {"plataforma": 1800000, "inicial_30": 160000},
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
        "krediya": {"plataforma": 1430000, "inicial_30": 99000},
        "credimovil": {"plataforma": 1100000, "inicial_10": 110000, "inicial_15": 165000},
    },
    "AND-RLM-C75-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1150000, "inicial_30": 115000},
    },
    "AND-RLM-N60X-128": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 820000, "inicial_30": 46000},
    },
    "AND-RLM-N70-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 935000, "inicial_30": 110000},
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
        "krediya": {"plataforma": 616000, "inicial_30": 168800},
        "credimovil": {"plataforma": 630000, "inicial_10": 63000, "inicial_15": 94500},
    },
    "AND-TEC-SPGO3-128": {
        "contado": 420000,
        "addi_sistecredito": 780000,
        "banco_bogota": 620000,
        "krediya": {"plataforma": 726000, "inicial_30": 131800},
        "credimovil": {"plataforma": 690000, "inicial_10": 69000, "inicial_15": 103500},
    },
    "AND-TEC-SP40-256": {
        "contado": 550000,
        "addi_sistecredito": 930000,
        "banco_bogota": 750000,
        "krediya": {"plataforma": 817000, "inicial_30": 173100},
        "credimovil": {"plataforma": 825000, "inicial_10": 82500, "inicial_15": 123750},
    },
    "AND-TEC-SP40PP-256": {
        "contado": None,
        "addi_sistecredito": None,
        "banco_bogota": None,
        "krediya": {"plataforma": 1300000, "inicial_30": 170000},
        "credimovil": {"plataforma": 1080000, "inicial_10": 108000, "inicial_15": 162000},
    },
    "AND-TEC-SP50-256": {
        "contado": 690000,
        "addi_sistecredito": 1090000,
        "banco_bogota": 1040000,
        "krediya": {"plataforma": 1138000, "inicial_30": 133400},
        "credimovil": {"plataforma": 970000, "inicial_10": 97000, "inicial_15": 145500},
    },
    "AND-TEC-POVAC2": {
        "contado": 1040000,
        "addi_sistecredito": 1470000,
        "banco_bogota": 1440000,
        "krediya": {"plataforma": 1500000, "inicial_30": 255000},
    },
    "AND-TEC-CAM50P-256": {
        "contado": 1250000,
        "addi_sistecredito": 1650000,
        "banco_bogota": 1600000,
        "krediya": {"plataforma": 1300000, "inicial_30": 540000},
    },
    "AND-TEC-CAM50U-256": {
        "contado": 1280000,
        "addi_sistecredito": 1780000,
        "banco_bogota": 1630000,
        "krediya": {"plataforma": 1635000, "inicial_30": 355500},
    },
    "AND-ITE-A100C-128": {
        "contado": 370000,
        "addi_sistecredito": 750000,
        "banco_bogota": 720000,
        "credimovil": {"plataforma": 700000, "inicial_10": 70000, "inicial_15": 105000},
    },

    # =================================================================
    # IPHONE NUEVOS Y APPLE ECOSISTEMA (DESDE IPHONE 13 EN ADELANTE)
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
        "contado": 2200000,
        "addi_sistecredito": 2850000,
        "banco_bogota": 2600000,
        "renting": {"plataforma": 3100000, "inicial_20": 620000, "inicial_30": 930000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "NEW-APL-IP16-128": {
        "contado": 2600000,
        "addi_sistecredito": 3280000,
        "banco_bogota": 3000000,
        "renting": {"plataforma": 3500000, "inicial_20": 700000, "inicial_30": 1050000},
        "obsequio": "COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods)",
    },
    "NEW-APL-IP17-256": {
        "contado": 3300000,
        "addi_sistecredito": 4170000,
        "banco_bogota": 3750000,
        "renting": {"plataforma": 4100000, "inicial_20": 820000, "inicial_30": 1230000},
    },
    "NEW-APL-IP17P-256": {
        "contado": 4120000,
        "addi_sistecredito": 4970000,
        "banco_bogota": 4570000,
    },
    "NEW-APL-IP17PM-256-AN": {
        "contado": 4250000,
        "addi_sistecredito": 5250000,
        "banco_bogota": 4750000,
        "renting": {"plataforma": 5200000, "inicial_20": 1040000, "inicial_30": 1560000},
    },
    "NEW-APL-IP17PM-256-SIL": {
        "contado": 4300000,
        "addi_sistecredito": 5250000,
        "banco_bogota": 4750000,
        "renting": {"plataforma": 5200000, "inicial_20": 1040000, "inicial_30": 1560000},
    },
    "NEW-APL-IP18P-256-VA": {
        "contado": 4450000,
        "addi_sistecredito": 5850000,
        "banco_bogota": 5390000,
    },
    "NEW-APL-IP18P-256-NEG": {
        "contado": 4350000,
        "addi_sistecredito": 5600000,
        "banco_bogota": 5100000,
    },
    "NEW-APL-IP18P-512": {
        "contado": 5150000,
    },
    "NEW-APL-IP18PM-256-VIN": {
        "contado": 5350000,
        "addi_sistecredito": 6749900,
        "banco_bogota": 6349900,
    },
    "NEW-APL-IP18PM-256-MIX": {
        "contado": 5250000,
        "addi_sistecredito": 6200000,
        "banco_bogota": 5950000,
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
    # IPHONE OPEN BOX — SEMINUEVOS (DESDE IPHONE 13 EN ADELANTE)
    # =================================================================
    "OBX-APL-IP13-128": {
        "contado": 1150000,
        "addi_sistecredito": 1750000,
        "banco_bogota": 1500000,
        "renting": {"plataforma": 1850000, "inicial_20": 370000, "inicial_30": 555000},
        "obsequio": "Estuche y Vidrio templado",
    },
    "OBX-APL-IP13P-128": {
        "contado": 1590000,
        "addi_sistecredito": 2240000,
        "banco_bogota": 1940000,
        "renting": {"plataforma": 2300000, "inicial_20": 460000, "inicial_30": 690000},
    },
    "OBX-APL-IP13P-256": {
        "contado": 1680000,
        "addi_sistecredito": 2330000,
        "banco_bogota": 2030000,
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
        "contado": 1300000,
        "addi_sistecredito": 2150000,
        "banco_bogota": 1800000,
        "renting": {"plataforma": 2500000, "inicial_20": 500000, "inicial_30": 750000},
    },
    "OBX-APL-IP14P-128": {
        "contado": 1820000,
        "addi_sistecredito": 2590000,
        "banco_bogota": 2210000,
        "renting": {"plataforma": 2500000, "inicial_20": 500000, "inicial_30": 750000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP14P-256": {
        "contado": 1900000,
        "addi_sistecredito": 2650000,
        "banco_bogota": 2300000,
    },
    "OBX-APL-IP14PM-128": {
        "contado": 1980000,
        "addi_sistecredito": 2750000,
        "banco_bogota": 2350000,
        "renting": {"plataforma": 2900000, "inicial_20": 580000, "inicial_30": 870000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP14PM-256": {
        "contado": 2350000,
        "addi_sistecredito": 3100000,
        "banco_bogota": 2700000,
        "renting": {"plataforma": 3150000, "inicial_20": 630000, "inicial_30": 945000},
    },
    "OBX-APL-IP15-128": {
        "contado": 1790000,
        "addi_sistecredito": 2580000,
        "banco_bogota": 2230000,
        "renting": {"plataforma": 2500000, "inicial_20": 500000, "inicial_30": 750000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP15P-128": {
        "contado": 2050000,
        "addi_sistecredito": 2900000,
        "banco_bogota": 2550000,
        "renting": {"plataforma": 3000000, "inicial_20": 600000, "inicial_30": 900000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP15P-256": {
        "contado": 2200000,
        "addi_sistecredito": 3050000,
        "banco_bogota": 2650000,
        "renting": {"plataforma": 3250000, "inicial_20": 650000, "inicial_30": 975000},
    },
    "OBX-APL-IP15PM-256": {
        "contado": 2530000,
        "addi_sistecredito": 3350000,
        "banco_bogota": 2950000,
        "renting": {"plataforma": 3500000, "inicial_20": 700000, "inicial_30": 1050000},
        "obsequio": "COMBO 2 (Cubo, Cable, Estuche, Vidrio) o COMBO 3 (AirPods)",
    },
    "OBX-APL-IP16-128": {
        "contado": 2180000,
        "addi_sistecredito": 3000000,
        "banco_bogota": 2650000,
        "renting": {"plataforma": 3200000, "inicial_20": 640000, "inicial_30": 960000},
        "obsequio": "COMBO 4 (Cubo, Cable, Estuche, Vidrio y AirPods)",
    },
    "OBX-APL-IP16P-128": {
        "contado": 2580000,
        "addi_sistecredito": 3385000,
        "banco_bogota": 3035000,
        "renting": {"plataforma": 3600000, "inicial_20": 720000, "inicial_30": 1080000},
        "obsequio": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
    },
    "OBX-APL-IP16P-256": {
        "contado": 2650000,
        "addi_sistecredito": 3520000,
        "banco_bogota": 3170000,
        "renting": {"plataforma": 3700000, "inicial_20": 740000, "inicial_30": 1110000},
        "obsequio": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
    },
    "OBX-APL-IP16PM-256": {
        "contado": 2950000,
        "addi_sistecredito": 3900000,
        "banco_bogota": 3500000,
        "renting": {"plataforma": 4200000, "inicial_20": 840000, "inicial_30": 1260000},
        "obsequio": "COMBO 5 (Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)",
    },
    "OBX-APL-IP17-256": {
        "contado": None,
        "addi_sistecredito": 3250000,
        "banco_bogota": 3000000,
    },
    "OBX-APL-IP17P-256": {
        "contado": 3520000,
        "addi_sistecredito": 4430000,
        "banco_bogota": 4030000,
    },
    "OBX-APL-IP17PM-256": {
        "contado": 4000000,
        "addi_sistecredito": 4800000,
        "banco_bogota": 4450000,
    },
}


def get_platform_info(sku: str) -> Dict[str, Any]:
    return PLATAFORMAS_POR_SKU.get(sku, {})


def format_platform_summary_markdown(sku: str, filtro_plataforma: Optional[str] = None) -> str:
    """
    Devuelve el desglose formateado en Markdown de los precios de desembolso y cuotas iniciales
    para un SKU dado según `editada.xlsx`.
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
        lines.append(f"  - **Banco de Bogotá (Valor de desembolso):** **{_fmt_cop(bog)}**")
    if kred:
        plat = kred["plataforma"]
        ini30 = kred["inicial_30"]
        ini20 = int(plat * 0.20)
        lines.append(
            f"  - **Krediya:** Valor plataforma **{_fmt_cop(plat)}** | "
            f"**Inicial aprobada al 30%: {_fmt_cop(ini30)}** *(o si te aprueban al 20%: {_fmt_cop(ini20)})*"
        )
    if cred:
        plat = cred["plataforma"]
        ini10 = cred["inicial_10"]
        ini15 = cred["inicial_15"]
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

