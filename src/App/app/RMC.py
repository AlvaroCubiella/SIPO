#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Morochos
#
# Created:     11/07/2019
# Copyright:   (c) Morochos 2019
# Licence:     <your licence>
#-------------------------------------------------------------------------------
from app.NMEA import NMEA
import datetime

class RMC(NMEA):
    def __init__(self, port = 'COM1', BR = 4800, timeout = 2, sts = 'RMC'):
        #expreg_nmea = "\\$??(?P<sentencia>.*?)[\\,|\\, ](?P<hour>\\d{1,2})(?P<min>\\d{1,2})(?P<sec>\\d{1,2})" +\
        #"\\.(?P<msec>\\d{1,3})[\\,|\\, ](?P<status>.*?)[\\,|\\, ](?P<Lat>\\d{1,2})(?P<Lat_min>\\d{1,2}[\\.|\\,]"+\
        #"\\d{1,6})[\\,|\\, ](?P<Lat_cuadrante>[N|n|S|s])[\\,|\\, ](?P<Lon>\\d{1,3})(?P<Lon_min>\\d{1,2}[\\.|\\,]"+\
        #"\\d{1,6})[\\,|\\, ](?P<Lon_cuadrante>[W|w|E|e])[\\,|\\, ](?P<Speed>\\d{1,3}\\.\\d{1,2})[\\,|\\, ](?P<Dir>"+\
        #"\\d{1,3}\\.\\d{1,2})[\\,|\\, ](?P<dia>\\d{1,2})(?P<Mes>\\d{1,2})(?P<Año>\\d{1,4})[\\,|\\, ](?P<value>.*?)\\r?\\n"

        expreg_nmea = "\\$??(?P<sentencia>.*?)[\\,|\\, ](?P<hour>\\d{1,2})(?P<min>\\d{1,2})(?P<sec>\\d{1,2})" +\
        "[\\.(?P<msec>\\d{1,3})|\\][\\,|\\, ](?P<status>.*?)[\\,|\\, ](?P<Lat>\\d{1,2})(?P<Lat_min>\\d{1,2}[\\.|\\,]"+\
        "\\d{1,6})[\\,|\\, ](?P<Lat_cuadrante>[N|n|S|s])[\\,|\\, ](?P<Lon>\\d{1,3})(?P<Lon_min>\\d{1,2}[\\.|\\,]"+\
        "\\d{1,6})[\\,|\\, ](?P<Lon_cuadrante>[W|w|E|e])[\\,|\\, ](?P<Speed>\\d{1,3}\\.\\d{1,2})[\\,|\\, ](?P<Dir>"+\
        "\\d{1,3}\\.\\d{1,2})[\\,|\\, ](?P<dia>\\d{1,2})(?P<Mes>\\d{1,2})(?P<Año>\\d{1,4})[\\,|\\, ](?P<value>.*?)\\r?\\n"

        NMEA.__init__(self, port, BR, timeout, sts, expreg_nmea)

    def Get_Time(self, sep=':'):
        """ Regresa la hora de NMEA HH:MM:SS
        -sep = separador para formato de hora. Por defecto ':'
        """
        try:
            time = self.NMEA_data['hour'].zfill(2)+str(sep)+self.NMEA_data['min'].zfill(2)+str(sep)+self.NMEA_data['sec'].zfill(2)
            return (time)
        except AttributeError:
            return None

    def Get_Date(self, sep='/'):
        """ Regresa la fecha de NMEA DD/MM/YY
        -sep = separador para formato de fecha. Por defecto '/'
        """
        try:
            date = self.NMEA_data['dia'].zfill(2)+str(sep)+self.NMEA_data['Mes'].zfill(2)+str(sep)+self.NMEA_data['Año'].zfill(2)
            return (date)
        except AttributeError:
            return None

    def Get_DateTime(self):
        """ Regresa la fecha y hora de NMEA como clase datetime.datetime, luego dar el formato desea"""
        try:
            fechahora = datetime.datetime(int('20'+self.NMEA_data['Año']),int(self.NMEA_data['Mes']),int(self.NMEA_data['dia']),int(self.NMEA_data['hour']),\
            int(self.NMEA_data['min']),int(self.NMEA_data['sec']))
            return (fechahora)
        except:
            return None

    def Get_Latitud_Grados(self):
        """Regresa el valor de latitud expresado en grados y decimas de grado DD.DDDD"""
        try:
            lat = round(float(self.NMEA_data['Lat']) + float(self.NMEA_data['Lat_min'])/60, 6)
            if 's' in self.NMEA_data['Lat_cuadrante'].lower():
                return str(lat * -1)
            else:
                return str(lat)
        except AttributeError:
            return None

    def Get_Longitud_Grados(self):
        """Regresa el valor de longitud expresado en grados y decimas de grado DDD.DDDD"""
        try:
            lon = round(float(self.NMEA_data['Lon']) + float(self.NMEA_data['Lon_min'])/60, 6)
            if 'w' in self.NMEA_data['Lon_cuadrante'].lower():
                return str(lon * -1)
            else:
                return str(lon)
        except AttributeError:
            return None

    def Get_Lat_GradosMinutos(self):
        """Regresa el valor de Latitud en grados y minutos"""
        try:
            lat = (self.NMEA_data['Lat'] + ' ' + self.NMEA_data['Lat_min'] + ' ' +\
                self.NMEA_data['Lat_cuadrante'])
            return lat
        except AttributeError:
            return None

    def Get_Lon_GradosMinutos(self):
        """Regresa el valor de longitud en grados y minutos"""
        try:
            lon = (self.NMEA_data['Lon'] + ' ' + self.NMEA_data['Lon_min'] + ' ' +\
                self.NMEA_data['Lon_cuadrante'])
            return lon
        except AttributeError:
            return None

    def Get_Speed(self):
        """Regresa la velocidad"""
        try:
            speed = self.NMEA_data['Speed']
            return speed
        except AttributeError:
            return None 