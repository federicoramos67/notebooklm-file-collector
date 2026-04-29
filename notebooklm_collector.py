#!/usr/bin/env python3
"""NotebookLM File Collector v4.0

Aplicación de escritorio con interfaz gráfica para recopilar, filtrar y
organizar archivos compatibles con Google NotebookLM desde una carpeta y
sus subcarpetas. Crea una carpeta destino elegida por el usuario con sufijo
``_notebooklm`` y, cuando hay más de 50 archivos, los distribuye en
sub-carpetas (lotes) agrupadas por tipo. Permite ordenar los archivos
según el criterio elegido antes de copiarlos.

Uso:
    python notebooklm_collector_v4.py
"""

import logging
import os
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Tkinter availability check
# ---------------------------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk
except ModuleNotFoundError:
    print(
        "ERROR: El módulo 'tkinter' no está instalado.\n"
        "En Linux instalalo con:  sudo apt install python3-tk\n"
        "En Windows / macOS viene incluido con Python."
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "4.0"
APP_TITLE = f"NotebookLM File Collector v{VERSION}"

EXTENSIONES_PERMITIDAS: frozenset = frozenset({
    ".pdf", ".docx", ".txt", ".md", ".csv", ".pptx",
    ".avif", ".bmp", ".gif", ".heic", ".heif", ".ico",
    ".jp2", ".jpe", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp",
    ".3g2", ".3gp", ".aac", ".aif", ".aifc", ".aiff", ".amr",
    ".au", ".avi", ".cda", ".m4a", ".mid", ".mp3", ".mp4", ".mpeg",
    ".ogg", ".opus", ".ra", ".ram", ".snd", ".wav", ".wma",
    ".epub",
})

LIMITE_TAMANO_MB: int = 200
LIMITE_ARCHIVOS_LOTE: int = 50
PRIORIDAD_EXTENSIONES: List[str] = [".txt", ".md", ".docx", ".pdf", ".csv"]

OPCIONES_ORDEN = [
    "Nombre (A -> Z)",
    "Nombre (Z -> A)",
    "Fecha de modificacion (mas nuevo primero)",
    "Fecha de modificacion (mas antiguo primero)",
    "Tamano (mayor primero)",
    "Tamano (menor primero)",
    "Tipo / Extension",
]

# Paleta de colores -- tema oscuro
C = {
    "bg":        "#0f1117",
    "panel":     "#1a1d27",
    "card":      "#22263a",
    "border":    "#2e3250",
    "accent":    "#4f8ef7",
    "accent2":   "#7c5cfc",
    "success":   "#2dd4a0",
    "warning":   "#f7c94f",
    "danger":    "#f75f5f",
    "text":      "#e8eaf0",
    "text_dim":  "#7a80a0",
    "btn_start": "#2dd4a0",
    "btn_stop":  "#f75f5f",
    "btn_clean": "#4f8ef7",
}

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.NullHandler()],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _agrupar_por_extension(
    archivos: List[Tuple[Path, str]]
) -> Dict[str, List[Path]]:
    """Agrupa una lista de (path, ext) en un dict {ext: [path, ...]}."""
    grupos: Dict[str, List[Path]] = {}
    for path, ext in archivos:
        grupos.setdefault(ext, []).append(path)
    return grupos


def _ordenar_extensiones(grupos: Dict[str, List[Path]]) -> List[str]:
    """Devuelve las extensiones ordenadas con las de mayor prioridad primero."""
    return sorted(
        grupos.keys(),
        key=lambda x: (x not in PRIORIDAD_EXTENSIONES, x),
    )


def _aplicar_orden(paths: List[Path], criterio: str) -> List[Path]:
    """Ordena una lista de Path segun el criterio elegido por el usuario.

    Args:
        paths: Lista de rutas a ordenar.
        criterio: String con el nombre del criterio (debe coincidir con OPCIONES_ORDEN).

    Returns:
        Nueva lista ordenada.
    """
    if criterio == "Nombre (A -> Z)":
        return sorted(paths, key=lambda p: p.name.lower())
    elif criterio == "Nombre (Z -> A)":
        return sorted(paths, key=lambda p: p.name.lower(), reverse=True)
    elif criterio == "Fecha de modificacion (mas nuevo primero)":
        return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
    elif criterio == "Fecha de modificacion (mas antiguo primero)":
        return sorted(paths, key=lambda p: p.stat().st_mtime)
    elif criterio == "Tamano (mayor primero)":
        return sorted(paths, key=lambda p: p.stat().st_size, reverse=True)
    elif criterio == "Tamano (menor primero)":
        return sorted(paths, key=lambda p: p.stat().st_size)
    elif criterio == "Tipo / Extension":
        return sorted(paths, key=lambda p: (p.suffix.lower(), p.name.lower()))
    return paths


# ---------------------------------------------------------------------------
# Tooltip helper
# ---------------------------------------------------------------------------

class Tooltip:
    """Tooltip simple para widgets Tkinter."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None) -> None:
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=self.text,
            bg="#2e3250",
            fg="#e8eaf0",
            font=("Courier New", 9),
            padx=8,
            pady=4,
            relief="flat",
        ).pack()

    def _hide(self, _event=None) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ---------------------------------------------------------------------------
# Main application class
# ---------------------------------------------------------------------------

class NotebookLMCollector:
    """Ventana principal de la aplicacion NotebookLM File Collector v4."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("820x800")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)

        self.origen: str = ""
        self.destino: str = ""
        self.cancelar: bool = False
        self.validos_list: List[Tuple[Path, str]] = []
        self._running: bool = False

        self._setup_styles()
        self._setup_ui()

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def _setup_styles(self) -> None:
        """Configura estilos ttk para combobox y progressbar."""
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Dark.TCombobox",
            fieldbackground=C["card"],
            background=C["card"],
            foreground=C["text"],
            selectbackground=C["accent"],
            selectforeground=C["text"],
            arrowcolor=C["accent"],
            bordercolor=C["border"],
            lightcolor=C["border"],
            darkcolor=C["border"],
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", C["card"])],
        )
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=C["card"],
            background=C["accent"],
            bordercolor=C["border"],
            lightcolor=C["accent"],
            darkcolor=C["accent2"],
        )

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------

    def _make_button(self, parent, text, command, color, width=20, **kwargs):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Courier New", 10, "bold"),
            bg=color,
            fg=C["bg"],
            activebackground=C["text"],
            activeforeground=C["bg"],
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            cursor="hand2",
            width=width,
            **kwargs,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=C["text"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    def _make_entry(self, parent, **kwargs):
        return tk.Entry(
            parent,
            font=("Courier New", 10),
            bg=C["card"],
            fg=C["text"],
            insertbackground=C["accent"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightcolor=C["accent"],
            highlightbackground=C["border"],
            **kwargs,
        )

    def _section_label(self, parent, text, pady_top=0):
        """Etiqueta de seccion con linea decorativa."""
        frm = tk.Frame(parent, bg=C["bg"])
        frm.pack(fill="x", pady=(pady_top, 2))
        tk.Label(
            frm,
            text=text,
            font=("Courier New", 8, "bold"),
            bg=C["bg"],
            fg=C["text_dim"],
        ).pack(side="left")
        tk.Frame(frm, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=6
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Construye todos los widgets de la interfaz."""

        # ── HEADER ──────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=C["panel"], pady=16)
        header.pack(fill="x")
        tk.Label(
            header,
            text="  NotebookLM File Collector",
            font=("Courier New", 16, "bold"),
            bg=C["panel"],
            fg=C["accent"],
        ).pack()
        tk.Label(
            header,
            text=f"v{VERSION}  .  Organizador de archivos para Google NotebookLM",
            font=("Courier New", 9),
            bg=C["panel"],
            fg=C["text_dim"],
        ).pack()

        tk.Frame(self.root, bg=C["accent2"], height=2).pack(fill="x")

        # ── BODY ────────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=C["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # ── SECCION: CARPETA ORIGEN ──────────────────────────────────────
        self._section_label(body, "1  CARPETA ORIGEN")
        row_orig = tk.Frame(body, bg=C["bg"])
        row_orig.pack(fill="x", pady=(4, 0))
        self.ent_orig = self._make_entry(row_orig)
        self.ent_orig.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        btn_orig = self._make_button(
            row_orig, "Explorar...", self._seleccionar_origen,
            color=C["accent"], width=14
        )
        btn_orig.pack(side="left")
        Tooltip(btn_orig, "Elegir la carpeta que queres escanear")

        # ── SECCION: CARPETA DESTINO ─────────────────────────────────────
        self._section_label(body, "2  CARPETA DESTINO", pady_top=14)
        row_dest = tk.Frame(body, bg=C["bg"])
        row_dest.pack(fill="x", pady=(4, 0))
        self.ent_dest = self._make_entry(row_dest)
        self.ent_dest.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        btn_dest = self._make_button(
            row_dest, "Cambiar...", self._seleccionar_destino,
            color=C["accent2"], width=14
        )
        btn_dest.pack(side="left")
        Tooltip(btn_dest, "Elegir donde se crea la carpeta _notebooklm")

        # ── SECCION: ORDEN DE ARCHIVOS ───────────────────────────────────
        self._section_label(body, "3  ORDEN DE ARCHIVOS DENTRO DE CADA LOTE", pady_top=14)
        row_orden = tk.Frame(body, bg=C["bg"])
        row_orden.pack(fill="x", pady=(4, 0))
        self.orden_var = tk.StringVar(value=OPCIONES_ORDEN[0])
        self.cmb_orden = ttk.Combobox(
            row_orden,
            textvariable=self.orden_var,
            values=OPCIONES_ORDEN,
            state="readonly",
            font=("Courier New", 10),
            style="Dark.TCombobox",
        )
        self.cmb_orden.pack(side="left", fill="x", expand=True, ipady=4)
        self.cmb_orden.bind("<<ComboboxSelected>>", self._on_orden_changed)
        Tooltip(self.cmb_orden, "Como se ordenan los archivos dentro de cada lote al copiar")

        # ── SECCION: PLAN ────────────────────────────────────────────────
        self._section_label(body, "4  PLAN DE ORGANIZACION", pady_top=14)
        self.txt_plan = scrolledtext.ScrolledText(
            body,
            height=7,
            font=("Courier New", 9),
            bg=C["card"],
            fg=C["success"],
            insertbackground=C["accent"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightcolor=C["border"],
            highlightbackground=C["border"],
            wrap="none",
        )
        self.txt_plan.pack(fill="x", pady=(4, 0))

        # ── STATS BAR ────────────────────────────────────────────────────
        self.lbl_stats = tk.Label(
            body,
            text="  Selecciona una carpeta para empezar",
            font=("Courier New", 9),
            bg=C["bg"],
            fg=C["text_dim"],
            anchor="w",
        )
        self.lbl_stats.pack(fill="x", pady=(6, 0))

        # ── BARRA DE PROGRESO ────────────────────────────────────────────
        self.progress = ttk.Progressbar(
            body,
            mode="indeterminate",
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x", pady=(6, 0))

        # ── BOTONES ──────────────────────────────────────────────────────
        row_btn = tk.Frame(body, bg=C["bg"])
        row_btn.pack(pady=14)

        self.btn_inicio = self._make_button(
            row_btn, "  Iniciar recopilacion",
            self._iniciar_proceso, color=C["btn_start"], width=22
        )
        self.btn_inicio.config(state="disabled")
        self.btn_inicio.pack(side="left", padx=6)
        Tooltip(self.btn_inicio, "Copiar archivos al destino segun el plan")

        self.btn_cancelar = self._make_button(
            row_btn, "  Cancelar",
            self._cancelar_proceso, color=C["btn_stop"], width=14
        )
        self.btn_cancelar.config(state="disabled")
        self.btn_cancelar.pack(side="left", padx=6)

        self.btn_limpiar = self._make_button(
            row_btn, "  Limpiar",
            self._limpiar_todo, color=C["btn_clean"], width=14
        )
        self.btn_limpiar.pack(side="left", padx=6)
        Tooltip(self.btn_limpiar, "Resetear todos los campos")

        # ── LOG ──────────────────────────────────────────────────────────
        self._section_label(body, "5  REGISTRO DE OPERACIONES")
        self.txt_log = scrolledtext.ScrolledText(
            body,
            height=10,
            font=("Courier New", 9),
            bg=C["panel"],
            fg=C["text"],
            insertbackground=C["accent"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightcolor=C["border"],
            highlightbackground=C["border"],
            wrap="none",
        )
        self.txt_log.pack(fill="both", expand=True, pady=(4, 0))
        self.txt_log.tag_config("ok",    foreground=C["success"])
        self.txt_log.tag_config("error", foreground=C["danger"])
        self.txt_log.tag_config("warn",  foreground=C["warning"])
        self.txt_log.tag_config("info",  foreground=C["accent"])
        self.txt_log.tag_config("dim",   foreground=C["text_dim"])

        self.btn_save_log = self._make_button(
            body, "  Guardar log",
            self._guardar_log, color=C["border"], width=18
        )
        self.btn_save_log.config(state="disabled", fg=C["text"])
        self.btn_save_log.pack(pady=(8, 0))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_orden_changed(self, _event=None) -> None:
        """Actualiza el texto de stats cuando cambia el criterio de orden."""
        if self.validos_list:
            n = len(self.validos_list)
            self.lbl_stats.config(
                text=f"  {n} archivos listos  .  orden: {self.orden_var.get()}",
                fg=C["success"],
            )

    # ------------------------------------------------------------------
    # Folder selection & analysis
    # ------------------------------------------------------------------

    def _seleccionar_origen(self) -> None:
        """Abre el dialogo de seleccion de carpeta origen y lanza el analisis."""
        path = filedialog.askdirectory(title="Seleccionar carpeta origen")
        if not path:
            return
        self.origen = path
        self.ent_orig.delete(0, "end")
        self.ent_orig.insert(0, path)

        origen_path = Path(path)
        destino_default = str(
            origen_path.parent / (origen_path.name + "_notebooklm")
        )
        self.destino = destino_default
        self.ent_dest.delete(0, "end")
        self.ent_dest.insert(0, destino_default)

        self._analizar_carpeta()

    def _seleccionar_destino(self) -> None:
        """Permite al usuario elegir manualmente donde se creara la carpeta destino."""
        path = filedialog.askdirectory(
            title="Elegir carpeta contenedora del destino _notebooklm"
        )
        if not path:
            return

        if self.origen:
            nombre_dest = Path(self.origen).name + "_notebooklm"
            self.destino = str(Path(path) / nombre_dest)
        else:
            self.destino = str(Path(path) / "_notebooklm")

        self.ent_dest.delete(0, "end")
        self.ent_dest.insert(0, self.destino)

        if self.validos_list:
            self._refrescar_plan()

    def _analizar_carpeta(self) -> None:
        """Escanea recursivamente la carpeta origen y clasifica los archivos."""
        validos: List[Tuple[Path, str]] = []
        muy_grandes: List[Path] = []
        limite_bytes = LIMITE_TAMANO_MB * 1024 * 1024

        for root_dir, _dirs, files in os.walk(self.origen):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext not in EXTENSIONES_PERMITIDAS:
                    continue
                full_path = Path(root_dir) / file
                try:
                    size = full_path.stat().st_size
                except OSError as exc:
                    logger.warning("No se pudo leer '%s': %s", full_path, exc)
                    continue
                if size <= limite_bytes:
                    validos.append((full_path, ext))
                else:
                    muy_grandes.append(full_path)

        self.validos_list = validos
        self._mostrar_plan(validos, muy_grandes)

    def _refrescar_plan(self) -> None:
        """Recalcula el plan usando archivos ya analizados (tras cambio de destino)."""
        self._mostrar_plan(self.validos_list, [])

    # ------------------------------------------------------------------
    # Plan preview
    # ------------------------------------------------------------------

    def _mostrar_plan(
        self,
        validos: List[Tuple[Path, str]],
        muy_grandes: List[Path],
    ) -> None:
        """Renderiza el plan de organizacion en el panel de vista previa."""
        self.txt_plan.delete("1.0", "end")

        if not validos:
            self.lbl_stats.config(
                text="  No se encontraron archivos compatibles", fg=C["danger"]
            )
            self.btn_inicio.config(state="disabled")
            return

        grupos = _agrupar_por_extension(validos)
        exts_ordenadas = _ordenar_extensiones(grupos)

        lines: List[str] = [f"Destino  ->  {self.destino}\n\n"]

        if len(validos) <= LIMITE_ARCHIVOS_LOTE:
            lines.append(
                f"Total: {len(validos)} archivos  (entran en carpeta unica)\n\n"
            )
            for ext in exts_ordenadas:
                lines.append(f"  .  {len(grupos[ext]):>3} archivos  {ext}\n")
        else:
            lines.append(
                f"Total: {len(validos)} archivos  ->  se dividiran en lotes por tipo\n\n"
            )
            lote_num = 1
            for ext in exts_ordenadas:
                count = len(grupos[ext])
                tipo = ext.lstrip(".")
                if count <= LIMITE_ARCHIVOS_LOTE:
                    lines.append(
                        f"  Lote{lote_num:02d}_{tipo:<12}  {count:>3} archivos\n"
                    )
                    lote_num += 1
                else:
                    sublotes = -(-count // LIMITE_ARCHIVOS_LOTE)
                    for i in range(1, sublotes + 1):
                        archs = (
                            LIMITE_ARCHIVOS_LOTE
                            if i < sublotes
                            else (count % LIMITE_ARCHIVOS_LOTE or LIMITE_ARCHIVOS_LOTE)
                        )
                        lines.append(
                            f"  Lote{lote_num:02d}_{tipo}_{i:<10}  {archs:>3} archivos\n"
                        )
                    lote_num += 1

        if muy_grandes:
            lines.append(
                f"\n  {len(muy_grandes)} archivo(s) omitidos por superar {LIMITE_TAMANO_MB} MB\n"
            )

        self.txt_plan.insert("1.0", "".join(lines))
        self.lbl_stats.config(
            text=f"  {len(validos)} archivos listos  .  orden: {self.orden_var.get()}",
            fg=C["success"],
        )
        self.btn_inicio.config(state="normal")

    # ------------------------------------------------------------------
    # Copy process
    # ------------------------------------------------------------------

    def _iniciar_proceso(self) -> None:
        """Inicia el hilo de copia si no hay uno ya en ejecucion."""
        if self._running:
            return
        self._running = True
        self.cancelar = False
        self.btn_inicio.config(state="disabled")
        self.btn_cancelar.config(state="normal")
        self.btn_save_log.config(state="disabled")
        self.txt_log.delete("1.0", "end")
        self.progress.start(12)
        threading.Thread(target=self._ejecutar_copia, daemon=True).start()

    def _ejecutar_copia(self) -> None:
        """Copia los archivos validos al destino (se ejecuta en hilo separado)."""
        try:
            dest_path = Path(self.destino)
            dest_path.mkdir(parents=True, exist_ok=True)

            validos = self.validos_list
            grupos = _agrupar_por_extension(validos)
            exts_ordenadas = _ordenar_extensiones(grupos)
            criterio = self.orden_var.get()

            copiados = 0
            total = len(validos)

            self._log(f"Iniciando copia  .  {total} archivos  .  orden: {criterio}\n", "info")

            if total <= LIMITE_ARCHIVOS_LOTE:
                for ext in exts_ordenadas:
                    paths_ordenados = _aplicar_orden(grupos[ext], criterio)
                    for arch in paths_ordenados:
                        if self.cancelar:
                            break
                        try:
                            shutil.copy2(arch, dest_path / arch.name)
                            self._log(f"  OK  {arch.name}", "ok")
                            copiados += 1
                            self._log_progreso(copiados, total)
                        except OSError as exc:
                            self._log(f"  ERR {arch.name}: {exc}", "error")
                            logger.error("copy2 failed for '%s': %s", arch, exc)
            else:
                lote_idx = 1
                for ext in exts_ordenadas:
                    if self.cancelar:
                        break
                    tipo = ext.lstrip(".")
                    archivos = _aplicar_orden(grupos[ext], criterio)

                    if len(archivos) <= LIMITE_ARCHIVOS_LOTE:
                        lote_dir = dest_path / f"Lote{lote_idx:02d}_{tipo}"
                        lote_dir.mkdir(exist_ok=True)
                        self._log(f"\n  [{lote_dir.name}]", "info")
                        for arch in archivos:
                            if self.cancelar:
                                break
                            try:
                                shutil.copy2(arch, lote_dir / arch.name)
                                self._log(f"    OK  {arch.name}", "ok")
                                copiados += 1
                                self._log_progreso(copiados, total)
                            except OSError as exc:
                                self._log(f"    ERR {arch.name}: {exc}", "error")
                                logger.error("copy2 failed for '%s': %s", arch, exc)
                        lote_idx += 1
                    else:
                        sublote = 1
                        for i in range(0, len(archivos), LIMITE_ARCHIVOS_LOTE):
                            if self.cancelar:
                                break
                            lote_dir = dest_path / f"Lote{lote_idx:02d}_{tipo}_{sublote}"
                            lote_dir.mkdir(exist_ok=True)
                            self._log(f"\n  [{lote_dir.name}]", "info")
                            chunk = archivos[i: i + LIMITE_ARCHIVOS_LOTE]
                            for arch in chunk:
                                if self.cancelar:
                                    break
                                try:
                                    shutil.copy2(arch, lote_dir / arch.name)
                                    self._log(f"    OK  {arch.name}", "ok")
                                    copiados += 1
                                    self._log_progreso(copiados, total)
                                except OSError as exc:
                                    self._log(f"    ERR {arch.name}: {exc}", "error")
                                    logger.error("copy2 failed for '%s': %s", arch, exc)
                            sublote += 1
                        lote_idx += 1

            status = "FINALIZADO" if not self.cancelar else "CANCELADO"
            self._log(f"\n  {status}  .  {copiados}/{total} archivos copiados", "info")
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Proceso terminado",
                    f"{status}\nArchivos procesados: {copiados}",
                ),
            )

        except Exception as exc:
            self._log(f"  ERROR inesperado: {exc}", "error")
            logger.exception("Unexpected error during copy")
        finally:
            self._running = False
            self.root.after(0, self._restaurar_botones)

    def _log_progreso(self, copiados: int, total: int) -> None:
        """Escribe una linea de progreso cada 10 archivos."""
        if copiados % 10 == 0:
            pct = int(copiados / total * 100)
            self._log(f"   -> {copiados}/{total}  ({pct}%)", "dim")

    def _restaurar_botones(self) -> None:
        """Rehabilita los controles de la UI tras finalizar la copia."""
        self.progress.stop()
        self.btn_cancelar.config(state="disabled")
        self.btn_save_log.config(state="normal")
        self.btn_inicio.config(state="normal")

    # ------------------------------------------------------------------
    # Thread-safe logging
    # ------------------------------------------------------------------

    def _log(self, msg: str, tag: str = "ok") -> None:
        """Inserta msg en el widget de log de forma thread-safe con color."""
        self.root.after(0, self._log_insert, msg, tag)

    def _log_insert(self, msg: str, tag: str) -> None:
        """Escribe directamente en el widget de log (hilo principal)."""
        self.txt_log.insert("end", msg + "\n", tag)
        self.txt_log.see("end")

    # ------------------------------------------------------------------
    # Control actions
    # ------------------------------------------------------------------

    def _cancelar_proceso(self) -> None:
        """Senaliza al hilo de copia que debe detenerse."""
        self.cancelar = True

    def _limpiar_todo(self) -> None:
        """Limpia todos los campos y reestablece el estado inicial."""
        self.ent_orig.delete(0, "end")
        self.ent_dest.delete(0, "end")
        self.txt_plan.delete("1.0", "end")
        self.txt_log.delete("1.0", "end")
        self.lbl_stats.config(
            text="  Selecciona una carpeta para empezar", fg=C["text_dim"]
        )
        self.btn_inicio.config(state="disabled")
        self.btn_save_log.config(state="disabled")
        self.origen = ""
        self.destino = ""
        self.validos_list = []

    def _guardar_log(self) -> None:
        """Abre un dialogo para guardar el contenido del log en un archivo .txt."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"log_notebooklm_{timestamp}.txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos", "*.*")],
        )
        if not file:
            return
        try:
            with open(file, "w", encoding="utf-8") as fh:
                fh.write(self.txt_log.get("1.0", "end"))
        except OSError as exc:
            messagebox.showerror("Error al guardar", str(exc))
            logger.error("Could not save log to '%s': %s", file, exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = NotebookLMCollector(root)
    root.mainloop()
