import platform
import subprocess
import winreg
import uuid

# Mini
key = '4C530006041107108575'
# Novatech
key = '0000000000007D'


def get_hard_drive_serial_number():
    # Levanto los numeros de serie de los discos que esten conectados a la PC,
    # incluyendo el del Pendriver (KEY)
    system = platform.system()
    if system == 'Windows':
        command = 'wmic diskdrive get serialnumber'
    elif system == 'Linux':
        command = 'udevadm info --query=property --name=/dev/sda | grep ID_SERIAL'
    else:
        return None

    try:
        result = subprocess.check_output(
            command, shell=True, universal_newlines=True)
        # devuelve una lista con todos los numeros de serie de los discos
        serial_number = [linea.strip()
                         for linea in result.splitlines() if linea.strip()]
        if 'SerialNumber' in serial_number:
            serial_number.pop(serial_number.index('SerialNumber'))
        return serial_number
    except subprocess.CalledProcessError:
        return None


def Key_Reg(devices=[0]):
    # Valido la llave del pendriver
    try:
        if key in devices:
            devices.pop(devices.index(key))
            return devices, True
        else:
            return devices, False
    except:
        return devices, False


def registrar_uuid(uuid_str):
    try:
        clave_registro = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\NombreAplicacion", 0, winreg.KEY_WRITE)
        winreg.SetValueEx(clave_registro, "UUID", 0, winreg.REG_SZ, uuid_str)
        winreg.CloseKey(clave_registro)
        # print("UUID registrado con éxito en el Registro de Windows.")
    except Exception as e:
        # print("Error al registrar la UUID en el Registro de Windows:", str(e))
        msg = f"Error al registrar la UUID en el Registro de Windows: {str(e)}"


def validar_uuid(cadena):
    try:
        # Generar una clave UUID a partir de la cadena
        uuid_str = uuid.uuid5(uuid.NAMESPACE_DNS, cadena)
        return uuid_str
    except ValueError:
        return False


def create_reg(uuid=0):
    clave_padre = winreg.HKEY_CURRENT_USER
    ruta_clave = f"Software\mscbgc"
    clave_nombre = 'device_ID'
    try:
        nueva_clave = winreg.CreateKey(clave_padre, ruta_clave)
        winreg.SetValueEx(nueva_clave, clave_nombre,
                          0, winreg.REG_SZ, str(uuid))
        winreg.CloseKey(nueva_clave)
    except:
        msg = f'Ah ocurrido un error al intentar registrar el producto'
        return msg
    msg = f'Activación exitosa!!!'
    return msg


def read_reg(uuid_str):
    # Abrir una clave existente o crear una nueva clave
    clave_padre = winreg.HKEY_CURRENT_USER
    ruta_clave = f"Software\mscbgc"
    clave_nombre = 'device_ID'
    try:
        clave = winreg.OpenKey(clave_padre, ruta_clave)
        valor, tipo = winreg.QueryValueEx(clave, clave_nombre)
        winreg.CloseKey(clave)
        if str(uuid_str) == valor:
            return True
    except FileNotFoundError:
        return None


def check():
    # Cargo los numeros de serie de los discos de almacenamiento y la llave
    serial_number = get_hard_drive_serial_number()
    # print("Número de serie del disco duro:", serial_number)

    # Verifico que la llave sea la correcta y luego valido el uuid del disco
    devices, validate = Key_Reg(serial_number)
    uuid_str = validar_uuid(devices[0])
    # print("Número de UUID del disco duro:", uuid_str)
    # Al iniciar el programa verifico que este registrado
    key_value = read_reg(uuid_str)
    if key_value == None:
        msg = f'Software no registrado'
        if validate:
            msg = create_reg(uuid_str)
        else:
            msg = f'Se requiere de una llave para activar el software'
    elif key_value:
        msg = f'Programa registrado'
        validate = True
    return (validate, msg)
