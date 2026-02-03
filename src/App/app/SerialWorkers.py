import time
import logging
import serial
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from app.RMC import RMC
from app.DBS import DBS
from app.cfg import Cfg

try:
    unicode
except (NameError, AttributeError):
    unicode = str

def to_bytes(seq):
    """convierte una secuencia a tipo bytes"""
    if isinstance(seq, bytes):
        return seq
    elif isinstance(seq, bytearray):
        return bytes(seq)
    elif isinstance(seq, memoryview):
        return seq.tobytes()
    elif isinstance(seq, unicode):
        raise TypeError(
            'unicode strings are not supported, please encode to bytes: {!r}'.format(seq))
    else:
        return bytes(bytearray(seq))

LF = to_bytes([10])

class Timeout(object):
    """Abstracción para operaciones de tiempo de espera."""
    if hasattr(time, 'monotonic'):
        TIME = time.monotonic
    else:
        TIME = time.time

    def __init__(self, duration):
        self.is_infinite = (duration is None)
        self.is_non_blocking = (duration == 0)
        self.duration = duration
        if duration is not None:
            self.target_time = self.TIME() + duration
        else:
            self.target_time = None

    def expired(self):
        return self.target_time is not None and self.time_left() <= 0

    def time_left(self):
        if self.is_non_blocking:
            return 0
        elif self.is_infinite:
            return None
        else:
            delta = self.target_time - self.TIME()
            if delta > self.duration:
                self.target_time = self.TIME() + self.duration
                return self.duration
            else:
                return max(0, delta)

class BaseSerialWorker(QObject):
    """Clase base para workers que leen de puertos serie."""
    finished = pyqtSignal()
    # La señal intReady se define en las subclases porque los tipos pueden diferir (dict vs str)

    def __init__(self):
        super(BaseSerialWorker, self).__init__()
        self.working = True
        self.ser = None

    def work(self):
        """Bucle principal de trabajo. Las subclases deben implementar _read_cycle."""
        if self.ser and hasattr(self.ser, 'is_open') and not self.ser.is_open:
            try:
                self.ser.open()
            except Exception as e:
                logging.critical(f"Error al abrir puerto en worker: {e}")
                self.working = False

        while self.working:
            try:
                self._read_cycle()
            except TimeoutError:
                self._handle_timeout()
            except serial.SerialException as e:
                self._handle_serial_error(e)
            except Exception as e:
                logging.error(f"Error inesperado en worker: {e}")
            
            time.sleep(0.05)
        
        if self.ser and hasattr(self.ser, 'close'):
             self.ser.close()
        self.finished.emit()

    def _read_cycle(self):
        raise NotImplementedError

    def _handle_timeout(self):
        # La implementación por defecto registra una advertencia
        if self.ser and hasattr(self.ser, 'port'):
             logging.warning(f"Timeout al intentar leer el puerto serie {str(self.ser.port)}.")
        else:
             logging.warning("Timeout en puerto serie.")

    def _handle_serial_error(self, e):
        if self.ser and hasattr(self.ser, 'port'):
             logging.critical(f'Ocurrio un error al intentar de abrir el puerto serie seleccionado. Puerto {self.ser.port}: {e}')
        # self.working = False # Opcional: ¿detener en error crítico? El código original a veces se detiene, a veces no.

    def Read_until(self, expected=LF, size=None):
        """
        Lee hasta encontrar una secuencia esperada ('\\n' por defecto), se supere el tamaño
        o hasta que ocurra un timeout.
        """
        lenterm = len(expected)
        line = bytearray()
        timeout = Timeout(self.ser.timeout)
        while True:
            if hasattr(self.ser, 'is_open') and not self.ser.is_open:
                self.ser.open()
            c = self.ser.read(1)
            if c:
                line += c
                if line[-lenterm:] == expected:
                    break
                if size is not None and len(line) >= size:
                    break
            else:
                raise TimeoutError
            if timeout.expired():
                break
        return bytes(line)

class NMEA_Worker(BaseSerialWorker):
    intReady = pyqtSignal(dict)

    def __init__(self, ser):
        super(NMEA_Worker, self).__init__()
        # La clase RMC maneja la conexión serial internamente o la envuelve
        self.ser = RMC(port=ser.port, BR=ser.baudrate, timeout=2)
        self.line = {
            'latD': 'NaN', 'lonD': 'NaN', 'lat': 'NaN', 'lon': 'NaN',
            'hora': 'NaN', 'fecha': 'NaN', 'Velocidad': 'NaN',
        }

    def _read_cycle(self):
        self.ser.Read()
        line = {
            'latD': self.ser.Get_Latitud_Grados(),
            'lonD': self.ser.Get_Longitud_Grados(),
            'lat': self.ser.Get_Lat_GradosMinutos(),
            'lon': self.ser.Get_Lon_GradosMinutos(),
            'hora': self.ser.Get_Time(),
            'fecha': self.ser.Get_Date(sep=''),
            'Velocidad': self.ser.Get_Speed()
        }
        self.line = line
        self.intReady.emit(line)

    def _handle_timeout(self):
        super()._handle_timeout()
        line = {
            'latD': 'NaN', 'lonD': 'NaN', 'lat': 'NaN', 'lon': 'NaN',
            'hora': 'NaN', 'fecha': 'NaN', 'Velocidad': 'NaN',
        }
        self.line = line
        self.intReady.emit(line)

class DBS_Worker(BaseSerialWorker):
    intReady = pyqtSignal(str)

    def __init__(self, ser):
        super(DBS_Worker, self).__init__()
        self.ser = DBS(port=ser.port, BR=ser.baudrate, timeout=3)
        self.line = 'NaN'

    def _read_cycle(self):
        self.ser.Read()
        line = self.ser.Get_Z_Metros()
        self.line = line
        self.intReady.emit(line)

    def _handle_timeout(self):
        super()._handle_timeout()
        self.intReady.emit("NaN")

class ConfiguredSerialWorker(BaseSerialWorker):
    """Worker que necesita acceder a la configuración global (Cfg)."""
    def __init__(self, ser, section_name):
        super(ConfiguredSerialWorker, self).__init__()
        # Recrear el objeto serial con reglas de timeout específicas si es necesario, 
        # o usar el que se pasó. Punto clave: Main.pyw pasó un objeto serial.
        # El código original re-instanciaba la lógica serial dentro de __init__ a veces.
        # CTD: serial.Serial(..., timeout=5)
        # TSG: serial.Serial(..., timeout=ser.timeout)
        
        self.ser = serial.Serial(port=ser.port, baudrate=ser.baudrate, timeout=ser.timeout)
            
        _Config = Cfg()
        self.cfg = _Config.GetCfg()
        self.section_name = section_name
        self.data_format()

    def data_format(self):
        self.format = dict()
        for i, k in enumerate(self.cfg['Configuracion'][self.section_name]['filas']):
            self.format[i] = k.split()[0]

    def _read_cycle(self):
        dato = dict()
        self.ser.reset_input_buffer()
        self.ser.reset_input_buffer() # Doble reinicio en el original
        
        line = self.Read_until().decode('ASCII')
        line = line.split()
        for i, k in enumerate(line):
            dato[self.format[i]] = k
        self.intReady.emit(dato)

    def _handle_timeout(self):
        # CTD se cierra en timeout, TSG no explícitamente en el bloque catch pero continúa el bucle.
        # CTD Original: self.ser.close(), log, emit NaN, emit format con NaNs
        # TSG Original: log, emit format con NaNs
        
        # Estandarizamos a registrar log y emitir NaNs
        super()._handle_timeout()
        
        if self.section_name == 'CTD':
             self.ser.close()
             self.intReady.emit("NaN")
        
        # Emitir todas las claves como NaN
        nan_dict = dict()
        # Note: original code iterated over cfg keys to set them to NaN
        # for i, k in enumerate(self.cfg['Configuracion'][self.section_name]['filas']):
        #    self.format[k] = 'NaN'
        # This looks like it was modifying self.format (the dict needed for mapping indices) 
        # to have keys as values? Original code: self.format[k] = 'NaN'. 
        # Wait, self.format is {index: name}. 
        # Original code line 291: self.format[k] = 'NaN'. k is the key from config?
        # Actually line 292: self.format[k] = 'NaN'.
        # self.intReady.emit(self.format)
        # This seems buggy in original or I misunderstood. simpler to emit a dict with all keys nan.
        
        # Intentemos replicar la emisión "segura" de NaN
        # Necesitamos emitir un diccionario donde las claves sean los nombres de las variables
        output = {}
        # Releer las claves correctamente
        for raw_k in self.cfg['Configuracion'][self.section_name]['filas']:
             key_name = raw_k.split()[0]
             output[key_name] = 'NaN'
        
        self.intReady.emit(output)

class CTD_Worker(ConfiguredSerialWorker):
    intReady = pyqtSignal(dict)
    def __init__(self, ser):
         # Sobreescritura de timeout específica para CTD
         ser.timeout = 5
         super(CTD_Worker, self).__init__(ser, 'CTD')

class TSG_Worker(ConfiguredSerialWorker):
    intReady = pyqtSignal(dict)
    def __init__(self, ser):
         # Específico para TSG
         super(TSG_Worker, self).__init__(ser, 'TSG')
