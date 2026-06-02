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
5. Despliega — la app leerá `requirements.txt` automáticamente.

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
README.md
.gitignore
.streamlit/
  config.toml             # Tema oscuro
app/
  components/
    kpi_cards.py          # Tarjetas KPI
    sections.py           # Secciones del dashboard
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
```
