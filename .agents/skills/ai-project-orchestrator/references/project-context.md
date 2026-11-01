# Contexto y referencias

Pregunta por la ruta Obsidian cuando sea mencionada y no esté configurada. Descubre `context/`, lee sus manifiestos y ejecuta scripts solo si son seguros. Usa un grafo con relaciones `root`, `derived`, `reference`, `sibling` y `academic_variant`.

El contexto se carga progresivamente. Excluye secretos, `.env`, `.git`, dependencias, binarios y datos sensibles. Registra en el manifiesto qué archivos se incluyeron, su hash y la fase que los necesitó.
