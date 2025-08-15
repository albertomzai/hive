# orquestador.py (V11 - Workflows por Etapas)
import docker
import os
import time
import json
import shutil
import argparse
import subprocess
import re
import errno
import stat
import sys
import ast
from github import Github, GithubException

# --- CONFIGURACIÓN ---
AGENT_IMAGE = "agente-constructor"
WORKSPACE_DIR_NAME = "workspace"
TASKS_DIR = "tasks"
PROCESSED_TASKS_DIR = os.path.join(TASKS_DIR, "processed")
FAILED_TASKS_DIR = os.path.join(TASKS_DIR, "failed")
PLANS_DIR = "plans"

AGENT_INFO = {
    "investigador": {"prompt": "prompts/investigador.txt", "output_file": "api_data.json"},
    "arquitecto":   {"prompt": "prompts/arquitecto.txt", "output_file": "plan_construccion.json"},
    "analista":     {"prompt": "prompts/analista.txt"},
    "backend":      {"prompt": "prompts/backend.txt", "output_file": "backend.py"},
    "frontend":     {"prompt": "prompts/frontend.txt", "output_file": "static/index.html"},
    "qa":           {"prompt": "prompts/qa.txt"},
    "e2e":       {"prompt": "prompts/e2e_tester.txt"}, # <-- Nuevo Agente!
    "jefe_de_proyecto": {"prompt": "prompts/jefe_de_proyecto.txt"},
    "documentador": {"prompt": "prompts/documentador.txt"}
}

# --- HELPERS ---
def handle_remove_readonly(func, path, exc):
    excvalue = exc[1]; os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO); func(path)

def log_message(message, level="INFO"):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level.upper()}] {message}")

def run_git_command(command, cwd):
    try:
        subprocess.run(command, check=True, cwd=cwd, capture_output=True, text=True, encoding='utf-8')
    except subprocess.CalledProcessError as e:
        if "nothing to commit" in e.stdout or "no changes added to commit" in e.stdout: log_message("No hay nuevos cambios que guardar.", "GIT")
        else: log_message(f"Error ejecutando Git: {e.stderr}", "ERROR"); raise

def get_llm_response_directo(prompt: str, config: dict) -> str:
    # Cuando el orquestador llama directamente, necesita localhost
    api_base = config.get("api_base", "").replace("host.docker.internal", "localhost")
    from openai import OpenAI
    client = OpenAI(base_url=api_base, api_key=config.get("api_key"))
    response = client.chat.completions.create(model=config.get("model_name"), messages=[{"role": "user", "content": prompt}], temperature=0.5)
    return response.choices[0].message.content

def leer_codigo_proyecto(path: str) -> str:
    contenido_completo = ""
    directorios_a_ignorar = {'.git', '__pycache__', 'docs', '.venv', 'node_modules'}
    extensiones_relevantes = ('.py', '.js', '.html', '.css', '.json', '.md', 'requirements.txt', 'Dockerfile')
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in directorios_a_ignorar]
        for file in files:
            if file.endswith(extensiones_relevantes):
                try:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, path)
                    contenido_completo += f"\n\n{'='*20}\n--- FICHERO: {rel_path} ---\n{'='*20}\n\n"
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        contenido_completo += f.read()
                except Exception: pass
    return contenido_completo

def limpiar_workspace(repo_local_path: str):
    """
    Borra todo el contenido de un directorio excepto la carpeta .git.
    """
    log_message(f"Limpiando el directorio de trabajo: {repo_local_path}", "SYSTEM")
    if not os.path.isdir(repo_local_path):
        log_message("El directorio a limpiar no existe.", "WARNING")
        return
        
    for item in os.listdir(repo_local_path):
        if item == '.git':
            continue
        item_path = os.path.join(repo_local_path, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, onerror=handle_remove_readonly)
            else:
                os.remove(item_path)
        except Exception as e:
            log_message(f"No se pudo borrar {item_path}: {e}", "WARNING")
    log_message("Directorio local limpiado. Listo para una construcción desde cero.", "SUCCESS")

def preparar_repositorio(config: dict, repo_local_path: str):
    """
    Asegura que el repo exista en GitHub, lo clona y, si es modo 'nuevo',
    limpia el directorio local para un inicio desde cero.
    """
    github_pat = config.get("github_pat")
    repo_name = config.get("github_project")
    org_name = config.get("github_org") # Opcional, para repos en organizaciones
    repo_url_auth = config["github_repo"].replace("https://", f"https://{github_pat}@")

    if not github_pat or not repo_name:
        log_message("Se requiere 'github_pat' y 'github_project' en la config para gestionar el repo.", "FATAL")
        raise ValueError("Configuración de GitHub incompleta.")

    log_message(f"Conectando a GitHub para preparar el repositorio '{repo_name}'...", "GIT")
    g = Github(github_pat)
    user = g.get_user()
    try:
        user.create_repo(repo_name, private=True)
        log_message(f"Repositorio '{repo_name}' creado con éxito.", "SUCCESS")
    except GithubException as e:
        if e.status == 422:
            log_message(f"El repositorio '{repo_name}' ya existe.", "INFO")
        else:
            log_message(f"Error al crear/verificar repo: {e}.", "WARNING")

    # CLONAR O ACTUALIZAR
    if not os.path.exists(repo_local_path):
        log_message(f"Clonando repositorio...", "GIT")
        run_git_command(["git", "clone", repo_url_auth, repo_local_path], os.getcwd())
    else:
        log_message("El repositorio ya estaba clonado, actualizando...", "GIT")
        run_git_command(["git", "pull"], repo_local_path)
    return True

def inyectar_guias_de_estilo(rol_agente: str, contexto: dict):
    """
    Lee las guías de estilo relevantes del directorio /resources y
    las añade al contexto de un agente según su rol.
    """
    guias = {}
    
    # La guía genérica se carga para casi todos los agentes clave.
    if rol_agente in ["arquitecto", "jefe_de_proyecto", "backend", "frontend"]:
        try:
            with open("resources/generic_style_guide.md", 'r', encoding='utf-8') as f:
                guias["GUIA_ESTILO_GENERICA"] = f.read()
        except FileNotFoundError:
            log_message("Advertencia: No se encontró 'resources/generic_style_guide.md'.", "WARNING")

    # Las guías específicas se cargan solo para el rol correspondiente.
    if rol_agente == "backend":
        try:
            with open("resources/backend_style_guide.md", 'r', encoding='utf-8') as f:
                guias["GUIA_ESTILO_BACKEND"] = f.read()
        except FileNotFoundError: pass # No es un error si no existe

    if rol_agente == "frontend":
        try:
            with open("resources/frontend_style_guide.md", 'r', encoding='utf-8') as f:
                guias["GUIA_ESTILO_FRONTEND"] = f.read()
        except FileNotFoundError: pass

    if guias:
        log_message(f"Inyectando guías de estilo en el contexto de [{rol_agente.upper()}]: {list(guias.keys())}", "INFO")
        contexto.update(guias)

# --- LÓGICA DE AGENTES ---
def ejecutar_etapa_e2e_dev(client, etapa_info, repo_local_path, contexto_global):
    """
    Orquesta el agente E2E de forma híbrida: crea la configuración,
    llama al LLM para obtener el código del test y lo guarda directamente.
    """
    log_message(f"--- 👷 Fase de Construcción para: [E2E] ---", "STAGE")
    try:
        # --- ¡NUEVO PASO! Limpiar el directorio de tests antiguos ---
        test_dir = os.path.join(repo_local_path, "cypress", "e2e")
        if os.path.exists(test_dir):
            log_message(f"   - Limpiando directorio de tests E2E existente: {test_dir}", "SETUP")
            shutil.rmtree(test_dir)
        os.makedirs(test_dir, exist_ok=True)
        # --- FIN DEL NUEVO PASO ---

        # --- PASO 1: El Orquestador crea los ficheros de configuración ---
        log_message("   - Creando ficheros de configuración para Cypress...", "SETUP")
        package_json_content = {
            "name": os.path.basename(repo_local_path),
            "version": "1.0.0",
            "scripts": { "cypress:run": "cypress run" },
            "devDependencies": { "cypress": "^13.0.0" }
        }
        with open(os.path.join(repo_local_path, "package.json"), "w") as f:
            json.dump(package_json_content, f, indent=2)

        cypress_config_content = """
const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5000',
    setupNodeEvents(on, config) {},
  },
});
"""
        with open(os.path.join(repo_local_path, "cypress.config.js"), "w") as f:
            f.write(cypress_config_content)

        # --- PASO 2: El Agente genera el código del test ---
        tareas = etapa_info.get("tareas", [])
        contexto_e2e = {
            **contexto_global,
            "tarea_especifica": "Generar un test de Cypress. Tareas:\n- " + "\n- ".join(tareas)
        }
        prompt_path = AGENT_INFO['e2e']['prompt']
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        prompt_final = f"{prompt_template}\n\nCONTEXTO:\n{json.dumps(contexto_e2e, indent=2)}"
        
        log_message("   - [E2E-Tester] Solicitando generación del código del test al LLM...", "INFO")
        test_code = get_llm_response_directo(prompt_final, contexto_global.get("llm_config"))
        test_code = re.sub(r'^```(?:javascript)?\n|\n```$', '', test_code).strip()

        # Guardar el fichero de test
        test_dir = os.path.join(repo_local_path, "cypress", "e2e")
        os.makedirs(test_dir, exist_ok=True)
        output_path = os.path.join(test_dir, "test_spec.cy.js")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(test_code)
        log_message(f"   ✅ Fichero de test E2E guardado en: {output_path}")

        # Sincronizar con GitHub
        run_git_command(["git", "add", "."], repo_local_path)
        run_git_command(["git", "commit", "-m", "Agente [E2E-Tester]: Genera ficheros de prueba"], repo_local_path)
        run_git_command(["git", "push"], repo_local_path)
        run_git_command(["git", "pull"], repo_local_path)
        return True
    except Exception as e:
        log_message(f"   - ❌ Fallo crítico en la etapa E2E-DEV: {e}", "FATAL")
        return False
    
def ejecutar_etapa_e2e_qa(repo_local_path, contexto_global):
    log_message("--- 🧪 Iniciando Etapa de Pruebas End-to-End (E2E) ---", "SYSTEM")
    server_process = None
    try:
        # --- PASO 1: El Orquestador crea los ficheros de configuración ---
        log_message("   - Creando ficheros de configuración para Cypress...", "SETUP")
        
        # Plantilla para package.json
        package_json_content = {
            "name": os.path.basename(repo_local_path),
            "version": "1.0.0",
            "scripts": { "cypress:run": "cypress run" },
            "devDependencies": { "cypress": "^13.0.0" }
        }
        with open(os.path.join(repo_local_path, "package.json"), "w") as f:
            json.dump(package_json_content, f, indent=2)

        # --- ¡CONFIGURACIÓN CORREGIDA! ---
        # Plantilla para cypress.config.js que deshabilita el fichero de soporte.
        cypress_config_content = """
const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5000',
    supportFile: false, // <-- LÍNEA CLAVE AÑADIDA
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
"""
        with open(os.path.join(repo_local_path, "cypress.config.js"), "w") as f:
            f.write(cypress_config_content)
        
        # --- PASO 2: Instalar dependencias de Cypress ---
        log_message("   - Instalando dependencias de Node.js con 'npm install'...", "QA")
        subprocess.run(["npm", "install"], cwd=repo_local_path, check=True, shell=(os.name == 'nt'))
        
        # --- PASO 3: Levantar el servidor Flask ---
        log_message("   - Levantando el servidor Flask en segundo plano...", "INFO")
        server_process = subprocess.Popen([sys.executable, "app.py"], cwd=repo_local_path)
        time.sleep(5)

        # --- PASO 4: Ejecutar las pruebas de Cypress ---
        log_message("   - Ejecutando Cypress...", "QA")
        subprocess.run(["npx", "cypress", "run"], cwd=repo_local_path, check=True, shell=(os.name == 'nt'))

        log_message("   - ✅ Pruebas E2E han pasado.", "SUCCESS")
        return True
        
    except Exception as e:
        log_message(f"   - ❌ Las pruebas E2E han fallado: {e}", "FAIL")
        return False
    finally:
        if server_process:
            log_message("   - Deteniendo el servidor Flask.", "INFO")
            server_process.terminate()

def ejecutar_etapa_e2e_qa_old(repo_local_path, contexto_global):
    log_message("--- 🧪 Iniciando Etapa de Pruebas End-to-End (E2E) ---", "SYSTEM")
    server_process = None
    try:
        # 1. Levantar el servidor en segundo plano
        log_message("   - Levantando el servidor Flask en segundo plano...", "INFO")
        server_process = subprocess.Popen([sys.executable, "app.py"], cwd=repo_local_path)
        time.sleep(5) # Dar tiempo al servidor para que arranque

        # 2. Instalar dependencias de Cypress y ejecutar las pruebas
        log_message("   - Instalando dependencias y ejecutando Cypress...", "QA")
        # Idealmente, esto se haría con un package.json, pero para empezar:
        subprocess.run(["npx", "cypress", "run"], cwd=repo_local_path, check=True)

        log_message("   - ✅ Pruebas E2E han pasado.", "SUCCESS")
        return True
    except Exception as e:
        log_message(f"   - ❌ Las pruebas E2E han fallado: {e}", "FAIL")
        # Aquí llamaríamos al Jefe de Proyecto con el log de Cypress
        return False
    finally:
        # 5. Asegurarse de que el servidor se detiene siempre
        if server_process:
            log_message("   - Deteniendo el servidor Flask.", "INFO")
            server_process.terminate()

def run_agent_mission(client, role: str, context: dict):
    """
    Lanza un agente constructor en un contenedor Docker con un prompt robusto
    que fuerza un formato de salida JSON multi-archivo y multi-acción.
    """
    log_message(f"🚀 Despachando Agente: {role.upper()}...")
    
    prompt_path = AGENT_INFO[role]["prompt"]
    with open(prompt_path, 'r', encoding='utf-8') as f: system_prompt = f.read()
    
    mission_prompt = f"{system_prompt}\n\nCONTEXTO:\n{json.dumps(context, indent=2)}"
    
    # --- ¡NUEVO PROMPT MULTI-ACCIÓN! ---
    # Este prompt le enseña al agente a crear, actualizar y eliminar ficheros.
    json_format_instruction = f"""
Tu respuesta DEBE ser un único objeto JSON válido que describa una lista de operaciones de fichero.
La estructura del JSON debe ser la siguiente:
{{
  "files": [
    {{
      "filename": "ruta/al/fichero_a_crear.py",
      "action": "create_or_update",
      "code": "..."
    }},
    {{
      "filename": "fichero_a_eliminar.py",
      "action": "delete"
    }}
  ]
}}

Donde "..." es el contenido completo del fichero que has generado.
Para cada fichero, especifica la 'action': 'create_or_update' para crear o modificar, y 'delete' para eliminar.
Si solo necesitas modificar un fichero, la lista 'files' contendrá un solo elemento.
No incluyas ninguna otra explicación o texto fuera de este objeto JSON.
"""
    mission_prompt += json_format_instruction
    # --- FIN DEL NUEVO PROMPT ---

    environment = {
        "LLM_CONFIG": json.dumps(context.get("llm_config", {})),
        "TASK_PROMPT": mission_prompt,
        "GIT_REPO_URL": context.get("github_repo"),
        "GITHUB_PAT": context.get("github_pat"),
    }
    
    container = None
    try:
        container = client.containers.run(
            AGENT_IMAGE, 
            environment=environment, 
            detach=True
        )
        
        result = container.wait()
        log_output = container.logs().decode('utf-8')

        os.makedirs("logs", exist_ok=True)
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        log_filename = f"{timestamp}-{role}.log"
        
        if result['StatusCode'] != 0:
            log_filename = log_filename.replace(".log", "-ERROR.log")
            log_message(f"El agente '{role}' ha fallado. Guardando su log en 'logs/{log_filename}'", "ERROR")

        with open(os.path.join("logs", log_filename), "w", encoding="utf-8") as f:
            f.write(log_output)

        if result['StatusCode'] != 0:   
            raise Exception(f"El contenedor finalizó con error {result['StatusCode']}. Revisa el log: logs/{log_filename}")

        log_message(f"✅ Misión del Agente {role.upper()} finalizada.", "SUCCESS")
        return True
        
    except Exception as e:
        log_message(f"ERROR FATAL al ejecutar el agente '{role}': {e}", "FATAL")
        return False
    finally:
        if container:
            try: container.remove()
            except docker.errors.NotFound: pass

def run_jefe_de_proyecto_agent(contexto_global: dict, requisito: str, codigo_fallido: str, razon_fallo: str, plan_path: str, doc_content: str = ""):
    log_message("Despachando Agente [JEFE DE PROYECTO] para crear tarea de corrección...", "AGENT")
    try:
        prompt_path = AGENT_INFO['jefe_de_proyecto']['prompt']
        with open(prompt_path, 'r', encoding='utf-8') as f: prompt_template = f.read()
        
        prompt_final = prompt_template.replace("{REQUISITO}", requisito)
        prompt_final = prompt_final.replace("{CODIGO_FALLIDO}", codigo_fallido)
        prompt_final = prompt_final.replace("{RAZON_FALLO}", razon_fallo)
        prompt_final = prompt_final.replace("{DOCUMENTACION_EXISTENTE}", doc_content)

        respuesta_str = get_llm_response_directo(prompt_final, contexto_global.get("llm_config"))
        log_message(f"Respuesta cruda del Jefe de Proyecto: {respuesta_str}", "DEBUG")

        json_extraido = re.search(r'\{.*\}', respuesta_str, re.DOTALL).group(0)
        respuesta_json = None
        try:
            respuesta_json = json.loads(json_extraido)
        except json.JSONDecodeError:
            respuesta_json = ast.literal_eval(json_extraido)

        nuevo_objetivo = respuesta_json.get("nuevo_objetivo")
        if not nuevo_objetivo: raise ValueError("El Jefe de Proyecto no devolvió un 'nuevo_objetivo' válido.")

        nueva_tarea_config = contexto_global.copy()
        etapa_fallida = contexto_global.get('etapa_actual')
        nueva_tarea_config["objetivo"] = nuevo_objetivo
        nueva_tarea_config["etapas_a_ejecutar"] = [f"{etapa_fallida}-dev", f"{etapa_fallida}-qa"]
        nueva_tarea_config["plan_de_origen"] = os.path.basename(plan_path)
        
        nueva_tarea_config.pop("modo_proyecto", None)
        nueva_tarea_config.pop("fase_ejecucion", None)

        timestamp = time.strftime('%Y%m%d-%H%M%S')
        nuevo_fichero_tarea = os.path.join(TASKS_DIR, f"T{timestamp}-FIX-{etapa_fallida}.json")
        
        with open(nuevo_fichero_tarea, 'w', encoding='utf-8') as f:
            json.dump(nueva_tarea_config, f, indent=2, ensure_ascii=False)
            
        log_message(f"Nueva tarea de corrección generada en: {nuevo_fichero_tarea}", "SUCCESS")
        log_message(f"Objetivo de la nueva tarea: '{nuevo_objetivo}'", "INFO")
        return True

    except Exception as e:
        log_message(f"El agente Jefe de Proyecto falló de forma irrecuperable: {e}", "FATAL")
        return False
    


def ejecutar_etapa_documentacion_docker(client, contexto_global: dict, repo_path: str, componente: str = "full"):
    """
    Prepara el contexto y lanza el agente documentador estándar para generar la documentación.
    """
    log_message(f"--- 📖 Iniciando Etapa de Documentación para: [{componente.upper()}] ---", "SYSTEM")
    try:
        ruta_codigo = os.path.join(repo_path, componente) if componente != "full" else repo_path
        if not os.path.exists(ruta_codigo):
            log_message(f"No se encontró el directorio del componente '{componente}' para documentar.", "WARNING")
            return True

        log_message(f"Leyendo código desde: {ruta_codigo}...", "INFO")
        codigo_del_proyecto = leer_codigo_proyecto(ruta_codigo)
        
        # El nombre del fichero de salida es dinámico, y lo pasamos en el contexto.
        output_filename = f"docs/{componente}_documentation.md" if componente != "full" else "README.md"
        
        contexto_documentador = {
            **contexto_global,
            "CONTEXTO_DEL_CODIGO": codigo_del_proyecto,
            "FICHERO_A_GENERAR": output_filename
        }

        # Usamos la función genérica run_agent_mission, que sabe cómo guardar ficheros.
        if not run_agent_mission(client, "documentador", contexto_documentador):
            log_message(f"El agente documentador para '{componente}' falló.", "ERROR")
            return False
        
        # --- ¡NUEVA LÓGICA DE SINCRONIZACIÓN! ---
        log_message(f"Sincronizando workspace tras la documentación de [{componente.upper()}]...", "GIT")
        run_git_command(["git", "pull"], repo_path)
        # --- FIN DE LA NUEVA LÓGICA ---
        
        log_message(f"Documentación para '{componente}' generada con éxito.", "SUCCESS")
        return True
    except Exception as e:
        log_message(f"Fallo crítico en la fase de documentación para '{componente}': {e}", "FATAL")
        return False

def ejecutar_etapa_documentacion(client, context: dict, repo_path: str, componente: str):
    """
    Orquesta nuestro propio agente documentador (basado en tu lógica original).
    Puede documentar un componente específico o el proyecto completo.
    """
    log_message(f"--- 📖 Iniciando Etapa de Documentación para: [{componente.upper()}] ---", "SYSTEM")
    
    # --- Fase 1: Contextualizador ---
    log_message(f"   - [Contextualizador] Leyendo código del componente '{componente}'...")
    try:
        ruta_codigo = os.path.join(repo_path, componente) if componente != "full" else repo_path
        if not os.path.exists(ruta_codigo):
            log_message(f"   - No se encontró el directorio '{ruta_codigo}' para documentar.", "WARNING")
            return True # No es un error fatal.

        codigo_del_proyecto = leer_codigo_proyecto(ruta_codigo)
        if not codigo_del_proyecto:
            log_message("   - ❌ No se encontró código relevante para documentar en la ruta especificada."); return True

        log_message(f"   - [Contextualizador] ✅ Código leído ({len(codigo_del_proyecto)} caracteres).")
    except Exception as e:
        log_message(f"   - ❌ Error leyendo el código del proyecto: {e}"); return False

    # --- Fase 2: Documentador ---
    log_message("   - [Documentador] Generando prompt para el LLM...")
    try:
        prompt_path = AGENT_INFO['documentador']['prompt']
        with open(prompt_path, 'r', encoding='utf-8') as f: prompt_template = f.read()
        
        prompt_final = prompt_template.replace("{CONTEXTO_DEL_CODIGO}", codigo_del_proyecto)
        
        log_message("   - [Documentador] Solicitando generación de la documentación al LLM...")
        documentacion_md = get_llm_response_directo(prompt_final, context.get("llm_config"))
        
        documentacion_md = re.sub(r'^```(?:markdown)?\n', '', documentacion_md)
        documentacion_md = re.sub(r'\n```$', '', documentacion_md)

        log_message("   - [Documentador] ✅ Documentación recibida del LLM.")
    except Exception as e:
        log_message(f"   - ❌ Error durante la generación con el LLM: {e}"); return False

    # --- Guardado y Commit ---
    try:
        # CORRECCIÓN: El nombre del fichero de salida ahora es dinámico y correcto.
        output_filename = f"{componente}_documentation.md" if componente != "full" else "README.md"
        # La documentación general (README) va a la raíz, la de componentes a /docs
        docs_dir = os.path.join(repo_path, "docs") if componente != "full" else repo_path
        os.makedirs(docs_dir, exist_ok=True)
        
        output_path = os.path.join(docs_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f: f.write(documentacion_md)
        log_message(f"   ✅ Documentación guardada en: {output_path}")

        log_message("   - Guardando la nueva documentación en GitHub...")
        git_add_path = os.path.relpath(output_path, repo_path)
        run_git_command(["git", "add", git_add_path], repo_path)
        run_git_command(["git", "commit", "-m", f"Agente [Documentador]: Genera/actualiza documentación para {componente}"], repo_path)
        run_git_command(["git", "push"], repo_path)
        log_message("   ✅ Documentación subida a GitHub.")
        return True
    except Exception as e:
        log_message(f"   - ❌ Error guardando el fichero o haciendo commit: {e}"); return False
    
def ejecutar_etapa_construccion(client, etapa_info, repo_local_path, contexto_global):
    """
    Ejecuta únicamente la fase de construcción de una etapa.
    Lanza un agente para generar el código y lo sube a Git.
    Devuelve True si tiene éxito, False si falla.
    """
    etapa = etapa_info.get("etapa")
    tareas = etapa_info.get("tareas", [])
    requisito_completo = f"Construir la etapa de '{etapa}' cumpliendo con TODOS los siguientes requisitos:\n- " + "\n- ".join(tareas)
    
    log_message(f"--- 👷 Fase de Construcción para: [{etapa.upper()}] ---", "STAGE")
    rol_obrero = etapa
    contexto_obrero = {**contexto_global, "tarea_especifica": requisito_completo}
    inyectar_guias_de_estilo(rol_obrero, contexto_obrero) # <-- Nueva llamada

    if etapa == "frontend":
        doc_backend_path = os.path.join(repo_local_path, "docs", "backend_documentation.md")
        if os.path.exists(doc_backend_path):
            log_message("Documentación del backend encontrada. Inyectando en el contexto del frontend.", "INFO")
            with open(doc_backend_path, 'r', encoding='utf-8') as f:
                contexto_obrero["DOCUMENTACION_BACKEND"] = f.read()

    if not run_agent_mission(client, rol_obrero, contexto_obrero):
        log_message(f"El agente constructor '{rol_obrero}' falló. Abortando construcción.", "ERROR")
        return False

    log_message(f"Actualizando workspace tras la construcción de [{etapa.upper()}]...", "GIT")
    run_git_command(["git", "pull"], repo_local_path)
    run_git_command(["git", "add", "."], repo_local_path)
    run_git_command(["git", "commit", "-m", f"Agente [{etapa.upper()}]: Completa la construcción de la etapa"], repo_local_path)
    run_git_command(["git", "push"], repo_local_path)
    

    # --- ¡NUEVA LÓGICA DE SINCRONIZACIÓN! ---
    log_message(f"Sincronizando workspace tras la construcción de [{etapa.upper()}]...", "GIT")
    run_git_command(["git", "pull"], repo_local_path)
    # --- FIN DE LA NUEVA LÓGICA ---

    log_message(f"✅ Construcción de la etapa [{etapa.upper()}] finalizada y subida.", "SUCCESS")
    return True

def ejecutar_etapa_qa(client, etapa_info, repo_local_path, contexto_global, no_qa, plan_path):
    """
    Ejecuta la fase de QA. Si falla, busca la documentación específica del componente
    y la pasa al Jefe de Proyecto para una corrección informada.
    """
    if no_qa:
        log_message("Modo rápido activado (--no-qa). Saltando todas las fases de QA.", "INFO")
        return True

    etapa = etapa_info.get("etapa") # ej: "backend"
    log_message(f"--- 🧐 Fase de QA para la Etapa [{etapa.upper()}] ---", "STAGE")
    
    try:
        codigo_actual = leer_codigo_proyecto(repo_local_path)
    except Exception as e:
        log_message(f"ERROR CRÍTICO: No se pudo leer el código del proyecto para QA: {e}", "FATAL")
        return False

    if etapa == "backend":
        requirements_path = os.path.join(repo_local_path, "requirements.txt")
        if os.path.exists(requirements_path):
            log_message("Fichero 'requirements.txt' encontrado. Instalando dependencias...", "SYSTEM")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", requirements_path], check=True, capture_output=True, text=True)
                log_message("Dependencias instaladas correctamente.", "SUCCESS")
            except subprocess.CalledProcessError as e:
                log_message(f"Fallo al instalar dependencias: {e.stderr}", "FATAL")
                return False
        else:
            log_message("Advertencia: No se encontró 'requirements.txt' para la etapa de backend.", "WARNING")

        try:
            log_message(f"Ejecutando pruebas unitarias para [{etapa.upper()}] con pytest...", "QA")
            resultado_tests = subprocess.run(["pytest"], cwd=repo_local_path, check=True, capture_output=True, text=True, encoding='utf-8')
            log_message(f"Todas las pruebas para [{etapa.upper()}] han pasado.", "SUCCESS")
            return True
        except subprocess.CalledProcessError as e:
            if e.returncode == 5:
                log_message("Pytest no encontró tests para ejecutar. Marcando como exitoso.", "INFO")
                return True
            
            log_message(f"Las pruebas para [{etapa.upper()}] han fallado.", "FAIL")
            razon_fallo = f"PYTEST FALLÓ:\n--- STDOUT ---\n{e.stdout}\n--- STDERR ---\n{e.stderr}"
            
            contexto_global["etapa_actual"] = etapa
            requisito_completo = f"Corregir la etapa de '{etapa}' que falló las pruebas de QA."
            
            # --- ¡NUEVA LÓGICA! Buscar y cargar la documentación específica del componente ---
            doc_path = os.path.join(repo_local_path, "docs", f"{etapa}_documentation.md")
            doc_content = "No se encontró documentación específica para este componente."
            if os.path.exists(doc_path):
                log_message(f"Documentación de '{etapa}' encontrada. Añadiendo al contexto del Jefe de Proyecto.", "INFO")
                with open(doc_path, 'r', encoding='utf-8') as f:
                    doc_content = f.read()
            # --- FIN DE LA NUEVA LÓGICA ---

            tarea_de_correccion_creada = run_jefe_de_proyecto_agent(contexto_global, requisito_completo, codigo_actual, razon_fallo, plan_path, doc_content)
            return tarea_de_correccion_creada

    elif etapa == "frontend":
        log_message("QA para la etapa de frontend aún no implementado. Marcando como exitoso.", "INFO")
        return True
        
    else:
        log_message(f"No hay un método de QA definido para la etapa '{etapa}'. Marcando como exitoso.", "INFO")
        return True

    
def main(args):
    log_message("🧠 Orquestador V12 (Workflows por Etapas): Iniciando colmena...", "SYSTEM")
    client = docker.from_env()
    os.makedirs(PROCESSED_TASKS_DIR, exist_ok=True)
    os.makedirs(FAILED_TASKS_DIR, exist_ok=True)
    os.makedirs(PLANS_DIR, exist_ok=True)

    while True:
        task_files = sorted([f for f in os.listdir(TASKS_DIR) if f.endswith('.json')])
        
        if not task_files:
            log_message("No hay más tareas en la cola. La Colmena finaliza su trabajo.", "SYSTEM")
            break

        current_task_file = task_files[0]
        task_path = os.path.join(TASKS_DIR, current_task_file)
        log_message(f"--- 📬 Nueva Tarea Encontrada: {current_task_file} ---", "TASK")
        
        exito_mision = True
        try:
            with open(task_path, 'r', encoding='utf-8') as f: config = json.load(f)
            
            project_name = config.get("github_project")
            if not project_name: raise ValueError(f"La tarea {current_task_file} no especifica un 'github_project'.")

            workspace_dir = os.path.abspath(WORKSPACE_DIR_NAME)
            repo_local_path = os.path.join(workspace_dir, project_name)
            contexto_global = config.copy()
            
            etapas_a_ejecutar = contexto_global.get("etapas_a_ejecutar", [])
            log_message(f"Workflow solicitado: {etapas_a_ejecutar}", "INFO")

            preparar_repositorio(config, repo_local_path)

            plan_path = ""
            plan = {}
            
            # --- ¡LÓGICA CORREGIDA! ---
            # Cargamos el plan solo si el workflow NO empieza con la planificación.
            if etapas_a_ejecutar and etapas_a_ejecutar[0] != "planificacion":
                plan_de_origen = contexto_global.get("plan_de_origen")
                if plan_de_origen:
                    plan_path = os.path.join(PLANS_DIR, plan_de_origen)
                else:
                    nombre_base_tarea = os.path.splitext(current_task_file)[0]
                    nombre_plan_a_buscar = f"{nombre_base_tarea.split('-FIX-')[0]}_plan_construccion.json"
                    plan_path = os.path.join(PLANS_DIR, nombre_plan_a_buscar)
                
                if not os.path.exists(plan_path): raise FileNotFoundError(f"Se requiere un plan para este workflow, pero no se encontró en '{plan_path}'")
                log_message(f"Usando plan de ejecución: '{plan_path}'", "INFO")
                with open(plan_path, 'r', encoding='utf-8') as f: plan = json.load(f)

            for etapa_actual in etapas_a_ejecutar:
                log_message(f"--- Ejecutando Etapa: [{etapa_actual.upper()}] ---", "SYSTEM")
                
                if etapa_actual == "planificacion":
                    limpiar_workspace(repo_local_path)
                    contexto_arquitecto = { **contexto_global, "tarea_especifica": "Generar plan de construcción." }
                    if not run_agent_mission(client, "arquitecto", contexto_arquitecto):
                        exito_mision = False; break
                    
                    run_git_command(["git", "pull"], repo_local_path)
                    plan_original_path = os.path.join(repo_local_path, "plan_construccion.json")
                    if os.path.exists(plan_original_path):
                        nombre_base_tarea = os.path.splitext(current_task_file)[0]
                        nuevo_nombre_plan = f"{nombre_base_tarea}_plan_construccion.json"
                        plan_path = os.path.join(PLANS_DIR, nuevo_nombre_plan)
                        shutil.move(plan_original_path, plan_path)
                        # Recargamos el plan por si se usa en la misma ejecución
                        with open(plan_path, 'r', encoding='utf-8') as f: plan = json.load(f)
                    else:
                        raise FileNotFoundError("El arquitecto no generó 'plan_construccion.json'.")
                
                elif etapa_actual.endswith(("-dev")): # MODIFICADO para unificar
                    componente, fase = etapa_actual.split('-')
                    etapa_info = next((e for e in plan.get('plan', []) if e.get("etapa") == componente), None)
                    if not etapa_info: raise ValueError(f"No se encontró la etapa '{componente}' en el plan.")
                    
                    if componente == 'e2e':
                        if not ejecutar_etapa_e2e_dev(client, etapa_info, repo_local_path, contexto_global): exito_mision = False; break
                    else: # Para backend y frontend, usamos la función estándar
                        if not ejecutar_etapa_construccion(client, etapa_info, repo_local_path, contexto_global): exito_mision = False; break
                
                elif etapa_actual.endswith(("-qa")):
                    # ... (código sin cambios)
                    if etapa_actual == "e2e-qa":
                        if not ejecutar_etapa_e2e_qa(repo_local_path, contexto_global): exito_mision = False; break
                    else:
                        componente, fase = etapa_actual.split('-')
                        etapa_info = next((e for e in plan.get('plan', []) if e.get("etapa") == componente), None)
                        if not etapa_info: raise ValueError(f"No se encontró la etapa '{componente}' en el plan.")
                        if not ejecutar_etapa_qa(client, etapa_info, repo_local_path, contexto_global, args.no_qa, plan_path): exito_mision = False; break
                    # --- FIN DE LA LÓGICA MODIFICADA ---
                elif etapa_actual.endswith("-doc"):
                    componente = etapa_actual.split('-')[0]
                    if not ejecutar_etapa_documentacion(client, contexto_global, repo_local_path, componente):
                        exito_mision = False; break
                
                elif etapa_actual == "documentacion":
                    if not ejecutar_etapa_documentacion(client, contexto_global, repo_local_path, "full"):
                        exito_mision = False; break
 
                else:
                    log_message(f"Etapa desconocida: '{etapa_actual}'. Saltando.", "WARNING")

            if exito_mision: log_message("✅ Workflow completado con éxito.", "SUCCESS")
                
        except Exception as e:
            exito_mision = False
            log_message(f"Error fatal procesando la tarea {current_task_file}: {e}", "FATAL")
        
        if os.path.exists(task_path):
            if exito_mision:
                log_message(f"Archivando tarea completada '{current_task_file}'...", "SYSTEM")
                shutil.move(task_path, os.path.join(PROCESSED_TASKS_DIR, current_task_file))
            else:
                log_message(f"Moviendo tarea fallida '{current_task_file}' a cuarentena...", "WARNING")
                shutil.move(task_path, os.path.join(FAILED_TASKS_DIR, current_task_file))

        log_message(f"Misión para '{current_task_file}' finalizada.", "TASK")

    log_message("🏁 Colmena finalizada.", "SYSTEM")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Orquestador de la Colmena de Agentes IA V9 (Autónomo).")
    parser.add_argument("--no-qa", action="store_true", help="Desactiva el ciclo de QA para una ejecución rápida.")
    args = parser.parse_args()
    main(args)
