# import sys, os
# import datetime
# import time
# import wmi
# import configparser
from threading import Thread
# import re
# import json
# import serial
# import RMC

from app.cfg import Cfg
from gui.Frm_Config_ui import *
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QAction, QInputDialog, QLineEdit, QFileDialog, QDialog, QTableWidgetItem
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Variable global
# _Config = dict()


__autor__ = 'Alvaro Cubiella'
__version__ = 'V1.01'


class Frm_Config(QDialog, Ui_Frm_Config):
    # Aca heredo la clase de la ventana, si no hay nada simplemente aparece una ventana vacia
    def __init__(self, *args, **kwargs):
        self.__load_cfg()
        QDialog.__init__(self, *args, **kwargs)
        # QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
#        QtGui.QMainWindow.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)                            # Pone la ventana en modo persistente
        self.setupUi(self)

        # Eventos botones
        self.btn_Guardar.clicked.connect(self.click_btn_Guardar)
        self.btn_Salir.clicked.connect(self.closeEvent)

        self.dirpick_Estructura.clicked.connect(self.dirpickEstructura)
        self.dirpick_SeaSaveini.clicked.connect(self.dirpick_SeaSaveIni)
        self.dirpick_SeaSaveV7.clicked.connect(self.dirpickSeaSave7)

        # Eventos dentro de la tabla
        # self.tabla_CTD.doubleClicked.connect(self.on_click)

        # Eventos en Checks
        self.chk_GPS.stateChanged.connect(self.chg_chk_GPS)
        self.chk_CTD.stateChanged.connect(self.chg_chk_CTD)
        self.chk_TSG.stateChanged.connect(self.chg_chk_TSG)
        self.chk_BAT.stateChanged.connect(self.chg_chk_BAT)

        # Cargo los cuadros con sus valores correspondientes del archivo Config.ini
        # Pestaña Directorios
        self.txt_DirEstructura.setText(
            self.cfg['Directorios']['Estructura'])
        self.txt_DirSeaSaveV7.setText(
            self.cfg['Directorios']['seasave7'])
        self.txt_DirSeaSaveini.setText(
            self.cfg['Directorios']['seasaveini'])
        # Pestaña Campaña
        self.txt_SiglasBuque.setText(self.cfg['Campania']['Siglasbuque'])
        self.txt_Anio.setText(str(self.cfg['Campania']['Anio']))
        self.txt_Nro_Campania.setText(str(self.cfg['Campania']['Nrocampania']))
        # Pestaña Puertos
        # GPS - COM
        self.chk_GPS.setChecked(
            int(self.cfg['Configuracion']['NMEA']['Status']))
        self.cbox_GPS_COM.addItem(self.cfg['Configuracion']['NMEA']['Port'])
        self.cbox_GPS_COM.setCurrentText(
            self.cfg['Configuracion']['NMEA']['Port'])
        # GPS Baud Rate
        self.cbox_GPS_BR.addItems(['4800', '9600'])
        self.cbox_GPS_BR.setCurrentText(
            str(self.cfg['Configuracion']['NMEA']['BR']))
        # CTD - COM
        self.chk_CTD.setChecked(
            int(self.cfg['Configuracion']['CTD']['Status']))
        self.cbox_CTD_COM.addItem(self.cfg['Configuracion']['CTD']['Port'])
        self.cbox_CTD_COM.setCurrentText(
            self.cfg['Configuracion']['CTD']['Port'])
        # CTD Baud Rate
        self.cbox_CTD_BR.addItems(['600', '1200', '4800', '9600', '19200'])
        self.cbox_CTD_BR.setCurrentText(
            str(self.cfg['Configuracion']['CTD']['BR']))
        # TSG - COM
        self.chk_TSG.setChecked(
            int(self.cfg['Configuracion']['TSG']['Status']))
        self.cbox_TSG_COM.addItem(self.cfg['Configuracion']['TSG']['Port'])
        self.cbox_TSG_COM.setCurrentText(
            self.cfg['Configuracion']['TSG']['Port'])
        # TSG Baud Rate
        self.cbox_TSG_BR.addItems(['600', '1200', '4800', '9600'])
        self.cbox_TSG_BR.setCurrentText(
            str(self.cfg['Configuracion']['TSG']['BR']))
        # BAT - COM
        self.chk_BAT.setChecked(
            int(self.cfg['Configuracion']['Batimetria']['Status']))
        self.cbox_BAT_COM.addItem(
            self.cfg['Configuracion']['Batimetria']['Port'])
        self.cbox_BAT_COM.setCurrentText(
            self.cfg['Configuracion']['Batimetria']['Port'])
        # BAT Baud Rate
        self.cbox_BAT_BR.addItems(['4800', '9600'])
        self.cbox_BAT_BR.setCurrentText(
            str(self.cfg['Configuracion']['Batimetria']['BR']))

        # Pestaña Datos Instrumentos
        # CTD
        variables = self.cfg['Configuracion']['CTD']['filas']
        self.spinBox_CTD.setValue(len(variables))
        self.tabla_CTD.setRowCount(len(variables))
        self.oldval_spinBox_CTD = self.spinBox_CTD.value()
        j = 0
        for i in variables:
            self.tabla_CTD.setItem(0, j, QTableWidgetItem(i))
            j += 1

        # TSG
        variables = self.cfg['Configuracion']['TSG']['filas']
        self.spinBox_TSG.setValue(len(variables))
        self.tabla_TSG.setRowCount(len(variables))
        self.oldval_spinBox_TSG = self.spinBox_TSG.value()
        j = 0
        for i in variables:
            self.tabla_TSG.setItem(0, j, QTableWidgetItem(i))
            j += 1

        # Pestaña Ventana

        # Eventos spin control CTD
        self.spinBox_CTD.valueChanged.connect(self.chg_spinBox_CTD)
        self.spinBox_TSG.valueChanged.connect(self.chg_spinBox_TSG)

    def __load_cfg(self):
        self._Config = Cfg()
        self.cfg = self._Config.GetCfg()
        pass

    def click_btn_Guardar(self, event):
        self.cfg['Directorios']['Estructura'] = self.txt_DirEstructura.text()
        self.cfg['Directorios']['seasave7'] = self.txt_DirSeaSaveV7.text()
        self.cfg['Directorios']['seasaveini'] = self.txt_DirSeaSaveini.text()

        self.cfg['Campania']['Siglasbuque'] = self.txt_SiglasBuque.text()
        self.cfg['Campania']['Anio'] = self.txt_Anio.text()
        self.cfg['Campania']['Nrocampania'] = self.txt_Nro_Campania.text().zfill(3)

        self.cfg['Configuracion']['NMEA']['Status'] = str(
            self.chk_GPS.checkState())
        self.cfg['Configuracion']['NMEA']['Port'] = self.cbox_GPS_COM.currentText()
        # GPS Baud Rate
        self.cfg['Configuracion']['NMEA']['BR'] = self.cbox_GPS_BR.currentText()
        # CTD - COM
        self.cfg['Configuracion']['CTD']['Status'] = str(
            self.chk_CTD.checkState())
        self.cfg['Configuracion']['CTD']['Port'] = self.cbox_CTD_COM.currentText()
        self.cfg['Configuracion']['CTD']['BR'] = self.cbox_CTD_BR.currentText()
        # TSG - COM
        self.cfg['Configuracion']['TSG']['Status'] = str(
            self.chk_TSG.checkState())
        self.cfg['Configuracion']['TSG']['Port'] = self.cbox_TSG_COM.currentText()
        # TSG Baud Rate
        self.cfg['Configuracion']['TSG']['BR'] = self.cbox_TSG_BR.currentText()
        # BAT - COM
        self.cfg['Configuracion']['Batimetria']['Status'] = str(
            self.chk_BAT.checkState())
        self.cfg['Configuracion']['Batimetria']['Port'] = self.cbox_BAT_COM.currentText()
        # BAT Baud Rate
        self.cfg['Configuracion']['Batimetria']['BR'] = self.cbox_BAT_BR.currentText()

        # Datos Instrumentos
        # CTD
        self.cfg['Configuracion']['CTD']['Variables'] = str(
            self.spinBox_CTD.value())
        nom_fila = list()
        for i in range(0, self.tabla_CTD.rowCount()):
            item = self.tabla_CTD.item(i, 0).text()
            nom_fila.append(item)
        self.cfg['Configuracion']['CTD']['filas'] = nom_fila
        # TSG
        self.cfg['Configuracion']['TSG']['Variables'] = str(
            self.spinBox_TSG.value())
        nom_fila = list()
        for i in range(0, self.tabla_TSG.rowCount()):
            item = self.tabla_TSG.item(i, 0).text()
            nom_fila.append(item)
        self.cfg['Configuracion']['TSG']['filas'] = nom_fila

        self._Config.SetCfg(self.cfg)
        self.close()
        return self.cfg

    def dirpickEstructura(self, event):
        pass

    def dirpick_SeaSaveIni(self, event):
        file = str(QFileDialog.getExistingDirectory(
            self, "Seleccione directorio"))
        self.txt_DirSeaSaveini.setText(file)

    def dirpickSeaSave7(self, event):
        pass

    def filepick(self, event):
        print('sel file')

    def chg_spinBox_CTD(self, event):
        variables = list()
        for i in range(0, self.tabla_CTD.rowCount()):
            item = self.tabla_CTD.item(i, 0).text()
            variables.append(item)
        if self.oldval_spinBox_CTD < self.spinBox_CTD.value():
            add_row = self.spinBox_CTD.value() - self.oldval_spinBox_CTD
            for i in range(0, add_row):
                variables.append('')
            self.actualizo_tabla(variables, 'tabla_CTD')
        else:
            rest_row = self.oldval_spinBox_CTD - self.spinBox_CTD.value()
            try:
                for i in range(0, rest_row):
                    variables.pop()
                self.actualizo_tabla(variables, 'tabla_CTD')
            except:
                pass
        self.oldval_spinBox_CTD = self.spinBox_CTD.value()

    def chg_spinBox_TSG(self, event):
        variables = list()
        for i in range(0, self.tabla_TSG.rowCount()):
            item = self.tabla_TSG.item(i, 0).text()
            variables.append(item)
        if self.oldval_spinBox_TSG < self.spinBox_TSG.value():
            variables.append('')
            self.actualizo_tabla(variables, 'tabla_TSG')
        else:
            try:
                variables.pop()
                self.actualizo_tabla(variables, 'tabla_TSG')
            except:
                pass
        self.oldval_spinBox_TSG = self.spinBox_TSG.value()

    def chg_chk_GPS(self, event):
        if self.chk_GPS.checkState() != 0:
            self.cbox_GPS_COM.setEnabled(True)
            self.cbox_GPS_BR.setEnabled(True)
            self.cbox_GPS_DataBits.setEnabled(True)
        else:
            self.cbox_GPS_COM.setEnabled(False)
            self.cbox_GPS_BR.setEnabled(False)
            self.cbox_GPS_DataBits.setEnabled(False)

    def chg_chk_CTD(self, event):
        if self.chk_CTD.checkState() != 0:
            self.cbox_CTD_COM.setEnabled(True)
            self.cbox_CTD_BR.setEnabled(True)
            self.cbox_CTD_DataBits.setEnabled(True)
        else:
            self.cbox_CTD_COM.setEnabled(False)
            self.cbox_CTD_BR.setEnabled(False)
            self.cbox_CTD_DataBits.setEnabled(False)

    def chg_chk_TSG(self, event):
        if self.chk_TSG.checkState() != 0:
            self.cbox_TSG_COM.setEnabled(True)
            self.cbox_TSG_BR.setEnabled(True)
            self.cbox_TSG_DataBits.setEnabled(True)
        else:
            self.cbox_TSG_COM.setEnabled(False)
            self.cbox_TSG_BR.setEnabled(False)
            self.cbox_TSG_DataBits.setEnabled(False)

    def chg_chk_BAT(self, event):
        if self.chk_BAT.checkState() != 0:
            self.cbox_BAT_COM.setEnabled(True)
            self.cbox_BAT_BR.setEnabled(True)
            self.cbox_BAT_DataBits.setEnabled(True)
        else:
            self.cbox_BAT_COM.setEnabled(False)
            self.cbox_BAT_BR.setEnabled(False)
            self.cbox_BAT_DataBits.setEnabled(False)

    def actualizo_tabla(self, variables, tabla):
        eval('self.' + tabla + '.setRowCount(0)')
        eval('self.' + tabla + '.setRowCount('+str(len(variables))+')')
        j = 0
        for i in variables:
            eval('self.' + tabla + '.setItem(0,j,QTableWidgetItem("' + i + '"))')
            j += 1

    # Atiendo el cierre de programa

    def closeEvent(self, event):
        self.close()

    @pyqtSlot()
    def on_click(self):
        print("\n")
        for currentQTableWidgetItem in self.tabla_CTD.selectedItems():
            print(currentQTableWidgetItem.row(),
                  currentQTableWidgetItem.column(), currentQTableWidgetItem.text())
