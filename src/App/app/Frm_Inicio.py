import glob
import os
import json
import subprocess

from decouple import config
from dotenv import load_dotenv

from app.cfg import Cfg
from app.utils import validate_import_json

from gui.Frm_Inicio_ui import *

from PyQt5.QtWidgets import QApplication, QMessageBox, QMainWindow, QAction, QInputDialog, QLineEdit, QFileDialog, QDialog, QTableWidgetItem
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

class Frm_Inicio(QDialog, Ui_Frm_Inicio):
    #Aca heredo la clase de la ventana, si no hay nada simplemente aparece una ventana vacia
    def __init__(self, *args, **kwargs):
        self._Config = Cfg()
        self._cfg = self._Config.GetCfg()
        QDialog.__init__(self, *args, **kwargs)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)                            # Pone la ventana en modo persistente
        self.setupUi(self)

        #########################################################################
        ## Configuro estado de incio de los botones y variables
        #########################################################################
        self.btn_Cancel.setFocus()
        self.btn_Cargar.setEnabled(False)

        self.tree_json.setVisible(False)
        self.resize(self.minimumSize())

        self.tree_json.setColumnCount(2)
        self.tree_json.setHeaderLabels(["Key", "Value"])

        self.focus = None
        #########################################################################
        ## Configuro estado de incio de la ventana
        #########################################################################
        self.box_Camps.setVisible(False)


        #########################################################################
        ## Control de eventos de botonos y funciones
        #########################################################################
        self.btn_Cancel.clicked.connect(self.close)
        self.btn_Cargar.clicked.connect(self.Cargar_env)
        self.rbtn_Cargar.stateChanged.connect(self.checkboxStateChanged)
        self.cbox_view.stateChanged.connect(self.checkboxStateChanged)
        self.rbtn_Nueva.stateChanged.connect(self.checkboxStateChanged)
        self.cbox_Recientes.installEventFilter(self)
        self.cbox_Cargar.activated.connect(self.select_item_cbox)
        self.cbox_Recientes.activated.connect(self.select_item_cbox)
        #self.cbox_Cargar.currentIndexChanged.connect(self.select_item_cbox)
        #self.cbox_Recientes.currentIndexChanged.connect(self.select_item_cbox)
       
        #########################################################################
        ## Cargo valoren dentro de los combo box
        #########################################################################
        self.__GetLastFiles

    def checkboxStateChanged(self, state):
        if self.focus == 'rbtn_Cargar':
            if self.rbtn_Cargar.isChecked():
                self.box_Camps.setVisible(True)
                self.cargar_campanias()
            else:
                self.cbox_Cargar.clear()
                self.box_Camps.setVisible(False)      
        elif self.focus == 'cbox_view':
            if self.cbox_view.isChecked():
                min_x = self.minimumWidth()
                min_y = self.minimumHeight()
                self.setFixedSize(*(self.maximumWidth(),self.maximumHeight()))
                self.tree_json.setVisible(True)
                self.setMinimumSize(QtCore.QSize(min_x, min_y))
            else:
                max_x = self.maximumWidth()
                max_y = self.maximumHeight()
                self.setFixedSize(*(self.minimumWidth(),self.minimumHeight()))
                self.tree_json.setVisible(False)
                self.setMaximumSize(QtCore.QSize(max_x, max_y))
        elif self.focus == 'rbtn_Nueva':
            if self.rbtn_Nueva.isChecked():
                self.box_Camps.setVisible(False)
                self.btn_Cargar.setEnabled(True)
                self.btn_Cargar.setText('Importar')
                #self.cargar_campanias()
            else:
                self.cbox_Cargar.clear()
                self.box_Camps.setVisible(False)  
                self.btn_Cargar.setEnabled(False)
                self.btn_Cargar.setText('Cargar')

    def cargar_campanias(self):
        # Buscara todas las campanias que esten dentro de la estructura de carpetas
        # Directorio base para iniciar la búsqueda
        directorio_base = os.getenv('OF_DATA_DIR')
        # Patrón para buscar archivos JSON en todas las subcarpetas
        patron_json = os.path.join(directorio_base, '**', '*.json')
        # Obtener la lista de archivos JSON
        self._archivos_json = glob.glob(patron_json, recursive=True)
        # Excluir la carpeta 'varios' de los resultados
        self._archivos_json = [archivo for archivo in self._archivos_json if ('Varios' or 'varios' ) not in archivo]
        self._archivos_json = [archivo for archivo in self._archivos_json if ('CNV' or 'cnv' ) not in archivo]
        self._archivos_json = [archivo for archivo in self._archivos_json if ('HEX' or 'hex' ) not in archivo]
        # Elimino cualquier archivo json que no tenga la estructura de un import
        for file in self._archivos_json:
            with open(file, 'r') as f:  
                json_file = json.load(f)
            valido = validate_import_json(json_file)
            if not valido:
                self._archivos_json.remove(file)
        
        self.cbox_Cargar.clear()
        self._archivos_json = list(reversed(self._archivos_json))
        for i in self._archivos_json:
            i = os.path.basename(i)
            i = i.replace('.json','')
            self.cbox_Cargar.addItem(i)

    def populate_tree_widget(self, data, parent_item=None):
        if parent_item == None:
            parent_item = self.tree_json
        if 'Archivos' in set(data):
            data.pop('Archivos')
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    child_item = QTreeWidgetItem(parent_item, [key])
                    if key == 'Expedicion':  # Expandir solo el elemento 'Expedicion'
                        child_item.setExpanded(True)
                    self.populate_tree_widget(value, child_item)
                elif isinstance(value, list):
                    child_item = QTreeWidgetItem(parent_item, [key])
                    for item in value:
                        self.populate_tree_widget(item, child_item)
                else:
                    child_item = QTreeWidgetItem(parent_item, [key, str(value)])

    def select_item_cbox(self):
        if self.focus == 'cbox_Cargar':
            index = self.cbox_Cargar.currentIndex()
            selected_file = self._archivos_json[index]
            #print(f"Archivo seleccionado: {selected_file}")
        elif self.focus == 'cbox_Recientes':
            index = self.cbox_Recientes.currentIndex()
            selected_file = self._lastfiles[index]
            #print(f"Archivo seleccionado: {selected_file}")
        if selected_file == "":
            self.btn_Cargar.setEnabled(False)
        else:
            self.btn_Cargar.setEnabled(True)
            self.tree_json.clear()
            with open(selected_file, 'r') as f:  
                data = json.load(f)
            self.populate_tree_widget(data)
        

    #Funcio para manejar los eventos de foco de la ventana
    def eventFilter(self, obj, event):
        # Manejar el evento de recibir foco en el QComboBox
        if obj == self.cbox_Recientes and event.type() == event.FocusIn:
            self.rbtn_Cargar.setChecked(False)
            self.box_Camps.setVisible(False)
            self.rbtn_Nueva.setChecked(False)
            self.btn_Cargar.setEnabled(False)
            self.focusInEventHandler(obj)   
            #self.GetLastFiles
        elif obj == self.rbtn_Cargar and event.type() == event.FocusIn:             
            self.rbtn_Nueva.setChecked(False)
            self.btn_Cargar.setEnabled(False)
            #self.cbox_Recientes.clear()    
            self.focusInEventHandler(obj)      
        elif obj == self.rbtn_Nueva and event.type() == event.FocusIn:
            self.rbtn_Cargar.setChecked(False)
            self.box_Camps.setVisible(False)
            #self.cbox_Recientes.clear()
            self.focusInEventHandler(obj) 
        elif obj == self.cbox_Cargar and event.type() == event.FocusIn:
        #    self.cargar_campanias()
            self.focusInEventHandler(obj)           
        elif obj == self.cbox_view and event.type() == event.FocusIn:
            self.focusInEventHandler(obj)      
        return super().eventFilter(obj, event)

    def focusInEventHandler(self, sender_object):
        # Actualizar la etiqueta con información sobre el objeto
        self.focus = sender_object.objectName()

    @property
    def __GetLastFiles(self):
        self._lastfiles = self._cfg['Archivos']
        if not self._lastfiles == None:
            self.cbox_Recientes.clear()
            if not self._lastfiles[0] == "":
                self._lastfiles.insert(0, "")
            #self._lastfiles = list(set(self._lastfiles))                    # Elimino repetidos
            if self._lastfiles != []:
                for i in self._lastfiles:
                    # Agrego los ultimos 5 archivos cargados
                    self.cbox_Recientes.addItem(i)
        else:
            self._lastfiles = ['']

    def open_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_dialog = QFileDialog()
        file_dialog.setDirectory(os.getenv('OF_DATA_DIR'))

        file_dialog.setNameFilter("Archivos JSON (*.json)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setViewMode(QFileDialog.List)
        
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                pass
                #print(f"Archivo seleccionado: {file_path}")  # Aquí puedes manejar el archivo seleccionado según tus necesidades
        try:
            return os.path.normpath(file_path)
        except NameError:
            return None

    # edito valores de las variables de entorno segun la campaña seleccionada
    def Editar_venv(self, archivo, variable, nuevo_valor):
        with open(archivo, 'r') as f:
            lines = f.readlines()

        with open(archivo, 'w') as f:
            for line in lines:
                if line.startswith(variable):
                    f.write(f"{variable}={nuevo_valor}\n")
                else:
                    f.write(line)


    def Cargar_env(self):
        if self.btn_Cargar.text() == 'Cargar':
            if self.focus == 'cbox_Recientes':
                self._selected_file = self.cbox_Recientes.currentText()
            elif self.focus == 'cbox_Cargar':
                index = self.cbox_Cargar.currentIndex()
                self._selected_file = self._archivos_json[index]
            elif self.focus == 'rbtn_Nueva':
                pass
                #print('Nuevo')
        elif self.btn_Cargar.text() == 'Importar':
            self._selected_file = self.open_file_dialog()

        try:
            with open(self._selected_file, 'r') as f:  
                json_file = json.load(f) 
            self._cfg['Campania']['Siglasbuque'] = json_file['Expedicion']['Buque']
            self._cfg['Campania']['Anio'] = json_file['Expedicion']['Anio']
            self._cfg['Campania']['Nrocampania'] = json_file['Expedicion']['Numero']
        except:
            pass


        if self._selected_file in self._lastfiles:
            index = self._lastfiles.index(self._selected_file)
            self._lastfiles.pop(index)
            self._lastfiles.insert(0, self._selected_file)
        elif self._selected_file is None:
            return
        else:
            if len(self._lastfiles) > 7:
                self._lastfiles.pop(-1)
                self._lastfiles.insert(0, self._selected_file)
            else:
                self._lastfiles.insert(0, self._selected_file)
        if "" in self._lastfiles:
            self._lastfiles.remove("")
        self._cfg['Archivos'] = self._lastfiles
        self._Config.SetCfg(self._cfg)
        cmd = []
        #cadena = "{OF_DATA_DIR}"
        #cmd.append(f"{os.getcwd()}{os.sep}SIAVO_Cfg.exe -f siavo.env --edit OF_DATA_BUQUE '{cadena}{os.sep}{self._cfg['Campania']['Siglasbuque']}'")
        #cadena = "{OF_DATA_BUQUE}"
        #cmd.append(f"{os.getcwd()}{os.sep}SIAVO_Cfg.exe -f siavo.env --edit OF_BUQUE_ANO '{cadena}{os.sep}{self._cfg['Campania']['Anio']}'")
        #cadena = "{OF_BUQUE_ANO}"
        #cmd.append(f"{os.getcwd()}{os.sep}SIAVO_Cfg.exe -f siavo.env --edit OF_BUQUE_NROCAMP '{cadena}{os.sep}{str(self._cfg['Campania']['Nrocampania']).zfill(3)}'")
        #for i in cmd:
        #    result = subprocess.run(["powershell", "-Command", i], capture_output=True, text=True, shell=True)
        # Ejemplo de uso
        archivo = 'siavo.env'
        variables_a_editar = {
            'OF_DATA_BUQUE': f"${{OF_DATA_DIR}}\\{self._cfg['Campania']['Siglasbuque']}",
            'OF_BUQUE_ANO': f"${{OF_DATA_BUQUE}}\\{self._cfg['Campania']['Anio']}",
            'OF_BUQUE_NROCAMP': f"${{OF_BUQUE_ANO}}\\{str(self._cfg['Campania']['Nrocampania']).zfill(3)}",
        }
        for variable, nuevo_valor in variables_a_editar.items():
            self.Editar_venv(archivo, variable, nuevo_valor)

        self.close()

    def GetSelectedFile(self):
        return self._selected_file