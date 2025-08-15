# Guía de Estilo Específica para Backend

Esta guía complementa la guía genérica con reglas específicas para la construcción de servicios de backend.

### 1. Gestión de Secretos y Configuración

* **Protección de Credenciales Sensibles:** Los secretos (como API keys, credenciales de base de datos) deben **leerse SIEMPRE desde un archivo `.env`** utilizando librerías como `dotenv`. **Nunca escribas una clave directamente en el código**. El fichero `.env` debe estar incluido en el `.gitignore`.
* **Evitar Exposición de Variables de Entorno:** Presta especial atención a no exponer variables de entorno sensibles en el código generado o en las respuestas de la API.