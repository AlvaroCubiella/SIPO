"""
SIPO (Sistema de Integración de Perfiles Oceanograficos)

SIPO es una solución integral para la gestión y consolidación de datos recolectados durante campañas oceanográficas. 
    - El sistema automatiza la fusión de flujos de datos provenientes de múltiples sensores y fuentes:

    - Integración de Datos de Sensores: Sincroniza registros de CTD (Conductividad, Temperatura, Presión) con sistemas TSG (Termosalinógrafo).

    - Georreferenciación y Batimetría: Vincula automáticamente cada muestra con coordenadas GPS (Latitud/Longitud) y datos de profundidad del ecosonda.

    - Gestión de Metadatos: Almacena información crítica de la expedición, incluyendo el buque, números de serie de los sensores y sus fechas de última calibración.

    - Estructura Estandarizada: Genera salidas en formato JSON jerárquico, facilitando el post-procesamiento científico y la trazabilidad de las estaciones (Superficie, Fondo y Cubierta)."""

import sys
import os
import logging
import datetime
import time
import subprocess
from threading import Thread
import json
import serial
import shutil

# Importo modulos PyQt5
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QAction, QInputDialog, QLineEdit, QFileDialog, QDialog
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Importo modulos de la App
from app.RMC import RMC
from app.DBS import DBS
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
from app.StationManager import StationManager
from app.SerialWorkers import NMEA_Worker, CTD_Worker, TSG_Worker, DBS_Worker

from dotenv import load_dotenv

__autor__ = 'Alvaro Cubiella'
__version__ = 'V1.61'
__contacto__ = 'alvarocubiella@gmail.com'

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

# Helper functions and Worker classes moved to app.SerialWorkers.py



class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        # Aca heredo la clase de la ventana
        super(MainWindow, self).__init__()
        try:
            self._Config = Cfg()
        except FileNotFoundError:
            Cfg.NuevoConfig()
            self._Config = Cfg()
        # Paso la estructura de datos del archivo Json para agregar mas info.
        self.estructura = kwargs['estructura']
        # Cargo las variables del archivo de configuracion
        self.cfg = self._Config.GetCfg()
        # Directorio de trabajo de la campania a partir de las variables de entorno
        self.dir_Camp = os.getenv('OF_BUQUE_NROCAMP')
        self.W_Dir = f"{self.dir_Camp}{os.sep}Varios{os.sep}Planillas"
        if not (os.path.exists(self.W_Dir)):
            os.makedirs(self.W_Dir)
        self.DEMO = datetime.datetime(2020, 12, 31, 0, 0, 0)
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint |
                            QtCore.Qt.WindowStaysOnTopHint)  # Pone la ventana en modo persistente
        self.setupUi(self)
        self.setWindowTitle(f"Planilla V.{(__version__)}")
        self.station_manager = StationManager(self.cfg, self.estructura)
        self.thread = None
        self.worker = None

        # Configuro opciones de los botones de la barra de menu
        self.btn_Salir.setShortcut('Alt+S')

        # Configuro eventos en los cuadros de texto
        # Se genera al cambiar el contenido del cuadro
        self.txt_EstGral.textChanged.connect(self.chg_txt_EstGral)

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
        # Inicio un puerto para NMEA con sentencia RMC
        ports = RMC(port='COM1',
                    BR=4800,
                    sts='RMC',
                    timeout=1,
                    )
        # Escaneo los puertos serial disponibles
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
        msg = f"Programa desarrollado por: {__autor__}\rVersion {__version__}\rContacto:{__contacto__}"
        self.msg_Box(mensaje=f'{msg}\r', titulo='Información',
                     icono=QMessageBox.Information)

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

    ########################################################################
    # Inicializo el hilo del GPS
    ########################################################################

    def init_NMEA(self):
        # Inicializo el hilo que administra el puerto Serie del NMEA
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['NMEA']['Port'],
                                baudrate=self.cfg['Configuracion']['NMEA']['BR'],
                                timeout=self.cfg['Configuracion']['NMEA']['Intervalo'],
                                )
            ser.close()
            self.NMEA = NMEA_Worker(ser)
            self.thread_NMEA = QThread()
            self.NMEA.moveToThread(self.thread_NMEA)
            self.thread_NMEA.started.connect(self.NMEA.work)
            self.NMEA.intReady.connect(self.onIntReadyNMEA)
            self.NMEA.finished.connect(self.loop_finished)
            self.NMEA.finished.connect(self.thread_NMEA.quit)
            self.NMEA.finished.connect(self.NMEA.deleteLater)
            self.thread_NMEA.finished.connect(self.thread_NMEA.deleteLater)

        except IOError as e:
            # Vuelen boton iniciar y detener a condiciones iniciales
            self.loop_finished()
            logging.critical(
                f'Error GPS. No se pudo inicializar el puerto {ser.port}\r\n{str(e)}')
            self.msg_Box(mensaje='Error al inicializar el puerto seleccionado!!!\r',
                         titulo='I/O Error GPS', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo del NMEA
    ########################################################################
    def onIntReadyNMEA(self, i):
        self.NMEA_Str = i
        self.updateStatusBar()

    ########################################################################
    # Inicializo hilo de Batimetria
    ########################################################################
    def init_DBS(self):
        # Inicializo el hilo que administra el puerto Serie del dato de Batimetria
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['Batimetria']['Port'],
                                baudrate=self.cfg['Configuracion']['Batimetria']['BR'],
                                timeout=self.cfg['Configuracion']['Batimetria']['Intervalo'],
                                )
            ser.close()
            # a new worker to perform those tasks
            self.DBS = DBS_Worker(ser)
            # a new thread to run our background tasks in
            self.thread_DBS = QThread()
            # move the worker into the thread, do this first before connecting the signals
            self.DBS.moveToThread(self.thread_DBS)
            # begin our worker object's loop when the thread starts running
            self.thread_DBS.started.connect(self.DBS.work)
            self.DBS.intReady.connect(self.onIntReadyDBS)
            # do something in the gui when the worker loop ends
            self.DBS.finished.connect(self.loop_finished)
            # tell the thread it's time to stop running
            self.DBS.finished.connect(self.thread_DBS.quit)
            # have worker mark itself for deletion
            self.DBS.finished.connect(self.DBS.deleteLater)
            # have thread mark itself for deletion
            self.thread_DBS.finished.connect(self.thread_DBS.deleteLater)

        except IOError as e:
            # Vuelen boton iniciar y detener a condiciones iniciales
            self.loop_finished()
            logging.critical(
                f'Error Batimetria. No se pudo inicializar el puerto {ser.port}\r\n{str(e)}')
            self.msg_Box(mensaje=f"Error al inicializar el puerto seleccionado!!!\r\n{str(e)}",
                         titulo='I/O Error Batimetria', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo de Batimetria
    ########################################################################
    def onIntReadyDBS(self, i):
        self.DBS_Str = i
        self.updateStatusBar()

    ########################################################################
    # Inicializo el hilo del CTD
    ########################################################################

    def init_CTD(self):
        # Inicializo el hilo que administra el puerto Serie del dato de CTD
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['CTD']['Port'],
                                baudrate=self.cfg['Configuracion']['CTD']['BR'],
                                timeout=self.cfg['Configuracion']['CTD']['Intervalo'] + 1
                                )
            ser.close()
            # a new worker to perform those tasks
            self.CTD = CTD_Worker(ser)
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
        except IOError as e:
            # Vuelen boton iniciar y detener a condiciones iniciales
            self.loop_finished()
            logging.critical(
                f'Error CTD. No se pudo inicializar el puerto {e}')
            self.msg_Box(mensaje='Error al inicializar el puerto seleccionado!!!\r',
                         titulo='I/O Error CTD', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo del CTD
    ########################################################################
    def onIntReadyCTD(self, i):
        self.CTD_str = i

    ########################################################################
    # Inicializo el hilo del TSG
    ########################################################################
    def init_TSG(self):
        # Inicializo el hilo que administra el puerto Serie del dato de Termosalinografo
        try:
            ser = serial.Serial(port=self.cfg['Configuracion']['TSG']['Port'],
                                baudrate=self.cfg['Configuracion']['TSG']['BR'],
                                )
            ser.timeout = self.cfg['Configuracion']['TSG']['Intervalo'] + 1
            ser.close()
            # a new worker to perform those tasks
            self.TSG = TSG_Worker(ser)
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
            logging.critical(
                f'Error TSG. No se pudo inicializar el puerto {ser.port}')
            self.msg_Box(mensaje='Error al inicializar el puerto seleccionado!!!\r',
                         titulo='I/O Error TSG', icono=QMessageBox.Critical)
            return

    ########################################################################
    # Atiendo la señal generada a partir del hilo del TSG
    ########################################################################
    def onIntReadyTSG(self, i):
        self.TSG_str = i

    ########################################################################
    # Inicializa las variables de datos y los Hilos
    ########################################################################

    def setAdquisicion(self):
        self.NMEA_Str = {
            'latD': 'NaN',
            'lonD': 'NaN',
            'lat': 'NaN',
            'lon': 'NaN',
            'hora': 'NaN',
            'fecha': 'NaN',
        }
        self.DBS_Str = 'NaN'
        ########################################################################
        # Inicializo las clases de los hilos correspondientes
        ########################################################################
        try:
            # Activo lectura de cada dato segun el archivo config.json
            if self.cfg['Configuracion']['NMEA']['Status'] == '2':
                self.init_NMEA()
                self.thread_NMEA.start()
                logging.info('Hilo NMEA iniciado')
            if self.cfg['Configuracion']['CTD']['Status'] == '2':
                self.init_CTD()
                self.thread_CTD.start()
                logging.info('Hilo CTD iniciado')
            if self.cfg['Configuracion']['TSG']['Status'] == '2':
                self.init_TSG()
                self.thread_TSG.start()
                logging.info('Hilo TSG iniciado')
            if self.cfg['Configuracion']['Batimetria']['Status'] == '2':
                self.init_DBS()
                self.thread_DBS.start()
                logging.info('Hilo DBS iniciado')
        except:
            logging.error('Error al inicializar los hilos')

    def updateStatusBar(self):
        # Construye la cadena de estado combinada en el statusBar
        nmea_str = f"Vel: {self.NMEA_Str.get('Velocidad', 'N/A')} knt"
        dbs_str = f"Z: {self.DBS_Str} metros"
        status_message = f"{nmea_str} | {dbs_str}"
        # Actualiza el statusBar con la cadena combinada
        self.statusBar().showMessage(status_message)

    # Código para finalizar el bucle de los hilos activos
    def loop_finished(self):
        self.flag = False

    # Evento cambio de valor en cuadro de textos
    def chg_txt_EstGral(self, event):
        cadena = self.txt_EstGral.text()
        if not (event.isnumeric()):
            cadena = cadena[:-1]
        self.txt_EstGral.setText(cadena)
        self.act_btn_Inicio()

    # Actualizacion estado de botones
    def act_btn_Inicio(self):
        if (self.txt_EstGral.text() != ''):
            self.btn_Inicio.setEnabled(True)
        else:
            self.btn_Inicio.setEnabled(False)

    # Acciones de botones
    def click_btn_Inicio(self):
        # Recargo el cfg antes de iniciar por si se realizaro modificaciones en el archivode configuracion
        self._Config = Cfg()
        self.cfg = self._Config.GetCfg()
        self.txt_EstGral.setText(self.txt_EstGral.text().zfill(4))
        # cargo la ruta de la campaña activa a partir de las variables de entorno
        path = os.getenv('OF_BUQUE_NROCAMP')
        self.f_json = windows._selected_file
        
        # Seteo el directorio de trabajo en el manager
        self.station_manager.set_working_dir(self.f_json)

        if self.btn_Inicio.text() == 'Inicio':
            # Verificaciones previas
            self.station_manager.nro_estacion = self.txt_EstGral.text()
            self.station_manager.init_vars() # Preparar rutas
            
            exists, xmlcon_path = self.station_manager.check_xmlcon_exists()
            if not exists:
                logging.critical(f'El archivo de configuracion {xmlcon_path} no existe')
                self.msg_Box(mensaje=f'El archivo de configuracion {xmlcon_path} no existe\nNo se puede inicar',
                             titulo='xmlcon no encontrado', icono=QMessageBox.Critical)
                return
            
            # Chequeo si existe estacion
            if self.station_manager.station_exists(self.txt_EstGral.text()):
                reply = QMessageBox.question(self, 'Estación Existente', 'El número de estación ya existe. Desea Continuar? ',
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            # Iniciar Estacion
            self.station_manager.start_station(self.txt_EstGral.text())

            self.btn_Inicio.setText('Fin')
            self.btn_Cubierta.setEnabled(True)
            self.txt_EstGral.setEnabled(False)
            self.Menu_Config.setEnabled(False)
            self.fdo = 0
            
            # Inicialización de variables locales para mapeo (Lógica heredada mantenida por seguridad)
            # TSG
            self.TSG_str = {
                'scan': 'NaN', 'lat': 'NaN', 'lon': 'NaN', 'sal': 'NaN',
                'temp': 'NaN', 'cond': 'NaN', 'temp38': 'NaN',
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
            self.CTD_str = {
                'cond': 'NaN', 'press': 'NaN', 'sal': 'NaN',
                'scan': 'NaN', 'temp': 'NaN', 'bot': 'NaN',
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

            self.setAdquisicion()               # Inicio Hilos
            logging.info('Threads iniciados')
            
            time.sleep(1)
            # Registrar Posicion Inicio
            self.station_manager.W_Pos(self.NMEA_Str, self.DBS_Str, is_start=True)
            
        else:
            self.btn_Inicio.setText('Inicio')
            self.Menu_Config.setEnabled(True)
            self.btn_Cubierta.setEnabled(False)
            self.btn_Superficie.setEnabled(False)
            self.btn_skipover.setEnabled(False)
            self.btn_Fondo.setEnabled(False)
            self.txt_EstGral.setEnabled(True)
            
            # Registrar Posicion Fin
            self.station_manager.W_Pos(self.NMEA_Str, self.DBS_Str, is_start=False)
            self.station_manager.W_SkipOver(self.txt_SkipOver.text())
            self.station_manager.stop_station()
            
            self.stop_loop()

            reply = QMessageBox.question(self, 'Agregar comentarios', 'Quiere agragar algun comentario de la estación? ',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    self.Frm_Note_load()
                except NameError:
                    pass
            else:
                pass

    def click_btn_Cubierta(self):
        self.station_manager.W_CTD(self.CTD_str, loc='Cubierta')
        if self.fdo == 0:
            self.btn_Cubierta.setEnabled(False)
            self.btn_Superficie.setEnabled(True)
            self.btn_skipover.setEnabled(True)
        else:
            self.btn_Cubierta.setEnabled(False)

    def click_btn_Superficie(self):
        self.station_manager.W_TSGvsCTD(self.CTD_str, self.TSG_str, self.NMEA_Str)
        if self.fdo == 0:
            self.btn_Superficie.setEnabled(False)
            # self.btn_skipover.setEnabled(False)
            self.btn_Fondo.setEnabled(True)
        else:
            self.btn_Superficie.setEnabled(False)
            self.btn_Cubierta.setEnabled(True)

    def click_btn_Fondo(self):
        self.station_manager.W_CTD(self.CTD_str, loc='Fondo')
        self.btn_Fondo.setEnabled(False)
        self.btn_Superficie.setEnabled(True)
        self.fdo = 1

    def getSkipover(self):
        self.txt_SkipOver.setText(self.CTD_str.get('Scan', 'NaN'))
        # self.estacion[self.txt_EstGral.text(
        # )]['Skipover'] = self.CTD_str['Scan']
        # self.save_json()
        # self.btn_skipover.setEnabled(False)

    # Abro el formulario de configuracion
    def Frm_Config_load(self, event):
        self.ventana = Frm_Config.Frm_Config(self)
        self.ventana.show()

    def Frm_Note_load(self):
        self.win_note = Frm_Note.Frm_Note(self)
        self.win_note.lbl_Titulo.setText(
            f"Estación General {self.txt_EstGral.text()}")
        self.win_note.exec_()
        self.station_manager.add_comment(self.win_note.comentario)

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
        if self.cfg['Configuracion']['NMEA']['Status'] == '2':
            self.NMEA.working = False
        if self.cfg['Configuracion']['CTD']['Status'] == '2':
            self.CTD.working = False
        if self.cfg['Configuracion']['TSG']['Status'] == '2':
            self.TSG.working = False
        if self.cfg['Configuracion']['Batimetria']['Status'] == '2':
            self.DBS.working = False

    ###########################################################################
    # Administro archivo json
    ###########################################################################
    # Funciones de gestion de datos movidas a StationManager
    # - save_json
    # - init_vars
    # - W_Pos
    # - W_SkipOver
    # - W_Bott
    # - W_CTD
    # - W_TSGvsCTD

    def expira(self):
        if self.cfg['Configuracion']['NMEA']['Status'] != '2':
            exit()
        fecha = self.NMEA_Str['fecha']
        delta = self.DEMO - fecha
        if delta.days < 0:
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
