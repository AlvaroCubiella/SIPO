import json
import os
from app.utils import cfg

class Cfg():
    def __init__(self):
        self._file = 'config.json'
        self.dir_file = os.getcwd() + os.sep + self._file
        if not(os.path.isfile(self.dir_file)):
            raise FileNotFoundError (f'No such file or directory: {self.dir_file}')
        
    @property
    def GetFile(self):
        return self._file

    def GetCfg(self):
        # Cargo archivo cfg como un diccionario
        with open(self._file, 'r') as archivo:
            _config = json.load(archivo)
        return _config

    def SetCfg(self, cfg):
        """
        Persiste en un archivo config.json los parametros de configuracion.

        Args:
            cfg (_dict_): diccionario con los paramteros de configuracion para trabajar.
        """
        # Guardo el archivo config.json con la estructura de nuevo_archivo
        with open(self._file, 'w') as archivo:
            json.dump (cfg, archivo, indent = 4)

    def NuevoConfig():
        # Creo estructura de diccionario vacio para el archivo config.json
        nuevo_archivo = cfg()

        # Creo el archivo config.json con la estructura de nuevo_archivo
        with open('config.json', 'w') as archivo:
            json.dump (nuevo_archivo, archivo, indent = 4)  

if __name__ == '__main__':
    try:
        f_cfg = Cfg()
    except FileNotFoundError:
        f_cfg = Cfg.NuevoConfig()
        cfg = Cfg()
    f_cfg = cfg.GetCfg()
    print(f_cfg)