#!/usr/bin/env python3
"""NotebookLM File Collector.

Aplicación de escritorio con interfaz gráfica para recopilar, filtrar y
organizar archivos compatibles con Google NotebookLM desde una carpeta y
sus subcarpetas.  Crea una carpeta destino automática con sufijo
``_notebooklm`` y, cuando hay más de 50 archivos, los distribuye en
sub-carpetas (lotes) agrupadas por tipo.

Uso:
    python notebooklm_collector.py
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
# Tkinter availability check — gives a friendly error on headless / no-tk systems
# ---------------------------------------------------------------------------
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext
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
VERSION = "3.6"
APP_TITLE = f"NotebookLM File Collector v{VERSION}"

# Extensiones soportadas por NotebookLM
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

# Extensiones que aparecen primero en el plan y en la copia
PRIORIDAD_EXTENSIONES: List[str] = [".txt", ".md", ".docx", ".pdf", ".csv"]

# ---------------------------------------------------------------------------
# Logging setup (debug/error only — UX output stays as print/tk)
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
    """Agrupa una lista de (path, ext) en un dict {ext: [path, ...]}.

    Args:
        archivos: Lista de tuplas ``(path, extension)``.

    Returns:
        Diccionario donde cada clave es una extensión y el valor es la lista
        de rutas correspondientes.
    """
    grupos: Dict[str, List[Path]] = {}
    for path, ext in archivos:
        grupos.setdefault(ext, []).append(path)
    return grupos


def _ordenar_extensiones(grupos: Dict[str, List[Path]]) -> List[str]:
    """Devuelve las extensiones ordenadas con las de mayor prioridad primero.

    Args:
        grupos: Diccionario ``{ext: [paths]}``.

    Returns:
        Lista de extensiones ordenadas.
    """
    return sorted(
        grupos.keys(),
        key=lambda x: (x not in PRIORIDAD_EXTENSIONES, x),
    )


# ---------------------------------------------------------------------------
# Main application class
# ---------------------------------------------------------------------------

class NotebookLMCollector:
    """Ventana principal de la aplicación NotebookLM File Collector."""

    def __init__(self, root: tk.Tk) -> None:
        """Inicializa la ventana y configura la interfaz.

        Args:
            root: Ventana raíz de Tkinter.
        """
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("760x680")

        self.origen: str = ""
        self.destino: str = ""
        self.cancelar: bool = False
        self.stats: dict = {}
        self.validos_list: List[Tuple[Path, str]] = []
        self._running: bool = False  # guard against concurrent copy threads

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Construye todos los widgets de la interfaz."""
        # Header
        tk.Label(
            self.root,
            text=APP_TITLE,
            font=("Arial", 14, "bold"),
        ).pack(pady=10)

        # Origen
        frame_orig = tk.Frame(self.root)
        frame_orig.pack(fill="x", padx=20)
        tk.Label(frame_orig, text="Carpeta Origen:").pack(side="left")
        self.ent_orig = tk.Entry(frame_orig)
        self.ent_orig.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(
            frame_orig, text="Explorar...", command=self._seleccionar_origen
        ).pack(side="left")

        # Panel Vista Previa (Plan de lotes)
        tk.Label(self.root, text="Plan de organización:").pack(
            anchor="w", padx=20, pady=(10, 0)
        )
        self.txt_plan = scrolledtext.ScrolledText(
            self.root, height=8, bg="#f0fff0", wrap="none"
        )
        self.txt_plan.pack(fill="x", padx=20)

        # Stats bar
        self.lbl_stats = tk.Label(
            self.root, text="Seleccione una carpeta para empezar", fg="blue"
        )
        self.lbl_stats.pack(pady=5)

        # Botones Control
        frame_ctrl = tk.Frame(self.root)
        frame_ctrl.pack(pady=10)
        self.btn_inicio = tk.Button(
            frame_ctrl,
            text="▶ Iniciar recopilación",
            state="disabled",
            command=self._iniciar_proceso,
        )
        self.btn_inicio.pack(side="left", padx=5)
        self.btn_cancelar = tk.Button(
            frame_ctrl,
            text="⛔ Cancelar",
            state="disabled",
            command=self._cancelar_proceso,
        )
        self.btn_cancelar.pack(side="left", padx=5)
        self.btn_limpiar = tk.Button(
            frame_ctrl, text="🗑 Limpiar", command=self._limpiar_todo
        )
        self.btn_limpiar.pack(side="left", padx=5)

        # Log
        tk.Label(self.root, text="Registro de operaciones:").pack(
            anchor="w", padx=20
        )
        self.txt_log = scrolledtext.ScrolledText(
            self.root, height=12, wrap="none"
        )
        self.txt_log.pack(fill="both", expand=True, padx=20, pady=5)

        self.btn_save_log = tk.Button(
            self.root,
            text="💾 Guardar log",
            state="disabled",
            command=self._guardar_log,
        )
        self.btn_save_log.pack(pady=5)

    # ------------------------------------------------------------------
    # Folder selection & analysis
    # ------------------------------------------------------------------

    def _seleccionar_origen(self) -> None:
        """Abre el diálogo de selección de carpeta y lanza el análisis."""
        path = filedialog.askdirectory()
        if not path:
            return
        self.origen = path
        self.ent_orig.delete(0, "end")
        self.ent_orig.insert(0, path)
        # Build dest path with pathlib for cross-platform safety
        origen_path = Path(path)
        self.destino = str(
            origen_path.parent / (origen_path.name + "_notebooklm")
        )
        self._analizar_carpeta()

    def _analizar_carpeta(self) -> None:
        """Escanea recursivamente la carpeta origen y clasifica los archivos."""
        self.stats = {}
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

    # ------------------------------------------------------------------
    # Plan preview
    # ------------------------------------------------------------------

    def _mostrar_plan(
        self,
        validos: List[Tuple[Path, str]],
        muy_grandes: List[Path],
    ) -> None:
        """Renderiza el plan de organización en el panel de vista previa.

        Args:
            validos: Archivos que cumplen criterios de extensión y tamaño.
            muy_grandes: Archivos omitidos por superar el límite de tamaño.
        """
        self.txt_plan.delete("1.0", "end")

        if not validos:
            self.lbl_stats.config(
                text="No se encontraron archivos compatibles", fg="red"
            )
            self.btn_inicio.config(state="disabled")
            return

        grupos = _agrupar_por_extension(validos)
        exts_ordenadas = _ordenar_extensiones(grupos)

        lines: List[str] = [f"Destino: {self.destino}\n"]

        if len(validos) <= LIMITE_ARCHIVOS_LOTE:
            lines.append(
                f"Total archivos: {len(validos)} (Caben en carpeta única)\n"
            )
            for ext in exts_ordenadas:
                lines.append(f"  - {len(grupos[ext])} archivos {ext}\n")
        else:
            lines.append(
                f"Total archivos: {len(validos)} "
                f"(Se organizarán en lotes por tipo)\n"
            )
            lote_num = 1
            for ext in exts_ordenadas:
                count = len(grupos[ext])
                tipo = ext.lstrip(".")
                if count <= LIMITE_ARCHIVOS_LOTE:
                    lines.append(
                        f"  📁 Lote{lote_num}_{tipo}: {count} archivos\n"
                    )
                    lote_num += 1
                else:
                    sublotes = -(-count // LIMITE_ARCHIVOS_LOTE)  # ceiling div
                    for i in range(1, sublotes + 1):
                        archs = (
                            LIMITE_ARCHIVOS_LOTE
                            if i < sublotes
                            else (count % LIMITE_ARCHIVOS_LOTE or LIMITE_ARCHIVOS_LOTE)
                        )
                        lines.append(
                            f"  📁 Lote{lote_num}_{tipo}_{i}: {archs} archivos\n"
                        )
                    lote_num += 1

        if muy_grandes:
            lines.append(
                f"\n⚠️  {len(muy_grandes)} archivo(s) omitido(s) por superar "
                f"{LIMITE_TAMANO_MB} MB\n"
            )

        self.txt_plan.insert("1.0", "".join(lines))
        self.lbl_stats.config(
            text=f"✅ {len(validos)} archivos listos para organizar",
            fg="green",
        )
        self.btn_inicio.config(state="normal")

    # ------------------------------------------------------------------
    # Copy process
    # ------------------------------------------------------------------

    def _iniciar_proceso(self) -> None:
        """Inicia el hilo de copia si no hay uno ya en ejecución."""
        if self._running:
            return
        self._running = True
        self.cancelar = False
        self.btn_inicio.config(state="disabled")
        self.btn_cancelar.config(state="normal")
        self.btn_save_log.config(state="disabled")
        self.txt_log.delete("1.0", "end")
        threading.Thread(target=self._ejecutar_copia, daemon=True).start()

    def _ejecutar_copia(self) -> None:
        """Copia los archivos válidos al destino (se ejecuta en hilo separado)."""
        try:
            dest_path = Path(self.destino)
            dest_path.mkdir(parents=True, exist_ok=True)

            validos = self.validos_list
            grupos = _agrupar_por_extension(validos)
            exts_ordenadas = _ordenar_extensiones(grupos)

            copiados = 0
            total = len(validos)

            if total <= LIMITE_ARCHIVOS_LOTE:
                for ext in exts_ordenadas:
                    for arch in grupos[ext]:
                        if self.cancelar:
                            break
                        try:
                            shutil.copy2(arch, dest_path / arch.name)
                            self._log(f"🟢 Copiado: {arch.name}")
                            copiados += 1
                            self._log_progreso(copiados, total)
                        except OSError as exc:
                            self._log(f"🔴 Error copiando {arch.name}: {exc}")
                            logger.error("copy2 failed for '%s': %s", arch, exc)
            else:
                lote_idx = 1
                for ext in exts_ordenadas:
                    if self.cancelar:
                        break
                    tipo = ext.lstrip(".")
                    archivos = grupos[ext]

                    if len(archivos) <= LIMITE_ARCHIVOS_LOTE:
                        lote_dir = dest_path / f"Lote{lote_idx}_{tipo}"
                        lote_dir.mkdir(exist_ok=True)
                        for arch in archivos:
                            if self.cancelar:
                                break
                            try:
                                shutil.copy2(arch, lote_dir / arch.name)
                                self._log(f"🟢 [{tipo}] -> {arch.name}")
                                copiados += 1
                                self._log_progreso(copiados, total)
                            except OSError as exc:
                                self._log(
                                    f"🔴 Error copiando {arch.name}: {exc}"
                                )
                                logger.error(
                                    "copy2 failed for '%s': %s", arch, exc
                                )
                        lote_idx += 1
                    else:
                        sublote = 1
                        for i in range(0, len(archivos), LIMITE_ARCHIVOS_LOTE):
                            if self.cancelar:
                                break
                            lote_dir = (
                                dest_path / f"Lote{lote_idx}_{tipo}_{sublote}"
                            )
                            lote_dir.mkdir(exist_ok=True)
                            chunk = archivos[i : i + LIMITE_ARCHIVOS_LOTE]
                            for arch in chunk:
                                if self.cancelar:
                                    break
                                try:
                                    shutil.copy2(arch, lote_dir / arch.name)
                                    self._log(
                                        f"🟢 [{tipo}_{sublote}] -> {arch.name}"
                                    )
                                    copiados += 1
                                    self._log_progreso(copiados, total)
                                except OSError as exc:
                                    self._log(
                                        f"🔴 Error copiando {arch.name}: {exc}"
                                    )
                                    logger.error(
                                        "copy2 failed for '%s': %s", arch, exc
                                    )
                            sublote += 1
                        lote_idx += 1

            status = "✅ Finalizado" if not self.cancelar else "⛔ Cancelado"
            self._log(f"\n--- {status} --- total: {copiados} archivos")
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Proceso terminado",
                    f"{status}\nArchivos procesados: {copiados}",
                ),
            )

        except Exception as exc:  # noqa: BLE001
            self._log(f"🔴 ERROR inesperado: {exc}")
            logger.exception("Unexpected error during copy")
        finally:
            self._running = False
            self.root.after(0, self._restaurar_botones)

    def _log_progreso(self, copiados: int, total: int) -> None:
        """Escribe una línea de progreso periódica cada 10 archivos.

        Args:
            copiados: Cantidad de archivos copiados hasta el momento.
            total: Total de archivos a copiar.
        """
        if copiados % 10 == 0:
            self._log(f"   ↳ Progreso: {copiados}/{total} archivos")

    def _restaurar_botones(self) -> None:
        """Rehabilita los controles de la UI tras finalizar la copia."""
        self.btn_cancelar.config(state="disabled")
        self.btn_save_log.config(state="normal")
        self.btn_inicio.config(state="normal")

    # ------------------------------------------------------------------
    # Thread-safe logging
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        """Inserta ``msg`` en el widget de log de forma thread-safe.

        Args:
            msg: Texto a agregar al registro.
        """
        self.root.after(0, self._log_insert, msg)

    def _log_insert(self, msg: str) -> None:
        """Escribe directamente en el widget de log (debe llamarse desde el hilo principal).

        Args:
            msg: Texto a insertar.
        """
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    # ------------------------------------------------------------------
    # Control actions
    # ------------------------------------------------------------------

    def _cancelar_proceso(self) -> None:
        """Señaliza al hilo de copia que debe detenerse."""
        self.cancelar = True

    def _limpiar_todo(self) -> None:
        """Limpia todos los campos y reestablece el estado inicial."""
        self.ent_orig.delete(0, "end")
        self.txt_plan.delete("1.0", "end")
        self.txt_log.delete("1.0", "end")
        self.lbl_stats.config(
            text="Seleccione una carpeta para empezar", fg="blue"
        )
        self.btn_inicio.config(state="disabled")
        self.btn_save_log.config(state="disabled")
        self.origen = ""
        self.destino = ""
        self.validos_list = []

    def _guardar_log(self) -> None:
        """Abre un diálogo para guardar el contenido del log en un archivo .txt."""
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
