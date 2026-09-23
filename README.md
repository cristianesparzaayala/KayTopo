# KayTopo v0.1.2-alpha

<p align="center">
  <img src="assets/branding/KayTopo_logo.png" alt="KayTopo" width="360">
</p>

<p align="center">
  Herramienta offline para conversión y preparación de información topográfica orientada a flujos CAD y CivilCAD.
</p>

<p align="center">
  © 2026 <strong>Cristian Esparza Ayala</strong> · GNU GPL v3 o posterior
</p>

## Descargar KayTopo

La versión pública inicial es **v0.1.2-alpha**. Es una versión funcional de prueba pensada para validación con usuarios reales antes de una versión estable.

- **[KayTopo Setup para Windows](https://github.com/cristianesparzaayala/KayTopo/releases/download/v0.1.2-alpha/KayTopo_Setup_v0.1.2-alpha.exe)** — recomendado para la mayoría de usuarios.
- **[KayTopo Portable para Windows](https://github.com/cristianesparzaayala/KayTopo/releases/download/v0.1.2-alpha/KayTopo_Portable_v0.1.2-alpha.exe)** — un solo ejecutable, sin instalación.
- **[Documentación y plantillas](https://github.com/cristianesparzaayala/KayTopo/releases/download/v0.1.2-alpha/KayTopo_Documentacion_v0.1.2-alpha.zip)**.
- **[Ver la Release v0.1.2-alpha](https://github.com/cristianesparzaayala/KayTopo/releases/tag/v0.1.2-alpha)**.

> KayTopo está en fase **alpha**. Verifica siempre CRS, datum/marco, zona UTM y calidad de las fuentes antes de utilizar resultados en trabajo profesional.

## Qué hace KayTopo

KayTopo permite preparar información topográfica para AutoCAD y CivilCAD mediante un flujo breve y local:

1. Importa coordenadas desde **KML, KMZ, CSV o TXT**.
2. Identifica o configura el sistema de coordenadas de origen.
3. Convierte a una salida **UTM**.
4. Conserva elevaciones Z existentes y, opcionalmente, completa Z faltante desde un **DEM/GeoTIFF**.
5. Muestra una vista previa 2D.
6. Exporta archivos preparados para CAD y CivilCAD.

### Sistemas de coordenadas de origen

- Geográficas.
- UTM.
- TME.
- CRS definido mediante EPSG.

### Salidas

- **CSV** y **TXT** para importación de puntos.
- **DXF** con capas `KTOPO_*`, puntos CAD reales, poligonal y numeración.
- Archivo `.info.txt` con procedencia y parámetros de exportación.

Cuando existe relieve generado desde un DEM, KayTopo separa **vértices** y **puntos de relieve** en archivos independientes para facilitar el trabajo en CivilCAD.

## Elevaciones y DEM

KayTopo conserva las elevaciones Z originales del levantamiento cuando existen.

Si un punto no tiene Z, puede utilizar un DEM/GeoTIFF local mediante:

- **valor de celda**;
- **interpolación bilineal**.

También puede generar puntos interiores de relieve a partir del raster, con un límite configurable para evitar saturar el dibujo CAD.

KayTopo **no transforma datums verticales**. Una elevación de un DEM y una cota de levantamiento pueden pertenecer a referencias verticales distintas.

## Filosofía de confiabilidad

KayTopo no confirma silenciosamente un CRS ambiguo. Puede proponer una interpretación basada en el formato o magnitud de los datos, pero el usuario confirma el sistema antes de transformar coordenadas.

Las Z originales nunca se sustituyen por valores DEM.

La exactitud final depende del CRS declarado, datum/marco, calidad del archivo de entrada, resolución y referencia del DEM y demás fuentes utilizadas.

## Documentación

- [Manual de usuario](docs/MANUAL_USUARIO.md)
- [Plantillas de entrada CSV/TXT](examples/README.md)
- [Formato de entrada técnico](docs/FORMATO_ENTRADA.md)
- [Validación](docs/VALIDACION.md)
- [Notas de versión](CHANGELOG.md)

Para información de desarrollo, compilación y empaquetado consulta [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Compatibilidad y alcance actual

KayTopo está orientado a Windows y a flujos de trabajo con AutoCAD/CivilCAD.

El DXF utiliza entidades CAD estándar. KayTopo no intenta crear objetos propietarios de CivilCAD sin una interfaz pública documentada; para CivilCAD se prioriza la exportación ASCII limpia de puntos.

La aplicación funciona **sin conexión a Internet durante el uso normal**.

## Licencia

KayTopo se distribuye bajo **GNU GPL v3 o posterior**. Consulta [LICENSE](LICENSE).

El código puede estudiarse, modificarse y redistribuirse bajo los términos de esa licencia, conservando los avisos de copyright y licencia aplicables.

## Aviso técnico

KayTopo es una herramienta de procesamiento de datos. No sustituye un levantamiento topográfico, control geodésico, revisión profesional ni certificación técnica.
