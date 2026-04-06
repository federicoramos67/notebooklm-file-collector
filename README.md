# NotebookLM File Collector

> Aplicacion de escritorio en Python con interfaz grafica para recopilar, filtrar y organizar archivos compatibles con Google NotebookLM desde cualquier carpeta y sus subcarpetas.

---

## Que hace

NotebookLM tiene un limite de 50 archivos por notebook y solo acepta ciertos formatos. Esta herramienta resuelve ese problema automaticamente:

1. Vos elegis una carpeta (con subcarpetas incluidas)
2. La app escanea todo y filtra solo los archivos que NotebookLM acepta
3. Crea una carpeta destino automaticamente al lado de la original con el sufijo `_notebooklm`
4. Si hay 50 o menos archivos los copia ordenados por tipo
5. Si hay mas de 50 los organiza en lotes separados por extension: `Lote1_txt`, `Lote2_md`, `Lote3_pdf`, etc.

---

## Caracteristicas

- Escaneo recursivo de subcarpetas
- Filtro automatico de extensiones soportadas por NotebookLM
- Omite archivos mayores a 200 MB (limite de la plataforma)
- Carpeta destino creada automaticamente sin intervension del usuario
- Organizacion en lotes por tipo de archivo cuando superan el limite de 50
- Vista previa del plan de organizacion antes de iniciar
- Boton de cancelacion durante el proceso
- Boton de limpieza del registro (estilo Google Colab)
- Guardado del log de operaciones en .txt
- Scrollbars horizontales y verticales en el panel de plan y en el registro
- Interfaz grafica sin necesidad de usar la terminal

---

## Formatos soportados

| Categoria | Extensiones |
|-----------|-------------|
| Documentos | `.pdf` `.docx` `.txt` `.md` `.csv` `.pptx` |
| Imagenes | `.jpg` `.jpeg` `.png` `.webp` `.gif` `.bmp` `.tiff` `.heic` y mas |
| Audio | `.mp3` `.wav` `.aac` `.ogg` `.opus` `.m4a` `.wma` y mas |
| Video | `.mp4` `.avi` `.mpeg` `.3gp` y mas |
| Ebook | `.epub` |

---

## Requisitos

- Python 3.8 o superior
- `tkinter` (incluido por defecto en Windows y macOS)
- Sin dependencias externas adicionales

---

## Instalacion y uso

### Opcion A: Ejecutar el script directamente

```bash
python notebooklm_collector.py
```

### Opcion B: Compilar como ejecutable .exe para Windows

```bash
pip install pyinstaller
pyinstaller --onefile --windowed notebooklm_collector.py
```

El `.exe` quedara en la carpeta `dist/` y puede ejecutarse en cualquier PC con Windows sin tener Python instalado.

---

## Flujo de uso

```
1. Abrir la aplicacion
2. Hacer clic en Explorar y elegir la carpeta con tus archivos
3. Revisar el plan de organizacion que aparece automaticamente
4. Hacer clic en Iniciar recopilacion
5. Al finalizar abrir la carpeta destino y subir los lotes a NotebookLM
```

---

## Estructura de carpetas generada

**Menos de 50 archivos:**
```
mi_carpeta_notebooklm/
  archivo1.txt
  archivo2.txt
  documento.pdf
  imagen.jpg
```

**Mas de 50 archivos:**
```
mi_carpeta_notebooklm/
  Lote1_txt/     -> hasta 50 archivos .txt
  Lote2_md/      -> hasta 50 archivos .md
  Lote3_pdf/     -> hasta 50 archivos .pdf
  Lote4_jpg/     -> hasta 50 archivos .jpg
```

---

## Licencia

MIT License - libre para usar, modificar y distribuir.

---

## Autor

Desarrollado por **Federico Ramos** | Uruguay
[LinkedIn](https://www.linkedin.com/in/federico-ramos-904024281) | [GitHub](https://github.com/federicoramos67)
