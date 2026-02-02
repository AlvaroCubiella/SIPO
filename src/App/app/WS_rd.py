import os
import sys

import pandas as pd

file = "E:\\SiavoVB_Anexo\\Estructura\\MA\\2024\\016\\Meteo\\CR300 INIDEP_minuto.dat"

# Leer el archivo, ignorando la primer fila innecesaria
data = pd.read_csv(file, skiprows=1, header=None)

# Combinar las filas 1, 2 y 3 para formar el encabezado
header_row1 = data.iloc[0]
header_row2 = data.iloc[1]
header_row3 = data.iloc[2]

# Combinar nombres de columnas
columns = header_row1 + " (" + header_row2 + ", " + header_row3 + ")"
columns[0] = 'DateTime'
columns[1] = 'Registro'
# Configurar las columnas en el DataFrame
data.columns = columns
data = data[3:]  # Ignorar las filas de encabezado originales

# Resetear el índice
data.reset_index(drop=True, inplace=True)

# Convertir la columna 'TIMESTAMP' a datetime
data['DateTime'] = pd.to_datetime(
    data['DateTime'], format="%Y-%m-%d %H:%M:%S", errors='coerce')

print()
