import json
import os
import xmltodict


class xmlcon_rd():
    def __init__(self, xmlcon_file=None, xml_str=None) -> None:
        self._xmlcon_file = xmlcon_file
        self.xml_str = xml_str
        self.sensors = self.__xml_to_json()
        self.__Sensor()

    def __read_xmlcon(self):
        # Lee el archivo XML
        if self.xml_str != None:
            # Corroboro si el xml es de tipo Lista
            if isinstance(self.xml_str, list):
                xml = ''
                xml = ''.join([str(elem) for elem in self.xml_str])
                return xml
            else:
                return self.xml_str
        elif self._xmlcon_file != None:
            with open(self._xmlcon_file, 'r') as xml_file:
                xml_content = xml_file.read()
            return xml_content
        else:
            return None

    def __xml_to_json(self):
        # Convierte el XML a JSON
        xml_contenedor = self.__read_xmlcon()
        self.json_data = xmltodict.parse(xml_contenedor, xml_attribs=False)
        return self.json_data            # regresa una lista

    def __Sensor(self):

        if 'Sensors' in self.json_data:
            sensores = self.json_data['Sensors']['sensor']
        elif 'SBE_InstrumentConfiguration' in self.json_data:
            instrumento = self.json_data['SBE_InstrumentConfiguration']['Instrument']
            if 'SBE 25plus' in instrumento['Name']:
                sensores = instrumento['TCP_Sensors']['Sensor']
                sensores_aux = instrumento['ExternalVoltageSensors']['Sensor']
                self._load_25plus(sensores, sensores_aux)
            elif instrumento['Name'] in ['SBE 911plus/917plus CTD', 'SBE 25 Sealogger CTD']:
                sensores = instrumento['SensorArray']['Sensor']
                self._load_911(sensores)

    def _load_911(self, sensores):
        self._sensors = {
            'Prim': {},
            'Sec': {},
            'Aux': {},
        }
        prim = [0, 1, 2]
        sec = [3, 4]
        aux = [3, 4, 5, 6, 7, 8]
        for num, sensor in enumerate(sensores):
            if num in prim:
                for key, val in sensor.items():
                    self._sensors['Prim'].update({key: val})
            elif not sensor is None:
                if 'TemperatureSensor' in sensor or 'ConductivitySensor' in sensor:
                    if num in sec:
                        for key, val in sensor.items():
                            self._sensors['Sec'].update({key: val})
                    elif not sensor is None:
                        for key, val in sensor.items():
                            self._sensors['Aux'].update({key: val})
                elif not sensor is None:
                    for key, val in sensor.items():
                        # compruebo si la key del diccionario no existe. Si existe, la creo como secundaria (,2)
                        if key in self._sensors['Aux']:
                            key += ', 2'
                        if key != 'NotInUse':
                            self._sensors['Aux'].update({key: val})
            else:
                pass

    def _load_25plus(self, sensores, sensores_aux):
        self._sensors = {
            'Prim': {},
            'Sec': {},
            'Aux': {},
        }
        prim = [0, 1, 2]
        aux = [0, 1, 2, 3, 4, 5, 6, 7]
        for num, sensor in enumerate(sensores):
            if num in prim:
                for key, val in sensor.items():
                    self._sensors['Prim'].update({key: val})

        for num, sensor in enumerate(sensores_aux):
            if num in aux:
                for key, val in sensor.items():
                    # compruebo si la key del diccionario no existe. Si existe, la creo como secundaria (,2)
                    if key in self._sensors['Aux']:
                        key += ', 2'
                    if key != 'NotInUse':
                        self._sensors['Aux'].update({key: val})

    def GetSensors(self):
        return self._sensors

    def GetPrimary(self):
        prim = self._sensors['Prim']
        return prim

    def GetSecondary(self):
        Sec = self._sensors['Sec']
        return Sec

    def GetAuxiliary(self):
        Aux = self._sensors['Aux']
        return Aux


if __name__ == '__main__':
    # E:\SiavoVB_Anexo\Estructura\VA\2024\003\CNV\0109.cnv
    f_xml = xmlcon_rd(xmlcon_file=f"E:\\Programas\\Py\\CNV_V1.01\\temp.xmlcon")
    # f_xml = xmlcon(os.getcwd(), 'test.xmlcon')
    sensors = f_xml.GetSensors()
    print(sensors)
