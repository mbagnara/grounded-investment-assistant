# Project Submission Corrections Tracker

Este registro controla las correcciones necesarias para fortalecer el cumplimiento de la rúbrica **Project Submission Guidelines: Full Code** del notebook `UTAIGA_Project_2_Full_Code_Notebook_v3.ipynb`.

## Estado general

- **Correcciones activas:** 7
- **Implementadas:** 7 de 7
- **Verificadas y completadas:** 0 de 7
- **Punto actual:** todas las correcciones implementadas — validación final pendiente
- **Última actualización:** 2026-07-19

El punto 1, exportar el notebook a HTML, queda fuera del avance activo porque se realizará después de completar todas las demás correcciones.

## Registro de correcciones

| Punto | Recomendación | Estado | Criterio de finalización |
|---:|---|---|---|
| 1 | Convertir el notebook final a HTML | **DEFERRED — FINAL STEP** | Exportar la versión definitiva con código, markdown y outputs visibles; revisar el HTML antes de enviarlo. |
| 2 | Evitar respuestas oficiales truncadas | **IMPLEMENTED — FINAL VALIDATION PENDING** | Los 20 resultados oficiales deben tener `finish_reason` distinto de `length`/`max_tokens`, contener respuestas completas y terminar sin errores. |
| 3 | Agregar observaciones explícitas para cada test case | **IMPLEMENTED — FINAL VALIDATION PENDING** | Incluir una interpretación específica para cada uno de los cinco casos oficiales. |
| 4 | Completar observaciones de Data Preparation y corregir nombres de archivos | **IMPLEMENTED — FINAL VALIDATION PENDING** | Documentar decisiones de carga, chunking, metadata, Chroma e IDs; alinear la descripción con los archivos reales. |
| 5 | Interpretar narrativamente las métricas de evaluación | **IMPLEMENTED — FINAL VALIDATION PENDING** | Explicar fortalezas, debilidades y patrones del retriever y del generador. |
| 6 | Agregar comparación narrativa de las tres configuraciones | **IMPLEMENTED — FINAL VALIDATION PENDING** | Explicar trade-offs, resultados y justificación de la configuración seleccionada. |
| 7 | Corregir la decisión cuando GEPA no modifica el prompt | **IMPLEMENTED — FINAL VALIDATION PENDING** | No etiquetar como optimizado un prompt idéntico; conservar baseline o demostrar una modificación material. |
| 8 | Explicitar la limitación de usar el mismo modelo para generación y evaluación | **IMPLEMENTED — FINAL VALIDATION PENDING** | Documentar riesgo de sesgo correlacionado y mitigación mediante revisión humana o juez independiente. |

## Punto 2 — historial de implementación

### 2026-07-19 — Código actualizado

- Se aumentó `max_tokens` a 650 para `Config_1_Precision_Focused` y `Config_2_Balanced`, las dos configuraciones que produjeron respuestas truncadas en el caso oficial 5.
- Se agregó `finish_reason` a los resultados del baseline y de cada configuración.
- Se propagó `finish_reason` a la matriz oficial de respuestas y a los artefactos CSV.
- Se agregó una validación fail-fast que rechaza cualquier ejecución oficial terminada por `length` o `max_tokens`.
- La validación también rechaza respuestas exitosas sin `finish_reason`, porque su finalización no podría comprobarse.
- Se agregó `finish_reason` a la tabla visible de las cinco respuestas del pipeline seleccionado.
- Se limpiaron los outputs obsoletos desde la sección 3.1 para evitar presentar resultados calculados con las configuraciones anteriores.
- La validación estructural y sintáctica del notebook pasó sin errores; la verificación de respuestas requiere una nueva ejecución.

### Verificación pendiente

La ejecución se realizará una sola vez después de implementar todas las correcciones activas. El punto 2 permanece pendiente de validación hasta esa ejecución final.

1. Reiniciar el kernel y ejecutar el notebook completo.
2. Confirmar que se generan 20 respuestas oficiales sin errores.
3. Confirmar que ninguna fila tiene `finish_reason` igual a `length` o `max_tokens`.
4. Revisar visualmente que las cinco respuestas del pipeline seleccionado tengan una conclusión completa.
5. Confirmar que las métricas y conclusiones narrativas sigan coincidiendo con los nuevos resultados.
6. Solo después de estas comprobaciones, cambiar el estado del punto 2 a **COMPLETED**.

## Estrategia de validación final

Para evitar múltiples ejecuciones costosas, las correcciones se implementarán y validarán primero de manera estructural y sintáctica. Cuando las siete correcciones activas estén implementadas:

1. se revisará nuevamente la cobertura completa de la rúbrica;
2. se reiniciará el kernel y se ejecutará el notebook completo una sola vez;
3. se verificarán outputs, errores, métricas, respuestas completas y consistencia narrativa;
4. se actualizará el estado de cada punto desde **FINAL VALIDATION PENDING** a **COMPLETED**;
5. finalmente, se exportará y revisará el HTML requerido para la entrega.

## Punto 3 — historial de implementación

### 2026-07-19 — Observaciones por caso agregadas

- Se agregó el encabezado `Observations for the Five Official Test Cases` dentro de la sección 4.3.
- Se agregó una observación empresarial específica para cada uno de los cinco casos oficiales.
- La tabla toma dinámicamente `coverage_status`, `finish_reason`, fuentes y entidades faltantes desde `final_results_df`.
- Se agregó un estado de validación que distingue errores, truncamiento, evidencia parcial y respuestas soportadas.
- Las observaciones mantienen revisión profesional incluso cuando la evidencia aparece como soportada.
- La implementación no agrega llamadas al modelo y se actualizará automáticamente durante la ejecución final.

### Verificación pendiente

Durante la ejecución final se debe confirmar que:

1. la tabla contiene exactamente cinco filas;
2. cada observación corresponde al caso y a la cobertura recuperada;
3. no existen respuestas truncadas o con error;
4. los gaps reportados coinciden con las fuentes y entidades realmente faltantes;
5. las observaciones siguen siendo consistentes con el contenido final de cada respuesta.

## Punto 4 — historial de implementación

### 2026-07-19 — Descripción y observaciones de preparación actualizadas

- Se corrigieron los archivos descritos en el notebook: `stock_price_details.csv` y `sec_filings_10q.pdf` reemplazan referencias que no correspondían a los inputs reales.
- El encabezado original 1.1 con `CSVLoader` se conservó para mantener alineación literal con la rúbrica. Debajo se agregó una nota breve que aclara que la implementación usa pandas para validar el esquema y controlar explícitamente la separación entre `page_content` y metadata al crear objetos LangChain `Document`.
- Se agregó la sección `Data Preparation Observations` inmediatamente después de construir y verificar la colección Chroma.
- La nueva explicación documenta la unidad de indexación de cada fuente, la preservación de página del PDF y la relación entre `page_content`, metadata y embeddings.
- Se justificaron `chunk_size=1000` y `chunk_overlap=200` como un balance entre foco semántico y continuidad en texto financiero.
- Se explicó por qué las tres fuentes comparten una colección Chroma y cómo `dataset` permite mantener routing y filtros por fuente.
- Se documentó el valor de los IDs deterministas, el reinicio de la colección y la conservación inmutable de los archivos raw.
- No se modificó la lógica de ingestión ni ningún archivo de datos.

### Verificación pendiente

Durante la ejecución y revisión final se debe confirmar que:

1. los tres archivos descritos coinciden con los archivos realmente cargados;
2. los conteos indexados por dataset coinciden con los documentos preparados;
3. los chunks SEC conservan `page`, `chunk_id`, `source_file` y `dataset`;
4. la colección se reconstruye sin duplicados ni registros obsoletos;
5. las observaciones permanecen consistentes con los parámetros y outputs definitivos.

## Punto 5 — historial de implementación

### 2026-07-19 — Interpretación narrativa y dinámica de métricas agregada

- Se agregó `Baseline Metric Interpretation` después de la evaluación baseline de la sección 1.7.
- Se documentó qué mide cada métrica, qué componente evalúa y qué acción técnica corresponde cuando su resultado es bajo.
- Se agregó una función reutilizable que convierte cualquier resumen de métricas en una tabla con score, fortaleza descriptiva, significado y foco recomendado.
- Las bandas `Strong`, `Moderate` y `Needs attention` son ayudas descriptivas y no reemplazan los umbrales de aprobación de DeepEval.
- La interpretación baseline reúne `Context Relevance` con las métricas del generador para hacer visible si el principal límite se encuentra en retrieval o generación.
- Cuando `Context Relevance` es la métrica más débil, el notebook explica que prompt tuning no puede compensar evidencia que el retriever no recuperó.
- Se agregó `Official Test Metric Interpretation` para el pipeline finalmente seleccionado.
- La lectura oficial usa solo métricas aplicables sin respuesta esperada y evita atribuir `Answer Correctness` a los cinco casos oficiales.
- Las observaciones se calculan desde los DataFrames producidos por la ejecución, por lo que se actualizarán con los resultados finales sin nuevas llamadas al LLM.

### Verificación pendiente

Durante la ejecución final se debe confirmar que:

1. la tabla baseline incluye exactamente una fila por cada una de las cinco métricas;
2. la tabla oficial incluye las cuatro métricas aplicables y no incluye `Answer Correctness`;
3. los scores coinciden con los resúmenes de DeepEval mostrados inmediatamente antes;
4. la métrica más fuerte y el área de atención impresas corresponden a los nuevos resultados;
5. cualquier comentario sobre `Context Relevance` aparece solo cuando esa métrica es efectivamente la más baja;
6. las interpretaciones finales son consistentes con los outputs generados después de la ejecución completa.

## Punto 6 — historial de implementación

### 2026-07-19 — Comparación narrativa de configuraciones agregada

- Se agregó `RAG Configuration Comparison Observations` después de seleccionar la mejor configuración y antes de guardar los artefactos.
- Se aclaró que las tres alternativas representan hipótesis completas de operación y no un experimento causal de una sola variable, porque cambian simultáneamente chunking, retrieval y generación.
- Se agregó una función reutilizable que traduce el scorecard a una comparación orientada a decisiones.
- La comparación muestra ranking ponderado, elegibilidad frente a quality gates, estado de selección y perfil de retrieval de cada alternativa.
- Para cada configuración se identifican dinámicamente su métrica más fuerte y su principal área de atención.
- La tabla conserva la rationale definida para cada alternativa y agrega cobertura de fuentes, cobertura soportada y cantidad promedio de documentos recuperados.
- La narrativa explica por qué fue seleccionada la configuración ganadora y muestra una advertencia explícita si ninguna alternativa supera todos los quality gates.
- La implementación reutiliza resultados existentes y no agrega ejecuciones de retrieval, embeddings o LLM.

### Verificación pendiente

Durante la ejecución final se debe confirmar que:

1. aparecen exactamente las tres configuraciones definidas en 3.1;
2. ranking, weighted score y quality-gate status coinciden con el scorecard original;
3. solo una configuración aparece como `Selected`;
4. la configuración seleccionada coincide con `best_rag_config_name` y el pipeline usado en la sección 4;
5. las métricas fuerte y débil de cada alternativa coinciden con sus scores finales;
6. la advertencia de selección aparece únicamente cuando `rag_selection_decision` es `SELECTED_WITH_WARNINGS`;
7. la explicación permanece consistente con los resultados de la ejecución completa.

## Punto 7 — historial de implementación

### 2026-07-19 — Gate de modificación material y decisión `KEEP_SEED` agregados

- Se agregó `prompt_materially_modified` al conjunto formal de quality gates de la sección 2.4.
- Un prompt GEPA solo puede recibir `APPROVE` cuando difiere materialmente del seed y supera todos los demás controles de calidad.
- Se reemplazó la decisión ambigua `REJECT` por `KEEP_SEED` cuando el candidato es equivalente o falla algún gate.
- La decisión se separó en una celda pequeña para distinguir el cálculo de métricas de la política de aprobación.
- Se agregó `prompt_decision_reason` para explicar si GEPA no produjo un cambio o cuáles quality gates fallaron.
- La tabla visible de gates convierte cada resultado a booleano explícito y ahora incluye la verificación de modificación material.
- El contrato downstream permanece estable: las secciones 3 y 4 utilizan el candidato únicamente con `APPROVE`; en cualquier otro caso conservan el seed.
- Se limpió el output obsoleto de la celda de decisión para evitar mostrar una aprobación calculada con la política anterior.

### Verificación pendiente

Durante la ejecución final se debe confirmar que:

1. `prompt_was_modified=False` produce `prompt_decision=KEEP_SEED`;
2. un prompt modificado que falla cualquier quality gate también produce `KEEP_SEED`;
3. `APPROVE` aparece solo si el prompt cambió y todos los gates son verdaderos;
4. `prompt_decision_reason` coincide con la condición observada;
5. `selected_prompt_name` es `seed` cuando la decisión es `KEEP_SEED`;
6. las secciones 3 y 4 usan efectivamente el prompt indicado por `selected_prompt_name`;
7. los artefactos guardados no etiquetan como optimizado un prompt equivalente al seed.

## Punto 8 — historial de implementación

### 2026-07-19 — Limitación de independencia de evaluación documentada

- Se agregó la sección `Evaluation Independence Limitation` junto a la interpretación de métricas y antes de la optimización de prompts.
- Se documentó que `gpt-4.1-mini` participa tanto como generador de respuestas como juez G-Eval de DeepEval.
- Se explicó que usar la misma familia de modelo puede producir sesgo correlacionado, preferencias de estilo compartidas y blind spots similares.
- Los scores actuales se presentan como evidencia comparativa válida para el proof of concept, pero no como garantía independiente de calidad productiva.
- Se recomendaron como mitigaciones un juez distinto, revisión humana ciega por expertos financieros, controles deterministas, múltiples evaluadores para decisiones de alto impacto y conservación de trazas.
- Se agregó una regla explícita de interpretación: antes de un uso broker-facing se requiere validación independiente humana y de modelo.
- El cambio es exclusivamente documental y no agrega llamadas, costos ni dependencias de ejecución.

### Verificación pendiente

Durante la revisión final se debe confirmar que:

1. la sección aparece visible junto a la evaluación y antes de GEPA;
2. el nombre del modelo documentado coincide con `EVALUATOR_MODEL_NAME` y el modelo generador vigente;
3. las conclusiones y recomendaciones no presentan los scores como garantía independiente;
4. el notebook conserva los controles deterministas de cobertura, errores y truncamiento mencionados;
5. la exportación HTML mantiene visible esta limitación y sus mitigaciones.

## Estado antes de la validación final

Las siete correcciones activas están implementadas y permanecen en estado **FINAL VALIDATION PENDING**. No se marcarán como completadas hasta reiniciar el kernel, ejecutar el notebook completo y contrastar todos los outputs con los criterios registrados. Después de esa validación se realizará la exportación HTML diferida.
