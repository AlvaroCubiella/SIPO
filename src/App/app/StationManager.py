import os
import json
import logging
import shutil
from app import utils

class StationManager:
    def __init__(self, cfg, estructura):
        self.cfg = cfg
        self.estructura = estructura
        
        # Estado de la estación
        self.nro_estacion = None
        self.estacion = dict()
        self.statusAdq = False
        
        # Contadores y Banderas
        self.countCub = 0
        self.countSup = 0
        self.countFdo = 0
        self.fdo = 0  # 0: Bajada/Superficie no completa, 1: Subida/Fondo marcado
        
        # Rutas y Archivos
        self.file_json = None
        self._ROOT_DIR = None
        self._hex_file = None
        self._xmlcon_file = None
        self.sensors = None

    def set_working_dir(self, file_json_path):
        """Configura la ruta del archivo JSON de la campaña."""
        path = os.getenv('OF_BUQUE_NROCAMP')
        if not path:
             # Alternativa si no hay variable de entorno, aunque debería haber
             path = os.path.dirname(file_json_path)
             
        file_name = os.path.basename(file_json_path)
        self.file_json = os.path.join(path, file_name)

    def init_vars(self):
        """Inicializa variables de rutas basadas en la configuración."""
        ROOT = self.cfg['Directorios']['Estructura']
        buque = str(self.cfg['Campania']['Siglasbuque'])
        anio = str(self.cfg['Campania']['Anio'])
        nrocamp = str(self.cfg['Campania']['Nrocampania']).zfill(3)
        self._ROOT_DIR = os.path.join(ROOT, buque, anio, nrocamp)
        self._hex_file = f"{self.nro_estacion.zfill(4)}.hex"
        self._xmlcon_file = f"{self.nro_estacion.zfill(4)}.xmlcon"

    def check_xmlcon_exists(self):
        """Verifica si existe el archivo xmlcon virgen."""
        xmlcon = os.path.join(self._ROOT_DIR, 'Virgenes', self._xmlcon_file)
        if not os.path.exists(xmlcon):
            return False, xmlcon
        
        self.sensors = utils.read_xmlcon(xmlcon)
        logging.info('xmlcon cargado')
        return True, xmlcon

    def start_station(self, nro_estacion):
        """Inicia una nueva estación."""
        self.nro_estacion = nro_estacion
        
        # Inicializar estructura de estación
        self.estacion = dict()
        estacion_data = utils.Estacion()
        estacion_data['NroEstacion'] = self.nro_estacion
        self.estacion[self.nro_estacion] = estacion_data
        
        # Resetear contadores
        self.countCub = 0
        self.countSup = 0
        self.countFdo = 0
        self.fdo = 0
        self.statusAdq = True
        
        self.init_vars()

    def stop_station(self):
        """Finaliza la estación actual."""
        self.statusAdq = False

    def station_exists(self, nro_estacion):
        """Verifica si la estación ya existe en la estructura."""
        return nro_estacion in self.estructura['Estaciones']

    def save_json(self):
        """Guarda la estructura actual en el archivo JSON."""
        if not self.file_json:
            logging.error("No se ha definido file_json para guardar.")
            return

        # Actualizar la estructura global con la estación actual
        # Asegurarse de que self.nro_estacion es válido
        if self.nro_estacion and self.estacion:
             self.estructura['Estaciones'].update(self.estacion)

        try:
            with open(self.file_json, 'w+') as archivo:
                json.dump(self.estructura, archivo, indent=4)
        except Exception as e:
            logging.error(f"Error al guardar JSON: {e}")

    def W_Pos(self, nmea_data, dbs_data, is_start=True):
        """Registra la posición y datos iniciales/finales."""
        station_entry = self.estacion[self.nro_estacion]
        
        if is_start:
            # Inicio
            station_entry['Posicion']['Inicio']['Latitud'] = nmea_data.get('latD', 'NaN')
            station_entry['Posicion']['Inicio']['Longitud'] = nmea_data.get('lonD', 'NaN')
            station_entry['FechaHora']['Inicio']['HoraGMT'] = nmea_data.get('hora', 'NaN')
            station_entry['FechaHora']['Inicio']['FechaGMT'] = nmea_data.get('fecha', 'NaN')
            station_entry['Batimetria']['Inicio'] = str(dbs_data)
            
            # Sensores (Primarios, Secundarios, Auxiliares) se toman de self.sensors cargado previamente
            if self.sensors:
                for sensor_type, sensor_list in self.sensors.GetPrimary().items():
                    station_entry['Instrumento']['Sensores']['Primarios'][sensor_type] = {
                        'SerialNumber': sensor_list['SerialNumber'],
                        'CalibrationDate': sensor_list['CalibrationDate'],
                    }
                for sensor_type, sensor_list in self.sensors.GetSecondary().items():
                    station_entry['Instrumento']['Sensores']['Secundarios'][sensor_type] = {
                        'SerialNumber': sensor_list['SerialNumber'],
                        'CalibrationDate': sensor_list['CalibrationDate'],
                    }
                for sensor_type, sensor_list in self.sensors.GetAuxiliary().items():
                    station_entry['Instrumento']['Sensores']['Auxiliares'][sensor_type] = {
                        'SerialNumber': sensor_list['SerialNumber'],
                        'CalibrationDate': sensor_list['CalibrationDate'],
                    }
        else:
            # Fin
            station_entry['Posicion']['Fin']['Latitud'] = nmea_data.get('latD', 'NaN')
            station_entry['Posicion']['Fin']['Longitud'] = nmea_data.get('lonD', 'NaN')
            station_entry['FechaHora']['Fin']['HoraGMT'] = nmea_data.get('hora', 'NaN')
            station_entry['FechaHora']['Fin']['FechaGMT'] = nmea_data.get('fecha', 'NaN')
            station_entry['Batimetria']['Fin'] = str(dbs_data)
            
        self.save_json()

    def W_CTD(self, ctd_data, loc):
        """Registra dato de CTD en Cubierta o Fondo."""
        # loc debe ser 'Cubierta' o 'Fondo'
        pos = self.countCub if loc == 'Cubierta' else self.countFdo
        self.estacion[self.nro_estacion][loc][str(pos)] = ctd_data
        self.save_json()
        
        if loc == 'Cubierta':
            self.countCub += 1
        else:
             self.countFdo += 1

    def W_TSGvsCTD(self, ctd_data, tsg_data, nmea_data):
        """Registra comparación TSG vs CTD en Superficie."""
        self.estacion[self.nro_estacion]['Superficie'][str(self.countSup)] = {
            'Hora': nmea_data.get('hora', 'NaN'),
            'CTD': ctd_data,
            'TSG': tsg_data,
        }
        self.countSup += 1
        self.save_json()

    def W_Bott(self, ctd_data):
        """Salva el registro del CTD al disparar una botella."""
        try:
            bot_idx = ctd_data.get('Bot', 'NaN') # Asumiendo que 'Bot' es la clave correcta
            # NOTA: En el código original era self.CTD_str['Bot']. Ajustar si la clave es diferente.
            # En Main.pyw: self.CTD_str['bot'] = i (minúscula) pero self.estacion...[...][self.CTD_str['Bot']] (Mayúscula?)
            # Revisando Main.pyw linea 827: self.CTD_str['bot'] = i
            # linea 1032: self.estacion...['Botellas'][self.CTD_str['Bot']]
            # Parece haber inconsistencia mayúscula/minúscula en el original.
            # Asumiré que ctd_data viene con las claves correctas.
            
            # Corrección para robustez: buscar case-insensitive o asegurar clave
            key_bot = 'Bot' if 'Bot' in ctd_data else 'bot'
            if key_bot in ctd_data:
                 self.estacion[self.nro_estacion]['Botellas'][ctd_data[key_bot]] = ctd_data
                 self.save_json()
        except Exception as e:
            logging.error(f"Error en W_Bott: {e}")

    def W_SkipOver(self, skip_over_value):
        """Guarda el valor de SkipOver."""
        try:
            self.estacion[self.nro_estacion]['Skipover'] = skip_over_value
            self.save_json()
        except:
            pass

    def add_comment(self, comentario):
        """Agrega comentario a la estación."""
        try:
             self.estacion[self.nro_estacion]['Comentarios'] = comentario
             self.save_json()
        except Exception as e:
             logging.error(f"Error guardando comentario: {e}")
