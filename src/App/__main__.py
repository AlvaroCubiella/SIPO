# -------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      ALVAR
#
# Created:     19/07/2020
# Copyright:   (c) ALVAR 2020
# Licence:     <your licence>
# -------------------------------------------------------------------------------

import sys
import os
import glob
import logging
import datetime
import time
import subprocess
from threading import Thread
import re
import json
import serial
import shutil

from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QAction, QInputDialog, QLineEdit, QFileDialog, QDialog
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Importo modulos de la App
from app.RMC import RMC
from app import DBS
from app.cfg import Cfg
from app import utils
from app import Key_Reg

# Importo las GUI de la App
from gui.Main_ui import *
from gui.Frm_Inicio_ui import *
from gui.Frm_Note_ui import *

# Importo los modulos para controlar las GUI de la App
from app import Frm_Config
from app import Frm_Inicio
from app import Frm_Note

from decouple import config
from dotenv import load_dotenv

# Variable global
_Config = dict()

__autor__ = 'Alvaro Cubiella'
__version__ = 'V1.01'

# Gerarquia de los mensajes
# DEBUG = 10
# INFO = 20
# Warning = 30
# ERROR = 40
# CRITICAL = 50

# Establezco a partir de quenivel se imprimen los mensajes y formato
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s -  %(processName)s - %(levelname)s - %(message)s",
                    filename='App.log',
                    filemode='a')

try:
    unicode
except (NameError, AttributeError):
    unicode = str       # for Python 3, pylint: disable=redefined-builtin,invalid-name

# all Python versions prior 3.x convert ``str([17])`` to '[17]' instead of '\x11'
# so a simple ``bytes(sequence)`` doesn't work for all versions


def to_bytes(seq):
    """convert a sequence to a bytes type"""
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
        # handle list of integers and bytes (one or more items) for Python 2 and 3
        return bytes(bytearray(seq))


LF = to_bytes([10])


class Timeout(object):
    """\
    Abstraction for timeout operations. Using time.monotonic() if available
    or time.time() in all other cases.

    The class can also be initialized with 0 or None, in order to support
    non-blocking and fully blocking I/O operations. The attributes
    is_non_blocking and is_infinite are set accordingly.
    """
    if hasattr(time, 'monotonic'):
        # Timeout implementation with time.monotonic(). This function is only
        # supported by Python 3.3 and above. It returns a time in seconds
        # (float) just as time.time(), but is not affected by system clock
        # adjustments.
        TIME = time.monotonic
    else:
        # Timeout implementation with time.time(). This is compatible with all
        # Python versions but has issues if the clock is adjusted while the
        # timeout is running.
        TIME = time.time

    def __init__(self, duration):
        """Initialize a timeout with given duration"""
        self.is_infinite = (duration is None)
        self.is_non_blocking = (duration == 0)
        self.duration = duration
        if duration is not None:
            self.target_time = self.TIME() + duration
        else:
            self.target_time = None

    def expired(self):
        """Return a boolean, telling if the timeout has expired"""
        return self.target_time is not None and self.time_left() <= 0

    def time_left(self):
        """Return how many seconds are left until the timeout expires"""
        if self.is_non_blocking:
            return 0
        elif self.is_infinite:
            return None
        else:
            delta = self.target_time - self.TIME()
            if delta > self.duration:
                # clock jumped, recalculate
                self.target_time = self.TIME() + self.duration
                return self.duration
            else:
                return max(0, delta)

    def restart(self, duration):
        """\
        Restart a timeout, only supported if a timeout was already set up
        before.
        """
        self.duration = duration
        self.target_time = self.TIME() + duration

#########################################################################################
# Hilo para leer la señal NMEA
#########################################################################################


class NMEA_Ext(QObject):
    finished = pyqtSignal()
    # le digo que la señal a enviar es un diccionario
    intReady = pyqtSignal(dict)

    @pyqtSlot()
    def __init__(self, ser):
        super(NMEA_Ext, self).__init__()
        self.working = True
        self.ser = RMC(port=ser.port, BR=ser.baudrate, timeout=5)

    def work(self):
        while self.working:
            try:
                # line=''
                line = self.ser.Read()
                line = {'latD': self.ser.Get_Latitud_Grados(),
                        'lonD': self.ser.Get_Longitud_Grados(),
                        'lat': self.ser.Get_Lat_GradosMinutos(),
                        'lon': self.ser.Get_Lon_GradosMinutos(),
                        'hora': self.ser.Get_Time(),
                        'fecha': self.ser.Get_Date(sep=''),
                        'Velocidad': self.ser.Get_Speed()
                        }
                self.line = line
                self.intReady.emit(line)
            except TimeoutError:
                print('timeout')
                self.intReady.emit(None)
            time.sleep(0.05)
        self.finished.emit()

#########################################################################################
# Hilo para leer la señal CTD
#########################################################################################


class CTD_Thread(QObject):
    finished = pyqtSignal()
    # le digo que la señal a enviar es un diccionario
    intReady = pyqtSignal(dict)

    @pyqtSlot()
    def __init__(self, ser):
        super(CTD_Thread, self).__init__()
        self.working = True
        self.ser = serial.Serial(
            port=ser.port, baudrate=ser.baudrate, timeout=5)
        _Config = Cfg()
        self.cfg = _Config.GetCfg()
        self.data_format()

    def data_format(self):
        # Armo un diccionario con las variables en el orden correspondiente
        self.format = dict()
        for i, k in enumerate(self.cfg['Configuracion']['CTD']['filas']):
            self.format[i] = k.split()[0]

    def Read_until(self, expected=LF, size=None):
        """\
        Read until an expected sequence is found ('\n' by default), the size
        is exceeded or until timeout occurs.
        """
        lenterm = len(expected)
        line = bytearray()
        timeout = Timeout(self.ser.timeout)
        while True:
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

    def work(self):
        if not self.ser.is_open:
            self.ser.open()
        while self.working:
            dato = dict()
            try:
                self.ser.reset_input_buffer()  # Borro buffer del puerto serie
                self.ser.reset_input_buffer()  # Borro buffer del puerto serie
                # dato = comm_NMEA.read_until().decode('ASCII')
                line = self.Read_until().decode('ASCII')
                line = line.split()
                for i, k in enumerate(line):
                    dato[self.format[i]] = k
                self.intReady.emit(dato)
            except TimeoutError:
                self.ser.close()
                for i, k in enumerate(self.cfg['Configuracion']['CTD']['filas']):
                    self.format[k] = 'NaN'
                self.intReady.emit(self.format)
            except serial.SerialException:
                # -- Error al abrir el puerto serie
                print('Ocurrio un error al intentar de abrir el puerto serie seleccionado.\r\n \
                        No se pudo completar la operacion. Puerto %s' % (str(self.ser.port)))
                self.working = False
            time.sleep(0.05)
        self.ser.close()
        self.finished.emit()

#########################################################################################
# Hilo para leer la señal TSG
#########################################################################################


class TSG_Thread(QObject):
    finished = pyqtSignal()
    # le digo que la señal a enviar es un diccionario
    intReady = pyqtSignal(dict)

    @pyqtSlot()
    def __init__(self, ser):
        super(TSG_Thread, self).__init__()
        self.working = True
        self.ser = serial.Serial(
            port=ser.port, baudrate=ser.baudrate, timeout=ser.timeout)
        _Config = Cfg()
        self.cfg = _Config.GetCfg()
        self.data_format()

    def data_format(self):
        # Armo un diccionario con las variables en el orden correspondiente
        self.format = dict()
        for i, k in enumerate(self.cfg['Configuracion']['TSG']['filas']):
            self.format[i] = k.split()[0]

    def Read_until(self, expected=LF, size=None):
        """\
        Read until an expected sequence is found ('\n' by default), the size
        is exceeded or until timeout occurs.
        """
        lenterm = len(expected)
        line = bytearray()
        timeout = Timeout(self.ser.timeout)
        while True:
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

    def work(self):
        if not self.ser.is_open:
            self.ser.open()
        while self.working:
            dato = dict()
            try:
                self.ser.reset_input_buffer()  # Borro buffer del puerto serie
                self.ser.reset_input_buffer()  # Borro buffer del puerto serie
                # dato = comm_NMEA.read_until().decode('ASCII')
                line = self.Read_until().decode('ASCII')
                line = line.split()
                for i, k in enumerate(line):
                    dato[self.format[i]] = k
                self.intReady.emit(dato)
            except TimeoutError:
                print('TIMEOUT')
                for i, k in enumerate(self.cfg['Configuracion']['TSG']['filas']):
                    self.format[k] = 'NaN'
                self.intReady.emit(self.format)
            except serial.SerialException:
                # -- Error al abrir el puerto serie
                print('Ocurrio un error al intentar de abrir el puerto serie seleccionado.\r\n \
                        No se pudo completar la operacion. Puerto %s' % (str(self.ser.port)))
                # self.working = False
            time.sleep(0.05)
        self.ser.close()
        self.finished.emit()


###########################################################################
# Hilo Batimetria
###########################################################################
class Hilo_DBS(Thread):
    def __init__(self, MainWindow, Menu):
        Thread.__init__(self)
        self.MainWindow = MainWindow
        self.port = Menu['Configuracion']['Batimetria']['Port']
        self.depth = DBS.DBS(self.port)
        self.stop = False

    def stop(self):
        self._Thread__stop()

    def run(self):
        while self.MainWindow.hilos:
            #        while (self.MainWindow.btn_inicio.GetLabel() == 'Fin (F1)'):
            self.depth.Read()


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    # Aca heredo la clase de la ventana, si no hay nada simplemente aparece una ventana vacia
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__()
        try:
            self._Config = Cfg()
        except FileNotFoundError:
            Cfg.NuevoConfig()
            self._Config = Cfg()
        # Paso la estructura de datos del archivo Json para agregar mas info.
        self.estructura = kwargs['estructura']
        self.cfg = self._Config.GetCfg()
        # Directorio de trabajo de la campania a partir de las variables de entorno
        self.dir_Camp = os.getenv('OF_BUQUE_NROCAMP')
        # Compruebo si el directorio existe, sino, lo creo completo con la app CLI
        if not (os.path.exists(self.dir_Camp)):
            print(f"Creo el diretorio: {self.dir_Camp}")

        self.W_Dir = f"{self.dir_Camp}{os.sep}Varios{os.sep}Planillas"
        if not (os.path.exists(self.W_Dir)):
            os.makedirs(self.W_Dir)
        self.DEMO = datetime.datetime(2020, 12, 31, 0, 0, 0)
        # QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        # QtGui.QMainWindow.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint |
                            QtCore.Qt.WindowStaysOnTopHint)                            # Pone la ventana en modo persistente
        self.setupUi(self)
        self.setWindowTitle(f"Planilla V.{(__version__)}")
        self.thread = None
        self.worker = None

        # Activo el seguimiento del mouse
#        self.setMouseTracking(True)

        # Configuro opciones de los botones de la barra de menu
        self.btn_Salir.setShortcut('Alt+S')

        # Configuro eventos en los cuadros de texto
        # Se genera al cambiar el contenido del cuadro
        self.txt_EstGral.textChanged.connect(self.chg_txt_EstGral)
        # Se generea el evento cuando pierdo focus o se presiona enter
        self.txt_fTSG.editingFinished.connect(self.chg_txt_fTSG)

        # Configuro eventos de los botones
        self.btn_Inicio.clicked.connect(self.click_btn_Inicio)
        self.btn_Cubierta.clicked.connect(self.click_btn_Cubierta)
        self.btn_Superficie.clicked.connect(self.click_btn_Superficie)
        self.btn_Fondo.clicked.connect(self.click_btn_Fondo)
        self.btn_skipover.clicked.connect(self.getSkipover)

        # Funciones del Menu
        self.btn_Salir.triggered.connect(self.close)
        self.Menu_Config.triggered.connect(self.Frm_Config_load)
        self.Acercade.triggered.connect(self.about)

        self.flag = False

        ports = RMC(port='COM1',
                    BR=4800,
                    sts='RMC',
                    timeout=1,
                    )
        # ports = NMEA.NMEA(timeout = 0.1, sts = self.cbox_NMEAExt_Sentencia.currentText())
        ports.scan_ports()
        self.cfg['list_ports'] = ports.list_ports

        valido, msg = Key_Reg.check()
        if not (valido):
            self.msg_Box(mensaje=f'{msg}\r',
                         titulo='Llave Invalida', icono=QMessageBox.Critical)
            # Queda para una version nueva
            self.lcd_Timer = QTimer(self)
            self.lcd_Timer.timeout.connect(self.showTime)
            self.count = 15
            self.flag = True
            self.lcd_Timer.start(1000)

    def about(self):
        msg = f"Programa desarrollado para uso del INIDEP\rVersion {__version__}\rDesarrollado por: {__autor__}"
        self.msg_Box(mensaje=f'{msg}\r',
                     titulo='Llave Invalida', icono=QMessageBox.information)

    def showTime(self):
        # Corre el programa por X segundos y se cierra automaticamente (para versiones DEMO)
        if self.flag:
            self.count -= 1
            f"Planilla V.{(__version__)}"
            self.setWindowTitle('Planilla V.%s DEMO (%.0f)' %
                                (__version__, self.count))
            # text = str(self.count / 10)
            if self.count < 0:
                sys.exit(0)

    def setAdquisicion(self):
        self.NMEA_Str = {
            'latD': 'NaN',
            'lonD': 'NaN',
            'lat': 'NaN',
            'lon': 'NaN',
            'hora': 'NaN',
            'fecha': 'NaN',
        }
        re_exp_NMEA = ''
        ########################################################################
        # Inicializo las clases de los hilos correspondientes
        ########################################################################
        self.init_NMEA()
        self.init_CTD()
        self.init_TSG()

        # self.btn_Detener.clicked.connect(self.stop_loop)                # stop the loop on the stop button click
        try:
            if self.cfg['Configuracion']['NMEA']['Status'] == '2':
                self.thread_NMEA.start()
            if self.cfg['Configuracion']['CTD']['Status'] == '2':
                self.thread_CTD.start()
            if self.cfg['Configuracion']['TSG']['Status'] == '2':
                self.thread_TSG.start()
        except:
            print('error al iniciar los hilos')

    ########################################################################
    # Inicializo el com del GPS
    ########################################################################
    def init_NMEA(self):
        # Inicializo el com del NMEA
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['NMEA']['Port'],
                                baudrate=self.cfg['Configuracion']['NMEA']['BR'],
                                timeout=self.cfg['Configuracion']['NMEA']['Intervalo'],
                                )
            ser.close()
            self.NMEA = NMEA_Ext(ser)
            self.thread_NMEA = QThread()
            self.NMEA.moveToThread(self.thread_NMEA)
            self.thread_NMEA.started.connect(self.NMEA.work)
            self.NMEA.intReady.connect(self.onIntReadyNMEA)
            self.NMEA.finished.connect(self.loop_finished)
            self.NMEA.finished.connect(self.thread_NMEA.quit)
            self.NMEA.finished.connect(self.NMEA.deleteLater)
            self.thread_NMEA.finished.connect(self.thread_NMEA.deleteLater)

        except IOError:
            # Vuelen boton iniciar y detener a condiciones iniciales
            self.loop_finished()
            self.msg_Box(mensaje='Error al inicializar el puerto seleccionado!!!\r',
                         titulo='I/O Error NMEA', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo del NMEA
    ########################################################################
    def onIntReadyNMEA(self, i):
        self.NMEA_Str = i
        print(f"Cadena de NMEA: {self.NMEA_Str}")
        self.statusBar().showMessage(f"Vel: {self.NMEA_Str['Velocidad']} knt")
    ########################################################################
    # Inicializo el com del CTD
    ########################################################################

    def init_CTD(self):
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['CTD']['Port'],
                                baudrate=self.cfg['Configuracion']['CTD']['BR'],
                                )
            ser.timeout = self.cfg['Configuracion']['CTD']['Intervalo'] + 1
            ser.close()
            # a new worker to perform those tasks
            self.CTD = CTD_Thread(ser)
            # a new thread to run our background tasks in
            self.thread_CTD = QThread()
            # move the worker into the thread, do this first before connecting the signals
            self.CTD.moveToThread(self.thread_CTD)
            # begin our worker object's loop when the thread starts running
            self.thread_CTD.started.connect(self.CTD.work)
            self.CTD.intReady.connect(self.onIntReadyCTD)
            # do something in the gui when the worker loop ends
            self.CTD.finished.connect(self.loop_finished)
            # tell the thread it's time to stop running
            self.CTD.finished.connect(self.thread_CTD.quit)
            # have worker mark itself for deletion
            self.CTD.finished.connect(self.CTD.deleteLater)
            # have thread mark itself for deletion
            self.thread_CTD.finished.connect(self.thread_CTD.deleteLater)
        except IOError:
            # Vuelen boton iniciar y detener a condiciones iniciales
            self.loop_finished()
            self.msg_Box(mensaje='Error al inicializar el puerto seleccionado!!!\r',
                         titulo='I/O Error CTD', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo del CTD
    ########################################################################
    def onIntReadyCTD(self, i):
        self.CTD_str = i
        try:
            if self.fire_bott < str(int(self.CTD_str['Bot'])):
                self.fire_bott = str(int(self.CTD_str['Bot']))
                self.W_Bott()
        except KeyError:
            print('No se encontro variable de botella para el CTD')

        print(f"Cadena de CTD: {self.CTD_str}")

    ########################################################################
    # Inicializo el com del TSG
    ########################################################################
    def init_TSG(self):
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['TSG']['Port'],
                                baudrate=self.cfg['Configuracion']['TSG']['BR'],
                                )
            ser.timeout = self.cfg['Configuracion']['TSG']['Intervalo'] + 1
            ser.close()
            # a new worker to perform those tasks
            self.TSG = TSG_Thread(ser)
            # a new thread to run our background tasks in
            self.thread_TSG = QThread()
            # move the worker into the thread, do this first before connecting the signals
            self.TSG.moveToThread(self.thread_TSG)
            # begin our worker object's loop when the thread starts running
            self.thread_TSG.started.connect(self.TSG.work)
            self.TSG.intReady.connect(self.onIntReadyTSG)
            # do something in the gui when the worker loop ends
            self.TSG.finished.connect(self.loop_finished)
            # tell the thread it's time to stop running
            self.TSG.finished.connect(self.thread_TSG.quit)
            # have worker mark itself for deletion
            self.TSG.finished.connect(self.TSG.deleteLater)
            # have thread mark itself for deletion
            self.thread_TSG.finished.connect(self.thread_TSG.deleteLater)
        except IOError:
            # Vuelen boton iniciar y detener a condiciones iniciales
            self.loop_finished()
            self.msg_Box(mensaje='Error al inicializar el puerto seleccionado!!!\r',
                         titulo='I/O Error TSG', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo del TSG
    ########################################################################
    def onIntReadyTSG(self, i):
        self.TSG_str = i
        print(f"Cadena de TSG: {self.TSG_str}")

    def loop_finished(self):
        self.flag = False

    # Evento cambio de valor en cuadro de textos
    def chg_txt_EstGral(self, event):
        cadena = self.txt_EstGral.text()
        if not (event.isnumeric()):
            cadena = cadena[:-1]
        self.txt_EstGral.setText(cadena)
        self.act_btn_Inicio()

    def chg_txt_fTSG(self):
        self.txt_fTSG.setText(self.txt_fTSG.text().upper())
        self.act_btn_Inicio()

    # Actualizacion estado de botones
    def act_btn_Inicio(self):
        if (self.txt_EstGral.text() != '' and self.txt_fTSG.text() != ''):
            self.btn_Inicio.setEnabled(True)
        else:
            self.btn_Inicio.setEnabled(False)

    # Acciones de botones
    def click_btn_Inicio(self):
        # Recargo el cfg antes de iniciar por si se realizaro modificaciones en el archivode configuracion
        self._Config = Cfg()
        self.cfg = self._Config.GetCfg()
        self.txt_EstGral.setText(self.txt_EstGral.text().zfill(4))
        self.txt_fTSG.setText(self.txt_fTSG.text().upper())
        path = os.getenv('OF_BUQUE_NROCAMP')       # Ruta de la campaña activa
        self.f_json = windows._selected_file
        file_json = os.path.basename(self.f_json)
        self.file_json = os.path.join(path, file_json)
        if self.btn_Inicio.text() == 'Inicio':
            if self.txt_EstGral.text() in self.estructura['Estaciones']:
                reply = QMessageBox.question(self, 'Estación Existente', 'El número de estación ya existe. Desea Continuar? ',
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            self.btn_Inicio.setText('Fin')
            self.btn_Cubierta.setEnabled(True)
            self.txt_EstGral.setEnabled(False)
            self.txt_fTSG.setEnabled(False)
            self.Menu_Config.setEnabled(False)
            self.fdo = 0

            ########################################################################
            # Cargo orden variables
            ########################################################################
            self.fire_bott = '0'
            # TSG
            # Inicializo variables
            self.TSG_str = {
                'scan': 'NaN',
                'lat': 'NaN',
                'lon': 'NaN',
                'sal': 'NaN',
                'temp': 'NaN',
                'cond': 'NaN',
                'temp38': 'NaN',
            }

            Nom_var = self.cfg['Configuracion']['TSG']['filas']
            for i in range(0, len(Nom_var)):
                if 'Scan' in Nom_var[i] or 'scan' in Nom_var[i]:
                    self.TSG_str['scan'] = i
                elif 'Lon' in Nom_var[i] or 'lon' in Nom_var[i]:
                    self.TSG_str['lon'] = i
                elif 'Lat' in Nom_var[i] or 'lat' in Nom_var[i]:
                    self.TSG_str['lat'] = i
                elif ('Temp' in Nom_var[i] or 'temp' in Nom_var[i]) and not ('SBE38' in Nom_var[i] or 'sbe38' in Nom_var[i]):
                    self.TSG_str['temp'] = i
                elif 'Cond' in Nom_var[i] or 'cond' in Nom_var[i]:
                    self.TSG_str['cond'] = i
                elif 'Sal' in Nom_var[i] or 'sal' in Nom_var[i]:
                    self.TSG_str['sal'] = i
                elif ('Temp' in Nom_var[i] or 'temp' in Nom_var[i]) and ('SBE38' in Nom_var[i] or 'sbe38' in Nom_var[i]):
                    self.TSG_str['temp38'] = i

            # CTD
            # Inicializo variables
            self.CTD_str = {
                'cond': 'NaN',
                'press': 'NaN',
                'sal': 'NaN',
                'scan': 'NaN',
                'temp': 'NaN',
                'bot': 'NaN',
            }

            Nom_var = self.cfg['Configuracion']['CTD']['filas']
            for i in range(0, len(Nom_var)):
                if 'Scan' in Nom_var[i] or 'scan' in Nom_var[i]:
                    self.CTD_str['scan'] = i
                elif 'Pres' in Nom_var[i] or 'pres' in Nom_var[i]:
                    self.CTD_str['press'] = i
                elif ('Temp' in Nom_var[i] or 'temp' in Nom_var[i]) and not ('SBE38' in Nom_var[i] or 'sbe38' in Nom_var[i]):
                    self.CTD_str['temp'] = i
                elif 'Cond' in Nom_var[i] or 'cond' in Nom_var[i]:
                    self.CTD_str['cond'] = i
                elif 'Sal' in Nom_var[i] or 'sal' in Nom_var[i]:
                    self.CTD_str['sal'] = i
                elif ('Bot' in Nom_var[i] or 'bot' in Nom_var[i]):
                    self.CTD_str['bot'] = i

            self.BAT_str = {

            }

            self.setAdquisicion()
            self.statusAdq = True
            # Contadores de evento para luego armar la planilla de la estacion
            self.countCub = 0
            self.countSup = 0
            self.countFdo = 0
            self.estacion = dict()
            estacion = utils.Estacion()
            estacion['NroEstacion'] = self.txt_EstGral.text()
            self.estacion[self.txt_EstGral.text()] = estacion
            time.sleep(1)
            self.W_Pos()
        else:
            self.btn_Inicio.setText('Inicio')
            self.Menu_Config.setEnabled(True)
            self.btn_Cubierta.setEnabled(False)
            self.btn_Superficie.setEnabled(False)
            self.btn_skipover.setEnabled(False)
            self.btn_Fondo.setEnabled(False)
            self.txt_EstGral.setEnabled(True)
            self.txt_fTSG.setEnabled(True)
            self.statusAdq = False
            self.W_Pos()
            self.stop_loop()

            reply = QMessageBox.question(self, 'Agregar comentarios', 'Quiere agragar algun comentario de la estación? ',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    self.Frm_Note_load()
                    print('aca')
                except NameError:
                    pass
            else:
                print('NO')

    def click_btn_Cubierta(self):
        self.W_CTD(pos=self.countCub, loc='Cubierta')
        self.countCub += 1
        if self.fdo == 0:
            self.btn_Cubierta.setEnabled(False)
            self.btn_Superficie.setEnabled(True)
            self.btn_skipover.setEnabled(True)
        else:
            self.btn_Cubierta.setEnabled(False)

    def click_btn_Superficie(self):
        self.W_TSGvsCTD()
        if self.fdo == 0:
            self.btn_Superficie.setEnabled(False)
            # self.btn_skipover.setEnabled(False)
            self.btn_Fondo.setEnabled(True)
        else:
            self.btn_Superficie.setEnabled(False)
            self.btn_Cubierta.setEnabled(True)

    def click_btn_Fondo(self):
        self.W_CTD(pos=self.countFdo, loc='Fondo')
        self.countFdo += 1
        self.btn_Fondo.setEnabled(False)
        self.btn_Superficie.setEnabled(True)
        self.fdo = 1

    def getSkipover(self):
        self.estacion[self.txt_EstGral.text(
        )]['Skipover'] = self.CTD_str['Scan']
        self.save_json()
        self.btn_skipover.setEnabled(False)

    def click_btn_Exportar(self):
        import openpyxl
        j = 0
        k = 0
        self.txt_EstGral.setText(self.txt_EstGral.text().zfill(4))
        xls = openpyxl.load_workbook('Planilla_V1.xlsx')
        planilla = xls.get_sheet_by_name('Hoja1')
        R_File = open(self.W_Dir + os.sep + 'Est%s.txt' %
                      self.txt_EstGral.text().zfill(4), "r")
        dato = R_File.readlines()
        R_File.close()
        planilla['A2'] = self.cfg['Campaña']['SiglasBuque'].upper(
        )+self.cfg['Campaña']['Año']+str(int(self.cfg['Campaña']['NroCampaña'])).zfill(2)
        flag_nmea = True
        flag_cub = True
        flag_sup = True
        for i in dato:
            i = i.replace('\n', '')
            i = i.split(',')
            if 'NMEA' in i:
                if flag_nmea:
                    planilla['F2'] = i[1]
                    planilla['A6'] = '%.4f' % (float(i[2]))
                    planilla['E6'] = '%.4f' % (float(i[3]))
                    planilla['J2'] = i[4]
                    planilla['O2'] = i[5]
                    if not (i[6] == 'NaN'):
                        planilla['Q6'] = str(round(float(i[6])))
                    else:
                        planilla['Q6'] = i[6]
                    flag_nmea = False
                else:
                    planilla['I6'] = '%.4f' % (float(i[2]))
                    planilla['M6'] = '%.4f' % (float(i[3]))
                    planilla['T2'] = i[4]
                    planilla['Y2'] = i[5]
                    if not (i[6] == 'NaN'):
                        planilla['S6'] = str(round(float(i[6])))
                    else:
                        planilla['S6'] = 'NaN'
            elif 'Cub' in i:
                if flag_cub:
                    planilla['E9'] = i[2][0:5]
                    planilla['H9'] = '%.1f' % (float(i[4]))
                    planilla['L9'] = '%.3f' % (float(i[5]))
                    planilla['P9'] = '%.3f' % (float(i[6]))
                    planilla['S9'] = '%.3f' % (float(i[7]))
                    flag_cub = False
                else:
                    planilla['E13'] = i[2][0:5]
                    planilla['H13'] = '%.1f' % (float(i[4]))
                    planilla['L13'] = '%.3f' % (float(i[5]))
                    planilla['P13'] = '%.3f' % (float(i[6]))
                    planilla['S13'] = '%.3f' % (float(i[7]))

            elif 'Sup' in i:
                if flag_sup:
                    planilla['E10'] = i[2][0:5]
                    planilla['H10'] = '%.1f' % (float(i[4]))
                    planilla['L10'] = '%.3f' % (float(i[5]))
                    planilla['P10'] = '%.3f' % (float(i[6]))
                    planilla['S10'] = '%.3f' % (float(i[7]))
                    planilla['W10'] = '%.3f' % (float(i[9]))
                    planilla['Z10'] = '%.3f' % (float(i[10]))
                    planilla['AC10'] = '%.0f' % (float(i[8]))
                    planilla['AG10'] = i[11]
                    # Delta Temp y Sal
                    planilla['E27'] = '%.3f' % (float(i[12]))
                    planilla['E28'] = '%.4f' % (float(i[13]))
                    flag_sup = False
                else:
                    planilla['E12'] = i[2][0:5]
                    planilla['H12'] = '%.1f' % (float(i[4]))
                    planilla['L12'] = '%.3f' % (float(i[5]))
                    planilla['P12'] = '%.3f' % (float(i[6]))
                    planilla['S12'] = '%.3f' % (float(i[7]))
                    planilla['W12'] = '%.3f' % (float(i[9]))
                    planilla['Z12'] = '%.3f' % (float(i[10]))
                    planilla['AC12'] = '%.0f' % (float(i[8]))
                    planilla['AG12'] = i[11]

            elif 'Fdo' in i:
                planilla['E11'] = i[2][0:5]
                planilla['H11'] = '%.1f' % (float(i[4]))
                planilla['L11'] = '%.3f' % (float(i[5]))
                planilla['P11'] = '%.3f' % (float(i[6]))
                planilla['S11'] = '%.3f' % (float(i[7]))
            elif 'Bott' in i:
                bot = int(i[-1])
                fila = 16 + bot
                col = ['B', 'E', 'H', 'M']
                if fila <= 22:
                    planilla['B' + str(fila)] = i[2][0:5]
                    planilla['E' + str(fila)] = '%.1f' % (float(i[4]))
                    planilla['H' + str(fila)] = '%.3f' % (float(i[5]))
                    planilla['M' + str(fila)] = '%.3f' % (float(i[6]))
                else:
                    fila = 10 + bot
                    planilla['T' + str(fila)] = i[2][0:5]
                    planilla['W' + str(fila)] = '%.1f' % (float(i[4]))
                    planilla['Z' + str(fila)] = '%.3f' % (float(i[5]))
                    planilla['AE' + str(fila)] = '%.3f' % (float(i[6]))
        xls.save(self.W_Dir + os.sep + '%s.xlsx' %
                 self.txt_EstGral.text().zfill(4))

    # Abro el formulario de configuracion
    def Frm_Config_load(self, event):
        self.ventana = Frm_Config.Frm_Config(self)
        self.ventana.show()

    def Frm_Note_load(self):
        self.win_note = Frm_Note.Frm_Note(self)
        self.win_note.lbl_Titulo.setText(
            f"Estación General {self.txt_EstGral.text()}")
        self.win_note.exec_()
        self.estacion[self.txt_EstGral.text(
        )]['Comentarios'] = self.win_note.comentario
        self.save_json()

    ########################################################################
    # Finalizo el programa
    ########################################################################
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Salir', 'Realmente desea salir de la aplicación? ',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                pass
            except NameError:
                pass
            finally:
                event.accept()
        else:
            event.ignore()

    ########################################################################
    # Detengo el trabajo de los hilos
    ########################################################################
    def stop_loop(self):
        self.NMEA.working = False
        self.CTD.working = False
        self.TSG.working = False

    ###########################################################################
    # Guardo archivo json
    ###########################################################################
    def save_json(self):

        self.estructura['Estaciones'].update(self.estacion)
        with open(self.file_json, 'w+') as archivo:
            json.dump(self.estructura, archivo, indent=4)

    ###########################################################################
    # Eventos de Adquisicion
    ###########################################################################
    def W_Pos(self):
        if self.statusAdq:
            # Se es vardadero esta adquiriendo. Modifico las variables iniciales
            self.estacion[self.txt_EstGral.text(
            )]['Posicion']['Inicio']['Latitud'] = self.NMEA.line['latD']
            self.estacion[self.txt_EstGral.text(
            )]['Posicion']['Inicio']['Longitud'] = self.NMEA.line['lonD']
            self.estacion[self.txt_EstGral.text(
            )]['FechaHora']['Inicio']['HoraGMT'] = self.NMEA.line['hora']
            self.estacion[self.txt_EstGral.text(
            )]['FechaHora']['Inicio']['FechaGMT'] = self.NMEA.line['fecha']
            self.estacion[self.txt_EstGral.text()]['Batimetria']['Inicio'] = 1
        else:
            # Deje de adquirir. Modifico las variables finales
            self.estacion[self.txt_EstGral.text(
            )]['Posicion']['Fin']['Latitud'] = self.NMEA_Str['latD']
            self.estacion[self.txt_EstGral.text(
            )]['Posicion']['Fin']['Longitud'] = self.NMEA_Str['lonD']
            self.estacion[self.txt_EstGral.text(
            )]['FechaHora']['Fin']['HoraGMT'] = self.NMEA_Str['hora']
            self.estacion[self.txt_EstGral.text(
            )]['FechaHora']['Fin']['FechaGMT'] = self.NMEA_Str['fecha']
            self.estacion[self.txt_EstGral.text()]['Batimetria']['Fin'] = 10
        self.save_json()

    def W_Bott(self):
        try:
            self.estacion[self.txt_EstGral.text(
            )]['Botellas'][self.CTD_str['Bot']] = self.CTD_str
        except:
            pass
        self.save_json()

    def W_CTD(self, pos, loc):
        # pos se refiere al contador del disparador correspondiente. Si es de cub o fdo
        # loc se refiere a si es cubierta o fondo
        self.estacion[self.txt_EstGral.text()][loc][str(pos)] = self.CTD_str
        self.save_json()

    def W_TSGvsCTD(self):
        CTD = self.CTD_str
        TSG = self.TSG_str
        delta_T = str(float(TSG['Temperature']) - float(CTD['Temp']))
        delta_S = str(float(TSG['Salinity']) - float(CTD['Sal']))
        self.estacion[self.txt_EstGral.text(
        )]['TSG_file'] = self.txt_fTSG.text()
        self.estacion[self.txt_EstGral.text()]['Superficie'][str(self.countSup)] = {
            'Hora': self.NMEA_Str['hora'],
            'CTD': CTD,
            'TSG': TSG,
            'deltaT': delta_T,
            'deltaS': delta_S,
        }
        self.countSup += 1
        self.save_json()

    def expira(self):
        if self.cfg['Configuracion']['NMEA']['Status'] != '2':
            print('salida 1')
            exit()
        fecha = self.NMEA_Str['fecha']
        delta = self.DEMO - fecha
        if delta.days < 0:
            print('salida 2')
            exit()
        else:
            return

    ########################################################################
    # Muestro mensaje emergente
    ########################################################################
    def msg_Box(self, mensaje='', titulo='', icono=QMessageBox.Information):
        msgBox = QMessageBox()
        msgBox.setIcon(icono)
        msgBox.setText(mensaje)
        msgBox.setWindowTitle(titulo)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()


class env():

    def __init__(self):
        self.env = 'siavo.env'
        self.paths = os.getcwd()+os.sep+self.env
        # self.encoding="ISO-8859-1"
        self.encoding = "utf-8"
    ##############################################################################
    ## Corroboro estructura de archivos de configuracion y variables de entorno ##
    ##############################################################################

    def load_env(self):
        # Compruebo si el archivo siavo.env exite, sino lo creo

        if not os.path.exists(os.path.join(os.getcwd(), self.env)):
            powershell_command = f"{os.getcwd()}{os.sep}SIAVO_Cfg.exe --CreateFile {self.env}"
            result = subprocess.run(
                ["powershell", "-Command", powershell_command], capture_output=True, text=True, shell=True)
            if result.stderr != '':
                logging.critical(f"No se ah creado el archivo {self.env}")
                sys.exit(0)
            else:
                logging.info(f"El archivo {self.env} ah sido creado.")
                # Como es un archivo nuevo, cambio el root a C:\\Siavo_Estructura
                destino = 'C:\\Siavo_Estructura'
                cmd = [
                    f"{os.getcwd()}{os.sep}SIAVO_Cfg.exe -f {self.env} --edit OF_DATA_ROOT {destino}"
                ]
                for i in cmd:
                    result = subprocess.run(
                        ["powershell", "-Command", i], capture_output=True, text=True, shell=True)

        # A partir del archivo env compruebo si la estructura de carpetas existe, sino, la creo
        # Creo la estructura de datos a partir del archivo env"
        powershell_command = f"{os.getcwd()}{os.sep}SIAVO_Cfg.exe -f {self.env} --mkroot -e"
        result = subprocess.run(
            ["powershell", "-Command", powershell_command], capture_output=True, text=True, shell=True)

    # Creo la estructura de carpeta root a partir del archivo siavo.env
    def mkroot(self):
        self.__crear_estructura()

    # Creo la estructura de carpeta de la campaña a partir del archivo siavo.env
    def mkcamp(self, f_json):
        self.f_json = f_json
        estructura_json = self.__CrearCamp()
        return estructura_json

    def open_env(self):
        # Leo el archivo .env
        with open(self.env, 'r') as f:
            lines = f.readlines()
        return lines

    def __crear_estructura(self):
        try:
            lines = self.open_env()
            env_lines = dict()
            flag = False
            for i, linea in enumerate(lines):
                if not linea.startswith(f"#"):
                    # Limpio y acondiciono la linea, luego la cargo en un diccionario.
                    key, item = linea.rsplit()[0].replace('\n', '').split('=')
                    env_lines[key] = item
                else:
                    if linea.startswith(f'# Estructura datos oceanograficos'):
                        break

            for key, item in env_lines.items():
                path = os.getenv(key)
                if not os.path.exists(path):
                    try:
                        os.makedirs(path)
                        logging.info(f"Directorio creado: {path}")
                    except:
                        logging.critical(f"No se pudo crear la ruta: {path}")

                    flag = True
            if flag:
                logging.info('Estructura de datos generada con exito.')
                return flag
        except FileNotFoundError:
            logging.error(
                f"No se pudo crear la estructura de datos. No se encontro el archivo de variables de entorno {self.paths}")

    def __CrearCamp(self):
        try:
            lines = self.open_env()
            for i, linea in enumerate(lines):
                if linea.startswith(f'# Estructura datos oceanograficos'):
                    # Ruta principal
                    root = os.getenv('OF_DATA_ROOT')
                    # Ruta de la campaña activa
                    path = os.getenv('OF_BUQUE_NROCAMP')
                    # Creo la estructura de carpetas dentro de la campaña importada
                    file_json = os.path.basename(self.f_json)
                    file_json = f"{path}{os.sep}{file_json}"
                    if not os.path.exists(file_json):
                        if os.path.exists(root):
                            if not os.path.exists(path):
                                os.makedirs(path)
                                for key, item in utils.exp_path.items():
                                    if key == "termosal":
                                        for tsg_key, tsg_item in item.items():
                                            path_tsg = f"{path}{os.sep}{key.capitalize()}{os.sep}{tsg_item}"
                                            try:
                                                os.makedirs(path_tsg)
                                            except:
                                                logging.error(
                                                    f"No se pudo crear el directorio {path_tsg}")
                                    else:
                                        try:
                                            path_ctd = f"{path}{os.sep}{item}"
                                            os.makedirs(f"{path_ctd}")
                                        except:
                                            logging.error(
                                                f"No se pudo crear el directorio {path_ctd}")

                                logging.info(
                                    f"Estructura de campaña generada con exito. {path}")
                                # Copio el archivo json en la estructura de la campaña
                                shutil.copy(self.f_json, os.getenv(
                                    'OF_BUQUE_NROCAMP'))
                        else:
                            logging.critical(
                                'Debe crear la estructura de datos antes de incorporar una campaña.')
                            sys.exit(0)
                    with open(file_json, 'r') as archivo:
                        estructura_json = json.load(archivo)
                    return estructura_json
        except:
            pass


if __name__ == '__main__':
    var_env = env()
    init = QtWidgets.QApplication([])
    load_dotenv(var_env.env, var_env.encoding)
    windows = Frm_Inicio.Frm_Inicio()
    windows.show()
    init.installEventFilter(windows)
    init.exec_()
    ##################################################################
    # Borro las variables de entorno, para recargar los valores
    ##################################################################
    del os.environ["OF_DATA_BUQUE"]
    del os.environ["OF_BUQUE_ANO"]
    del os.environ["OF_BUQUE_NROCAMP"]
    load_dotenv(var_env.env, var_env.encoding)
    var_env.mkroot()
    try:
        est_json = var_env.mkcamp(windows._selected_file)
        app = QtWidgets.QApplication([])
        window = MainWindow(estructura=est_json)
        window.show()
        app.installEventFilter(window)
        app.exec_()
    except AttributeError:
        sys.exit(0)
