import os
import subprocess
import time
import sys

# --- Configuración ---
TASKS_DIR = "tasks"
LOGS_DIR = "logs_tareas"  # Nueva carpeta para los logs de cada tarea
MAX_RETRIES = 1
DELAY_BETWEEN_RETRIES = 3

def main():
    """
    Orquesta la ejecución de múltiples tareas, mostrando su salida en tiempo real
    y guardando un log para cada una.
    """
    print(f"--- 🚀 Iniciando el Director de Orquesta de la Colmena ---")
    
    os.makedirs(LOGS_DIR, exist_ok=True) # Asegurarse de que la carpeta de logs existe
    
    if not os.path.isdir(TASKS_DIR):
        print(f"❌ ERROR: No se encontró el directorio '{TASKS_DIR}'.")
        sys.exit(1)

    json_files = sorted([f for f in os.listdir(TASKS_DIR) if f.endswith('.json')])

    if not json_files:
        print(f"✅ No se encontraron tareas .json en el directorio '{TASKS_DIR}'.")
        return

    print(f"📂 Se han encontrado {len(json_files)} tareas para ejecutar en orden:")
    for file in json_files:
        print(f"   - {file}")
    print("-" * 50)

    # Iterar y ejecutar cada tarea
    for filename in json_files:
        full_path = os.path.join(TASKS_DIR, filename)
        command = ["python", "-u", "orquestador.py", "-f", full_path]
        log_file_path = os.path.join(LOGS_DIR, filename.replace(".json", ".log"))
        
        print(f"\n▶️  Ejecutando Tarea: {filename} (Log en: {log_file_path})")
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                # --- ¡NUEVA LÓGICA DE EJECUCIÓN CON STREAMING! ---
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # Usamos Popen para tener control sobre la salida en tiempo real
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Redirigir error a la salida estándar
                    text=True,
                    encoding='utf-8',
                    env=env,
                    bufsize=1 # Procesar línea por línea
                )

                # Abrimos el archivo de log para escribir en él
                with open(log_file_path, "w", encoding="utf-8") as log_file:
                    # Leemos la salida del orquestador línea por línea
                    for line in iter(process.stdout.readline, ''):
                        # La mostramos en la consola
                        sys.stdout.write(line)
                        # Y la guardamos en el archivo de log
                        log_file.write(line)
                
                process.stdout.close()
                return_code = process.wait()

                if return_code != 0:
                    raise subprocess.CalledProcessError(return_code, command)
                
                print(f"✅ Éxito: La tarea '{filename}' se completó correctamente.")
                break

            except Exception as e:
                print(f"⚠️  FALLO (Intento {attempt + 1}/{MAX_RETRIES + 1}): La tarea '{filename}' falló.")
                if attempt < MAX_RETRIES:
                    print(f"   - Reintentando en {DELAY_BETWEEN_RETRIES} segundos...")
                    time.sleep(DELAY_BETWEEN_RETRIES)
                else:
                    print(f"❌ ERROR DEFINITIVO: La tarea '{filename}' falló después de {MAX_RETRIES + 1} intentos.")
                    print(f"   - El log completo de la ejecución se ha guardado en: {log_file_path}")

    print("\n🏁 Proceso de ejecución de todas las tareas finalizado. ---")

if __name__ == "__main__":
    main()