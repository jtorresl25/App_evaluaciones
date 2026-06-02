# Evaluaciones Docentes — Dashboard Streamlit

Dashboard ejecutivo para visualizar la trayectoria de evaluaciones docentes de **Juan Pablo Ramos Bonilla**.

## Requisitos

- Python 3.10 o superior
- Paquetes en `requirements.txt`

## Instalación

```bash
# Crear y activar entorno virtual (opcional pero recomendado)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt
```

## Ejecutar la app

```bash
streamlit run app.py
```

La app se abre en `http://localhost:8501`.

## Uso

1. Abre la app — verás la pantalla de bienvenida.
2. Carga el archivo **`Evaluaciones_Docentes_VF_base_streamlit.xlsx`** desde el panel lateral.
3. La app lee las hojas `BASE_GENERAL_DOCENTE` y (si existe) `BASE_DETALLE_PDF`.
4. Usa los filtros del sidebar para segmentar por modelo, curso o periodo.
5. Activa "Mostrar detalle PDF" para ver la tabla auxiliar de extracción.

## Estructura del proyecto

```
app.py                          # Punto de entrada Streamlit
app/
  components/
    kpi_cards.py                # Tarjetas KPI con HTML/CSS
    sections.py                 # Secciones completas del dashboard
  utils/
    data_loader.py              # Lectura y validación del Excel
    data_cleaning.py            # Limpieza, tipos y subconjuntos
    metrics.py                  # Cálculo de indicadores
    plots.py                    # Gráficos Plotly
  styles/
    main.css                    # Estilos visuales
assets/
  html_design/                  # Maqueta HTML de referencia visual
data/
  local_private/                # Archivos de trabajo (no versionar)
  sample/                       # Datos de muestra anonimizados
docs/                           # Documentación metodológica
```

## Reglas metodológicas clave

| Regla | Detalle |
|---|---|
| Separación de modelos | Modelo actual y anterior no se mezclan en la misma serie |
| Escala original | Modelo actual NO se convierte a /5 |
| Exclusiones | Registros `Sin docencia / No aplica` y `NC / No calculado` se excluyen de KPIs y gráficos |
| Fuente PDF | `BASE_DETALLE_PDF` solo se muestra como detalle auxiliar, no alimenta KPIs |
| Deltas | Si la columna existe, se usa; si está vacía se calcula como `puntaje_profesor - benchmark` |

## Privacidad

La app **no almacena ningún dato**. Todo el procesamiento ocurre en la sesión local del navegador.
El archivo Excel cargado no sale del equipo.

## Hojas esperadas en el Excel

### BASE_GENERAL_DOCENTE (obligatoria)

`id_registro`, `periodo`, `anio`, `semestre`, `modelo_evaluacion`, `escala_original`,
`nivel_analisis`, `codigo_curso`, `nombre_curso`, `puntaje_profesor`,
`benchmark_universidad`, `benchmark_facultad`, `benchmark_departamento`,
`delta_vs_universidad`, `delta_vs_facultad`, `delta_vs_departamento`,
`estado_registro`, `calidad_dato`, `fuente`, `nota`

### BASE_DETALLE_PDF (opcional)

`id_detalle`, `archivo_pdf`, `pagina`, `periodo`, `codigo_curso`, `nombre_curso`,
`nivel_analisis`, `aspecto`, `serie`, `puntaje`, `limite_inferior`, `limite_superior`,
`lectura_cualitativa`, `confianza`, `metodo_extraccion`, `requiere_revision`,
`estado_revision`, `fuente`, `observacion`
