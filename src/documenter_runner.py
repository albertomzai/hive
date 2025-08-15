# En orquestador.py
import requests # Asegúrate de tener 'requests' importado

def run_documenter_agent(context: dict, repo_local_path: str):
    """
    Se comunica con la API del servicio DeepWiki-Open para generar la documentación.
    """
    log_message("\n--- 📖 Fase de Documentación (Vía API) ---")
    
    # URL de la API de DeepWiki que está corriendo en tu máquina
    DEEPWIKI_API_URL = "http://localhost:8001/api/v1/github" # (La ruta exacta puede variar según su documentación)
    
    project_name = context.get("github_project", "proyecto-colmena")
    github_repo_url = context.get("github_repo")
    
    log_message(f"   - Solicitando a DeepWiki que documente el proyecto: {project_name}")
    
    # El cuerpo de la petición que la API de DeepWiki espera
    payload = {
        "url": github_repo_url,
        # Podríamos necesitar pasarle la configuración del LLM aquí
        # "llm_config": context.get("llm_config")
    }

    try:
        response = requests.post(DEEPWIKI_API_URL, json=payload)
        response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)

        log_message("   - ✅ Solicitud de documentación enviada con éxito.")
        log_message("   - DeepWiki está procesando en segundo plano. La documentación estará disponible en su interfaz.")
        # Aquí no gestionamos los archivos, el propio servicio de DeepWiki lo hace.
        
        return True
        
    except requests.exceptions.RequestException as e:
        log_message(f"❌ ERROR FATAL: No se pudo conectar con la API de DeepWiki en {DEEPWIKI_API_URL}.")
        log_message(f"   - Asegúrate de que el contenedor de DeepWiki esté corriendo con 'docker-compose up'.")
        log_message(f"   - Error: {e}")
        return False