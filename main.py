"""
Menú de Herramientas
=====================
Lanzador de programas personal hecho con PySide6.

Muestra una ventana con un botón por cada programa registrado. Cada botón
lanza el programa correspondiente (.exe o .py). Desde "Añadir programa" se
puede registrar uno nuevo eligiéndolo del disco; el icono se obtiene
automáticamente del propio archivo (icono de shell de Windows) y se cachea
en la carpeta icons/. Hay dos vistas intercambiables (Cuadrícula / Lista),
cada una con su propio tamaño de icono, tamaño de ventana y (la cuadrícula)
número de columnas. Todo persiste en config.json.

Ejecutar:
    python main.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QFileInfo, QLocale, QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon, QColor, QPainter, QPixmap, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QHBoxLayout, QToolButton, QPushButton, QFileDialog, QInputDialog,
    QColorDialog, QFontDialog, QMessageBox, QLabel, QFileIconProvider,
    QMenu, QScrollArea, QStyle, QComboBox, QSlider, QSizePolicy,
)

# ---------------------------------------------------------------------------
# Rutas y constantes
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Compilado con PyInstaller (--onefile incluido): __file__ apuntaría a
    # la carpeta temporal de extracción (_MEIPASS), que se borra al
    # cerrar la app. config.json e icons/ deben vivir junto al .exe real,
    # así que se usa la carpeta de sys.executable en su lugar.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = BASE_DIR / "config.json"
ICONS_DIR = BASE_DIR / "icons"

# Nombres de archivo que se buscan, en este orden, para el icono de la
# propia ventana/app (barra de título y barra de tareas). Basta con dejar
# uno de estos junto a main.py (o junto al .exe si está compilado).
APP_ICON_NAMES = ("app_icon.ico", "app_icon.png", "icono.ico", "icono.png")

DEFAULT_COLOR = "#3a3f4b"

LAYOUT_GRID = "grid"
LAYOUT_LIST = "list"

SIZE_MIN = 24
SIZE_MAX = 96
DEFAULT_GRID_ICON_SIZE = 48
DEFAULT_LIST_ICON_SIZE = 32

DEFAULT_COLUMNS = 4
DEFAULT_WINDOW_W = 560
DEFAULT_WINDOW_H = 420

FONT_SIZE_RATIO = 0.26      # tamaño de letra automático = icon_px * este factor
FONT_SIZE_AUTO_MIN = 9      # suelo del tamaño de letra automático


def load_app_icon() -> QIcon:
    """Icono de la ventana/app: el primero de APP_ICON_NAMES que exista
    junto a main.py (o junto al .exe si está compilado). Si no hay
    ninguno, se devuelve un QIcon vacío (Qt usa entonces su icono por
    defecto, sin dar error)."""
    for name in APP_ICON_NAMES:
        candidate = BASE_DIR / name
        if candidate.exists():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def effective_font_px(icon_px: int, ratio: float) -> int:
    """Tamaño de letra en función del tamaño de icono/botón actual y una
    proporción (ratio = tamaño_letra / tamaño_icono). Si no hay ninguna
    proporción fijada (0), se usa la proporción automática por defecto.
    Así, tanto el tamaño automático como uno elegido a mano por el
    usuario escalan igual al redimensionar el botón."""
    return max(FONT_SIZE_AUTO_MIN, round(icon_px * (ratio if ratio else FONT_SIZE_RATIO)))


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------
@dataclass
class Program:
    id: str
    name: str
    path: str
    type: str               # "exe" o "py"
    icon: str = ""            # ruta relativa (a BASE_DIR) al png cacheado
    color: str = DEFAULT_COLOR
    text_color: str = "#ffffff"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Program":
        return Program(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "Sin nombre"),
            path=data.get("path", ""),
            type=data.get("type", "exe"),
            icon=data.get("icon", ""),
            color=data.get("color", DEFAULT_COLOR),
            text_color=data.get("text_color", "#ffffff"),
        )


@dataclass
class Settings:
    """Preferencias de visualización. Cada vista (cuadrícula / lista)
    guarda por separado su tamaño de icono, tamaño de ventana y fuente de
    texto (familia/tamaño/negrita/cursiva) usados la última vez; la
    cuadrícula guarda además su número de columnas. La fuente es la misma
    para todos los botones de una vista (a diferencia de los colores, que
    cada programa puede tener el suyo)."""
    layout: str = LAYOUT_GRID

    grid_icon_size: int = DEFAULT_GRID_ICON_SIZE
    list_icon_size: int = DEFAULT_LIST_ICON_SIZE

    grid_columns: int = DEFAULT_COLUMNS

    grid_window_w: int = DEFAULT_WINDOW_W
    grid_window_h: int = DEFAULT_WINDOW_H
    list_window_w: int = DEFAULT_WINDOW_W
    list_window_h: int = DEFAULT_WINDOW_H

    grid_font_family: str = ""
    grid_font_ratio: float = 0.0   # tamaño_letra / tamaño_icono; 0 = automático
    grid_font_bold: bool = False
    grid_font_italic: bool = False

    list_font_family: str = ""
    list_font_ratio: float = 0.0
    list_font_bold: bool = False
    list_font_italic: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Settings":
        return Settings(
            layout=data.get("layout", LAYOUT_GRID),
            grid_icon_size=data.get("grid_icon_size", DEFAULT_GRID_ICON_SIZE),
            list_icon_size=data.get("list_icon_size", DEFAULT_LIST_ICON_SIZE),
            grid_columns=data.get("grid_columns", DEFAULT_COLUMNS),
            grid_window_w=data.get("grid_window_w", DEFAULT_WINDOW_W),
            grid_window_h=data.get("grid_window_h", DEFAULT_WINDOW_H),
            list_window_w=data.get("list_window_w", DEFAULT_WINDOW_W),
            list_window_h=data.get("list_window_h", DEFAULT_WINDOW_H),
            grid_font_family=data.get("grid_font_family", ""),
            grid_font_ratio=data.get("grid_font_ratio", 0.0),
            grid_font_bold=data.get("grid_font_bold", False),
            grid_font_italic=data.get("grid_font_italic", False),
            list_font_family=data.get("list_font_family", ""),
            list_font_ratio=data.get("list_font_ratio", 0.0),
            list_font_bold=data.get("list_font_bold", False),
            list_font_italic=data.get("list_font_italic", False),
        )

    def icon_size_for(self, layout: str) -> int:
        return self.grid_icon_size if layout == LAYOUT_GRID else self.list_icon_size

    def set_icon_size_for(self, layout: str, value: int) -> None:
        if layout == LAYOUT_GRID:
            self.grid_icon_size = value
        else:
            self.list_icon_size = value

    def window_size_for(self, layout: str) -> tuple[int, int]:
        if layout == LAYOUT_GRID:
            return self.grid_window_w, self.grid_window_h
        return self.list_window_w, self.list_window_h

    def set_window_size_for(self, layout: str, width: int, height: int) -> None:
        if layout == LAYOUT_GRID:
            self.grid_window_w, self.grid_window_h = width, height
        else:
            self.list_window_w, self.list_window_h = width, height

    def font_for(self, layout: str) -> tuple[str, float, bool, bool]:
        """(familia, proporción tamaño_letra/tamaño_icono, negrita,
        cursiva) para todos los botones de esta vista. Proporción 0
        significa automática."""
        if layout == LAYOUT_GRID:
            return self.grid_font_family, self.grid_font_ratio, self.grid_font_bold, self.grid_font_italic
        return self.list_font_family, self.list_font_ratio, self.list_font_bold, self.list_font_italic

    def set_font_for(self, layout: str, family: str, ratio: float, bold: bool, italic: bool) -> None:
        if layout == LAYOUT_GRID:
            self.grid_font_family = family
            self.grid_font_ratio = ratio
            self.grid_font_bold = bold
            self.grid_font_italic = italic
        else:
            self.list_font_family = family
            self.list_font_ratio = ratio
            self.list_font_bold = bold
            self.list_font_italic = italic


class ConfigStore:
    """Lee y escribe programas + preferencias en config.json."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> tuple[list[Program], Settings]:
        if not self.path.exists():
            return [], Settings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return [], Settings()
        programs = [Program.from_dict(item) for item in raw.get("programs", [])]
        settings = Settings.from_dict(raw.get("settings", {}))
        return programs, settings

    def save(self, programs: list[Program], settings: Settings) -> None:
        data = {
            "programs": [p.to_dict() for p in programs],
            "settings": settings.to_dict(),
        }
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Icono
# ---------------------------------------------------------------------------
CUSTOM_ICON_NAME = "icono.png"


def extract_icon(path: str, app: QApplication) -> QIcon:
    """Obtiene el icono para el botón.

    Para los .py: si en la misma carpeta del script existe un
    "icono.png", se usa ese. Si no existe, se usa el icono por defecto
    (el de Python, vía el shell de Windows) sin avisar.
    Para los .exe: icono del propio ejecutable (shell de Windows).
    """
    if path.lower().endswith(".py"):
        custom_icon_path = Path(path).resolve().parent / CUSTOM_ICON_NAME
        if custom_icon_path.exists():
            custom_icon = QIcon(str(custom_icon_path))
            if not custom_icon.isNull():
                return custom_icon

    provider = QFileIconProvider()
    icon = provider.icon(QFileInfo(path))
    if icon.isNull():
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    return icon


def cache_icon(icon: QIcon, program_id: str) -> str:
    """Guarda el icono como PNG cuadrado (SIZE_MAX x SIZE_MAX) en icons/ y
    devuelve la ruta relativa.

    Se redimensiona en un único paso con QPixmap.scaled(...,
    IgnoreAspectRatio): el propio dibujo del icono es lo que se estira o
    encoge para llenar el cuadrado exacto, en vez de calcularlo aparte y
    "pegarlo" centrado dentro de un cuadro de relleno. Así el archivo
    cacheado ya sale limpio y a un tamaño consistente pase lo que pase
    con la resolución nativa del icono de origen."""
    ICONS_DIR.mkdir(exist_ok=True)
    file_name = f"{program_id}.png"
    dest = ICONS_DIR / file_name

    source = icon.pixmap(QSize(SIZE_MAX, SIZE_MAX))
    if source.isNull():
        return ""

    square = source.scaled(
        SIZE_MAX, SIZE_MAX,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    square.save(str(dest), "PNG")
    return f"icons/{file_name}"


# ---------------------------------------------------------------------------
# Botón de un programa
# ---------------------------------------------------------------------------
class ProgramButton(QToolButton):
    """Botón que representa un programa registrado. Admite dos vistas:
    'grid' (icono arriba, texto debajo, en rejilla) y 'list' (icono a la
    izquierda, texto a la derecha, uno debajo de otro)."""

    # Espacio horizontal entre icono y texto en la vista de lista.
    LIST_ICON_TEXT_GAP_RATIO = 0.5   # separación = icon_px * este factor
    LIST_ICON_TEXT_GAP_MIN = 14

    def __init__(
        self, program: Program, layout: str, icon_px: int,
        font_family: str, font_ratio: float, font_bold: bool, font_italic: bool,
        parent=None,
    ):
        super().__init__(parent)
        self.program = program
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_view(layout, icon_px, font_family, font_ratio, font_bold, font_italic)

    def apply_view(
        self, layout: str, icon_px: int,
        font_family: str, font_ratio: float, font_bold: bool, font_italic: bool,
    ) -> None:
        self._layout_kind = layout
        self._icon_px = icon_px
        self._font_family = font_family
        self._font_bold = font_bold
        self._font_italic = font_italic
        # Tamaño de letra en proporción al tamaño de icono/botón actual
        # (ver effective_font_px): así, tanto si es automático como si el
        # usuario fijó uno a mano, escala junto con el botón al mover el
        # deslizador de tamaño.
        self._font_px = effective_font_px(icon_px, font_ratio)

        # El tamaño del botón depende solo del icono, no del texto: no se
        # redimensiona para hacerle hueco. En su lugar, el texto se pega
        # al borde superior/inferior (padding vertical mínimo).
        if layout == LAYOUT_GRID:
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            self.setIconSize(QSize(icon_px, icon_px))
            self.setFixedSize(icon_px + 60, icon_px + 50)
            self._extra_style = "padding: 1px 4px;"
        else:
            gap = max(self.LIST_ICON_TEXT_GAP_MIN, round(icon_px * self.LIST_ICON_TEXT_GAP_RATIO))
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            # El icono se dibuja en un lienzo más ancho que alto, con el
            # propio dibujo pegado a la izquierda: el hueco transparente
            # de la derecha es lo que separa visualmente icono y texto.
            self.setIconSize(QSize(icon_px + gap, icon_px))
            self.setFixedHeight(icon_px + 20)
            self.setMinimumWidth(240)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._extra_style = "text-align: left; padding: 1px 12px;"
        self.refresh()

    def refresh(self) -> None:
        self.setText(self.program.name)
        self.setIcon(self._build_icon())

        weight = "bold" if self._font_bold else "normal"
        style = "italic" if self._font_italic else "normal"
        family_css = f'font-family: "{self._font_family}";' if self._font_family else ""

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {self.program.color};
                color: {self.program.text_color};
                border: 1px solid #22252b;
                border-radius: 8px;
                font-size: {self._font_px}px;
                font-weight: {weight};
                font-style: {style};
                {family_css}
                {getattr(self, "_extra_style", "")}
            }}
            QToolButton:hover {{ border: 1px solid #6c9bff; }}
            QToolButton:pressed {{ background-color: #2a2e37; }}
        """)

    def _build_icon(self) -> QIcon:
        """Redimensiona el propio icono al tamaño exacto elegido (en vez
        de dejarlo a un tamaño fijo dentro de un cuadro más grande o más
        pequeño). Como el archivo cacheado ya es cuadrado (ver
        cache_icon), esto no deforma nada; solo lo agranda o encoge.

        Se usa QPixmap + scaled() a propósito en vez de QIcon.pixmap():
        Qt nunca hace zoom hacia arriba con QIcon.pixmap() (solo puede
        devolver un pixmap igual o más pequeño que el pedido), lo que
        dejaba iconos de baja resolución nativa (típico de un .exe) más
        pequeños que uno con un icono.png de alta resolución al llegar a
        tamaños de botón grandes. QPixmap.scaled() sí escala hacia
        arriba, evitando esa diferencia."""
        icon_path = BASE_DIR / self.program.icon if self.program.icon else None
        if not (icon_path and icon_path.exists()):
            return QIcon()

        icon_px = self._icon_px
        raw = QPixmap(str(icon_path))
        if raw.isNull():
            return QIcon()

        resized = raw.scaled(
            icon_px, icon_px,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        if self._layout_kind == LAYOUT_GRID:
            return QIcon(resized)

        gap = max(self.LIST_ICON_TEXT_GAP_MIN, round(icon_px * self.LIST_ICON_TEXT_GAP_RATIO))
        canvas = QPixmap(icon_px + gap, icon_px)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(0, 0, resized)
        painter.end()
        return QIcon(canvas)


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App Launcher")
        self.setWindowIcon(load_app_icon())

        self.store = ConfigStore(CONFIG_PATH)
        self.programs: list[Program]
        self.settings: Settings
        self.programs, self.settings = self.store.load()

        self.resize(*self.settings.window_size_for(self.settings.layout))

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        # -- Barra superior: añadir, vista y tamaño ----------------------
        top_bar = QHBoxLayout()

        add_btn = QPushButton("+  Añadir programa")
        add_btn.clicked.connect(self.add_program)
        top_bar.addWidget(add_btn)

        top_bar.addStretch()

        top_bar.addWidget(QLabel("Vista:"))
        self.view_combo = QComboBox()
        self.view_combo.addItem("Cuadrícula", LAYOUT_GRID)
        self.view_combo.addItem("Lista", LAYOUT_LIST)
        self.view_combo.setCurrentIndex(
            0 if self.settings.layout == LAYOUT_GRID else 1
        )
        self.view_combo.currentIndexChanged.connect(self.on_view_changed)
        top_bar.addWidget(self.view_combo)

        top_bar.addSpacing(16)
        top_bar.addWidget(QLabel("Tamaño:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(SIZE_MIN, SIZE_MAX)
        self.size_slider.setFixedWidth(140)
        self.size_slider.setValue(self.settings.icon_size_for(self.settings.layout))
        self.size_slider.valueChanged.connect(self.on_size_changed)
        top_bar.addWidget(self.size_slider)

        outer.addLayout(top_bar)

        self.empty_label = QLabel(
            "No hay programas todavía.\nPulsa «+ Añadir programa» para empezar."
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #888; padding: 40px;")
        outer.addWidget(self.empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        scroll.setWidget(self.container)
        outer.addWidget(scroll)

        self.rebuild_layout()

    # ------------------------------------------------------------------
    def rebuild_layout(self) -> None:
        """Reconstruye por completo la zona de botones según la vista, el
        tamaño y (en cuadrícula) el número de columnas actuales."""
        # Quitar botones existentes.
        for child in self.container.findChildren(QToolButton):
            child.setParent(None)
            child.deleteLater()

        # Desmontar el layout anterior del contenedor (si lo hay).
        old_layout = self.container.layout()
        if old_layout is not None:
            QWidget().setLayout(old_layout)

        self.empty_label.setVisible(len(self.programs) == 0)

        layout_kind = self.settings.layout
        icon_px = self.settings.icon_size_for(layout_kind)
        font_info = self.settings.font_for(layout_kind)

        if layout_kind == LAYOUT_GRID:
            new_layout = QGridLayout()
            new_layout.setSpacing(12)
            self.container.setLayout(new_layout)
            columns = max(1, self.settings.grid_columns)
            for index, program in enumerate(self.programs):
                row, col = divmod(index, columns)
                btn = self._make_button(program, layout_kind, icon_px, font_info)
                new_layout.addWidget(btn, row, col)
        else:
            new_layout = QVBoxLayout()
            new_layout.setSpacing(6)
            self.container.setLayout(new_layout)
            for program in self.programs:
                btn = self._make_button(program, layout_kind, icon_px, font_info)
                new_layout.addWidget(btn)
            new_layout.addStretch()

    def _make_button(
        self, program: Program, layout_kind: str, icon_px: int,
        font_info: tuple[str, float, bool, bool],
    ) -> ProgramButton:
        font_family, font_ratio, font_bold, font_italic = font_info
        btn = ProgramButton(program, layout_kind, icon_px, font_family, font_ratio, font_bold, font_italic)
        btn.clicked.connect(lambda checked=False, p=program: self.launch(p))
        btn.customContextMenuRequested.connect(
            lambda pos, b=btn: self.show_context_menu(b, pos)
        )
        return btn

    # ------------------------------------------------------------------
    def on_view_changed(self) -> None:
        # Recordar el tamaño de ventana actual para la vista que se deja.
        self.settings.set_window_size_for(self.settings.layout, self.width(), self.height())

        layout_kind = self.view_combo.currentData()
        self.settings.layout = layout_kind

        # Recuperar el tamaño de icono guardado para esta vista, sin
        # disparar rebuild_layout dos veces al tocar el slider.
        self.size_slider.blockSignals(True)
        self.size_slider.setValue(self.settings.icon_size_for(layout_kind))
        self.size_slider.blockSignals(False)

        # Y el tamaño de ventana que tenía la última vez que se usó.
        self.resize(*self.settings.window_size_for(layout_kind))

        self.store.save(self.programs, self.settings)
        self.rebuild_layout()

    def on_size_changed(self, value: int) -> None:
        self.settings.set_icon_size_for(self.settings.layout, value)
        self.store.save(self.programs, self.settings)
        self.rebuild_layout()

    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Solo en memoria; se persiste al cerrar o al cambiar de vista,
        # para no escribir en disco en cada píxel de redimensionado.
        self.settings.set_window_size_for(self.settings.layout, self.width(), self.height())

    def closeEvent(self, event) -> None:
        self.settings.set_window_size_for(self.settings.layout, self.width(), self.height())
        self.store.save(self.programs, self.settings)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    def add_program(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un programa", str(Path.home()),
            "Programas (*.exe *.py);;Ejecutables (*.exe);;Scripts Python (*.py)"
        )
        if not path:
            return

        suggested_name = Path(path).stem
        name, ok = QInputDialog.getText(
            self, "Nombre del programa", "Nombre a mostrar en el botón:",
            text=suggested_name
        )
        if not ok or not name.strip():
            return

        program_type = "py" if path.lower().endswith(".py") else "exe"
        program_id = uuid.uuid4().hex

        icon = extract_icon(path, QApplication.instance())
        icon_rel_path = cache_icon(icon, program_id)

        program = Program(
            id=program_id, name=name.strip(), path=path,
            type=program_type, icon=icon_rel_path, color=DEFAULT_COLOR,
        )
        self.programs.append(program)
        self.store.save(self.programs, self.settings)
        self.rebuild_layout()

    # ------------------------------------------------------------------
    def launch(self, program: Program) -> None:
        work_dir = str(Path(program.path).resolve().parent)
        try:
            if program.type == "py":
                try:
                    subprocess.Popen(["python", program.path], cwd=work_dir)
                except FileNotFoundError:
                    # Si "python" no está en el PATH, usamos el mismo
                    # intérprete con el que corre este lanzador.
                    subprocess.Popen([sys.executable, program.path], cwd=work_dir)
            else:
                subprocess.Popen([program.path], cwd=work_dir)
        except OSError as exc:
            QMessageBox.critical(
                self, "No se pudo iniciar",
                f"No se ha podido iniciar «{program.name}»:\n{exc}"
            )

    # ------------------------------------------------------------------
    def show_context_menu(self, button: ProgramButton, pos) -> None:
        program = button.program
        menu = QMenu(self)

        path_action = menu.addAction(f"📄  {program.path}")
        path_action.setEnabled(False)
        menu.addAction(
            "📋  Copiar ruta",
            lambda: QApplication.clipboard().setText(program.path)
        )
        menu.addSeparator()

        menu.addAction("▶  Ejecutar", lambda: self.launch(program))
        menu.addSeparator()

        menu.addAction("✏️  Cambiar texto del botón...", lambda: self.rename_program(program))
        menu.addAction("🎨  Cambiar color de fondo", lambda: self.change_color(program))
        menu.addAction("🖊  Cambiar color de letra", lambda: self.change_text_color(program))
        menu.addAction("🔤  Fuente del texto (todos los botones)...", self.edit_font)
        menu.addSeparator()

        menu.addAction("⬅  Mover antes", lambda: self.move_program(program, -1))
        menu.addAction("➡  Mover después", lambda: self.move_program(program, 1))

        if self.settings.layout == LAYOUT_GRID:
            menu.addSeparator()
            menu.addAction("🔢  Columnas de la cuadrícula...", self.change_grid_columns)

        menu.addSeparator()
        menu.addAction("🗑  Quitar", lambda: self.remove_program(program))
        menu.exec(button.mapToGlobal(pos))

    # ------------------------------------------------------------------
    def change_grid_columns(self) -> None:
        value, ok = QInputDialog.getInt(
            self, "Columnas de la cuadrícula", "Número de columnas:",
            self.settings.grid_columns, 1, 12, 1
        )
        if ok:
            self.settings.grid_columns = value
            self.store.save(self.programs, self.settings)
            self.rebuild_layout()

    # ------------------------------------------------------------------
    def rename_program(self, program: Program) -> None:
        name, ok = QInputDialog.getText(
            self, "Cambiar texto del botón", "Texto a mostrar en el botón:",
            text=program.name
        )
        if ok and name.strip():
            program.name = name.strip()
            self.store.save(self.programs, self.settings)
            self.rebuild_layout()

    def change_color(self, program: Program) -> None:
        color = QColorDialog.getColor(QColor(program.color), self, "Elige un color de fondo")
        if color.isValid():
            program.color = color.name()
            self.store.save(self.programs, self.settings)
            self.rebuild_layout()

    def edit_font(self) -> None:
        """Ventana de fuente, aplicada a TODOS los botones de la vista
        actual (cuadrícula o lista) — a diferencia de los colores, que
        cada programa puede tener el suyo. El tamaño elegido se guarda
        como proporción respecto al tamaño de icono actual, para que se
        mantenga esa misma proporción si luego cambias el tamaño de
        botón con el deslizador. Nota: en algunos sistemas Qt no usa el
        diálogo nativo de Windows para la fuente (por eso puede aparecer
        en inglés y sin selector de color); el color de letra se cambia
        aparte, con "Cambiar color de letra" (ese sí es 100% nativo)."""
        layout_kind = self.settings.layout
        icon_px = self.settings.icon_size_for(layout_kind)
        family, ratio, bold, italic = self.settings.font_for(layout_kind)
        base_size = effective_font_px(icon_px, ratio)

        current_font = QFont(family or QApplication.font().family(), base_size)
        current_font.setBold(bold)
        current_font.setItalic(italic)

        # PySide6 devuelve (ok, font) -- al revés que en PyQt5 -- así que
        # el orden de desempaquetado importa aquí.
        ok, chosen_font = QFontDialog.getFont(current_font, self, "Fuente del texto")
        if not ok:
            return

        # Algunos diálogos devuelven el tamaño en pixelSize() en vez de
        # pointSize() (que en ese caso da -1); sin este respaldo, el CSS
        # generado ("font-size: -1px") es inválido y Qt lo ignora
        # silenciosamente, dando la sensación de que el cambio no se
        # aplica.
        chosen_size = chosen_font.pointSize()
        if chosen_size <= 0:
            chosen_size = chosen_font.pixelSize()
        if chosen_size <= 0:
            chosen_size = base_size

        chosen_ratio = chosen_size / icon_px if icon_px else FONT_SIZE_RATIO

        self.settings.set_font_for(
            layout_kind, chosen_font.family(), chosen_ratio,
            chosen_font.bold(), chosen_font.italic(),
        )
        self.store.save(self.programs, self.settings)
        self.rebuild_layout()

    def change_text_color(self, program: Program) -> None:
        color = QColorDialog.getColor(QColor(program.text_color), self, "Elige un color de letra")
        if color.isValid():
            program.text_color = color.name()
            self.store.save(self.programs, self.settings)
            self.rebuild_layout()

    # ------------------------------------------------------------------
    def move_program(self, program: Program, direction: int) -> None:
        index = self.programs.index(program)
        new_index = index + direction
        if 0 <= new_index < len(self.programs):
            self.programs[index], self.programs[new_index] = (
                self.programs[new_index], self.programs[index]
            )
            self.store.save(self.programs, self.settings)
            self.rebuild_layout()

    def remove_program(self, program: Program) -> None:
        reply = QMessageBox.question(
            self, "Quitar programa",
            f"¿Seguro que quieres quitar «{program.name}» del menú?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.programs.remove(program)
            self.store.save(self.programs, self.settings)
            if program.icon:
                icon_file = BASE_DIR / program.icon
                if icon_file.exists():
                    icon_file.unlink(missing_ok=True)
            self.rebuild_layout()


def install_qt_translations(app: QApplication) -> None:
    """Intenta cargar las traducciones de Qt para el idioma del sistema,
    para que los diálogos que Qt dibuja por su cuenta (como el de fuente,
    que en Windows no siempre usa el diálogo nativo) aparezcan traducidos
    en vez de quedarse en inglés. Si el paquete de traducciones no está
    presente en la instalación de PySide6, no pasa nada: se sigue viendo
    en inglés, pero la app funciona igual."""
    translator = QTranslator(app)
    locale = QLocale.system()
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(locale, "qtbase", "_", translations_path):
        app.installTranslator(translator)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(load_app_icon())
    install_qt_translations(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
