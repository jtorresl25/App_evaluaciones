# Dashboard de evaluaciones docentes

Aplicación Streamlit para visualizar el desempeño docente histórico a partir de un archivo Excel de evaluaciones. Permite explorar benchmarks institucionales, comparación relativa y detalle auxiliar por curso/aspecto.

**La app no incluye datos precargados.** El análisis se genera únicamente desde el archivo Excel que el usuario cargue en cada sesión.

---

## Requisitos

- Python 3.10 o superior

## Instalación local

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

La app se abre en `http://localhost:8501`.

## Uso

1. Abre la app — verás la pantalla de bienvenida sin datos.
2. Carga el archivo Excel desde el panel lateral.
3. La app calcula todo desde el archivo cargado.
4. Usa el checkbox "Mostrar datos auxiliares" para ver la sección de detalle.
5. "Filtros avanzados" permite segmentar por modelo o periodo si es necesario.
6. Usa el botón **Descargar** (junto al título) o el botón **PNG** de cada gráfico para llevarte el análisis.

## Descargas

Todo se descarga con el mismo diseño del dashboard y refleja exactamente lo que se ve en pantalla: nombre del docente, filtros aplicados y curso seleccionado en los datos auxiliares.

| Opción | Dónde | Qué obtienes |
|---|---|---|
| Reporte completo (PDF) | Menú **Descargar** | Todas las secciones en hojas tamaño carta, sin gráficos ni tarjetas cortados, con fecha y número de página. Si "Mostrar datos auxiliares" está activo, incluye el detalle del curso seleccionado. |
| Página interactiva (HTML) | Menú **Descargar** | El mismo reporte en un archivo que se abre en cualquier navegador, incluso sin internet, con el detalle al pasar el mouse y un botón **Guardar como PDF**. |
| Un gráfico (PNG) | Botón **PNG** sobre cada gráfico | Imagen de 2640 px de ancho con título, contexto y pie; lista para Word o PowerPoint. |
| Todos los gráficos (ZIP) | Menú **Descargar** | Los PNG de todos los gráficos, numerados en el orden del dashboard. |

### Requisito: Chrome, Edge o Chromium

El PDF y los PNG se generan con un navegador Chromium sin interfaz, a través de la librería `choreographer`:

- **Windows / macOS (uso local):** basta con tener Google Chrome o Microsoft Edge instalado.
- **Streamlit Community Cloud:** el archivo `packages.txt` instala `chromium`.
- **Otra ruta:** define la variable de entorno `BROWSER_PATH` con la ruta del ejecutable.

Si no hay navegador disponible, la app sigue funcionando: el menú ofrece la página HTML (desde la cual se guarda el PDF con el navegador) y cada gráfico muestra el ícono de cámara de Plotly para bajarlo en PNG.

### Cómo está construido (mantenimiento)

- Las secciones dibujan con `Recorder` (`app/components/recorder.py`): `rec.html(...)`, `rec.columns(...)` y `rec.chart(...)` hacen lo mismo que `st.markdown`, `st.columns` y `st.plotly_chart`, y además registran lo dibujado en un `DashboardSnapshot`. Para que una sección nueva aparezca en las descargas, ábrela con `rec.section()` y dibuja sus gráficos con `rec.chart(fig, key=..., title=...)`.
- `app/export/report.py` arma el reporte con los mismos fragmentos HTML del dashboard y un CSS equivalente al de Streamlit; un script reparte los bloques en hojas y, si un gráfico es más alto que una hoja, lo reduce junto a su título en vez de cortarlo.
- `app/export/plotly_theme.py` fija el tema de Plotly ya resuelto: Streamlit usa colores marcadores que solo su navegador traduce. **Si cambias el tema en `.streamlit/config.toml`, actualiza este archivo.**
- `app/export/fonts/` contiene Spectral, IBM Plex Sans y Source Sans 3 (licencia SIL OFL) para que el reporte se vea igual sin conexión.
- Pruebas: `pip install pytest` y luego `python -m pytest tests` (usan datos sintéticos).

## Estructura esperada del Excel

### BASE_GENERAL_DOCENTE (obligatoria)

Columnas mínimas necesarias:

| Columna | Descripción |
|---|---|
| `periodo` | Periodo en formato `YYYY-S` (ej. `2025-2`) |
| `modelo_evaluacion` | Nombre del modelo de evaluación |
| `nivel_analisis` | Tipo de registro (`Periodo-Agregado`, nombre de curso, etc.) |
| `codigo_curso` | Código del curso |
| `nombre_curso` | Nombre del curso |
| `puntaje_profesor` | Puntaje del docente |
| `benchmark_universidad` | Promedio Universidad |
| `benchmark_facultad` | Promedio Facultad |
| `estado_registro` | `Sin docencia / No aplica`, `NC / No calculado`, o valor válido |

Columnas opcionales (se crean vacías si faltan): `anio`, `semestre`, `escala_original`, `benchmark_departamento`, `delta_vs_*`, `fuente`, `nota`, `calidad_dato`.

### BASE_DETALLE (opcional)

Hoja auxiliar de detalle por curso y aspecto. Puede provenir de reportes, extracción manual o consolidaciones. No alimenta los KPIs principales.

Si el archivo tiene la hoja antigua **`BASE_DETALLE_PDF`**, la app la usa como fallback y muestra un aviso.

---

## Privacidad

- La app **no almacena datos**. Todo el procesamiento ocurre en la sesión local.
- El archivo Excel no sale del equipo ni se transmite a ningún servidor externo.
- Las descargas se generan en el equipo o servidor donde corre la app; los archivos temporales que usa el navegador para dibujarlas se borran de inmediato.
- Antes de cargar el archivo, la app no muestra ningún dato personal ni resultado real.
- No se deben subir archivos Excel reales al repositorio.

---

## Despliegue en Streamlit Cloud

1. Sube el repositorio a GitHub (**sin archivos Excel reales**).
2. Ingresa a [share.streamlit.io](https://share.streamlit.io).
3. Conecta el repositorio.
4. Configura:
   - **Main file path:** `app.py`
   - **Python version:** 3.10 o superior
5. Despliega — la app leerá `requirements.txt` y `packages.txt` (Chromium para PDF y PNG) automáticamente.

No se necesitan secrets ni variables de entorno para el funcionamiento básico.

---

## Reglas metodológicas

| Regla | Detalle |
|---|---|
| Separación de modelos | Modelo actual y anterior no se mezclan en la misma serie |
| Escala original | Cada modelo se muestra en su escala original, sin conversión |
| Exclusiones | `Sin docencia / No aplica` y `NC / No calculado` se excluyen de KPIs y gráficos |
| Fuente auxiliar | `BASE_DETALLE` es referencia complementaria — no alimenta KPIs principales |
| Deltas | Si la columna existe se usa directamente; si falta se calcula como `puntaje_profesor − benchmark` |
| Periodos futuros | La app detecta todos los periodos del Excel dinámicamente (2026, 2027…) sin modificar código |

---

## Estructura del proyecto

```
app.py                    # Punto de entrada Streamlit
requirements.txt
packages.txt              # Chromium para Streamlit Cloud (PDF y PNG)
README.md
.gitignore
.streamlit/
  config.toml             # Tema oscuro
app/
  components/
    kpi_cards.py          # Tarjetas KPI
    sections.py           # Secciones del dashboard
    recorder.py           # Dibuja en Streamlit y registra para las descargas
    downloads.py          # Menú "Descargar"
  export/
    snapshot.py           # Registro de lo que muestra el dashboard
    report.py             # Reporte paginado (PDF/HTML) y tarjetas de gráficos (PNG)
    browser.py            # Render con Chrome/Edge/Chromium sin interfaz
    plotly_theme.py       # Tema Plotly igual al de pantalla
    fonts/                # Fuentes incrustadas (licencia OFL)
  utils/
    data_loader.py        # Lectura y validación del Excel
    data_cleaning.py      # Limpieza, parseo de periodos, subconjuntos
    metrics.py            # Cálculo de indicadores
    plots.py              # Gráficos Plotly
    pdf_analysis.py       # Métricas de BASE_DETALLE
  styles/
    main.css              # Estilos tema oscuro
data/
  sample/                 # (opcional) datos ficticios anonimizados
tests/
  test_export.py          # Pruebas de las descargas (datos sintéticos)
```
