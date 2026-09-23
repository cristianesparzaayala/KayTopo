# KayTopo v0.1 — Formato de entrada CSV/TXT

KayTopo acepta archivos simples de puntos y un **preámbulo opcional de metadatos**. Los metadatos se escriben al principio con:

```text
# CLAVE=VALOR
```

No es obligatorio incluirlos. Si faltan, la interfaz pedirá al usuario los datos necesarios antes de convertir.

## 1. UTM con Z

```text
# KAYTOPO_FORMAT=1
# CRS_TYPE=UTM
# DATUM=WGS84
# ZONE=14
# HEMISPHERE=N
# COLUMNS=ID,X,Y,Z
1,498235.421,2224185.672,2413.586
2,498247.183,2224197.348,2413.912
3,498261.752,2224189.203,2414.107
```

Campos mínimos:

- `CRS_TYPE=UTM`
- `DATUM=WGS84` o `ITRF2008`
- `ZONE=1..60`
- `HEMISPHERE=N` o `S`
- `COLUMNS=...` si el orden no puede inferirse con claridad

## 2. UTM sin Z

```text
# CRS_TYPE=UTM
# DATUM=ITRF2008
# ZONE=14
# HEMISPHERE=N
# COLUMNS=ID,X,Y
1,498235.421,2224185.672
2,498247.183,2224197.348
```

KayTopo permitirá continuar en 2D o agregar un DEM/GeoTIFF.

## 3. Coordenadas geográficas decimales

Convención recomendada: **X = longitud, Y = latitud**.

```text
# CRS_TYPE=GEOGRAPHIC
# DATUM=WGS84
# COLUMNS=ID,X,Y
1,-98.879000,20.112000
2,-98.878600,20.112300
```

También se admite GMS cuando está escrito explícitamente con hemisferio/símbolos.

## 4. TME — Transversa Modificada Ejidal

```text
# CRS_TYPE=TME
# DATUM=ITRF2008
# CENTRAL_MERIDIAN=-112.5
# COLUMNS=ID,X,Y
1,632103.481,2573880.995
```

Para TME el **meridiano central es obligatorio**. KayTopo v0.1 aplica los parámetros TME documentados por INEGI:

- factor de escala del meridiano central: `1.0`;
- latitud de origen: `0`;
- falso Este: `500000 m`;
- falso Norte: `0 m`.

Si el plano agrario indica el meridiano central en grados/minutos, conviértalo o introdúzcalo en la interfaz. La aplicación no debe inventarlo.

## 5. CRS por EPSG

```text
# CRS_TYPE=EPSG
# EPSG=4326
# COLUMNS=ID,X,Y
1,-98.879000,20.112000
```

## 6. Sin metadatos

Esto también es válido:

```text
1,498235.421,2224185.672,2413.586
2,498247.183,2224197.348,2413.912
```

KayTopo puede inferir el patrón de columnas, pero **no considerará confirmado** el CRS solo por la magnitud de los números. El usuario debe seleccionarlo en la pantalla de sistemas de coordenadas.

## Separadores

KayTopo v0.1 acepta:

- coma `,`;
- punto y coma `;`;
- tabulación;
- espacios.

Para intercambio se recomienda **punto decimal** (`498235.421`) y nunca separador de miles.

## Nombres de columnas reconocidos

Alias comunes:

- ID: `ID`, `N`, `NO`, `NUM`, `NUMERO`, `P`
- X: `X`, `E`, `ESTE`, `EASTING`, `LON`, `LONGITUD`
- Y: `Y`, `NORTE`, `NORTHING`, `LAT`, `LATITUD`
- Z: `Z`, `COTA`, `ELEV`, `ELEVACION`, `ALT`

## KML / KMZ

KML/KMZ se interpreta como coordenadas geográficas WGS84. KayTopo lee la secuencia de coordenadas de la geometría principal. Una tercera coordenada KML solo se toma como Z si el documento declara `altitudeMode=absolute`; el valor `0` típico de geometrías pegadas al terreno no se interpreta automáticamente como una elevación levantada.
