# FC27 Investment Agent

Asistente experimental para revisar cartas manualmente. Informe: [Advisor](data/advisor_report.md).
El recolector se ejecuta cada cuatro horas. Conserva los datos originales y exige
12 observaciones de mercado distintas y al menos 48 horas antes de WATCH_BUY.
Liquidez y segmentos son aproximaciones; cheapest-by-rating es una muestra sesgada,
no un registro de ventas ni de profundidad. El objetivo basado en mediana no es una predicción.
Los outcomes muestran rentabilidad hipotética después del 5% de EA, no operaciones ejecutadas.
Las fechas de régimen son configuración heredada del proyecto. Eventos y rumores requieren
registro con fuente; todavía no hay ingesta automática de noticias ni histórico FC25/26.

El workflow contiene una copia de los módulos para desplegarlos con la sesión web;
al modificar el código, hay que actualizar también esa copia o se restaurará en la siguiente ejecución.
No introducir portfolio personal ni tokens en este repositorio público.
