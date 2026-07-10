# Aprendizajes de implementación

Registro acumulativo de observaciones generalizables obtenidas durante las revisiones del proyecto. Cada entrada debe añadir conocimiento nuevo y útil para implementar sistemas RAG evaluables; no debe repetir el estado del proyecto ni funcionar como bitácora de actividades.

## Criterio para futuras entradas

Agregar una observación solamente cuando incluya al menos uno de estos elementos:

- Evidencia obtenida mediante ejecución o evaluación.
- Una causa técnica identificada.
- Una decisión de diseño reutilizable.
- Una práctica que mejore calidad, reproducibilidad, costo o seguridad.

Cada nueva revisión debe registrar, cuando corresponda: **hallazgo**, **evidencia**, **aprendizaje** y **acción recomendada**.

## Revisión 1 — Arquitectura y estado inicial

### Separar el prototipo del código reutilizable

**Hallazgo:** la implementación funcional vive principalmente en el notebook, mientras que casi todos los módulos de `src/` son esqueletos.

**Aprendizaje:** un notebook es apropiado para experimentar, pero dificulta las pruebas, la reutilización y la reproducción cuando concentra carga, chunking, recuperación, generación y evaluación. Una implementación madura debe mover esas responsabilidades a funciones o clases importables y dejar el notebook como orquestador y reporte.

### Mantener consistencia entre datos, documentación y benchmark

**Hallazgo:** los nombres descritos por el notebook y el benchmark (`all_prices_clean.csv`, `sec_filings.txt`) no coinciden con algunos archivos reales (`stock_price_details.csv`, `sec_filings_10q.pdf`). Además, el nombre del PDF sugiere 10-Q, aunque existen preguntas sobre un 10-K.

**Aprendizaje:** los contratos de datos forman parte del sistema. Los nombres de archivo, tipos de formulario, periodos y metadatos deben ser consistentes entre ingesta, recuperación y evaluación. Una inconsistencia puede parecer un fallo del LLM cuando en realidad es un fallo de procedencia o cobertura documental.

### Persistir artefactos reproducibles

**Hallazgo:** existían la colección Chroma y carpetas de resultados, pero no reportes exportados de evaluación o tuning.

**Aprendizaje:** además de mostrar DataFrames en el notebook, cada corrida debe guardar configuración, prompt, versión del modelo, resultados por caso, resumen de métricas y fecha. Sin estos artefactos no es posible comparar ejecuciones con confianza.

## Revisión 2 — Evaluación del prompt optimizado

### Comparar con el mismo protocolo

**Hallazgo:** las secciones 2.3 y 2.4 se diseñaron para evaluar baseline y prompt optimizado con las mismas preguntas, recuperación `k=5`, modelo y cinco métricas.

**Aprendizaje:** una comparación válida debe cambiar una sola variable. Para medir el efecto del prompt con mayor rigor, ambos prompts deben recibir exactamente los mismos contextos recuperados, no ejecutar dos recuperaciones independientes.

### Conservar resultados a distintos niveles

**Aprendizaje:** una evaluación útil necesita tres niveles de salida:

1. Respuesta generada y evidencia por pregunta.
2. Puntuación y razón por pregunta y métrica.
3. Resumen agregado por métrica y resultado global.

El promedio global por sí solo oculta regresiones críticas.

### Considerar el costo antes de ejecutar

**Hallazgo:** evaluar 20 preguntas con cinco métricas requiere aproximadamente 20 llamadas de generación y 100 llamadas de evaluación, además de las llamadas consumidas por la optimización.

**Aprendizaje:** las evaluaciones con LLM-as-a-judge deben diseñarse con presupuesto explícito, muestras pequeñas durante desarrollo y una corrida completa únicamente cuando el pipeline sea estable.

## Revisión 3 — Interpretación de resultados

### Una mejora promedio puede ocultar una regresión importante

**Evidencia:** el promedio global aumentó de `0.6676` a `0.6741`, mientras el success rate permaneció en `0.72`. Mejoraron Answer Relevance, Broker Actionability y Faithfulness, pero Answer Correctness cayó de `0.5223` a `0.4331` (`-17.07%`).

**Aprendizaje:** no debe declararse ganador a un prompt solo porque mejora el promedio. En dominios financieros, corrección y groundedness deben tratarse como métricas prioritarias o restricciones mínimas. Una mejora de estilo o utilidad no compensa necesariamente una pérdida de precisión factual.

**Acción recomendada:** usar una puntuación ponderada y umbrales de aceptación, por ejemplo:

```python
overall_score = (
    0.35 * answer_correctness
    + 0.25 * faithfulness
    + 0.15 * context_relevance
    + 0.10 * answer_relevance
    + 0.15 * broker_actionability
)
```

Un candidato no debe aprobarse si cae por debajo del baseline en una métrica crítica, aunque su promedio ponderado aumente.

### Distinguir prudencia de corrección

**Hallazgo:** el prompt optimizado fue más propenso a declarar que faltaba evidencia. Esto ayudó a la fidelidad, pero redujo la coincidencia con respuestas esperadas cuando la recuperación no encontró el documento correcto.

**Aprendizaje:** decir “no hay evidencia suficiente” puede ser la conducta segura y correcta dado el contexto recuperado, aunque obtenga una puntuación baja frente al benchmark. Deben evaluarse por separado la calidad de recuperación y la calidad de generación.

### No atribuir al prompt una métrica de recuperación

**Evidencia:** Context Relevance cambió entre baseline y optimizado pese a que ambos usaron `k=5`.

**Aprendizaje:** Context Relevance depende principalmente de los documentos recuperados. Si se comparan prompts con contextos idénticos, esta métrica debería ser constante salvo variabilidad del juez. Su cambio indica que no se aisló completamente la variable o que existe ruido de evaluación.

### Controlar la variabilidad del evaluador

**Aprendizaje:** las métricas basadas en otro LLM no son mediciones perfectamente deterministas. Para diferencias pequeñas, conviene fijar contextos, usar configuración determinista cuando sea posible y repetir la evaluación varias veces. Una mejora global de `0.0065` no constituye evidencia fuerte sin estimar variabilidad.

### Verificar que la optimización haya cambiado realmente el prompt

**Hallazgo:** el texto impreso como prompt optimizado parecía materialmente igual al seed, aunque una comparación directa reportó que había cambiado.

**Aprendizaje:** diferencias de espacios, saltos de línea o mutaciones del objeto pueden generar falsos positivos. Debe conservarse una copia inmutable del seed antes de optimizar y comparar versiones normalizadas:

```python
seed_prompt_text = optimized_prompt_seed.text_template

def normalize_prompt(text):
    return " ".join(text.split())

prompt_changed = (
    normalize_prompt(optimized_prompt_text)
    != normalize_prompt(seed_prompt_text)
)
```

## Revisión 4 — Diagnóstico del cuello de botella

### Mejorar recuperación antes de seguir ajustando prompts

**Evidencia:** varias respuestas recibieron fragmentos de un 10-Q de 2026 cuando la pregunta pedía el 10-K de 2025. Otras consultas de comparación recuperaron datos para una fecha, pero no para la segunda.

**Aprendizaje:** un prompt no puede recuperar hechos ausentes. Cuando las respuestas son fieles pero incorrectas respecto del benchmark, el primer diagnóstico debe ser recall y precisión de recuperación, no generación.

### Usar metadatos como restricciones estrictas

**Aprendizaje:** compañía, ticker, tipo de formulario, periodo fiscal, fecha y dataset deben almacenarse como metadatos consultables. Las preguntas financieras contienen restricciones que no deben resolverse únicamente por similitud semántica.

Ejemplo de metadatos para SEC:

```python
{
    "dataset": "sec_filings",
    "company": "Apple",
    "form_type": "10-K",
    "filing_year": 2025,
    "section": "Item 9A",
}
```

### No usar un vector store como base de datos numérica

**Hallazgo:** las consultas sobre precios y volúmenes exactos fallaron cuando necesitaban fechas específicas.

**Aprendizaje:** embeddings son adecuados para significado y lenguaje; no son el mecanismo principal para recuperar valores exactos por ticker y fecha. Los datos de mercado deben conservar columnas estructuradas y consultarse con pandas o SQL. El resultado estructurado puede incorporarse después al contexto del LLM.

### Descomponer preguntas comparativas

**Aprendizaje:** una pregunta con varias compañías, fechas o fuentes debe transformarse en subconsultas explícitas. Se recupera evidencia para cada entidad y luego se sintetiza. Una sola búsqueda top-k suele favorecer una parte de la pregunta y omitir las demás.

### Combinar recuperación semántica y léxica

**Aprendizaje:** términos como `10-K`, `Item 9A`, `0700.HK` y fechas exactas tienen alto valor léxico. Una estrategia robusta combina embeddings, búsqueda por palabras clave/BM25, filtros de metadatos y reranking.

### Favorecer diversidad y estructura documental

**Hallazgo:** algunos contextos contenían fragmentos repetidos del mismo documento.

**Aprendizaje:** debe deduplicarse la evidencia y utilizarse MMR o reranking para evitar que los primeros resultados repitan el mismo pasaje. En documentos SEC, dividir por secciones regulatorias suele ser mejor que usar solamente ventanas de tamaño fijo.

### Separar optimización y prueba

**Hallazgo:** el conjunto disponible de 20 ejemplos se usa tanto en el proceso de optimización como en la evaluación posterior.

**Aprendizaje:** esto introduce riesgo de sobreajuste y hace que la mejora estimada sea optimista. Deben existir conjuntos distintos de entrenamiento, validación y prueba; el test final no puede participar en GEPA ni en la selección de configuración.

## Próxima hipótesis a validar

La siguiente mejora con mayor probabilidad de elevar Answer Correctness es implementar recuperación consciente del tipo de fuente:

1. Consultas estructuradas para precios y volúmenes.
2. Filtros por compañía, formulario y periodo para SEC.
3. Subconsultas para preguntas comparativas.
4. Contextos fijos para comparar prompts.

Después de aplicar estos cambios se debe repetir el benchmark y comprobar si aumenta Answer Correctness sin reducir Faithfulness.
