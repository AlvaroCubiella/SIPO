import os
import xml.etree.ElementTree as ET


def cfg():
    modelo = {
        "Archivos": [

        ],
        "Campania": {
            "Siglasbuque": "VA",
            "Anio": 2021,
            "Nrocampania": 4
        },
        "Directorios": {
            "Estructura": "C:\\SiavoVB_Anexo\\Estructura",
            "seasave7": "C:\\Users\\User\\AppData\\Local\\Sea-Bird\\IniFiles\\seasave.ini",
            "seasaveini": "C:\\Users\\User\\AppData\\Local\\Sea-Bird\\IniFiles\\Seasave.ini",
            "sbedataproc": "C:\\Program Files (x86)\\Sea-Bird\\SBEDataProcessing-Win32\\SBEDataProc.exe"
        },
        "Configuracion": {
            "CTD": {
                "Variables": 6,
                "Status": 2,
                "Intervalo": 5,
                "Port": "COM14",
                "BR": 9600,
                "databits": 8,
                "Parity": "None",
                "Stopbits": 1,
                "filas": ["Scan", "Pres", "Temp", "Cond", "Sal", "Bot"]
            },
            "TSG": {
                "Variables": 15,
                "Status": 2,
                "Intervalo": 5,
                "Port": "COM15",
                "BR": 9600,
                "databits": 8,
                "Parity": "Even",
                "Stopbits": 1,
                "filas": ["ScanCount", "JulianDays", "Longitude", "Latitude", "Temperature", "Conductivity", "Salinity", "Density", "TemperatureSBE38", "SoundVelocity", "OxygenSaturation", "Time", "Elapsed", "Time", "NMEA"]
            },
            "NMEA": {
                "Status": 2,
                "Intervalo": 3,
                "Port": "COM11",
                "BR": 4800,
                "databits": 8,
                "Stopbits": 1
            },
            "Batimetria": {
                "Status": 2,
                "Intervalo": 3,
                "Port": "COM6",
                "BR": 9600,
                "databits": 8,
                "Stopbits": 1
            }
        }
    }

    return modelo

# Compruebo los archivo json compatibles para importar campanias


def validate_import_json(dic, modelo=None):
    """
    Comprueba si el archivo json tienen la misma estructura que uno para importar.
    """
    # Defino la estructura de un archivo import.json
    if modelo == None:
        modelo = {
            "Expedicion": {
                "Id": 0,
                "Buque": "MA",
                "Anio": 2020,
                "Numero": 17
            },
            "Instrumento": {
                "Id": 0,
                "Siglas": "SBE25_01"
            },
            "Archivos": {
                "Configuracion": [
                    "*.xmlcon",
                    "*.xml"
                ]
            },
            "Estaciones": {}
        }

    if type(modelo) is not type(dic):
        return False

    if isinstance(modelo, dict):
        # Comparo las etiquetas de cada dicionaio
        if set(modelo.keys()) != set(dic.keys()):
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
    "cnv": "CNV",
    "termosal": {
        "hex": "HEX",
        "cnv": "CNV"
    },
    "varios": "Varios",
}


def Estacion():
    estacion = {
        'NroEstacion': '',
        'Instrumento': {
            'Sensores': {
                'Primarios': {},
                'Secundarios': {},
                'Auxiliares': {},
            }
        },
        'Posicion': {
            'Inicio': {
                'Latitud': '',
                'Longitud': ''
            },
            'Fin': {
                'Latitud': '',
                'Longitud': ''
            }
        },
        'FechaHora': {
            'Inicio': {
                'FechaGMT': '',
                'HoraGMT': ''
            },
            'Fin': {
                'FechaGMT': '',
                'HoraGMT': ''
            }
        },
        'Batimetria': {
            'Inicio': 0,
            'Fin': 0
        },
        'Meteorologia': {},
        'Skipover': 0,
        'Cubierta': {},
        'Superficie': {},
        'Fondo': {},
        'Comentarios': ''
    }
    return estacion

# Cargo el archivo SeaSaveIni


def read_SeaSaveIni(file_SeaSaveIni):
    with open(file_SeaSaveIni, 'r') as file:
        for line in file:
            if line.startswith('ITEM_0'):
                return line.split('=')[1].strip()


def read_psa(psa_file):
    # Parsear el archivo XML
    tree = ET.parse(psa_file)
    root = tree.getroot()

    # Buscar el elemento ConfigurationFilePath y obtener su valor
    configuration_file_path = root.find(
        './/ConfigurationFilePath').attrib['value']
    tree = ET.parse(configuration_file_path)
    root = tree.getroot()

    sensors = []
    auxiliary_sensors = []
    instrument_type = root.find('.//Name').text
    if 'SBE 25plus' in instrument_type:
        #################################################################
        # Cargo el xmlcon para un SBE25 plus
        #################################################################
        # Buscar sensores TCP (Temperature, Conductivity, Pressure)
        tcp_sensors = root.find('.//TCP_Sensors')
        if tcp_sensors is not None:
            for sensor in tcp_sensors.findall('.//Sensor'):
                sensor_data = {
                    'index': int(sensor.get('index')),
                    # 'SensorID': sensor.get('SensorID'),
                    'Type': sensor[0].tag,
                    'SerialNumber': sensor[0].find('SerialNumber').text,
                    'CalibrationDate': sensor[0].find('CalibrationDate').text
                }

                # Corroboro que el sensor no sea 'NotInUse'
                if not sensor[0].tag == 'NotInUse':
                    sensors.append(sensor_data)
        # Buscar sensores externos
        external_sensors = root.find('.//ExternalVoltageSensors')
        if external_sensors is not None:
            offset_aux = int(sensors[-1]['index']) + 1
            for sensor in external_sensors.findall('.//Sensor'):
                sensor_data = {
                    'index': int(sensor.get('index')) + offset_aux,
                    # 'SensorID': int(sensor.get('SensorID')),
                    'Type': sensor.find('*').tag,
                    'SerialNumber': sensor.find('.//SerialNumber').text,
                    'CalibrationDate': sensor[0].find('CalibrationDate').text
                }
                if not sensor.find('*').tag == 'NotInUse':
                    sensors.append(sensor_data)

    elif instrument_type in ['SBE 911plus/917plus CTD', 'SBE 25 Sealogger CTD']:
        #################################################################
        # Cargo el xmlcon para un SBE9plus
        #################################################################
        for sensor in root.findall(".//SensorArray/Sensor"):
            sensor_data = {
                'index': int(sensor.get('index')),
                # 'SensorID': int(sensor.get('SensorID')),
                'Type': sensor[0].tag,
                'SerialNumber': sensor[0].find('SerialNumber').text,
                'CalibrationDate': sensor[0].find('CalibrationDate').text
            }

            # Corroboro que el sensor no sea 'NotInUse'
            if not sensor[0].tag == 'NotInUse':
                sensors.append(sensor_data)

    # Clasifico los sensores TC en primarios y secundarios y al resto como sensores auxiliares
    primary_sensors = {}
    secondary_sensors = {}
    auxiliary_sensors = {}

    prim = [0, 1, 2]
    sec = [3, 4]
    aux = [3, 4, 5, 6, 7, 8]
    for sensor in sensors:
        sensor_type = sensor['Type']
        if sensor['index'] in prim:
            if sensor_type not in primary_sensors and sensor_type in ['ConductivitySensor', 'TemperatureSensor', 'PressureSensor']:
                primary_sensors[sensor_type] = []
                primary_sensors[sensor_type].append(sensor)
        if sensor['index'] in sec:
            if sensor_type not in secondary_sensors and sensor_type in ['ConductivitySensor', 'TemperatureSensor']:
                secondary_sensors[sensor_type] = []
                secondary_sensors[sensor_type].append(sensor)
        if sensor['index'] in aux:
            if sensor_type not in auxiliary_sensors and not sensor_type in ['ConductivitySensor', 'TemperatureSensor']:
                auxiliary_sensors[sensor_type] = []
                auxiliary_sensors[sensor_type].append(sensor)
    sensors = {
        'PrimarySensor': primary_sensors,
        'SecondarySensor': secondary_sensors,
        'AuxiliarySensor': auxiliary_sensors,
    }
    return sensors
