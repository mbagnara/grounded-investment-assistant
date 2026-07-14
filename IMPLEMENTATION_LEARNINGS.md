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

## Revisión 8 — De archivos raw a documentos, embeddings y una colección Chroma

### La unidad de indexación no es el archivo completo

**Aprendizaje:** los tres archivos raw no se convierten en solamente tres embeddings. Cada fuente se transforma primero en unidades de recuperación pequeñas e independientes, representadas mediante objetos `Document` de LangChain:

```text
stock_price_details.csv → un Document por fila de precio
global_news.csv         → un Document por noticia
sec_filings_10q.pdf     → un Document por chunk de texto
```

Después, el modelo de embeddings genera un vector por cada `Document`. Si existen 500 filas de precios, 500 noticias y 100 chunks SEC, Chroma recibe aproximadamente 1,100 registros y embeddings, no tres.

```text
3 archivos raw
    ↓
1,100 Documents
    ↓
1,100 embeddings
    ↓
colección Chroma
```

**Razón de diseño:** un embedding que representara todo un CSV o todo el PDF sería demasiado general. También obligaría a enviar grandes cantidades de texto irrelevante al LLM. Las unidades pequeñas permiten recuperar únicamente las filas, noticias o fragmentos relacionados con la pregunta.

### `Document` mantiene juntos contenido y procedencia

Un `Document` contiene dos componentes con funciones distintas:

```python
Document(
    page_content="Text used for semantic retrieval",
    metadata={
        "dataset": "source identifier",
        "source_file": "original file",
    },
)
```

`page_content` es el texto enviado al modelo de embeddings y posteriormente al LLM si el documento es recuperado. `metadata` no se convierte en embedding en esta implementación; se almacena como información estructurada para filtros, trazabilidad, citas y diagnóstico.

Ejemplo de precio:

```python
Document(
    page_content=(
        "On this record, Date is 2026-03-12, ticker is 0700.HK, "
        "name is Tencent (Hong Kong), Open is 550.5, Close is 546.5..."
    ),
    metadata={
        "dataset": "stock_price_details",
        "source_file": "stock_price_details.csv",
        "row_id": 0,
        "ticker": "0700.HK",
        "date": "2026-03-12",
        "name": "Tencent (Hong Kong)",
    },
)
```

Esta separación permite combinar búsqueda semántica y restricciones exactas:

```text
page_content → "¿Este registro es semánticamente relevante?"
metadata     → "¿Pertenece exactamente a 0700.HK y a esta fecha?"
```

### Los CSV requieren representaciones distintas según su contenido

**Precios:** cada fila ya describe una observación independiente, por lo que se convierte en un `Document`. El resumen completo se usa como `page_content`; ticker, fecha, nombre y fila se extraen como metadata.

**Noticias:** cada fila representa un artículo. El texto semántico se construye explícitamente para que el embedding reciba los campos informativos:

```text
Title
Published at
Source
Description
Content
```

URL, fecha, título, fuente, query de recopilación y `row_id` se mantienen como metadata. Esto permite citar la noticia y aplicar filtros sin depender de que el embedding interprete correctamente una URL o una fecha exacta.

**Aprendizaje:** no existe una transformación universal para todos los CSV. El diseño de `page_content` y metadata debe reflejar qué representa cada fila y cómo se espera recuperarla.

### El PDF requiere chunking antes de crear embeddings

**Aprendizaje:** un filing completo es demasiado largo y contiene múltiples secciones. `PyPDFLoader` lo carga conservando procedencia por página y `RecursiveCharacterTextSplitter` divide esas páginas en chunks con overlap.

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

sec_docs = text_splitter.split_documents(sec_raw_docs)
```

Cada chunk conserva o recibe metadata como:

```python
{
    "dataset": "sec_filings",
    "source_file": "sec_filings_10q.pdf",
    "document_type": "10-Q",
    "page": 12,
    "chunk_id": 47,
}
```

El overlap ayuda a evitar que una idea ubicada en el límite entre dos chunks pierda completamente su contexto. El costo es cierta duplicación, por lo que retrieval debe deduplicar o favorecer diversidad cuando sea necesario.

#### Por qué el código agrega `chunk_id` pero no agrega `page` manualmente

**Aclaración:** la metadata `page` sí está presente en los chunks SEC, aunque no aparezca una asignación explícita como:

```python
doc.metadata["page"] = page_number
```

La razón es que `PyPDFLoader` agrega automáticamente la posición de página cuando carga el PDF:

```python
sec_loader = PyPDFLoader(str(sec_pdf_path))
sec_raw_docs = sec_loader.load()
```

Un documento de página puede tener inicialmente esta forma:

```python
Document(
    page_content="Text extracted from this PDF page...",
    metadata={
        "source": "../data/raw/sec_filings_10q.pdf",
        "page": 12,
    },
)
```

El notebook después enriquece esa metadata:

```python
doc.metadata.update({
    "dataset": "sec_filings",
    "source_file": sec_pdf_path.name,
    "document_type": "10-Q",
})
```

`update()` agrega las nuevas claves sin eliminar `page`. Conceptualmente, la metadata queda así:

```python
{
    "source": "../data/raw/sec_filings_10q.pdf",
    "page": 12,
    "dataset": "sec_filings",
    "source_file": "sec_filings_10q.pdf",
    "document_type": "10-Q",
}
```

Cuando se ejecuta:

```python
sec_docs = text_splitter.split_documents(sec_raw_docs)
```

`split_documents()` divide el `page_content`, pero copia la metadata del documento padre a cada chunk resultante. Si la página 12 genera tres chunks, los tres conservan:

```python
{"page": 12}
```

`chunk_id`, en cambio, no puede existir antes del split porque `PyPDFLoader` no sabe cuántos chunks producirá el text splitter. Por eso se crea después:

```python
for chunk_id, doc in enumerate(sec_docs):
    doc.metadata["chunk_id"] = chunk_id
```

El resultado final combina metadata heredada y metadata creada por el proyecto:

```python
{
    "dataset": "sec_filings",
    "source_file": "sec_filings_10q.pdf",
    "document_type": "10-Q",
    "page": 12,
    "chunk_id": 47,
}
```

```text
page     → creada por PyPDFLoader y heredada por el chunk
chunk_id → creada por el notebook después del chunking
```

No se reasigna `page` manualmente porque sería redundante y podría sobrescribir metadata confiable proporcionada por el loader.

La herencia se puede verificar directamente:

```python
print("Before chunking:", sec_raw_docs[0].metadata)
print("After chunking:", sec_docs[0].metadata)
```

Dependiendo de la versión del loader, también pueden aparecer campos como `page_label` o `total_pages`. Normalmente `page` utiliza índice basado en cero:

```text
page = 0 → primera página física del PDF
page = 1 → segunda página física del PDF
```

La posición física puede diferir del número visual impreso en el filing debido a portada, índice, numeración romana o anexos. Cuando existe, `page_label` ayuda a conservar esa distinción.

### El regex convierte texto legible en metadata filtrable

El precio llega como un único string. La expresión regular identifica y captura campos con nombre:

```python
price_record_pattern = re.compile(
    r"Date is (?P<date>[^,]+), ticker is (?P<ticker>[^,]+), "
    r"name is (?P<name>[^,]+),"
)

match = price_record_pattern.search(price_summary)
```

Si existe una coincidencia:

```python
fields = match.groupdict()
```

produce conceptualmente:

```python
{
    "date": "2026-03-12",
    "ticker": "0700.HK",
    "name": "Tencent (Hong Kong)",
}
```

Si `match` es `None`, la fila se registra como no procesada y no se agrega a `stock_docs`. Al terminar, el notebook genera un error si hubo filas no parseadas.

**Aprendizaje:** esta validación evita indexar silenciosamente documentos con ticker o fecha faltantes. Un documento con `metadata={"ticker": None}` podría existir en Chroma, pero no aparecería al aplicar un filtro exacto, creando un fallo difícil de diagnosticar.

### Las listas reúnen documentos independientes antes de indexarlos

Cada iteración del CSV construye una unidad válida y la agrega a su colección en memoria:

```python
stock_docs.append(Document(...))
news_docs.append(Document(...))
```

Las listas no fusionan los documentos; solamente los reúnen para enviarlos al vector store:

```python
csv_docs = stock_docs + news_docs
all_docs = csv_docs + sec_docs
```

Conceptualmente:

```text
all_docs
├── Document de precio 1
├── Document de precio 2
├── Document de noticia 1
├── Document de noticia 2
├── Document SEC chunk 1
└── Document SEC chunk 2
```

Chroma genera y almacena un embedding separado por elemento. Esto preserva la granularidad necesaria para recuperar evidencia específica.

### Una colección física puede contener tres fuentes lógicas

Los documentos se almacenan juntos en:

```python
collection_name = "investment_rag_v2"
```

La separación se mantiene mediante:

```python
metadata["dataset"]
```

```text
investment_rag_v2
├── dataset = stock_price_details
├── dataset = global_news
└── dataset = sec_filings
```

Esto permite recuperar solamente una fuente:

```python
filter={"dataset": {"$eq": "sec_filings"}}
```

o ejecutar búsquedas separadas por fuente y combinar los resultados para una pregunta multi-fuente.

**Aprendizaje:** una colección compartida es razonable para este proyecto educativo porque todas las fuentes utilizan el mismo embedding model y el routing puede separarlas mediante metadata. Colecciones independientes serían más apropiadas si las fuentes necesitaran modelos, permisos, ciclos de actualización o políticas de retención diferentes.

### Por qué este proyecto utiliza una sola colección

**Decisión de diseño:** `investment_rag_v2` funciona como una capa unificada de conocimiento financiero. Los documentos siguen siendo independientes y conservan su fuente, pero comparten el mismo espacio vectorial porque todos se generan con:

```python
OpenAIEmbeddings(model="text-embedding-3-small")
```

Usar una sola colección aporta cinco ventajas concretas en este proyecto:

1. **Simplifica el aprendizaje del pipeline.** Solo es necesario crear, persistir y administrar un vector store. Esto permite concentrarse en ingestión, embeddings, metadata, retrieval y generación sin introducir coordinación prematura entre varias bases vectoriales.

2. **Mantiene todas las fuentes en el mismo espacio semántico.** Una pregunta y todos los documentos se representan con el mismo embedding model. Sus vectores son comparables y pueden buscarse mediante una interfaz común.

3. **Facilita preguntas multi-fuente.** Una consulta puede necesitar simultáneamente noticias y filings, o precios y filings. El pipeline usa la misma colección, ejecuta búsquedas filtradas por cada dataset y combina los documentos recuperados.

4. **Centraliza persistencia y reproducibilidad.** Existe un solo nombre de colección, un único conteo de documentos y una única política de IDs deterministas. Esto hace más sencillo reconstruir y verificar el índice completo.

5. **Demuestra separación lógica mediante metadata.** Aunque físicamente comparten colección, los documentos no pierden su identidad. El campo `dataset` actúa como una partición lógica.

Ejemplo de pregunta de una sola fuente:

```text
What did the SEC filing say about internal controls?
```

El router selecciona:

```python
datasets = ["sec_filings"]
```

y Chroma recibe un filtro:

```python
filter={"dataset": {"$eq": "sec_filings"}}
```

Aunque precios y noticias estén almacenados en la misma colección, no participan en esa búsqueda.

Ejemplo multi-fuente:

```text
Based on the SEC filings and recent market news, which company appears lower risk?
```

El router puede seleccionar:

```python
datasets = ["sec_filings", "global_news"]
```

Luego realiza conceptualmente dos búsquedas sobre la misma colección:

```python
sec_docs = similarity_search(
    question,
    filter={"dataset": {"$eq": "sec_filings"}},
)

news_docs = similarity_search(
    question,
    filter={"dataset": {"$eq": "global_news"}},
)

retrieved_docs = sec_docs + news_docs
```

Este patrón garantiza representación de las fuentes solicitadas sin mantener varios objetos Chroma.

**Aclaración:** una sola colección no significa un único embedding ni un único documento combinado. Cada fila, noticia o chunk sigue almacenándose como un registro separado:

```text
Una colección
├── muchos embeddings de precios
├── muchos embeddings de noticias
└── muchos embeddings de chunks SEC
```

La colección es el contenedor común; los `Document` siguen siendo las unidades individuales de recuperación.

### Cuándo sería preferible usar colecciones separadas

La decisión de una colección no es universal. Conviene separar fuentes cuando exista al menos una de estas necesidades:

- Diferentes embedding models por tipo de contenido.
- Permisos de acceso distintos para noticias, precios o documentos regulatorios.
- Ciclos de actualización independientes y de gran escala.
- Políticas diferentes de retención o eliminación.
- Configuraciones de distancia o indexación incompatibles.
- Equipos o servicios distintos responsables de cada fuente.
- Volúmenes suficientemente grandes para escalar cada índice por separado.

Ejemplo:

```text
investment_news
investment_prices
investment_sec_filings
```

En esa arquitectura, un componente superior tendría que consultar una o varias colecciones y fusionar sus resultados. Esa complejidad puede ser útil en producción, pero no es necesaria para demostrar los objetivos actuales del notebook.

**Conclusión de diseño:** se utiliza una sola colección porque las tres fuentes comparten embedding model, pertenecen al mismo dominio financiero y pueden separarse de manera suficiente mediante metadata. Esto mantiene el pipeline sencillo y permite recuperación multi-fuente, sin sacrificar la procedencia individual de cada documento.

### Los IDs deterministas hacen reproducible la colección

Antes de indexar, cada `Document` recibe un ID derivado de su contenido y metadata:

```python
identity = json.dumps(doc.metadata, sort_keys=True) + doc.page_content
document_id = sha256(identity.encode("utf-8")).hexdigest()
```

**Aprendizaje:** el ID representa la identidad completa de la unidad indexada. Si contenido y metadata no cambian, el ID tampoco cambia. Esto ayuda a detectar duplicados y evita que la misma fila o chunk aparezca varias veces con IDs aleatorios después de reejecutar el notebook.

#### El ID funciona como clave de gestión del registro vectorial

El ID no es solamente una etiqueta descriptiva. Dentro de Chroma cumple una función similar a una clave primaria: permite distinguir y administrar cada registro independientemente de los demás.

Conceptualmente, un registro contiene:

```text
Chroma record
├── id         → identidad y gestión
├── embedding  → búsqueda por similitud
├── document   → texto original
└── metadata   → filtros y procedencia
```

El embedding responde a la pregunta “¿qué documentos se parecen semánticamente a la consulta?”. El ID responde a otra pregunta: “¿qué registro exacto debe insertarse, reemplazarse, consultarse o eliminarse?”.

Esta diferencia es importante porque dos documentos podrían tener embeddings muy parecidos y aun así representar registros distintos. Por ejemplo, dos observaciones consecutivas de Tencent pueden tener texto casi idéntico, pero pertenecen a fechas distintas y necesitan IDs distintos.

```text
Tencent — 2026-03-11 → document_id A
Tencent — 2026-03-12 → document_id B
```

#### Inserciones idempotentes y control de duplicados

Una operación es idempotente cuando repetirla no crea efectos adicionales. Si el mismo `Document` produce siempre el mismo ID, el pipeline puede reconocer que se trata de la misma unidad lógica.

```python
first_run_id = deterministic_document_id(doc)
second_run_id = deterministic_document_id(doc)

assert first_run_id == second_run_id
```

Sin IDs deterministas, dos ejecuciones podrían asignar valores aleatorios:

```text
Primera ejecución:  price-row-123 → random-id-A
Segunda ejecución:  price-row-123 → random-id-B
```

Chroma podría interpretar ambos como registros diferentes y devolver contenido duplicado durante retrieval. Con un ID estable:

```text
Primera ejecución:  price-row-123 → hash-X
Segunda ejecución:  price-row-123 → hash-X
```

el sistema puede detectar la duplicación antes de indexar o utilizar una operación de actualización/upsert cuando corresponda.

En el notebook se valida además que los IDs generados sean únicos dentro del lote:

```python
document_ids = [deterministic_document_id(doc) for doc in all_docs]

if len(document_ids) != len(set(document_ids)):
    raise ValueError("Duplicate document identities were detected before indexing.")
```

Esto evita enviar a Chroma dos unidades con la misma identidad durante una misma construcción del índice.

#### Actualización y eliminación selectiva

Un ID conocido permite administrar un registro sin reconstruir conceptualmente toda la colección:

```python
vector_store.delete(ids=[document_id])
```

También permite implementar un flujo de actualización:

```text
identificar el registro anterior
    ↓
eliminar o reemplazar por ID
    ↓
generar el embedding actualizado
    ↓
guardar la nueva versión
```

Por ejemplo, si se corrige una noticia o se reemplaza un chunk mal extraído, el ID permite dirigir la operación al registro correspondiente, en vez de buscarlo por similitud semántica y arriesgarse a modificar otro documento parecido.

El notebook actual reconstruye completamente `investment_rag_v2` en cada ejecución, por lo que todavía no necesita actualizaciones incrementales. Sin embargo, los IDs deterministas dejan preparado el modelo de datos para implementar esas operaciones posteriormente.

#### Trazabilidad desde Chroma hasta la fuente

El ID identifica el registro vectorial, pero debe complementarse con metadata de procedencia:

```python
{
    "source_file": "stock_price_details.csv",
    "row_id": 0,
    "ticker": "0700.HK",
    "date": "2026-03-12",
}
```

La combinación permite recorrer el linaje en ambas direcciones:

```text
archivo raw + fila/chunk
        ↓
Document
        ↓
document_id
        ↓
registro Chroma
```

Y durante una investigación:

```text
registro recuperado de Chroma
        ↓
document_id + metadata
        ↓
archivo, fila, página o chunk de origen
```

Esto facilita auditoría, explicación de respuestas y diagnóstico de problemas de retrieval.

#### `document_id`, `row_id` y `chunk_id` no cumplen la misma función

Los tres identificadores se complementan:

| Identificador | Alcance | Función |
|---|---|---|
| `document_id` | Toda la colección Chroma | Identifica de forma única el registro vectorial |
| `row_id` | Un CSV específico | Indica la fila raw que originó el documento |
| `chunk_id` | La lista de chunks SEC | Indica la unidad creada durante el chunking |

Ejemplo de precio:

```text
document_id = a87f...  → registro Chroma
source_file = stock_price_details.csv
row_id = 0             → fila de origen
```

Ejemplo SEC:

```text
document_id = b31c...  → registro Chroma
source_file = sec_filings_10q.pdf
page = 12              → página heredada del loader
chunk_id = 47          → chunk creado por el splitter
```

`row_id` o `chunk_id` por sí solos no garantizan unicidad global. Podría existir un `row_id=0` en ambos CSV, o un nuevo proceso de chunking podría volver a producir `chunk_id=0`. El hash incorpora contenido y metadata para crear una identidad válida en toda la colección.

#### Propiedad de detección de cambios

Como el hash depende de `page_content` y metadata, cualquier cambio relevante genera un ID diferente:

```text
mismo contenido + misma metadata → mismo ID
contenido modificado             → nuevo ID
metadata modificada              → nuevo ID
```

Esto convierte el ID en una huella de la versión exacta del documento. Puede utilizarse para detectar que una unidad necesita un nuevo embedding.

Por ejemplo:

```text
Close = 546.5 → hash-A
Close = 547.0 → hash-B
```

El nuevo valor produce una identidad diferente y señala que el registro vectorial anterior ya no representa el contenido actual.

#### Limitación de los IDs basados en contenido

Un ID nuevo no elimina automáticamente el registro anterior. En un pipeline incremental, si cambia el contenido y se agrega el nuevo hash sin eliminar el antiguo, ambas versiones podrían permanecer en Chroma.

```text
versión anterior → hash-A → todavía almacenada
versión nueva    → hash-B → agregada
```

Por eso, una estrategia incremental necesita además una clave estable de origen, por ejemplo:

```text
source_file + row_id
source_file + page + local_chunk_position
URL de la noticia
```

Esa clave estable permite localizar la versión anterior; el hash permite comprobar si su contenido cambió.

```text
source key → identidad lógica estable
content hash → versión exacta del contenido
```

El notebook evita actualmente este problema eliminando y reconstruyendo la colección antes de indexar. En un sistema de actualización continua habría que registrar ambas identidades o mantener un manifiesto de indexación.

#### Colisiones y seguridad práctica

SHA-256 produce un espacio de IDs extremadamente grande. La posibilidad de que dos contenidos diferentes generen accidentalmente el mismo hash es despreciable para la escala del proyecto. Aun así, el hash se utiliza aquí como mecanismo de identidad y reproducibilidad, no como prueba de autenticidad o firma digital del documento.

**Conclusión de gestión:** un ID bien diseñado permite responder cuatro preguntas operativas fundamentales:

```text
¿Ya indexé esta unidad?
¿Qué registro exacto recuperé?
¿Qué registro debo actualizar o eliminar?
¿Cambió el contenido desde la última indexación?
```

Los embeddings hacen posible encontrar documentos por significado; los IDs hacen posible gestionarlos con precisión durante todo su ciclo de vida.

### Modelo mental consolidado

```text
RAW SOURCE
    ↓
load and validate
    ↓
choose retrieval unit
    ├── price row
    ├── news article
    └── PDF chunk
    ↓
Document
    ├── page_content → embedding and LLM context
    └── metadata     → filters, provenance and citations
    ↓
list of Documents
    ↓
deterministic IDs + embedding model
    ↓
one Chroma collection
    ↓
source-aware filtered retrieval
```

**Conclusión:** el principio más importante es que los archivos son fuentes de datos, pero los `Document` son las unidades reales del RAG. La calidad del pipeline depende de elegir correctamente esas unidades, validar su metadata y conservar suficiente procedencia para recuperar y explicar cada respuesta.

## Revisión 9 — Protocolo experimental de la sección 1.5

### La sección 1.5 hace más que cargar el benchmark

**Aprendizaje:** aunque el encabezado menciona cargar el gold benchmark y evaluar el baseline, la función principal de esta sección es construir el protocolo experimental que conecta retrieval, generación y evaluación. Las métricas DeepEval se calculan posteriormente en la sección 1.7.

El flujo completo es:

```text
golden_benchmark_dataset.csv
        ↓
validar y limpiar
        ↓
normalizar nombres de fuentes
        ↓
separar optimización y holdout
        ↓
recuperar evidencia una vez
        ↓
congelar contextos
        ↓
diagnosticar retrieval
        ↓
generar respuestas baseline
        ↓
crear LLMTestCase para DeepEval
```

Esta separación de responsabilidades permite identificar si un fallo proviene del benchmark, retrieval, generación o evaluación.

### Validar el benchmark antes de consumir modelos

La sección exige las columnas:

```python
required_columns = {
    "question",
    "response",
    "source_hint",
    "supporting_sources",
    "context",
}
```

**Aprendizaje:** la validación debe ocurrir antes de realizar llamadas de embeddings o LLM. Si falta `question`, no existe input; si falta `response`, no puede evaluarse Correctness; si falta `supporting_sources`, no puede verificarse procedencia.

También se eliminan filas sin pregunta o respuesta:

```python
gold_df = gold_df.dropna(
    subset=["question", "response"]
).reset_index(drop=True)
```

y se asigna:

```python
gold_df["case_id"] = gold_df.index + 1
```

`case_id` funciona como clave de unión entre respuestas baseline, respuestas optimizadas, scores, razones del juez y diagnósticos. A diferencia del `document_id` de Chroma, identifica un caso experimental, no un documento indexado.

### Normalizar nombres físicos a datasets lógicos

El benchmark conserva nombres como:

```text
all_prices_clean.csv
sec_filings.txt
```

mientras la implementación utiliza:

```text
stock_price_details.csv
sec_filings_10q.pdf
```

`SOURCE_DATASET_MAP` transforma ambos contratos físicos a identificadores lógicos:

```text
all_prices_clean.csv       → stock_price_details
stock_price_details.csv    → stock_price_details
sec_filings.txt            → sec_filings
sec_filings_10q.pdf        → sec_filings
global_news.csv            → global_news
```

**Aprendizaje:** evaluación y retrieval deben comparar categorías estables, no depender directamente de nombres de archivo que pueden cambiar. Si una fuente no existe en el mapa, la ejecución se detiene para evitar clasificaciones silenciosamente incorrectas.

### El holdout representa el examen no visto por GEPA

El benchmark de 20 preguntas se divide en:

```text
optimization_df → 12 casos observados por GEPA
evaluation_df   →  8 casos holdout
```

El holdout puede entenderse como un examen final:

```text
optimization_df → ejercicios de práctica
evaluation_df   → examen con preguntas no usadas para optimizar
```

**Aprendizaje:** si GEPA optimizara y se evaluara sobre las mismas preguntas, un score mayor podría reflejar memorización o adaptación específica, no una mejora generalizable. Separar el holdout reduce data leakage y permite medir mejor si las reglas del nuevo prompt funcionan en ejemplos no vistos.

El split usa:

```python
.groupby("expected_dataset")
.sample(frac=0.4, random_state=42)
```

`groupby()` conserva representación aproximada de noticias, precios y filings. `random_state=42` garantiza que las mismas preguntas formen el holdout en ejecuciones repetidas.

### El holdout actual es suficiente para aprender, no para concluir estadísticamente

Ocho preguntas implican solamente ocho observaciones independientes por métrica:

```text
8 preguntas × 5 métricas = 40 scores
```

Los 40 scores no equivalen a 40 preguntas independientes porque las cinco métricas evalúan las mismas ocho respuestas.

**Aprendizaje:** una o dos preguntas pueden cambiar significativamente los promedios y quality gates. Las conclusiones deben expresarse como `APPROVE_PROVISIONAL` hasta repetir los jueces o ampliar el holdout.

En un proyecto mayor se separarían tres conjuntos:

```text
train      → optimizar el prompt
validation → seleccionar configuración y thresholds
test       → evaluación final una sola vez
```

El notebook utiliza una simplificación:

```text
optimization_df → train/validation combinados
evaluation_df   → holdout test
```

### Congelar contextos aísla el efecto del prompt

La sección ejecuta retrieval una sola vez por pregunta y guarda:

```python
benchmark_contexts[question] = {
    "documents": docs,
    "formatted_context": format_retrieved_context(docs),
    "retrieval_context": [doc.page_content for doc in docs],
    "retrieved_sources": [...],
    "diagnostics": retrieval_result["diagnostics"],
}
```

Cada representación tiene un consumidor distinto:

| Campo | Consumidor |
|---|---|
| `documents` | Diagnóstico y metadata |
| `formatted_context` | Prompt enviado al generador |
| `retrieval_context` | Métricas DeepEval |
| `retrieved_sources` | Trazabilidad y presentación |
| `diagnostics` | Auditoría del router y filtros |

Baseline, GEPA y prompt optimizado reutilizan el mismo cache:

```text
misma pregunta
misma evidencia
mismo modelo
misma temperatura
diferente prompt
```

**Aprendizaje:** si cada prompt ejecutara retrieval independientemente, una diferencia de score podría deberse a contextos distintos. Congelar la evidencia convierte la sección 2 en un experimento de prompt más limpio.

### El cache no entrega las respuestas holdout a GEPA

Guardar los documentos de todas las preguntas no significa necesariamente filtrar las respuestas esperadas del holdout al optimizador. GEPA recibe goldens construidos solamente desde `optimization_df`.

```text
Contexto holdout almacenado
→ necesario para ejecutar ambos prompts con la misma evidencia

Respuesta esperada holdout no entregada como Golden a GEPA
→ preserva la separación experimental
```

**Aprendizaje:** lo que debe mantenerse fuera del proceso de selección es el par evaluativo `pregunta + respuesta esperada`, no necesariamente la existencia técnica del contexto recuperado.

### Riesgo de utilizar la pregunta como clave del cache

Actualmente:

```python
benchmark_contexts[row["question"]] = {...}
```

funciona porque las preguntas del benchmark son únicas. Si dos filas tuvieran exactamente la misma pregunta, la segunda sobrescribiría la primera entrada.

Una opción más robusta sería:

```python
benchmark_contexts[row["case_id"]] = {...}
```

y acceder mediante `case_id` durante baseline, GEPA y evaluación.

**Aprendizaje:** las claves de cache deben representar la identidad del caso experimental. El texto de la pregunta es conveniente, pero `case_id` es más seguro cuando pueden existir duplicados o versiones de la misma pregunta.

### Diagnosticar retrieval antes de culpar al generador

`retrieval_quality()` compara:

- Dataset esperado.
- Datasets recuperados.
- Ticker solicitado.
- Fechas solicitadas.
- Cantidad de fuentes únicas.

y produce:

```text
SUPPORTED
PARTIAL
UNSUPPORTED
```

```text
UNSUPPORTED
→ no apareció el dataset esperado

PARTIAL
→ apareció la fuente, pero falta un constraint detectado

SUPPORTED
→ coincidieron la fuente y los constraints detectados
```

**Aclaración:** `SUPPORTED` no garantiza que el contexto contenga todos los hechos requeridos. Indica solamente que las verificaciones implementadas pasaron. Una pregunta puede recuperar el dataset correcto pero omitir la oración específica que contiene la respuesta.

Por ello, el estado debería interpretarse como calidad de constraints recuperados, no como una prueba completa de suficiencia factual.

### Las fechas naturales son una limitación del diagnóstico actual

`extract_question_constraints()` reconoce fechas ISO:

```text
2026-03-12
```

pero el benchmark también utiliza:

```text
October 23, 2025
November 6, 2025
April 17, 2026
```

Si la fecha no es detectada:

```python
requested_dates = []
date_match = None
```

el caso podría marcarse `SUPPORTED` aunque falte una de las fechas necesarias. Esto explica por qué un resultado de cobertura puede parecer correcto mientras la respuesta indica que no encontró el valor solicitado.

**Acción recomendada:** normalizar fechas naturales a `YYYY-MM-DD` antes de construir filtros y diagnósticos. Después, `date_match=False` podrá distinguir correctamente una recuperación parcial.

### Generar el baseline sobre el holdout establece el punto de comparación

La sección utiliza:

```python
baseline_eval_df = evaluation_df.copy()
```

y genera respuestas solamente para esos ocho casos. No vuelve a ejecutar retrieval; usa `benchmark_contexts`.

Cada fila de `baseline_results_df` conserva:

```text
case_id
question
expected_output
actual_output
retrieved_context
retrieved_sources
expected_dataset
retrieved_datasets
source_match
ticker_match
date_match
coverage_status
```

**Aprendizaje:** guardar respuesta y evidencia juntas permite investigar si un score bajo ocurrió porque la evidencia faltaba, el modelo la interpretó mal o el benchmark esperaba otra fuente.

### `LLMTestCase` conecta el pipeline con DeepEval

Cada respuesta baseline produce:

```python
LLMTestCase(
    input=question,
    actual_output=response.content,
    expected_output=expected_answer,
    retrieval_context=cached["retrieval_context"],
)
```

Los campos permiten evaluar dimensiones diferentes:

```text
input + actual_output + expected_output
→ Answer Correctness

actual_output + retrieval_context
→ Faithfulness

input + retrieval_context
→ Context Relevance

input + actual_output
→ Answer Relevance
```

**Aprendizaje:** un solo caso de prueba contiene las capas necesarias para separar corrección respecto del benchmark, fidelidad respecto de la evidencia y relevancia respecto de la pregunta.

### Objetos producidos por la sección 1.5

| Objeto | Responsabilidad |
|---|---|
| `gold_df` | Benchmark completo validado |
| `optimization_df` | Casos visibles para GEPA |
| `evaluation_df` | Casos holdout |
| `benchmark_contexts` | Evidencia congelada por pregunta |
| `baseline_rows` | Registros detallados del baseline |
| `baseline_results_df` | Tabla inspeccionable por caso |
| `baseline_test_cases` | Inputs de DeepEval para la sección 1.7 |

**Conclusión:** la sección 1.5 establece las condiciones de una comparación justa. Su valor principal no es generar una tabla, sino controlar qué ejemplos observa GEPA, qué evidencia recibe cada prompt y qué información queda disponible para explicar los resultados de evaluación.

## Revisión 10 — Métricas de retrieval y generación en la sección 1.6

### La sección 1.6 define el criterio de evaluación

La sección 1.6 no ejecuta todavía el benchmark. Su responsabilidad es definir las métricas que las secciones posteriores aplicarán a los `LLMTestCase` preparados en 1.5.

El flujo es:

```text
sección 1.5
→ prepara pregunta, respuesta esperada, respuesta baseline y contexto

sección 1.6
→ define qué dimensiones de calidad serán medidas

secciones 1.7 y 2.3
→ ejecutan las métricas sobre baseline y prompt optimizado
```

`EVALUATION_THRESHOLD = 0.5` es el mínimo que una evaluación individual debe alcanzar para considerarse exitosa. No significa que el 50% de todos los casos deba aprobar; se aplica al score producido por cada métrica para cada caso.

```text
score >= 0.5 → success = True
score <  0.5 → success = False
```

Este umbral es provisional y pedagógico. Un sistema financiero de producción necesitaría calibrarlo con evaluaciones humanas, costos de error y una muestra mayor.

### `GEval` utiliza un LLM como juez

Las métricas de esta sección son objetos `GEval`. Cada una entrega al LLM evaluador:

1. Un criterio escrito en lenguaje natural.
2. Los campos de `LLMTestCase` necesarios para aplicar ese criterio.
3. Un umbral para convertir el score en éxito o fracaso.

Por ejemplo:

```python
evaluation_params=[
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
]
```

indica que el juez puede observar la pregunta, la respuesta generada y la respuesta esperada. No recibe automáticamente todos los campos: cada métrica ve solamente los parámetros declarados.

**Aprendizaje:** `GEval` aporta una evaluación semántica flexible, pero no es completamente determinista. Dos ejecuciones pueden producir scores ligeramente diferentes aunque reciban los mismos inputs. Por eso debe complementarse con verificaciones Python y no interpretarse como una verdad exacta.

### Cada métrica observa una dimensión diferente

| Métrica | Inputs principales | Pregunta que intenta responder | Capa principal |
|---|---|---|---|
| Answer Correctness | pregunta, respuesta generada, respuesta esperada | ¿La respuesta coincide con lo que el benchmark considera correcto? | Generación |
| Faithfulness / Groundedness | respuesta generada, contexto recuperado | ¿Las afirmaciones están respaldadas por la evidencia entregada? | Generación respecto de retrieval |
| Context Relevance | pregunta, contexto recuperado | ¿Los documentos parecen relevantes y suficientes para responder? | Retrieval |
| Answer Relevance | pregunta, respuesta generada | ¿La respuesta contesta directamente y evita información innecesaria? | Generación |
| Broker Actionability | pregunta, respuesta generada, contexto | ¿La respuesta explica señales, riesgos e implicaciones útiles para un broker? | Generación y objetivo de producto |

Una respuesta puede comportarse de forma diferente en cada dimensión:

```text
respuesta coincide con el benchmark
pero incluye un dato ausente del contexto
→ Correctness alta, Faithfulness baja

respuesta se limita correctamente al contexto disponible
pero el retriever no encontró la evidencia esperada
→ Faithfulness alta, Correctness posiblemente baja

respuesta correcta y respaldada
pero extensa y poco directa
→ Correctness y Faithfulness altas, Answer Relevance baja
```

**Aprendizaje:** una sola puntuación no permite diagnosticar un RAG. Separar las dimensiones ayuda a identificar si el problema está en retrieval, grounding, redacción o utilidad para el usuario.

### Cómo funciona `Context Relevance`

`Context Relevance` recibe solamente:

```text
INPUT             → pregunta
RETRIEVAL_CONTEXT → documentos recuperados
```

El LLM juez inspecciona ambos y estima:

- Si los documentos hablan del tema solicitado.
- Si incluyen las entidades, periodos o hechos relevantes.
- Si aparentan contener evidencia suficiente para construir la respuesta.

Ejemplo de contexto relevante y suficiente:

```text
Pregunta:
¿Cuál fue el precio de AAPL el 12 de marzo de 2026?

Contexto:
AAPL cerró en $215 el 12 de marzo de 2026.
```

Ejemplo relevante pero insuficiente:

```text
Pregunta:
¿Cómo cambió el precio de AAPL entre el 12 y el 13 de marzo?

Contexto:
Solo contiene el precio del 12 de marzo.
```

En el segundo caso, el documento está relacionado con la pregunta, pero falta uno de los valores necesarios para calcular o explicar el cambio.

### `Context Relevance` no demuestra por sí sola la calidad del retriever

El LLM juez puede estimar si el contexto parece útil, pero no observa toda la colección Chroma. Por lo tanto, no puede determinar:

- Si existía un documento mejor que no apareció en el `top-k`.
- Si el resultado correcto quedó en la posición `k + 1`.
- Si el ranking fue óptimo.
- Si ticker, fecha, formulario o página coinciden exactamente.
- Si el corpus original contiene la respuesta.

Por eso se conserva también `retrieval_quality()` en la sección 1.5, con comprobaciones como:

```text
source_match
ticker_match
date_match
coverage_status
```

En un benchmark con documentos relevantes etiquetados también podrían calcularse métricas deterministas como:

```text
Hit Rate@k
Recall@k
Precision@k
MRR
nDCG
```

**Aprendizaje:** `Context Relevance` es una señal semántica útil, no un reemplazo de las métricas clásicas de information retrieval ni de los controles de metadata.

### Retrieval y generación deben evaluarse por separado

La primera versión agrupaba las cinco métricas bajo el nombre `baseline_metrics`. Ese nombre era ambiguo porque mezclaba una métrica del retriever con cuatro métricas que pueden cambiar al modificar el prompt.

La versión revisada separa explícitamente:

```python
retrieval_metrics = [
    context_relevance_metric,
]

prompt_evaluation_metrics = [
    correctness_metric,
    faithfulness_metric,
    answer_relevance_metric,
    broker_actionability_metric,
]

rag_evaluation_metrics = (
    retrieval_metrics + prompt_evaluation_metrics
)
```

La lista combinada describe la evaluación completa del RAG, pero no se usa directamente para decidir qué prompt gana.

```text
evaluación completa del RAG
├── retrieval_metrics
│   └── Context Relevance
└── prompt_evaluation_metrics
    ├── Answer Correctness
    ├── Faithfulness / Groundedness
    ├── Answer Relevance
    └── Broker Actionability
```

### El contexto congelado debe evaluarse una sola vez

Baseline y prompt optimizado reciben exactamente el mismo contexto guardado en `benchmark_contexts`. Como `Context Relevance` usa solamente pregunta y contexto, su input no cambia entre los dos prompts.

```text
misma pregunta + mismo contexto congelado
→ una sola evaluación de Context Relevance

respuesta baseline
→ métricas de generación

respuesta optimizada
→ las mismas métricas de generación
```

Evaluar `Context Relevance` dos veces podría producir scores diferentes únicamente por variabilidad del LLM juez. Esa diferencia no representaría una mejora ni una regresión del prompt.

**Decisión de diseño:** la sección 1.7 calcula `Context Relevance` una vez por caso holdout y guarda el resultado en `retrieval_evaluation_df`. Baseline y optimizado se comparan por separado mediante `baseline_evaluation_df` y `optimized_evaluation_df`.

### GEPA solo debe optimizar variables que puede controlar

GEPA modifica el prompt de generación. Puede influir en:

- Cómo el modelo interpreta la evidencia.
- Cuánto se apega al contexto.
- Qué tan directa resulta la respuesta.
- Cómo presenta riesgos e implicaciones.

GEPA no modifica:

- Los embeddings.
- La colección Chroma.
- El routing por dataset.
- Los filtros de metadata.
- El valor de `k`.
- Los documentos ya congelados.

Por eso la configuración utiliza:

```python
prompt_optimization_metrics = (
    prompt_evaluation_metrics.copy()
)
```

y no incluye `Context Relevance`.

**Aprendizaje:** un optimizador debe recibir objetivos que su variable de control pueda afectar. Optimizar un prompt con una métrica exclusiva de retrieval introduce ruido y dificulta interpretar los resultados.

### La comparación ponderada también excluye retrieval

La decisión entre baseline y prompt optimizado usa únicamente métricas de generación:

```python
METRIC_WEIGHTS = {
    "Answer Correctness": 0.40,
    "Faithfulness / Groundedness": 0.30,
    "Answer Relevance": 0.10,
    "Broker Actionability": 0.20,
}
```

Los pesos suman `1.0`. Correctness y Faithfulness reciben mayor importancia porque un error factual o una afirmación no respaldada tiene más costo que una pequeña diferencia de estilo.

`Context Relevance` se reporta junto con los diagnósticos del retriever, pero no aporta puntos a ninguno de los prompts porque ambos recibieron la misma evidencia.

### Organización final del protocolo

```text
1.5  preparar benchmark, holdout y contextos congelados
 ↓
1.6  definir métricas separadas de retrieval y generación
 ↓
1.7  evaluar retrieval una vez y establecer el baseline
 ↓
2.2  optimizar el prompt con métricas controlables por GEPA
 ↓
2.3  evaluar el prompt optimizado con las mismas métricas de generación
 ↓
2.4  comparar prompts sin atribuirles cambios del retriever
```

**Conclusión:** la sección 1.6 establece un contrato de evaluación por capas. `Context Relevance` ayuda a diagnosticar la evidencia recuperada; las otras cuatro métricas permiten comparar el comportamiento del generador. Mantener esas responsabilidades separadas produce un experimento más justo, interpretable y reproducible.
