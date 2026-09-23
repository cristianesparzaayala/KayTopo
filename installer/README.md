# Instalador de KayTopo

KayTopo se distribuye para Windows en dos formatos:

- **Setup**: recomendado para la mayoría de usuarios. Instala KayTopo para el usuario actual, crea acceso en Inicio, ofrece acceso directo opcional en el escritorio y registra el desinstalador en Windows.
- **Portable**: un solo `KayTopo.exe`, sin instalación.

## Instalación

El instalador usa Inno Setup y se genera desde `installer/KayTopo.iss`.

Ruta predeterminada:

```text
%LOCALAPPDATA%\Programs\KayTopo
```

No requiere permisos de administrador.

El acceso directo del escritorio es opcional. El acceso en el Menú Inicio y el desinstalador se crean automáticamente.

## Actualización

Todas las versiones del Setup comparten un `AppId` estable. Al ejecutar un Setup más reciente, Inno Setup reconoce la instalación existente y actualiza sus archivos conservando la misma instalación.

## Desinstalación

Windows muestra KayTopo en **Configuración > Aplicaciones > Aplicaciones instaladas**. También se crea un acceso de desinstalación en el grupo KayTopo del Menú Inicio.

La desinstalación elimina los archivos instalados por KayTopo. No elimina los DXF, CSV, TXT, DEM u otros archivos de proyecto que el usuario haya guardado fuera de la carpeta de instalación.

## Compilar localmente

1. Instala Inno Setup.
2. Ejecuta:

```bat
scripts\BUILD_INSTALLER_WINDOWS.bat
```

Se generan:

```text
dist\KayTopo.exe
dist\KayTopo_Setup_v0.1.2-alpha.exe
```

## GitHub Releases

El workflow `.github/workflows/release.yml` se activa al crear y subir una etiqueta `v*`, por ejemplo:

```text
v0.1.2-alpha
v1.0.0
```

Antes de crear la Release, GitHub ejecuta pruebas, compila el portable, compila el Setup, instala KayTopo, ejecuta un smoke test y lo desinstala. Después publica los paquetes y sus hashes SHA-256.

© 2026 Cristian Esparza Ayala
