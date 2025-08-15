Guía de Estilo y Buenas Prácticas para Vibe Coding en La Colmena

Esta guía busca unificar las **convenciones de estilo de código** con las **buenas prácticas para el desarrollo asistido por Inteligencia Artificial (IA)**, especialmente bajo la metodología del Vibe Coding. El objetivo es asegurar la **calidad, mantenibilidad y escalabilidad** del software, aprovechando al máximo la **velocidad y eficiencia** que ofrecen los Modelos de Lenguaje Grandes (LLMs).

1\. Principios Generales de Codificación

• **Simplicidad y Eficiencia:** Escribe código **simple, claro y directo**, adhiriéndote a principios como KISS (Keep It Simple, Stupid), YAGNI (You Aren't Gonna Need It) y DRY (Don't Repeat Yourself). El código debe ser conciso pero completo, evitando placeholders y omisiones en la implementación final. Esta metodología permite obtener soluciones funcionales rápidamente con pocos comandos y acelerar el desarrollo y lanzamiento de productos.

• **Modularidad y Responsabilidad Única:** Mantén cada archivo **enfocado en una única responsabilidad**. Separa la lógica en **archivos pequeños** en lugar de crear archivos monolíticos. Esta modularización es crucial para la **mantenibilidad y escalabilidad**, especialmente con código generado por IA. Al organizar el código de esta manera, se facilita la comprensión y modificación, ya que el desarrollador no necesita entender todo el sistema a la vez.

• **Nomenclatura Consistente:** Utiliza las convenciones de nomenclatura establecidas en el proyecto para funciones, variables y constantes:

    ◦ **Funciones:** `snake_case` (ej: `obtener_clima`)    ◦ **Variables:** `snake_case`    ◦ **Constantes:** `UPPER_SNAKE_CASE` (ej: `MAX_INTENTOS`)

• **Refactorización Periódica:** Aunque la IA puede generar código rápidamente, es fundamental **refactorizar periódicamente** para mejorar la legibilidad y eficiencia, asegurando la calidad y escalabilidad a largo plazo. La refactorización incluye mejorar la legibilidad, el rendimiento y las buenas prácticas, y se puede solicitar a la IA que sugiera estas mejoras. El código "casi perfecto" generado por IA requiere una intervención significativa del desarrollador para estar listo para producción, lo que puede generar nueva deuda técnica si no se gestiona correctamente.

2\. Gestión de Secretos y Configuración

• **Protección de Credenciales Sensibles:** Los secretos (como API keys, credenciales de base de datos) deben **leerse SIEMPRE desde un archivo** **.env** utilizando librerías como `dotenv`. **Nunca escribas una clave directamente en el código**. Este archivo `.env` debe configurarse para ser ignorado por Git (usando `.gitignore`) para prevenir su exposición accidental en repositorios públicos.

• **Evitar Exposición de Variables de Entorno:** Presta especial atención a no exponer variables de entorno sensibles en el código generado o en el frontend de la aplicación. Un error común al usar IA es que puede configurar la base de datos o el backend en desarrollo sin índices ni seguridad, exponiendo datos en el frontend.

3\. Requisitos de Documentación

• **Docstrings para Funciones Públicas:** Todas las funciones públicas deben tener un docstring estilo Google explicando qué hacen, incluyendo información de tipos en los parámetros y el valor de retorno. La IA puede ayudar a generar esta documentación.

• **Documentación a Nivel de Proyecto:** Elabora un **plan de proyecto detallado** en un archivo `README.md` o `project.md` que incluya:

    ◦ Una descripción clara del problema que resuelve tu software y su contexto.    ◦ El stack tecnológico a emplear (lenguajes, frameworks, bibliotecas), priorizando stacks populares con buena documentación y comunidad para mejores resultados de la IA.    ◦ Todas las funcionalidades previstas.    ◦ Cualquier información adicional relevante, como el esquema de una base de datos.    ◦ Puedes **utilizar la IA (por ejemplo, modelos razonadores) para ayudarte a definir este plan**. Este documento sirve como la base de conocimiento principal que se le entrega a la IA para el desarrollo.

4\. Manejo de Errores y Pruebas

• **Manejo de Excepciones:** Todas las llamadas a APIs externas o lecturas de archivos deben estar dentro de un bloque `try...except`. Usa **excepciones específicas** (ej: `FileNotFoundError`) en lugar de `except Exception:` genéricas. En caso de error, devuelve un mensaje claro y útil. La IA puede detectar y corregir errores automáticamente. Si algo no funciona, se puede pedir a la IA que lo reescriba desde cero o que depure el código pegándole el mensaje de error. Sin embargo, los problemas más complejos requieren un análisis más profundo.

• **Pruebas Rigurosas:** **Nunca asumas que el código generado por IA es perfecto**. El testing debe ser un **pilar fundamental** en todo el proceso de generación de código.

    ◦ Implementa **pruebas unitarias, de integración, de rendimiento y de extremo a extremo**.    ◦ Crea un test asociado a cada nueva funcionalidad o bloque de código que se genere o modifique.    ◦ Asegúrate de que todos los tests existentes sigan funcionando después de cada cambio.    ◦ Puedes **pedir a la IA que genere pruebas unitarias** para funciones clave.    ◦ La calidad de las predicciones de los agentes de IA depende de la calidad y representatividad de los datos de entrenamiento.

5\. Flujo de Trabajo y Control de Versiones (Git)

• **Desarrollo Iterativo y Modular:** Divide el proyecto en **partes pequeñas y manejables**. Implementa, prueba y realiza `commit` por cada bloque. Un flujo recomendado es: pedir una pequeña funcionalidad con contexto y reglas, revisar la respuesta y el código generado, crear un test, verificar que funcione y que los tests anteriores también pasen, y finalmente, versionar el código con Git.

• **Uso Fundamental de Git:** La implementación de un sistema de **control de versiones como Git y GitHub es esencial**. Permite:

    ◦ Crear "fotografías" de tu código en cada momento, facilitando la **vuelta a versiones anteriores** si la IA comete errores.    ◦ **Gestionar cambios** de forma estructurada (ramas `main`, `develop`, `feature`).    ◦ Facilitar la **colaboración** en equipo.    ◦ Detectar y resolver conflictos de fusión de manera más eficiente.    ◦ Git es increíblemente fácil de aprender y solo requiere conocer unos seis comandos de terminal para estar preparado.