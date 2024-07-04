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

class DBS(NMEA):
    def __init__(self, port = 'COM1', BR = 4800, timeout = 2, sts = 'DBS'):
        expreg_nmea = '\\$??(?P<sentencia>.*?)[\\,|\\, ](?P<ZF>\\d{1,})[\\.|\\. ](?P<ZFdec>\\d{1,})[\\,|\\, ]'+\
        '(?P<ZunF>[f])[\\,|\\, ](?P<ZM>\\d{1,})[\\.|\\. ](?P<ZMdec>\\d{1,})[\\,|\\, ](?P<ZunM>[M])[\\,|\\, ]' +\
        '(?P<ZFa>\\d{1,})[\\.|\\. ](?P<ZFadec>\\d{1,})[\\,|\\, ](?P<ZunFa>[F])'+\
        '(?P<value>.*?)\\r?\\n?'
        NMEA.__init__(self, port, BR, timeout, sts, expreg_nmea)

#        self.day = self.__dato['dia'].zfill(2)
#        self.month = self.__dato['Mes'].zfill(2)
#        self.year = self.__dato['Año'].zfill(2)
#        self.hour = self.__dato['hour'].zfill(2)
#        self.min = self.__dato['min'].zfill(2)
#        self.sec = self.__dato['sec'].zfill(2)

    def Get_Z_Metros(self):
        """ Regresa la profundidad en metros
        """
        try:
            prof = str(int(self.NMEA_data['ZM']) + int(self.NMEA_data['ZMdec']) / 100)
            return (prof)
        except AttributeError:
            return 'NaN'

    def Get_Z_Pies(self):
        """ Regresa la profundidad en pies
        """
        try:
            date = str(int(self.NMEA_data['ZF']) + int(self.NMEA_data['ZFdec']) / 100)
            return (date)
        except AttributeError:
            return 'NaN'