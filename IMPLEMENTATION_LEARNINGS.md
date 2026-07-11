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

## Revisión 6 — Alcance educativo y tratamiento de fuentes heterogéneas

### Conservar la raw data y mejorar su representación

**Decisión de diseño:** en esta etapa el objetivo principal es aprender y demostrar los componentes de un pipeline RAG. Los archivos de `data/raw/` son datos de prueba y se conservarán sin modificaciones, incluso cuando su cobertura sea incompleta o no coincida completamente con el benchmark.

**Aprendizaje:** no es necesario alterar la fuente original para mejorar la recuperación. La ingestión puede transformar cada registro en un `Document` controlado, separando el texto que recibirá el modelo de embeddings de los campos que se conservarán como metadatos. Esto mantiene la trazabilidad y permite experimentar de forma reproducible.

Para noticias, el contenido indexado debería construirse explícitamente con título, fecha, fuente, descripción y contenido. La URL, el identificador de fila, la consulta de origen y la fecha deben conservarse como metadatos para filtros y citación. Para precios, el texto original puede mantenerse como `page_content`, mientras se extraen `ticker`, `date`, `name` y `row_id` como metadatos durante la ingestión. Para el PDF, deben añadirse al menos `dataset`, `source_file`, `document_type`, `page` y `chunk_id` sin modificar el archivo original.

### Usar cada fuente para enseñar una capacidad distinta de RAG

**Hallazgo:** noticias, precios y filings se indexan actualmente en una sola colección y se recuperan con similitud semántica `top-k`, aunque representan tipos de información diferentes.

**Aprendizaje:** mantener una colección común es aceptable para el baseline educativo, pero una segunda versión debe demostrar recuperación consciente de la fuente. Las noticias permiten practicar búsqueda semántica, filtros temporales, deduplicación y diversidad. Los precios permiten observar las limitaciones de embeddings ante fechas y valores exactos, y practicar filtros por metadata. Los filings permiten estudiar extracción de PDF, chunking, procedencia y recuperación por tipo de documento.

La comparación pedagógica recomendada es:

```text
Baseline:
todos los documentos → Chroma → similarity top-k → LLM

Mejorado:
query routing → filtro de dataset → filtros específicos
→ similarity o MMR → contexto con fuentes → LLM grounded
```

### Incorporar routing y filtros sin convertir el proyecto en una aplicación SQL

**Aprendizaje:** aunque en producción los precios exactos se consultarían preferentemente con pandas o SQL, en este proyecto pueden mantenerse en Chroma para aprender metadata filtering. Un router sencillo puede clasificar la pregunta como `global_news`, `stock_price_details`, `sec_filings` o multi-fuente. Para precios puede extraer ticker y fecha; para filings, términos como `10-K`, `10-Q`, auditoría o controles internos.

**Acción recomendada:** implementar primero reglas deterministas y transparentes. Las preguntas multi-fuente deben ejecutar una recuperación separada por dataset con un `k` pequeño por fuente y después combinar los resultados. Esto evita que una fuente domine el `top-k` y permite inspeccionar fácilmente por qué se recuperó cada documento.

### Comparar similarity search con MMR

**Aprendizaje:** variar solamente el prompt no permite estudiar el efecto del retriever. Deben compararse configuraciones de recuperación que mantengan constantes el corpus, la pregunta y el generador:

| Configuración | Estrategia |
|---|---|
| A | Similarity, `k=5` |
| B | MMR, `k=5`, `fetch_k=20` |
| C | Similarity con filtro de dataset |
| D | MMR con filtro de dataset |

Esta comparación permite medir si el filtrado mejora la precisión de fuente y si MMR reduce fragmentos redundantes.

### Tratar la falta de cobertura como un resultado observable

**Hallazgo:** algunas preguntas del benchmark solicitan fechas, documentos o combinaciones de fuentes que no están completamente cubiertas por los archivos raw disponibles.

**Aprendizaje:** en un proyecto educativo, esta limitación no obliga a modificar los datos. Es una oportunidad para distinguir entre fallo de recuperación, fallo de generación y ausencia de evidencia. Cada pregunta puede clasificarse en una tabla derivada como `SUPPORTED`, `PARTIAL` o `UNSUPPORTED`, sin alterar los archivos raw.

Una abstención explícita puede ser el comportamiento correcto cuando el corpus no contiene la evidencia solicitada. Su calidad debe evaluarse por separado de la coincidencia con una respuesta esperada que quizá provenga de otra versión del dataset.

### Evaluar retrieval antes de evaluar la respuesta

**Aprendizaje:** las métricas del LLM no explican por sí solas dónde falla el pipeline. Antes de medir Correctness o Actionability deben registrarse métricas deterministas de recuperación:

1. **Source accuracy:** si se recuperó el dataset esperado.
2. **Retrieval hit rate:** si algún documento contiene la evidencia o términos requeridos.
3. **Metadata accuracy:** si ticker, fecha, formulario o página coinciden con la consulta.
4. **Diversity:** cuántas fuentes o pasajes únicos aparecen en el contexto.
5. **Abstention quality:** si el sistema reconoce correctamente evidencia ausente o insuficiente.

### Secuencia de aprendizaje recomendada

1. Construir documentos explícitos para los CSV sin cambiar la raw data.
2. Añadir metadatos consistentes a noticias, precios y PDF.
3. Conservar el retriever actual como baseline.
4. Implementar routing por dataset y filtros de ticker o fecha.
5. Comparar similarity con MMR.
6. Evaluar retrieval independientemente de generation.
7. Comparar prompts usando exactamente los mismos contextos recuperados.
8. Experimentar después con `chunk_size`, `chunk_overlap` y `k`.

**Conclusión:** las imperfecciones del corpus forman parte útil del experimento. El objetivo no es ocultarlas, sino demostrar que un pipeline RAG debe conocer los límites de sus fuentes, recuperar con una estrategia apropiada y abstenerse cuando la evidencia no está disponible.

## Revisión 7 — Resultados de la evaluación holdout de la versión 2

### La comparación controlada produjo una aprobación provisional

**Evidencia:** la versión 2 separó los ejemplos utilizados por GEPA de ocho casos holdout y reutilizó exactamente los mismos contextos para el baseline y el prompt optimizado. Sobre 40 evaluaciones —ocho preguntas por cinco métricas— el promedio global aumentó de `0.6991` a `0.7226` y el success rate de `0.725` a `0.775`, sin errores de ejecución.

El score ponderado también aumentó:

```text
Baseline:   0.6836
Optimizado: 0.7023
Diferencia: +0.0187
```

**Aprendizaje:** congelar los contextos y usar un holdout permite atribuir las diferencias principalmente al prompt, en lugar de confundirlas con cambios de retrieval o reutilización de los ejemplos de optimización. Bajo la política provisional definida, los cinco quality gates se cumplieron y el resultado fue `APPROVE`.

Esta aprobación significa que el prompt es el mejor candidato dentro del experimento actual; no demuestra todavía superioridad estadística o aptitud para producción.

### Las mejoras se concentraron en groundedness y utilidad

**Evidencia:** las mayores mejoras se observaron en:

| Métrica | Baseline | Optimizado | Delta |
|---|---:|---:|---:|
| Broker Actionability | 0.7952 | 0.8742 | +0.0790 |
| Faithfulness / Groundedness | 0.7046 | 0.7562 | +0.0516 |
| Answer Relevance | 0.8563 | 0.8647 | +0.0084 |

En el análisis por caso, el prompt optimizado ganó cuatro de ocho casos en Broker Actionability frente a dos del baseline, y cinco de ocho en Faithfulness frente a tres del baseline.

**Aprendizaje:** la optimización consiguió el comportamiento buscado por el prompt: respuestas mejor respaldadas y más útiles para una conversación con clientes. Answer Relevance ya era alta en el baseline, por lo que su mejora marginal de `0.0084` aporta poca evidencia adicional.

### El gate de Correctness pasó por un margen frágil

**Evidencia:** Answer Correctness disminuyó de `0.6582` a `0.6395`, una regresión de aproximadamente `0.0186`. La política permitía una caída máxima de `0.02`:

```text
Mínimo permitido: 0.6582 - 0.0200 = 0.6382
Resultado:         0.6395
Margen del gate:   aproximadamente 0.0013
```

La comparación por caso terminó equilibrada: tres victorias para cada prompt y dos empates. El menor promedio optimizado indica que la magnitud de las pérdidas fue ligeramente mayor que la de sus ganancias.

**Aprendizaje:** un gate booleano puede ocultar cuán cerca estuvo de fallar. Los reportes deben mostrar no solamente `passed`, sino también el valor observado, el límite exigido y el margen. La aprobación debe considerarse sensible al ruido del juez porque una variación pequeña podría cambiar el resultado.

**Acción recomendada:** repetir la evaluación varias veces con los mismos contextos y registrar la distribución de Correctness antes de considerar estable la decisión. El gate debería evaluarse con el promedio de repeticiones o con un intervalo de confianza, no solamente con una corrida.

### Context Relevance confirmó la variabilidad del juez

**Evidencia:** aunque baseline y optimizado recibieron contextos idénticos, Context Relevance cambió de `0.4814` a `0.4786`. Cinco de los ocho casos fueron empates, dos favorecieron al baseline y uno al optimizado.

**Aprendizaje:** una diferencia de `-0.0028` en una métrica cuyo input no cambió es evidencia empírica de variabilidad del evaluador LLM. No debe atribuirse al prompt ni interpretarse como una degradación del retriever.

**Decisión de diseño validada:** Context Relevance debe permanecer en la evaluación final para diagnosticar retrieval, pero no debe formar parte del objetivo de optimización de GEPA cuando el prompt no controla el contexto recuperado.

### GEPA produjo una modificación material del seed

**Evidencia:** la comparación normalizada reportó `Did GEPA modify the seed prompt? True`. Esto evita confundir cambios reales con diferencias únicamente de espacios o saltos de línea.

**Aprendizaje:** verificar que el optimizador modificó el prompt es una condición necesaria, pero no suficiente. La aceptación depende del desempeño holdout y de los quality gates. En esta ejecución ambas condiciones se cumplieron: hubo una modificación material y el candidato superó la política provisional.

### Un holdout pequeño limita la fuerza de la conclusión

**Hallazgo:** la evaluación final utilizó ocho preguntas, equivalentes a ocho observaciones por métrica. Los 40 scores agregados no constituyen 40 preguntas independientes, porque cada pregunta contribuye cinco métricas relacionadas.

**Aprendizaje:** el tamaño efectivo para evaluar cada métrica sigue siendo ocho. Por ello, cambios de una o dos preguntas pueden alterar sustancialmente promedios, success rate y gates. No debe interpretarse el aumento del success rate de `0.725` a `0.775` como evidencia robusta sin repeticiones o más casos holdout.

### Próxima validación recomendada

Manteniendo intactos los contextos y prompts de esta ejecución:

1. Repetir los jueces LLM al menos tres veces.
2. Reportar media, desviación, mínimo y máximo por métrica.
3. Mostrar el margen de cada quality gate.
4. Revisar manualmente los casos donde Correctness disminuyó.
5. Confirmar si la mejora de Faithfulness representa prudencia útil o abstenciones excesivas.
6. Mantener la decisión como `APPROVE_PROVISIONAL` hasta comprobar estabilidad.

**Conclusión:** la versión 2 ofrece evidencia favorable al prompt optimizado y mejora la validez del experimento. Sin embargo, el resultado está condicionado por un holdout pequeño y por un gate de Correctness que pasó con margen mínimo. La principal lección es que una política de aprobación debe comunicar también incertidumbre y distancia al límite, no solamente un resultado booleano.
