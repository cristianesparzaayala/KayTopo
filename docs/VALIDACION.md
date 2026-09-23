# Validación inicial de KayTopo v0.1

La prioridad de KayTopo es evitar transformaciones silenciosas o matemáticas improvisadas.

## Motor

- Transformaciones CRS estándar: **PROJ vía pyproj**.
- México ITRF2008 / UTM: EPSG 6366–6371 para zonas 11N–16N.
- WGS84 / UTM: EPSG 326xx / 327xx.
- TME: Transversa de Mercator parametrizada conforme a INEGI con `k0=1`, latitud de origen `0`, falso Este `500000 m`, falso Norte `0`, y meridiano central proporcionado por el usuario.

## Prueba oficial TME — INEGI

Referencia: *INEGI, Guía de Proyecciones Cartográficas*, sección 3.5, ejemplo de cálculo directo.

Entrada geodésica:

```text
Latitud:  23° 15' 34.75620" N
Longitud: 111° 12' 32.62310" W
Meridiano central TME: 112° 30' W
Elipsoide: GRS80
```

Resultado publicado por INEGI:

```text
E = 632103.481 m
N = 2573880.995 m
```

Resultado del motor usado por KayTopo en la prueba automatizada:

```text
E = 632103.480789... m
N = 2573880.994989... m
```

Diferencia respecto al valor publicado, redondeado a milímetros: **< 1 mm**.

Esta prueba se encuentra en `tests/test_core.py`.

## Pruebas incluidas

- lectura CSV/TXT con metadatos;
- KML WGS84 y eliminación del vértice duplicado de cierre;
- transformación WGS84 → UTM 14N;
- referencia TME de INEGI;
- exportación CivilCAD 2D sin cabeceras;
- DXF con layers, PDMODE/PDSIZE y autoría interna.

Ejecutar:

```bash
pytest
```

## Límites deliberados de v0.1

- No realiza transformación de datums verticales.
- No transforma coordenadas locales arbitrarias a UTM sin georreferenciación.
- La autodetección por rangos es una sugerencia, no una confirmación de CRS.
- Un DEM no aumenta la precisión del levantamiento; KayTopo conserva su resolución/origen.
- La aplicación no sustituye control geodésico ni verificación profesional cuando el trabajo lo requiera.


## Muestreo DEM

La batería también valida:

- lectura de CRS y resolución del raster;
- interpolación bilineal sobre una matriz de valores conocidos;
- preservación estricta de Z provenientes del levantamiento;
- comportamiento existente de valor de celda y generación de puntos de relieve.

La interpolación bilineal se verifica con un caso sintético donde el punto cae exactamente entre cuatro centros de celda y el resultado esperado es conocido.
