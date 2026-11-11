# CEL RED // Asesor Comercial y Sistema de Ventas IA
**Tienda de Celulares, Equipos Apple (Nuevos y Open Box) y Accesorios**  
**Base de Datos:** PostgreSQL 16 (`celred_db`) + `pgvector` (2048-D) + Integración SysCafé  

---

## 1. Descripción del Agente Comercial
El **Asesor Comercial IA de Cel Red** es un sistema conversacional multimodal (texto y voz neuronal con *barge-in*) conectado en tiempo real al inventario de **83 referencias oficiales** de la tienda:
- **48 Celulares Android Nuevos Sellados** (Samsung, Xiaomi Redmi, POCO, Realme, Tecno, Infinix, Oppo, Honor e Itel).
- **15 Equipos Nuevos Apple y Samsung Gama Alta** (desde iPhone 13 128GB Activo hasta iPhone 17 Pro Max, Samsung S25/S26 Ultra, A57 5G, MacBook Neo e iPad A16).
- **20 Equipos iPhone Open Box — Seminuevos Garantizados** (únicamente **desde el iPhone 13 hasta el iPhone 17**; se omiten iPhone 11, 12 y 18).
- **5 Plataformas Oficiales de Financiación:** **Addi**, **Sistecrédito**, **Banco de Bogotá**, **Krediya** (inicial 20%/30% en Android), **Credimóvil** (inicial 10%/15% en Android) y **Renting iPhone** (exclusivo iPhone para reportados o poco historial crediticio, inicial 20%/30%).
- **14 Sedes Oficiales** en Putumayo (Puerto Asís, Mocoa, La Hormiga, Orito), Nariño (Ipiales x3, Pasto x3, Túquerres, La Unión), Antioquia (Medellín) y Huila (Neiva).

---

## 2. Tabla Oficial de Obsequios por Compra de iPhone (Desde iPhone 13 en adelante)
| Referencia iPhone | Obsequio / Combo Oficial Incluido |
|---|---|
| **iPhone 13 128GB** | 🎁 **Estuche y Vidrio Templado** |
| **iPhone 13 Pro Max 128GB** | 🎁 **COMBO 2** *(Cubo, Cable, Estuche, Vidrio)* o **COMBO 3** *(AirPods)* |
| **iPhone 14 Pro 128GB** | 🎁 **COMBO 2** *(Cubo, Cable, Estuche, Vidrio)* o **COMBO 3** *(AirPods)* |
| **iPhone 14 Pro Max 128GB** | 🎁 **COMBO 2** *(Cubo, Cable, Estuche, Vidrio)* o **COMBO 3** *(AirPods)* |
| **iPhone 15 128GB** | 🎁 **COMBO 2** *(Cubo, Cable, Estuche, Vidrio)* o **COMBO 3** *(AirPods)* |
| **iPhone 15 Pro 128GB** | 🎁 **COMBO 2** *(Cubo, Cable, Estuche, Vidrio)* o **COMBO 3** *(AirPods)* |
| **iPhone 15 Pro Max 256GB** | 🎁 **COMBO 2** *(Cubo, Cable, Estuche, Vidrio)* o **COMBO 3** *(AirPods)* |
| **iPhone 16 128GB** | 🎁 **COMBO 4** *(Cubo, Cable, Estuche, Vidrio y AirPods)* |
| **iPhone 16 Pro 128GB** | 🎁 **COMBO 5** *(Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)* |
| **iPhone 16 Pro 256GB** | 🎁 **COMBO 5** *(Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)* |
| **iPhone 16 Pro Max 256GB** | 🎁 **COMBO 5** *(Reloj, Cable, Cubo, AirPods, Vidrio y Estuche)* |

---

## 3. Ejecución Rápida
```bash
docker compose up -d
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
- **Consola Web Cel Red:** [http://localhost:8000](http://localhost:8000)
- **Catálogo JSON (69 referencias):** [http://localhost:8000/api/productos](http://localhost:8000/api/productos)
