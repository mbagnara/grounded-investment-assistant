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

## Revisión 5 — Calibración de pesos y umbrales

### Los pesos y los umbrales resuelven problemas diferentes

**Aprendizaje:** un peso expresa cuánto influye una métrica en el ranking entre candidatos; un umbral expresa el mínimo que el sistema debe cumplir. Una métrica crítica no debe protegerse solamente con un peso alto, porque un resultado deficiente podría quedar oculto por mejoras en otras métricas. Correctness y Faithfulness deben funcionar también como puertas de aprobación independientes.

**Ejemplo:** supóngase que se utilizan estos pesos:

```python
weights = {
    "Answer Correctness": 0.35,
    "Faithfulness / Groundedness": 0.25,
    "Context Relevance": 0.15,
    "Answer Relevance": 0.10,
    "Broker Actionability": 0.15,
}
```

Con los resultados observados, la puntuación ponderada es:

```text
Baseline:   0.6396
Optimizado: 0.6265
```

El peso permite comparar ambos candidatos. Un umbral, en cambio, puede expresar una condición obligatoria:

```python
minimum_correctness = 0.50
passes_correctness_gate = answer_correctness >= minimum_correctness
```

El baseline, con `0.5223`, supera provisionalmente esa puerta. El optimizado, con `0.4331`, no la supera. Aunque el optimizado sea mejor en Actionability, esa mejora no debe compensar automáticamente una corrección insuficiente.

### Calibrar contra decisiones humanas

**Aprendizaje:** no existen pesos ni umbrales universales de DeepEval. Deben calibrarse con un conjunto representativo de respuestas revisadas por especialistas, quienes asignan puntuaciones por criterio y una decisión final de aceptar, corregir o rechazar. Los pesos pueden elegirse inicialmente según costo de fallo y después ajustarse para que la puntuación compuesta reproduzca esas decisiones humanas en un conjunto de validación.

**Ejemplo:** dos analistas revisan 100 respuestas sin conocer el score de DeepEval y registran:

| Caso | Correctness | Faithfulness | Decisión humana | Motivo |
|---|---:|---:|---|---|
| A | 0.88 | 0.91 | Aceptar | Respuesta correcta y respaldada |
| B | 0.62 | 0.90 | Corregir | Omite una parte de la comparación |
| C | 0.55 | 0.48 | Rechazar | Contiene una afirmación no respaldada |

Si los especialistas rechazan de manera consistente los casos con Faithfulness menor que `0.70`, esa observación proporciona evidencia para establecer una puerta cercana a ese valor. Si Actionability apenas cambia sus decisiones, su peso debería ser menor que el de Correctness o Faithfulness.

El registro mínimo para calibración podría tener esta estructura:

```python
human_labels = pd.DataFrame({
    "case_id": ["A", "B", "C"],
    "human_decision": ["accept", "revise", "reject"],
    "severity": ["none", "medium", "critical"],
})
```

### Elegir umbrales mediante riesgo observado

**Aprendizaje:** el umbral de cada métrica debe seleccionarse buscando una tasa de errores compatible con el uso previsto. En una aplicación financiera se prioriza minimizar respuestas aceptadas que contienen hechos incorrectos o no respaldados. La selección puede apoyarse en curvas precision-recall o ROC, pero debe confirmarse en un test separado y mediante análisis de errores severos.

**Ejemplo ilustrativo:** después de comparar los scores con las decisiones humanas, se prueban tres umbrales de Correctness:

| Umbral | Respuestas aprobadas | Aprobadas incorrectamente | Tasa de aprobación incorrecta |
|---:|---:|---:|---:|
| 0.50 | 80 | 12 | 15.0% |
| 0.60 | 65 | 4 | 6.2% |
| 0.70 | 45 | 1 | 2.2% |

Si la política del producto exige menos de 5% de respuestas incorrectas entre las aprobadas, `0.70` sería el primer candidato aceptable de esta tabla. Estos números son únicamente demostrativos; los valores reales deben calcularse con respuestas etiquetadas del proyecto.

```python
accepted = evaluation_df["correctness"] >= threshold
false_accepts = accepted & (evaluation_df["human_decision"] == "reject")

false_accept_rate = (
    false_accepts.sum() / accepted.sum()
    if accepted.sum() else 0
)
```

### Usar una política provisional cuando todavía hay pocos datos

**Hallazgo:** el benchmark actual contiene solamente 20 preguntas, una muestra demasiado pequeña para estimar umbrales estables.

**Aprendizaje:** mientras se amplía y etiqueta el benchmark, conviene usar reglas provisionales de no regresión: superar el baseline por un margen mínimo en la puntuación ponderada, no reducir el success rate y no caer más que una tolerancia pequeña en ninguna métrica crítica. Estas reglas son criterios temporales de selección, no objetivos definitivos de producción.

**Ejemplo aplicado al proyecto:** se define temporalmente que un nuevo prompt debe mejorar al menos `0.01` en la puntuación ponderada, mantener el success rate y no perder más de `0.02` en Correctness o Faithfulness.

```python
approved = all([
    candidate_weighted >= baseline_weighted + 0.01,
    candidate_success_rate >= baseline_success_rate,
    candidate_correctness >= baseline_correctness - 0.02,
    candidate_faithfulness >= baseline_faithfulness - 0.02,
])
```

Para la ejecución observada:

```text
Puntuación ponderada: 0.6396 → 0.6265   Falla
Success rate:         0.72   → 0.72     Cumple
Correctness:          0.5223 → 0.4331   Falla
Faithfulness:         0.7263 → 0.7584   Cumple
Resultado provisional: RECHAZAR
```

La tolerancia `0.02` y el margen `0.01` son reglas operativas iniciales. Deben reemplazarse cuando haya suficientes repeticiones para estimar el ruido del evaluador y suficientes etiquetas humanas para medir el riesgo real.

### Evaluar distribución, no solamente promedio

**Aprendizaje:** además del promedio, deben medirse el porcentaje de casos que supera cada umbral, el peor decil, los intervalos de confianza y la cantidad de fallos críticos. Un promedio aceptable no compensa una alucinación financiera severa.

**Ejemplo:** dos sistemas pueden tener el mismo promedio de Correctness:

```text
Sistema A: [0.80, 0.80, 0.80, 0.80, 0.80] → promedio 0.80
Sistema B: [0.40, 0.90, 0.90, 0.90, 0.90] → promedio 0.80
```

El Sistema B contiene un fallo mucho más grave, aunque el promedio sea idéntico. Por eso deben calcularse indicadores adicionales:

```python
scores = evaluation_df["correctness"]

summary = {
    "mean": scores.mean(),
    "minimum": scores.min(),
    "p10": scores.quantile(0.10),
    "pass_rate": (scores >= 0.70).mean(),
    "critical_failures": (scores < 0.50).sum(),
}
```

Una regla de aprobación más completa podría exigir simultáneamente:

```text
Promedio ponderado ≥ objetivo
Correctness pass rate ≥ 90%
Faithfulness pass rate ≥ 95%
Fallos críticos = 0
Límite inferior del intervalo de confianza ≥ mínimo aceptable
```
