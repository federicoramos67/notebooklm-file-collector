import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from datetime import datetime
from pathlib import Path

# --- Extensiones soportadas por NotebookLM ---
EXTENSIONES_PERMITIDAS = {
    \".pdf\", \".docx\", \".txt\", \".md\", \".csv\", \".pptx\",
    \".avif\", \".bmp\", \".gif\", \".heic\", \".heif\", \".ico\",
    \".jp2\", \".jpe\", \".jpeg\", \".jpg\", \".png\", \".tif\", \".tiff\", \".webp\",
    \".3g2\", \".3gp\", \".aac\", \".aif\", \".aifc\", \".aiff\", \".amr\",
    \".au\", \".avi\", \".cda\", \".m4a\", \".mid\", \".mp3\", \".mp4\", \".mpeg\",
    \".ogg\", \".opus\", \".ra\", \".ram\", \".snd\", \".wav\", \".wma\",
    \".epub\",
}

LIMITE_TAMANO_MB = 200
LIMITE_ARCHIVOS_LOTE = 50

class NotebookLMCollector:
    def __init__(self, root):
        self.root = root
        self.root.title(\"v3.6 NotebookLM File Collector\")
        self.root.geometry(\"760x680\")
        
        self.origen = \"\"
        self.destino = \"\"
        self.cancelar = False
        self.stats = {}

        self._setup_ui()

    def _setup_ui(self):
        # Header
        tk.Label(self.root, text=\"NotebookLM File Collector v3.6\", font=(\"Arial\", 14, \"bold\")).pack(pady=10)
        
        # Origen
        frame_orig = tk.Frame(self.root)
        frame_orig.pack(fill=\"x\", padx=20)
        tk.Label(frame_orig, text=\"Carpeta Origen:\").pack(side=\"left\")
        self.ent_orig = tk.Entry(frame_orig)
        self.ent_orig.pack(side=\"left\", fill=\"x\", expand=True, padx=5)
        tk.Button(frame_orig, text=\"Explorar...\", command=self._seleccionar_origen).pack(side=\"left\")

        # Panel Vista Previa (Plan de lotes)
        tk.Label(self.root, text=\"Plan de organización:\").pack(anchor=\"w\", padx=20, pady=(10,0))
        self.txt_plan = scrolledtext.ScrolledText(self.root, height=8, bg=\"#f0fff0\", wrap=\"none\")
        self.txt_plan.pack(fill=\"x\", padx=20)
        
        # Stats bar
        self.lbl_stats = tk.Label(self.root, text=\"Seleccione una carpeta para empezar\", fg=\"blue\")
        self.lbl_stats.pack(pady=5)

        # Botones Control
        frame_ctrl = tk.Frame(self.root)
        frame_ctrl.pack(pady=10)
        self.btn_inicio = tk.Button(frame_ctrl, text=\"▶ Iniciar recopilación\", state=\"disabled\", command=self._iniciar_proceso)
        self.btn_inicio.pack(side=\"left\", padx=5)
        self.btn_cancelar = tk.Button(frame_ctrl, text=\"⛔ Cancelar\", state=\"disabled\", command=self._cancelar_proceso)
        self.btn_cancelar.pack(side=\"left\", padx=5)
        self.btn_limpiar = tk.Button(frame_ctrl, text=\"🗑 Limpiar\", command=self._limpiar_todo)
        self.btn_limpiar.pack(side=\"left\", padx=5)

        # Log
        tk.Label(self.root, text=\"Registro de operaciones:\").pack(anchor=\"w\", padx=20)
        self.txt_log = scrolledtext.ScrolledText(self.root, height=12, wrap=\"none\")
        self.txt_log.pack(fill=\"both\", expand=True, padx=20, pady=5)
        
        self.btn_save_log = tk.Button(self.root, text=\"💾 Guardar log\", state=\"disabled\", command=self._guardar_log)
        self.btn_save_log.pack(pady=5)

    def _seleccionar_origen(self):
        path = filedialog.askdirectory()
        if path:
            self.origen = path
            self.ent_orig.delete(0, \"end\")
            self.ent_orig.insert(0, path)
            self.destino = path + \"_notebooklm\"
            self._analizar_carpeta()

    def _analizar_carpeta(self):
        self.stats = {}
        validos = []
        muy_grandes = []
        
        for root, dirs, files in os.walk(self.origen):
            for file in files:
                ext = Path(file).suffix.lower()
                full_path = Path(root) / file
                if ext in EXTENSIONES_PERMITIDAS:
                    size = full_path.stat().st_size
                    if size <= LIMITE_TAMANO_MB * 1024 * 1024:
                        validos.append((full_path, ext))
                    else:
                        muy_grandes.append(full_path)
        
        self.validos_list = validos
        self._mostrar_plan(validos, muy_grandes)

    def _mostrar_plan(self, validos, muy_grandes):
        self.txt_plan.delete(\"1.0\", \"end\")
        if not validos:
            self.lbl_stats.config(text=\"No se encontraron archivos compatibles\", fg=\"red\")
            self.btn_inicio.config(state=\"disabled\")
            return

        # Agrupar por extension
        grupos = {}
        for path, ext in validos:
            grupos[ext] = grupos.get(ext, []) + [path]
        
        # Ordenar extensiones (texto primero)
        prioridad = [\".txt\", \".md\", \".docx\", \".pdf\", \".csv\"]
        exts_ordenadas = sorted(grupos.keys(), key=lambda x: (x not in prioridad, x))

        plan_text = f\"Destino: {self.destino}\
\
\"
        
        if len(validos) <= LIMITE_ARCHIVOS_LOTE:
            plan_text += f\"Total archivos: {len(validos)} (Caben en carpeta única)\
\"
            for ext in exts_ordenadas:
                plan_text += f\"  - {len(grupos[ext])} archivos {ext}\
\"
        else:
            plan_text += f\"Total archivos: {len(validos)} (Se organizarán en lotes por tipo)\
\"
            lote_num = 1
            for ext in exts_ordenadas:
                count = len(grupos[ext])
                tipo = ext.replace(\".\", \"\")
                if count <= LIMITE_ARCHIVOS_LOTE:
                    plan_text += f\"  📁 Lote{lote_num}_{tipo}: {count} archivos\
\"
                    lote_num += 1
                else:
                    sublotes = (count // LIMITE_ARCHIVOS_LOTE) + (1 if count % LIMITE_ARCHIVOS_LOTE != 0 else 0)
                    for i in range(1, sublotes + 1):
                        archs = LIMITE_ARCHIVOS_LOTE if i < sublotes else count % LIMITE_ARCHIVOS_LOTE
                        if archs == 0: archs = LIMITE_ARCHIVOS_LOTE
                        plan_text += f\"  📁 Lote{lote_num}_{tipo}_{i}: {archs} archivos\
\"
                    lote_num += 1

        self.txt_plan.insert(\"1.0\", plan_text)
        self.lbl_stats.config(text=f\"✅ {len(validos)} archivos listos para organizar\", fg=\"green\")
        self.btn_inicio.config(state=\"normal\")

    def _iniciar_proceso(self):
        self.cancelar = False
        self.btn_inicio.config(state=\"disabled\")
        self.btn_cancelar.config(state=\"normal\")
        self.txt_log.delete(\"1.0\", \"end\")
        threading.Thread(target=self._ejecutar_copia).start()

    def _ejecutar_copia(self):
        try:
            dest_path = Path(self.destino)
            dest_path.mkdir(exist_ok=True)
            
            validos = self.validos_list
            grupos = {}
            for path, ext in validos:
                grupos[ext] = grupos.get(ext, []) + [path]
            
            prioridad = [\".txt\", \".md\", \".docx\", \".pdf\", \".csv\"]
            exts_ordenadas = sorted(grupos.keys(), key=lambda x: (x not in prioridad, x))
            
            copiados = 0
            
            if len(validos) <= LIMITE_ARCHIVOS_LOTE:
                for ext in exts_ordenadas:
                    for arch in grupos[ext]:
                        if self.cancelar: break
                        shutil.copy2(arch, dest_path / arch.name)
                        self._log(f\"🟢 Copiado: {arch.name}\")
                        copiados += 1
            else:
                lote_idx = 1
                for ext in exts_ordenadas:
                    if self.cancelar: break
                    tipo = ext.replace(\".\", \"\")
                    archivos = grupos[ext]
                    
                    if len(archivos) <= LIMITE_ARCHIVOS_LOTE:
                        lote_dir = dest_path / f\"Lote{lote_idx}_{tipo}\"
                        lote_dir.mkdir(exist_ok=True)
                        for arch in archivos:
                            if self.cancelar: break
                            shutil.copy2(arch, lote_dir / arch.name)
                            self._log(f\"🟢 [{tipo}] -> {arch.name}\")
                            copiados += 1
                        lote_idx += 1
                    else:
                        sublote = 1
                        for i in range(0, len(archivos), LIMITE_ARCHIVOS_LOTE):
                            if self.cancelar: break
                            lote_dir = dest_path / f\"Lote{lote_idx}_{tipo}_{sublote}\"
                            lote_dir.mkdir(exist_ok=True)
                            chunk = archivos[i:i+LIMITE_ARCHIVOS_LOTE]
                            for arch in chunk:
                                if self.cancelar: break
                                shutil.copy2(arch, lote_dir / arch.name)
                                self._log(f\"🟢 [{tipo}_{sublote}] -> {arch.name}\")
                                copiados += 1
                            sublote += 1
                        lote_idx += 1

            status = \"✅ Finalizado\" if not self.cancelar else \"⛔ Cancelado\"
            self._log(f\"\
--- {status} --- total: {copiados} archivos\")
            messagebox.showinfo(\"Proceso terminado\", f\"{status}\
Archivos procesados: {copiados}\")
            
        except Exception as e:
            self._log(f\"🔴 ERROR: {str(e)}\")
        finally:
            self.btn_cancelar.config(state=\"disabled\")
            self.btn_save_log.config(state=\"normal\")

    def _log(self, msg):
        self.txt_log.insert(\"end\", msg + \"\
\")
        self.txt_log.see(\"end\")

    def _cancelar_proceso(self):
        self.cancelar = True

    def _limpiar_todo(self):
        self.ent_orig.delete(0, \"end\")
        self.txt_plan.delete(\"1.0\", \"end\")
        self.txt_log.delete(\"1.0\", \"end\")
        self.lbl_stats.config(text=\"Seleccione una carpeta para empezar\", fg=\"blue\")
        self.btn_inicio.config(state=\"disabled\")
        self.btn_save_log.config(state=\"disabled\")

    def _guardar_log(self):
        file = filedialog.asksaveasfilename(defaultextension=\".txt\", initialfile=f\"log_notebooklm_{datetime.now().strftime('%Y%m%d_%H%M')}.txt\")
        if file:
            with open(file, \"w\", encoding=\"utf-8\") as f:
                f.write(self.txt_log.get(\"1.0\", \"end\"))

if __name__ == \"__main__\":
    root = tk.Tk()
    app = NotebookLMCollector(root)
    root.mainloop()
