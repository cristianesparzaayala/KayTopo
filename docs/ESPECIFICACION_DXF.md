# KayTopo Standard — DXF v0.1.1

## Unidades y representación

- Unidad de dibujo: **metros**.
- Entidades de vértice/relieve: `POINT` CAD real.
- `PDMODE = 34`: círculo + cruz.
- PDSIZE: equivalente a **5 mm en papel** según escala de referencia.
- Altura de número de vértice: equivalente a **3 mm en papel**.
- Número: `1, 2, 3...`, sin prefijo `P` y sin etiqueta Z.
- Poligonal: `LWPOLYLINE` cerrada en planta.
- La escala de referencia **no modifica las coordenadas ni fija la escala final del proyecto**.

## Layers

| Layer | Uso | ACI | Linetype | Lineweight |
|---|---|---:|---|---:|
| `KTOPO_LIMITE` | Poligonal | 1 | Continuous | 0.35 mm |
| `KTOPO_VERTICES` | POINT de vértices | 3 | Continuous | 0.25 mm |
| `KTOPO_NUMEROS` | Número de vértice | 7 | Continuous | 0.18 mm |
| `KTOPO_RELIEVE` | POINT interiores DEM | 8 | Continuous | 0.09 mm |
| `KTOPO_CONTROL` | Puntos de control reales, si existen | 6 | Continuous | 0.30 mm |
| `KTOPO_REFERENCIA` | Reservado para referencias | 4 | Dashed | 0.13 mm |
| `KTOPO_AUX` | Reservado para auxiliares | 8 | Dashed | 0.09 mm |

KayTopo crea únicamente las capas que utiliza en la exportación actual. Los objetos se crean **BYLAYER**.

## Autoría interna

El DXF incorpora comentarios `999` con:

```text
KayTopo
Copyright (c) 2026 Cristian Esparza Ayala
Generated with KayTopo 0.1.1-alpha
SPDX-License-Identifier: GPL-3.0-or-later
```

Estos datos no aparecen como texto en Model Space.
