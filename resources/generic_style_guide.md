# Guía de Estilo y Buenas Prácticas Genéricas de La Colmena

Esta guía busca unificar las convenciones de estilo con las buenas prácticas para el desarrollo asistido por IA. El objetivo es asegurar la calidad, mantenibilidad y escalabilidad del software.

### 1. Principios Generales de Codificación

* **Simplicidad y Eficiencia:** Escribe código simple, claro y directo (KISS, YAGNI, DRY). El código debe ser conciso pero completo, evitando placeholders.
* **Modularidad y Responsabilidad Única:** Mantén cada archivo enfocado en una única responsabilidad. Separa la lógica en archivos pequeños.
* **Nomenclatura Consistente:** Usa las convenciones del proyecto:
    * **Funciones y Variables:** `snake_case` (ej: `obtener_datos`)
    * **Constantes:** `UPPER_SNAKE_CASE` (ej: `MAX_INTENTOS`)
* **Refactorización Periódica:** El código generado por IA debe ser refactorizado periódicamente para mejorar su legibilidad y eficiencia.

### 2. Requisitos de Documentación

* **Docstrings para Funciones Públicas:** Todas las funciones públicas deben tener un docstring explicando qué hacen, sus parámetros y el valor que retornan.

### 3. Manejo de Errores y Pruebas

* **Manejo de Excepciones:** Todas las llamadas a APIs externas o lecturas de archivos deben estar dentro de un bloque `try...except` con excepciones específicas (ej: `FileNotFoundError`).
* **Pruebas Rigurosas:** El testing es un pilar fundamental. Se deben implementar pruebas unitarias y de integración para cada nueva funcionalidad. Nunca asumas que el código generado por IA es perfecto.

### 4. Flujo de Trabajo y Control de Versiones (Git)

* **Desarrollo Iterativo y Modular:** Divide el proyecto en partes pequeñas y manejables. Implementa, prueba y haz `commit` por cada bloque funcional.
* **Uso Fundamental de Git:** El uso de Git y GitHub es esencial para crear un historial del código, gestionar cambios y facilitar la colaboración.