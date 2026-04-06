# NotebookLM File Collector

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![GUI](https://img.shields.io/badge/GUI-Tkinter-orange)

> Aplicación de escritorio en Python con interfaz gráfica para recopilar, filtrar y organizar archivos compatibles con Google NotebookLM desde cualquier carpeta y sus subcarpetas.

---

## ¿Qué hace?

NotebookLM tiene un límite de 50 archivos por notebook y solo acepta ciertos formatos. Esta herramienta resuelve ese problema automáticamente:

1. Elegís una carpeta (con subcarpetas incluidas)
2. La app escanea todo y filtra solo los archivos que NotebookLM acepta
3. Crea una carpeta destino automáticamente al lado de la original con el sufijo `_notebooklm`
4. Si hay 50 o menos archivos, los copia ordenados por tipo
5. Si hay más de 50, los organiza en lotes separados por extensión: `Lote1_txt`, `Lote2_md`, `Lote3_pdf`, etc.

---

## ✨ Características

- 🔍 Escaneo recursivo de subcarpetas
- ✅ Filtro automático de extensiones soportadas por NotebookLM
- 🚫 Omite archivos mayores a 200 MB (límite de la plataforma)
- 📁 Carpeta destino creada automáticamente sin intervención del usuario
- 📦 Organización en lotes por tipo de archivo cuando superan el límite de 50
- 👁️ Vista previa del plan de organización antes de iniciar
- ⛔ Botón de cancelación durante el proceso
- 🧹 Botón de limpieza del registro (estilo Google Colab)
- 💾 Guardado del log de operaciones en `.txt`
- ↔️ Scrollbars horizontales y verticales en el panel de plan y en el registro
- 🖥️ Interfaz gráfica sin necesidad de usar la terminal

---

## 📂 Formatos soportados

| Categoría | Extensiones |
|-----------|-------------|
| Documentos | `.pdf` `.docx` `.txt` `.md` `.csv` `.pptx` |
| Imágenes | `.jpg` `.jpeg` `.png` `.webp` `.gif` `.bmp` `.tiff` `.heic` y más |
| Audio | `.mp3` `.wav` `.aac` `.ogg` `.opus` `.m4a` `.wma` y más |
| Video | `.mp4` `.avi` `.mpeg` `.3gp` y más |
| Ebook | `.epub` |

---

## 🛠️ Requisitos

- Python 3.8 o superior
- `tkinter` (incluido por defecto en Windows y macOS)
- Sin dependencias externas adicionales

---

## 🚀 Instalación y uso

### Opción A: Ejecutar el script directamente

```bash
python notebooklm_collector.py
```

### Opción B: Compilar como ejecutable `.exe` para Windows

```bash
pip install pyinstaller
pyinstaller --onefile --windowed notebooklm_collector.py
```

El `.exe` quedará en la carpeta `dist/` y puede ejecutarse en cualquier PC con Windows sin tener Python instalado.

---

## 📋 Flujo de uso

```
1. Abrir la aplicación
2. Hacer clic en "Explorar" y elegir la carpeta con tus archivos
3. Revisar el plan de organización que aparece automáticamente
4. Hacer clic en "Iniciar recopilación"
5. Al finalizar, abrir la carpeta destino y subir los lotes a NotebookLM
```

---

## 🗂️ Estructura de carpetas generada

**Menos de 50 archivos:**
```
mi_carpeta_notebooklm/
  archivo1.txt
  archivo2.txt
  documento.pdf
  imagen.jpg
```

**Más de 50 archivos:**
```
mi_carpeta_notebooklm/
  Lote1_txt/  -> hasta 50 archivos .txt
  Lote2_md/   -> hasta 50 archivos .md
  Lote3_pdf/  -> hasta 50 archivos .pdf
  Lote4_jpg/  -> hasta 50 archivos .jpg
```

---

## 📄 Licencia

MIT License — libre para usar, modificar y distribuir.

---

## 👤 Autor

Desarrollado por **Federico Ramos** | Uruguay

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Federico%20Ramos-blue?logo=linkedin)](https://www.linkedin.com/in/federico-ramos-904024281)
[![GitHub](https://img.shields.io/badge/GitHub-federicoramos67-black?logo=github)](https://github.com/federicoramos67)
