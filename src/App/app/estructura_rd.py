import os
import json

# Ruta del archivo JSON
json_file = "E:\\SiavoVB_Anexo\\Estructura\\MA\\2024\\017\\MA202417.json"

# Cargar el archivo JSON como un diccionario
with open(json_file, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Extraer estaciones y sus valores de Skipover
estaciones = data.get('Estaciones', {})
resultado = {estacion: info.get('Skipover')
             for estacion, info in estaciones.items()}

# Mostrar el resultado
for estacion, skipover in resultado.items():
    print(f"Estación: {estacion}, Skipover: {skipover}")
