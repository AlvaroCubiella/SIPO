import os

def cfg():
    modelo = {
            "Archivos": [
        
            ],
            "Campania":{
                "Siglasbuque": "VA",
                "Anio":2021,
                "Nrocampania":4
            },
            "Directorios":{
                "Datos": {
                    "Estructura":"C:\\SiavoVB_Anexo\\Estructura",
                    "seasave7": "C:\\SiavoVB_Anexo\\ConfRutinas",
                    "seasaveini": "C:\\SiavoVB_Anexo\\ConfInstrumentos"
                },
                "Adquisicion":{
                    "sea_save_ini": "C:\\Users\\Alvaro\\AppData\\Local\\Sea-Bird\\IniFiles\\seasave.ini",
                    "sea_savev7": "C:\\Program Files (x86)\\Sea-Bird\\SeasaveV7\\Seasave.exe",
                    "sbedataproc": "C:\\Program Files (x86)\\Sea-Bird\\SBEDataProcessing-Win32\\SBEDataProc.exe"
                }
            },
            "Configuracion":{
                "CTD":{
                    "Variables":6,
                    "Status":2,
                    "Intervalo":5,
                    "Port":"COM14",
                    "BR":9600,
                    "databits":8,
                    "Parity":"None",
                    "Stopbits":1,
                    "filas":["Scan","Pres","Temp","Cond","Sal","Bot"]
                },
                "TSG":{
                    "Variables":15,
                    "Status":2,
                    "Intervalo":5,
                    "Port":"COM15",
                    "BR":9600,
                    "databits":8,
                    "Parity":"Even",
                    "Stopbits":1,
                    "filas":["ScanCount", "JulianDays", "Longitude", "Latitude", "Temperature", "Conductivity", "Salinity", "Density", "TemperatureSBE38", "SoundVelocity", "OxygenSaturation", "Time", "Elapsed", "Time", "NMEA"]
                },
                "NMEA":{
                    "Status":2,
                    "Intervalo":3,
                    "Port":"COM11",
                    "BR":4800,
                    "databits":8,
                    "Stopbits":1
                },
                "Batimetria":{
                    "Status":2,
                    "Intervalo":3,
                    "Port":"COM6",
                    "BR":9600,
                    "databits":8,
                    "Stopbits":1
                }
            } 
        }
    
    return modelo

# Compruebo los archivo json compatibles para importar campanias
def validate_import_json(dic, modelo = None):
    """
    Comprueba si el archivo json tienen la misma estructura que uno para importar.
    """
    # Defino la estructura de un archivo import.json
    if modelo == None:
        modelo = {
            "Expedicion": {
                "Id":0,
                "Buque":"MA",
                "Anio":2020,
                "Numero":17
            },
            "Instrumento": {
                "Id":0,
                "Siglas":"SBE25_01"
            },
            "Archivos": {
                "Configuracion": [
                "*.xmlcon",
                "*.xml"
                ]
            },
            "Estaciones":{}
        }
        
    if type(modelo) is not type(dic):
        return False

    if isinstance(modelo, dict):
        if set(modelo.keys()) != set(dic.keys()):                   # Comparo las etiquetas de cada dicionaio
            return False

        for clave in modelo.keys():
            if clave == 'Estaciones':
                # No comparo estaciones porque rompe la validacion
                break
            if not validate_import_json(modelo[clave], dic[clave]):
                return False
    return True


# Estructura de carpetas a incluir dentro de una campaña nueva
exp_path = {
    "virgenes": "Virgenes",
    "cnv":"CNV",    
    "termosal": {
        "hex":"HEX",
        "cnv":"CNV"    
    },
    "varios":"Varios",
}

def Estacion():
    estacion = {
                'NroEstacion': '',
                'Posicion':{
                    'Inicio':{
                        'Latitud':'',
                        'Longitud':''
                    },
                    'Fin':{
                        'Latitud':'',
                        'Longitud':''
                    }
                },
                'FechaHora':{
                    'Inicio':{
                        'FechaGMT':'',
                        'HoraGMT':''
                    },
                    'Fin':{
                        'FechaGMT':'',
                        'HoraGMT':''
                    }
                },
                'Batimetria':{
                    'Inicio':0,
                    'Fin':0
                },
                'Meteorologia':{},
                'TSG_file':'',
                'Skipover':0,
                'Cubierta':{},
                'Superficie': {},
                'Fondo': {},
                'Botellas': {},
                'Comentarios':''            
            }
    return estacion

def xlsxStructura():
    celdas = {
        'Camp': {
            'Range': {
                'Col': {
                    'Ini': 'A',
                    'Fin': 'E'
                },
                'Fila': 1,
            },
            'lbl': 'Campaña',
            'campo': True
        },
        'Estacion': {
            'Range': {
                'Col': {
                    'Ini': 'F',
                    'Fin': 'I'
                },
                'Fila': 1,
            },
            'lbl':'Estacion Gral.',
            'campo': True
        },
        'FechaIni': {
            'Range': {
                'Col': {
                    'Ini': 'J',
                    'Fin': 'N'
                },
                'Fila': 1,
            },
            'lbl':'Fecha Inicio (GMT)',
            'campo': True
        },
        'HoraIni': {
            'Range': {
                'Col': {
                    'Ini': 'O',
                    'Fin': 'S'
                },
                'Fila': 1,
            },
            'lbl':'Hora Inicio (GMT)',
            'campo': True
        },
        'FechaFin': {
            'Range': {
                'Col': {
                    'Ini': 'T',
                    'Fin': 'X'
                },
                'Fila': 1,
            },
            'lbl':'Fecha Fin (GMT)',
            'campo': True
        },
        'HoraFin': {
            'Range': {
                'Col': {
                    'Ini': 'Y',
                    'Fin': 'AC'
                },
                'Fila': 1,
            },
            'lbl':'Hora Fin (GMT)',
            'campo': True
        },
        'Operador': {
            'Range': {
                'Col': {
                    'Ini': 'AD',
                    'Fin': 'AG'
                },
                'Fila': 1,
            },
            'lbl':'Operador',
            'campo': True
        },
        'Hoja': {
            'Range': {
                'Col': {
                    'Ini': 'AH',
                    'Fin': 'AJ'
                },
                'Fila': 1,
            },
            'lbl':'Hoja Nº',
            'campo': True
        },
        'Pos_Ini': {
            'Range': {
                'Col': {
                    'Ini': 'A',
                    'Fin': 'H'
                },
                'Fila': 4,
            },
            'lbl': 'Posicion Inicial',
        },
        'Lat_ini': {
            'Range': {
                'Col': {
                    'Ini': 'A',
                    'Fin': 'D'
                },
                'Fila': 5,
            },
            'lbl': 'Latitud',
            'campo': True
        },
        'Lon_ini': {
            'Range': {
                'Col': {
                    'Ini': 'E',
                    'Fin': 'H'
                },
                'Fila': 5,
            },
            'lbl': 'Longitud',
            'campo': True
        },
        'Pos_Fin': {
            'Range': {
                'Col': {
                    'Ini': 'I',
                    'Fin': 'P'
                },
                'Fila': 4,
            },
            'lbl': 'Posicion Final',
        },
        'Lat_fin': {
            'Range': {
                'Col': {
                    'Ini': 'I',
                    'Fin': 'L'
                },
                'Fila': 5,
            },
            'lbl': 'Latitud',
            'campo': True
        },
        'Lon_fin': {
            'Range': {
                'Col': {
                    'Ini': 'M',
                    'Fin': 'P'
                },
                'Fila': 5,
            },
            'lbl': 'Posicion Final',
            'campo': True
        },
        'Prof': {
            'Range': {
                'Col': {
                    'Ini': 'Q',
                    'Fin': 'T'
                },
                'Fila': 4,
            },
            'lbl': 'Profundidad',
        },
        'Prof_ini': {
            'Range': {
                'Col': {
                    'Ini': 'Q',
                    'Fin': 'R'
                },
                'Fila': 5,
            },
            'lbl': 'Inicial',
            'campo': True
        },
        'Prof_fin': {
            'Range': {
                'Col': {
                    'Ini': 'S',
                    'Fin': 'T'
                },
                'Fila': 5,
            },
            'lbl': 'Final',
            'campo': True,
        },
        'Viento': {
            'Range': {
                'Col': {
                    'Ini': 'U',
                    'Fin': 'X'
                },
                'Fila': 4,
            },
            'lbl': 'Viento',
        },
        'V_Vel': {
            'Range': {
                'Col': {
                    'Ini': 'U',
                    'Fin': 'V'
                },
                'Fila': 5,
            },
            'lbl': 'Vel',
            'campo': True,
        },
        'V_Dir': {
            'Range': {
                'Col': {
                    'Ini': 'W',
                    'Fin': 'X'
                },
                'Fila': 5,
            },
            'lbl': 'Dir',
            'campo': True,
        },
        'Mar': {
            'Range': {
                'Col': {
                    'Ini': 'Y',
                    'Fin': 'AB'
                },
                'Fila': 4,
            },
            'lbl': 'Mar',
        },
        'M_Est': {
            'Range': {
                'Col': {
                    'Ini': 'Y',
                    'Fin': 'Z'
                },
                'Fila': 5,
            },
            'lbl': 'Est',
            'campo': True,
        },
        'M_Dir': {
            'Range': {
                'Col': {
                    'Ini': 'AA',
                    'Fin': 'AB'
                },
                'Fila': 5,
            },
            'lbl': 'Dir',
            'campo': True,
        },
        'Temp': {
            'Range': {
                'Col': {
                    'Ini': 'AC',
                    'Fin': 'AF'
                },
                'Fila': 4,
            },
            'lbl': 'Temp',
            'campo': True,
        },
        'CTD': {
            'Range': {
                'Col': {
                    'Ini': 'A',
                    'Fin': 'D'
                },
                'Fila': 8,
            },
            'lbl': 'CTD',
        },
    }

    return celdas