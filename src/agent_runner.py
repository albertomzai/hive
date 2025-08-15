# src/agent_runner.py (Versión Autónoma con Git)
import os
import sys
import json
import re
import subprocess
import google.generativeai as genai
import ast # <-- AÑADIR ESTA LÍNEA

def get_llm_response(prompt: str, config: dict) -> str:
    """
    Obtiene una respuesta de un LLM, detectando si es una API de Google
    o una compatible con OpenAI (como LM Studio).
    """
    api_base = config.get("api_base")

    if api_base: # Si existe api_base, usamos el cliente de OpenAI
        print("   - Detectado servidor local (OpenAI compatible). Conectando...")
        from openai import OpenAI
        client = OpenAI(base_url=api_base, api_key=config.get("api_key"))
        
        response = client.chat.completions.create(
            model=config.get("model_name"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    
    else: # Si no, usamos el cliente de Google Gemini
        print("   - Detectado API de Google Gemini. Conectando...")
        import google.generativeai as genai
        genai.configure(api_key=config.get("api_key"))
        model = genai.GenerativeModel(config.get("model_name"))
        
        response = model.generate_content(prompt)
        return response.text

def run_command(command, cwd):
    """Ejecuta un comando de terminal, ahora sin lanzar excepción en error de push."""
    print(f"▶️ Ejecutando: '{' '.join(command)}'")
    try:
        # Usamos encoding utf-8 para compatibilidad
        result = subprocess.run(command, capture_output=True, text=True, cwd=cwd, check=True, encoding='utf-8')
        if result.stdout: print(f"✅ Éxito:\n{result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        # El error de "fetch first" en push no debe detener la misión si el commit se hizo.
        print(f"⚠️  ADVERTENCIA durante la ejecución del comando:\n{e.stderr}")
        if "git push" in " ".join(command) and ("fetch first" in e.stderr or "pull" in e.stderr):
             print("   - Se ignora el error de push por posible conflicto de concurrencia (lo resolverá el orquestador).")
             return e.stderr
        raise e

def main():
    print("--- 🏁 AGENTE AUTÓNOMO (Multi-Archivo) INICIADO ---")
    
    llm_config = json.loads(os.environ.get("LLM_CONFIG", "{}"))
    task_prompt = os.environ.get("TASK_PROMPT")
    git_repo_url = os.environ.get("GIT_REPO_URL")
    github_pat = os.environ.get("GITHUB_PAT")
    repo_dir = "repo_de_trabajo_agente"
    
    try:
        auth_url = git_repo_url.replace("https://", f"https://{github_pat}@")
        run_command(["git", "clone", auth_url, repo_dir], cwd="/app")
        run_command(["git", "config", "user.email", "agente@colmena.ai"], cwd=repo_dir)
        run_command(["git", "config", "user.name", "Agente Autónomo"], cwd=repo_dir)
        
        print(f"\n   - Tarea para LLM...")
        llm_response_text = get_llm_response(task_prompt, llm_config)
        print(f"   - Respuesta recibida del LLM.")

        # --- INICIO DEL PARSER "TRADUCTOR UNIVERSAL" (VERSIÓN FINAL) ---
        json_extraido_match = re.search(r'\{.*\}', llm_response_text, re.DOTALL)
        if not json_extraido_match:
            raise ValueError("Respuesta del LLM no contiene un bloque JSON identificable.")

        json_extraido_str = json_extraido_match.group(0)
        
        respuesta_json = None
        try:
            # Intento 1: Parseo estricto de JSON (el ideal)
            respuesta_json = json.loads(json_extraido_str)
        except json.JSONDecodeError as e:
            print(f"   - Fallo el parseo JSON estricto: {e}. Intentando parseo flexible con ast.literal_eval...")
            try:
                # Intento 2: Parseo flexible para diccionarios de Python (ej. comillas simples)
                respuesta_json = ast.literal_eval(json_extraido_str)
            except Exception as ast_error:
                print(f"   - El parseo flexible también falló: {ast_error}")
                raise ValueError("La respuesta del LLM no es ni JSON válido ni un diccionario de Python interpretable.")
        # --- FIN DEL PARSER ---

        files_to_create = respuesta_json.get("files")

        if not isinstance(files_to_create, list):
            raise ValueError("La respuesta JSON debe tener una clave 'files' que contenga una lista.")

        for file_info in files_to_create:
            filename = file_info.get('filename')
            code_content = file_info.get('code', '')
            if not filename: continue

            # Lógica de ensamblaje de código (esta parte ya la tenías bien)
            if isinstance(code_content, list):
                content_to_write = "\n".join(code_content)
            elif isinstance(code_content, dict):
                content_to_write = json.dumps(code_content, indent=2, ensure_ascii=False)
            else:
                content_to_write = str(code_content)
            
            file_path = os.path.join(repo_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f: f.write(content_to_write)
            print(f"   - Archivo '{filename}' guardado correctamente.")

        print("\n   - Subiendo trabajo a GitHub...")
        run_command(["git", "add", "."], cwd=repo_dir)
        commit_message = f"Agente completa tarea generando {len(files_to_create)} archivo(s)"
        run_command(["git", "commit", "-m", commit_message], cwd=repo_dir)
        run_command(["git", "push"], cwd=repo_dir)

        print("\n🎉 ¡MISIÓN COMPLETADA CON ÉXITO!")

    except Exception as e:
        print(f"❌ ERROR INESPERADO EN LA MISIÓN DEL AGENTE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()