# Modelo de recomendación

El agente es un asistente de decisión manual para PC; nunca compra ni vende.

1. **Datos y controles.** Cada observación se deduplica por `market-data hash`, se exige cobertura temporal (12 observaciones independientes, 48 h y al menos dos intervalos de 24 h) y coincidencia explícita de plataforma. Los precios extremos válidos se conservan y reducen la confianza.
2. **Señal base.** Mediana y cuantiles robustos por carta, comparación 4 h/24 h/3 d/7 d, descuento confirmado en dos observaciones separadas y beneficio neto tras el impuesto EA del 5% y redondeo por ticks.
3. **Contexto.** Fodder, meta y promos se separan cuando la clasificación está disponible. Eventos oficiales y rumores son capas independientes, siempre con fuente, fecha y confianza; la reacción posterior se mide sin atribuir causalidad automáticamente.
4. **Backtest sin leakage.** Los outcomes +1 d/+3 d/+7 d sólo se calculan con observaciones posteriores al timestamp de la señal. La validación será walk-forward/purged temporal; un modelo supervisado (logística/gradient boosting calibrado) sólo se activará cuando haya suficientes outcomes y supere al baseline fuera de muestra.
5. **Gates de recomendación.** `WATCH_BUY` requiere plataforma PC verificada, cobertura mínima, liquidez suficiente, margen neto positivo y estabilidad histórica fuera de muestra. Si falta histórico FC26/FC25 verificable, el agente permanece en `WAIT`; no se inventan series ni se promete rentabilidad.
