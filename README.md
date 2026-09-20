# APP Launcher

Lanzador de aplicaciones personal hecho con python **PySide6**. Muestra una ventana con un botón por
cada programa que registres; cada botón arranca ese programa (`.exe` o
`.py` sin necesidad de compilar). Todo es configurable desde la propia app: añadir, quitar, reordenar
y cambiar el color de cada botón.

## Requisitos

- Windows (la extracción automática de icono usa el shell de Windows).
- Python 3.10+
- Dependencias en `requirements.txt`

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

- **Añadir programa**: pulsa «+ Añadir programa», elige un `.exe` o `.py` del
  disco, y confirma (o edita) el nombre que verá el botón. El icono se
  extrae automáticamente del archivo.
- **Ejecutar**: clic normal en el botón.
- **Clic derecho** sobre un botón para:
  - Ver la ruta del archivo asociado (se muestra arriba del menú) y copiarla
  - Ejecutar
  - Cambiar texto del botón... — por botón
  - Cambiar color de fondo (paleta de Windows) — por botón
  - Cambiar color de letra (paleta de Windows) — por botón
  - Fuente del texto (todos los botones)... — familia, tamaño, negrita,
    cursiva; se aplica a la vista completa (cuadrícula o lista), no solo
    a ese botón
  - Mover antes / Mover después (reordenar)
  - Columnas de la cuadrícula... (solo en vista de cuadrícula)
  - Quitar
- **Vista**: arriba a la derecha puedes cambiar entre:
  - **Cuadrícula** (formato original: icono encima, texto debajo, en rejilla).
  - **Lista**: botones tipo barra, uno debajo de otro, con el icono a la
    izquierda del texto.
- **Tamaño**: el deslizador de al lado ajusta el tamaño del icono/botón.
  Cada vista recuerda su propio tamaño por separado, así que puedes tener
  la cuadrícula grande y la lista compacta (o al revés) y cada una
  conserva su ajuste al cambiar entre ellas.
- **Tamaño de la ventana**: se recuerda por separado para cada vista; al
  volver a abrir la app (o al cambiar de vista) se restaura el último
  tamaño de ventana usado en esa vista.

## Icono realmente redimensionado

Al añadir un programa, su icono se cachea ya normalizado a un cuadrado fijo
(estirándolo en un único paso, no centrándolo dentro de un cuadro de
relleno). Al mostrarlo en un botón, ese icono se vuelve a redimensionar
igual de directo, al tamaño exacto elegido con el deslizador — es el propio
dibujo el que se agranda o encoge, no un marco con el icono pegado dentro.
Además se usa `QPixmap.scaled()` (que sí escala hacia arriba) en vez de
`QIcon.pixmap()` (que nunca amplía más allá de la resolución nativa), así
que un icono de un `.exe` de baja resolución se ve igual de grande que uno
de un `icono.png` en alta resolución, incluso a tamaño de botón máximo.

## Tamaño de letra y estilo de texto

Por defecto, el tamaño de letra escala junto con el deslizador de tamaño
de icono. Desde el clic derecho:

- **Fuente del texto (todos los botones)...** abre el selector de fuente
  para fijar familia, tamaño, negrita y cursiva. **Se aplica a todos los
  botones de la vista actual** (cuadrícula o lista) a la vez — a
  diferencia de los colores, que cada programa puede tener el suyo. Al
  arrancar, la app intenta cargar las traducciones de Qt del idioma del
  sistema para que este diálogo (que en Windows no siempre usa el nativo)
  aparezca en español; si el paquete de traducciones no está en tu
  instalación de PySide6 seguirá en inglés, pero funciona igual.
- **Cambiar color de letra** abre la paleta de color estándar de Windows
  (esa sí siempre nativa) para el color del texto de **ese botón en
  concreto**.

El tamaño de botón lo decide solo el icono (no crece para hacerle hueco al
texto); a cambio, el texto se pega casi al borde superior e inferior del
botón (margen vertical mínimo). Si fijas un tamaño de letra a mano, se
guarda como proporción respecto al tamaño de icono del momento, así que
si luego mueves el deslizador de tamaño, la letra escala en la misma
proporción en vez de quedarse fija. Se guarda por vista en `config.json`;
si nunca la tocas, el tamaño sigue calculándose automáticamente según el
icono.

## Columnas de la cuadrícula

Desde el clic derecho de cualquier botón, con la vista de Cuadrícula
activa → **Columnas de la cuadrícula...**, puedes fijar cuántas columnas
tiene la rejilla (por ejemplo, 3 columnas para que con 12 programas salgan
4 filas). Se guarda en `config.json`.

## Icono de los `.py`

Para un script `.py`, si en su misma carpeta existe un archivo
`icono.png`, se usa como icono del botón. Si no existe, se usa el icono
por defecto (el de Python) sin avisar.

## Icono de la ventana (barra de título / barra de tareas)

Deja un archivo llamado `app_icon.ico`, `app_icon.png`, `icono.ico` o
`icono.png` (el primero que encuentre, en ese orden) junto a `main.py`
—o junto al `.exe` si está compilado— y la app lo usa automáticamente
como icono de la ventana y de la barra de tareas. Si no hay ninguno, usa
el icono por defecto de Qt sin dar error. Para el `.exe` compilado, usa
ese mismo archivo también en `--icon` de PyInstaller para que el icono
del ejecutable y el de la ventana coincidan.

## Cómo se lanzan los programas

- `.exe` → se ejecuta directamente, con la carpeta que lo contiene como
  directorio de trabajo.
- `.py` → se ejecuta como `python nombre.py` (si `python` no está en el
  PATH, se usa como respaldo el mismo intérprete con el que corre el
  lanzador), también desde la carpeta que contiene el script. Por eso, de
  momento, un script `.py` debe poder ejecutarse él solo desde su propia
  carpeta de proyecto (sin argumentos ni configuración adicional).

## Persistencia

La lista de programas se guarda en `config.json` (se crea automáticamente
al añadir el primer programa) y los iconos cacheados en `icons/`. Ambos se
generan junto al ejecutable real (junto a `main.py` en desarrollo, o junto
al `.exe` si está compilado); no hace falta tocarlos a mano.

## Compilar con PyInstaller

`config.json` e `icons/` se crean solos junto al `.exe` — **no los metas
con `--add-data`**. En modo `--onefile`, `--add-data` los copia dentro del
propio ejecutable, y en tiempo de ejecución PyInstaller los extrae a una
carpeta temporal (`_MEIPASS`) que borra al cerrar la app; el programa
nunca llegaría a ver ni guardar nada ahí, ni aunque los copies a mano
junto al `.exe` (la app seguiría mirando la carpeta temporal, no esa).

Comando recomendado:

```powershell
python -m PyInstaller --onefile --windowed --icon=icons\icono.ico --name=MiApp --collect-all PySide6 main.py
```

(el icono del propio `.exe`, vía `--icon`, es aparte de los iconos de
cada botón — esos los genera y cachea la app sola; para el icono del
`.exe`, Windows funciona mejor con un `.ico` que con un `.png`).

## Notas de diseño

- Pensado para Windows por ahora; ver `FILES.md` para posibles ampliaciones
  (multiplataforma, argumentos por programa, arrastrar para reordenar...).
- Un único archivo (`main.py`) para mantenerlo simple; si el proyecto
  crece, se puede separar en módulos (`config.py`, `widgets.py`, etc.).
