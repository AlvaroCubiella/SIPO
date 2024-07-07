import subprocess
import os, sys

### Obtengo la ruta relativa del CLI SIAVO_Cfg.exe
# Obtiene la ruta del directorio del script de prueba
test_dir = os.path.dirname(__file__)

# Combina el directorio del script de prueba con la ruta del archivo SIAVO_Cfg.exe
siavo_setup_path = os.path.relpath(os.path.join(test_dir, '..', 'SIAVO_Cfg.exe'))

print("Ruta relativa de SIAVO_Cfg.exe:", siavo_setup_path)
###

"""# Añade la ruta del directorio principal a PYTHONPATH
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)"""

#cmd = "SIAVO_Cfg.exe --CreateFile"
#cmd = "SIAVO_Cfg.exe --mkroot -e"
#cmd = "SIAVO_Cfg.exe --CreateFile"
#cmd = "SIAVO_Cfg.exe --CreateFile"

cmd = [
    "SIAVO_Cfg.exe --CreateFile",             # Creo archivo de variables de entorno
    "SIAVO_Cfg.exe -p",                       # Muestro el archivo de env en pantalla
    "SIAVO_Cfg.exe --mkroot -e",              # Creo la estructura de datos a partir del archivo env
    #"SIAVO_Cfg.exe --mkcamp -e",              # Creo la estructura de campaña a partir del archivo json default
    "SIAVO_Cfg.exe --mkcamp VA202306 -e",              # Creo la estructura de campaña a partir del archivo json VA202306
 ]
for i in cmd:
    # Comando de PowerShell que deseas ejecutar
    print(f"Ejecutando comando: {i}")
    powershell_command = f"{os.getcwd()}{os.sep}{i} siavo"      # Por algun motivo si no le pongo un nombre al archivo, me da error de permisos.

    # Ejecutar el comando de PowerShell desde Python
    result = subprocess.run(["powershell", "-Command", powershell_command], capture_output=True, text=True, shell=True)

    # Ver la salida del comando
    if '\x0c' in result.stdout:
        print(result.stdout.replace('\x0c', ''))
    else:
        print(result.stdout)
    print(result.stderr)
    print()