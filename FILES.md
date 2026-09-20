# FILES.md

Inventario de archivos del proyecto **Menú de Herramientas**.

| Archivo / carpeta   | Descripción                                                                 |
|----------------------|------------------------------------------------------------------------------|
| `main.py`            | Aplicación completa (PySide6). Un único fichero: modelo de datos, persistencia, extracción de icono y la ventana principal. |
| `requirements.txt`   | Dependencias necesarias (`PySide6`).                                        |
| `README.md`          | Instrucciones de instalación, uso y notas de diseño.                        |
| `config.json`         | **Se genera solo** la primera vez que añades un programa o cambias cualquier preferencia. Guarda la lista de programas (nombre/texto del botón, ruta, tipo, icono, color de fondo, color de texto, orden) y las preferencias (`settings`: vista actual, tamaño de icono, tamaño de ventana, nº de columnas y fuente de texto —familia/proporción de tamaño/negrita/cursiva—, todo por vista). No se sube a git. |
| `icons/`              | **Se genera sola.** Cachea el icono de cada programa como `.png` cuadrado (uno por `id`). No se sube a git. |

## Estructura interna de `main.py`

- **`Program`** — dataclass con los datos de un programa (`id`, `name`, `path`, `type`, `icon`, `color`, `text_color`). El color (de fondo y de letra) es individual por programa.
- **`ConfigStore`** — carga y guarda `config.json`.
- **`extract_icon` / `cache_icon`** — obtienen el icono del archivo vía el shell de Windows (`QFileIconProvider`) y lo cachean como PNG cuadrado (redimensionado en un único paso, sin recortes ni marcos).
- **`Settings`** — preferencias de visualización: vista activa (`grid`/`list`), tamaño de icono, tamaño de ventana, columnas de la cuadrícula y fuente de texto (familia/tamaño/negrita/cursiva), cada uno guardado por separado para cada vista. La fuente es la misma para todos los botones de una vista.
- **`ProgramButton`** — botón de un programa; admite vista de cuadrícula (icono arriba, texto debajo) o de lista (icono a la izquierda, texto a la derecha); redimensiona el icono directamente al tamaño exacto de botón.
- **`MainWindow`** — ventana principal: combo de vista, deslizador de tamaño, rejilla/lista de botones, alta/baja/reorden/color, fuente global por vista, columnas configurables, tamaño de ventana persistente por vista, y lanzamiento del proceso.

## Pendiente / posibles ampliaciones futuras

- Argumentos y carpeta de trabajo propios por programa.
- Soporte multiplataforma (Linux/macOS) para la extracción de icono y el lanzamiento de `.py`.
- Reordenar arrastrando con el ratón en vez de por menú contextual.
