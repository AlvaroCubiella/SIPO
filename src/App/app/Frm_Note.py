#import sys, os
#import datetime
#import time
#import wmi
#import configparser
from threading import Thread
#import re
#import json
#import serial
#import RMC

from gui.Frm_Note_ui import *
from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QAction, QInputDialog, QLineEdit, QFileDialog, QDialog, QTableWidgetItem
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Variable global
#_Config = dict()


__autor__ = 'Alvaro Cubiella'
__version__ = 'V1.01'


class Frm_Note(QDialog, Ui_Frm_Note):
    #Aca heredo la clase de la ventana, si no hay nada simplemente aparecehola una ventana vacia
    def __init__(self, *args, **kwargs):
        QDialog.__init__(self, *args, **kwargs)
        #QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
#        QtGui.QMainWindow.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        #self.setWindowFlags(Qt.WindowStaysOnTopHint)                            # Pone la ventana en modo persistente
        self.setupUi(self)
        self.comentario = ''

        #Eventos botones
        self.pushButton.clicked.connect(self.click_btnbox)

    def click_btnbox(self, event):
        self.comentario = self.plainTextEdit.toPlainText()
        self.close()

    #Atiendo el cierre de programa
    def closeEvent(self, event):
        self.close()