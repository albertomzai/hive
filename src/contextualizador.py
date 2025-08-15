import os

def crear_contexto_del_proyecto(directorio_proyecto, fichero_salida):
    """
    Recorre un directorio, lee los ficheros relevantes y vuelca
    todo el contenido en un único fichero de texto.
    """
    contenido_completo = ""
    directorios_a_ignorar = {'.git', '__pycache__', 'docs', '.venv', 'node_modules'}
    extensiones_relevantes = ('.py', '.js', '.html', '.css', '.json', '.md', 'requirements.txt', 'Dockerfile')

    print(f"---  creando contexto desde: {directorio_proyecto} ---")
    
    for root, dirs, files in os.walk(directorio_proyecto):
        # Evita que se exploren los directorios ignorados
        dirs[:] = [d for d in dirs if d not in directorios_a_ignorar]
        
        for file in files:
            if file.endswith(extensiones_relevantes):
                try:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, directorio_proyecto)
                    
                    contenido_completo += f"\n{'='*20}\n"
                    contenido_completo += f"--- INICIO DEL FICHERO: {rel_path} ---\n"
                    contenido_completo += f"{'='*20}\n\n"
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        contenido_completo += f.read()
                        
                    contenido_completo += f"\n\n{'='*20}\n"
                    contenido_completo += f"--- FIN DEL FICHERO: {rel_path} ---\n"
                    contenido_completo += f"{'='*20}\n"
                    
                except Exception as e:
                    print(f"   - No se pudo leer {file_path}: {e}")

    with open(fichero_salida, 'w', encoding='utf-8') as f:
        f.write(contenido_completo)
        
    print(f"--- Contexto completo guardado en: {fichero_salida} ---")

# Ejemplo de uso:
# crear_contexto_del_proyecto("./workspace/kanban", "./workspace/kanban/contexto_completo.txt")