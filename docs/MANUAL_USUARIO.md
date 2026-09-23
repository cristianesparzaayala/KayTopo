# KayTopo — Manual de usuario

**Versión:** 0.1.2-alpha  
**Autor:** Cristian Esparza Ayala  
**Licencia del software:** GNU GPL v3 o posterior

© 2026 Cristian Esparza Ayala

KayTopo es una herramienta de escritorio para convertir y preparar información topográfica de forma local y sin depender de Internet. Su flujo está orientado a llevar coordenadas a una salida UTM, completar elevaciones desde un DEM/GeoTIFF cuando sea necesario y preparar archivos compatibles con flujos AutoCAD/CivilCAD.

> KayTopo no sustituye un levantamiento topográfico, control geodésico ni certificación profesional. La exactitud final depende del CRS/datum declarado y de la calidad de los datos de origen.

## Flujo rápido

1. Importa KML, KMZ, CSV o TXT.
2. Confirma el sistema de coordenadas de origen.
3. Define la salida UTM.
4. Opcionalmente carga un DEM/GeoTIFF y elige el método de Z.
5. Revisa la vista previa.
6. Exporta CSV/TXT/DXF.

## Sistemas de entrada

- Coordenadas geográficas/geodésicas.
- UTM.
- TME — Transversa Modificada Ejidal.
- CRS por código EPSG.

La salida de esta versión se concentra en UTM.

## CSV/TXT con metadatos

Los metadatos son opcionales y deben aparecer antes de la primera fila de datos:

```text
# CLAVE=VALOR
```

### UTM con Z

```text
# KAYTOPO_FORMAT=1
# CRS_TYPE=UTM
# DATUM=WGS84
# ZONE=14
# HEMISPHERE=N
# COLUMNS=ID,X,Y,Z
1,498235.421,2224185.672,2413.586
2,498247.183,2224197.348,2413.912
```

### UTM sin Z

```text
# CRS_TYPE=UTM
# DATUM=ITRF2008
# ZONE=14
# HEMISPHERE=N
# COLUMNS=ID,X,Y
1,498235.421,2224185.672
2,498247.183,2224197.348
```

### Geográficas decimales

Convención recomendada: **X = longitud, Y = latitud**.

```text
# CRS_TYPE=GEOGRAPHIC
# DATUM=WGS84
# COLUMNS=ID,X,Y
1,-98.879000,20.112000
2,-98.878600,20.112300
```

### Geográficas GMS

```text
# CRS_TYPE=GEOGRAPHIC
# DATUM=WGS84
# COLUMNS=ID,X,Y
1    98°52'44.400"W    20°06'43.200"N
2    98°52'42.960"W    20°06'44.280"N
```

### TME

```text
# CRS_TYPE=TME
# DATUM=ITRF2008
# CENTRAL_MERIDIAN=-112.5
# COLUMNS=ID,X,Y
1,632103.481,2573880.995
2,632145.250,2573915.440
```

Para TME el meridiano central es obligatorio. KayTopo no debe inventarlo.

### CRS por EPSG

```text
# CRS_TYPE=EPSG
# EPSG=4326
# COLUMNS=ID,X,Y
1,-98.879000,20.112000
2,-98.878600,20.112300
```

## Reglas de formato

- Usa punto decimal.
- No uses separadores de miles.
- Se aceptan coma, punto y coma, tabulación o espacios.
- Si declaras `COLUMNS`, su orden debe coincidir con las filas.
- Los metadatos deben ir antes de la primera fila de coordenadas.

Alias reconocidos:

- ID: `ID`, `N`, `NO`, `NUM`, `NUMERO`, `P`
- X: `X`, `E`, `ESTE`, `EASTING`, `LON`, `LONGITUD`
- Y: `Y`, `NORTE`, `NORTHING`, `LAT`, `LATITUD`
- Z: `Z`, `COTA`, `ELEV`, `ELEVACION`, `ALT`

## DEM / GeoTIFF

KayTopo muestra CRS, resolución, dimensiones y NoData del raster.

Métodos disponibles para completar Z faltante:

- **Valor de celda:** conserva el valor de la celda DEM correspondiente.
- **Bilineal:** interpola entre cuatro centros de celda vecinos.

La interpolación bilineal suaviza el valor entre celdas, pero **no aumenta la resolución ni la precisión real del DEM**. KayTopo nunca reemplaza una Z existente de levantamiento.

## Exportación

Cuando existe relieve, los archivos de puntos se separan:

```text
Terreno_vertices.csv
Terreno_relieve.csv
Terreno_vertices.txt
Terreno_relieve.txt
Terreno.dxf
Terreno_KayTopo.info.txt
```

El DXF usa entidades CAD estándar y no intenta crear objetos propietarios de CivilCAD. Para CivilCAD, importa los archivos de puntos ASCII correspondientes.

## DXF Standard

- `KTOPO_LIMITE`: poligonal.
- `KTOPO_VERTICES`: POINT de vértices.
- `KTOPO_NUMEROS`: numeración.
- `KTOPO_RELIEVE`: puntos interiores DEM.
- `KTOPO_CONTROL`: puntos de control reales cuando existan.
- `KTOPO_REFERENCIA` y `KTOPO_AUX`: capas reservadas.

La escala de referencia del DXF solo controla el tamaño gráfico de símbolos y números. No modifica las coordenadas ni fija la escala final del proyecto.

## Plantillas

Consulta la carpeta [`examples/`](../examples/) para archivos CSV/TXT listos para copiar y editar.

## Autoría

KayTopo · © 2026 Cristian Esparza Ayala  
Software distribuido bajo GNU GPL v3 o posterior.
