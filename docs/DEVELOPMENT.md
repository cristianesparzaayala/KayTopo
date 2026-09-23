# Desarrollo de KayTopo

Este documento reúne instrucciones para desarrollo, pruebas, compilación y empaquetado. El README principal está orientado a usuarios finales.

## Requisitos

- Windows.
- Python compatible con las dependencias del proyecto.
- Git.
- Dependencias definidas en `requirements.txt` y `requirements-dev.txt`.
- Inno Setup para generar el instalador local.

## Ejecutar en desarrollo

En Windows:

```bat
scripts\RUN_DEV_WINDOWS.bat
```

O manualmente:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m kaytopo
```

## Ejecutar pruebas

```bat
python -m pytest -q
```

La batería incluye transformaciones de coordenadas, lectura de formatos, DEM/GeoTIFF, interpolación bilineal, DXF y comportamiento de exportación.

## Generar el ejecutable portable

```bat
scripts\BUILD_WINDOWS.bat
```

Si las pruebas pasan, el ejecutable se genera en:

```text
dist\KayTopo.exe
```

El ejecutable de Windows debe compilarse en Windows.

## Generar el instalador

Con Inno Setup instalado:

```bat
scripts\BUILD_INSTALLER_WINDOWS.bat
```

Se generan:

```text
dist\KayTopo.exe
dist\KayTopo_Setup_v0.1.2-alpha.exe
```

El instalador utiliza `installer/KayTopo.iss`.

## Instalación

La instalación predeterminada se realiza por usuario en:

```text
%LOCALAPPDATA%\Programs\KayTopo
```

No requiere permisos de administrador.

El Setup crea acceso en el Menú Inicio, ofrece un acceso directo opcional en el escritorio y registra el desinstalador en Windows.

Las versiones futuras conservan el mismo `AppId` para actualizar la instalación existente.

## CI de Windows

El workflow `.github/workflows/tests.yml` valida:

1. dependencias;
2. pruebas;
3. compilación del portable;
4. smoke test del ejecutable;
5. compilación del Setup;
6. instalación silenciosa;
7. smoke test de la aplicación instalada;
8. desinstalación;
9. verificación de eliminación.

## GitHub Releases

El workflow `.github/workflows/release.yml` se activa con tags `v*`, por ejemplo:

```text
v0.1.2-alpha
v1.0.0
```

Antes de crear una Release ejecuta pruebas y valida el ciclo del instalador.

Los assets generados incluyen:

- Setup de Windows.
- Portable.
- Documentación y plantillas.
- `SHA256SUMS.txt`.

Las versiones con sufijos `alpha`, `beta` o `rc` se publican como pre-release.

## Estructura relevante

```text
kaytopo/                  Código de la aplicación
tests/                    Pruebas
docs/                     Documentación técnica y manual
examples/                 Plantillas y ejemplos
assets/branding/          Identidad visual
installer/                Configuración del instalador
scripts/                  Scripts de desarrollo y compilación
.github/workflows/        CI y Releases
```

## Licencia

GNU GPL v3 o posterior.

© 2026 Cristian Esparza Ayala
