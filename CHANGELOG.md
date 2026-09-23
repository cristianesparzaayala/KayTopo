# Changelog

Todas las versiones públicas relevantes de KayTopo se documentan aquí.

## v0.1.2-alpha

Primera versión pública de prueba.

### Incluye

- Importación de KML, KMZ, CSV y TXT.
- Lectura de coordenadas geográficas, UTM, TME y CRS definido mediante EPSG.
- Conversión a UTM WGS 84 o México ITRF2008 / UTM.
- Conservación de elevaciones Z originales cuando existen.
- Uso opcional de DEM/GeoTIFF para completar Z faltante.
- Muestreo de elevación por valor de celda o interpolación bilineal.
- Generación opcional de puntos interiores de relieve desde el DEM.
- Vista previa 2D local.
- Exportación CSV, TXT y DXF.
- Separación de vértices y puntos de relieve en archivos de puntos.
- Capas DXF `KTOPO_*`, puntos CAD reales, poligonal y numeración.
- Registro `.info.txt` con procedencia y parámetros de exportación.
- Interfaz de escritorio con branding oficial de KayTopo.
- Ejecutable portable para Windows.
- Instalador Windows con acceso en Inicio, acceso directo opcional y desinstalador.
- Pruebas automáticas en Windows para código, portable, instalación, arranque y desinstalación.
- Manual de usuario, formato de entrada y plantillas de ejemplo.

### Estado

Esta versión se publica como **alpha** para validación con usuarios reales. No sustituye levantamientos topográficos, control geodésico ni revisión profesional. La exactitud final depende del CRS, datum/marco, calidad de los datos de entrada, resolución/referencia del DEM y demás fuentes utilizadas.

### Autor

© 2026 Cristian Esparza Ayala

Licencia: GNU GPL v3 o posterior.
