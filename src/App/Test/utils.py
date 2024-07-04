import os

def cls_to_qml(file):
    # Lee el archivo CLS
    with open(file, 'r') as f:
        lines = f.readlines()

    filename = os.path.splitext(file)
    # Abre un archivo QML y escribe el encabezado
    with open(f"{filename[0]}.qml", 'w') as qml_file:
        qml_file.write('<qgis style="2">\n')
        qml_file.write('  <transparencyLevelIntervals useGlobal="true">\n')

        # Itera sobre las líneas del archivo CLS para obtener los datos
        for line in lines:
            data = line.strip().split('"')  # Dividir la línea por comillas para obtener datos relevantes
            if len(data) >= 6:
                # Extrae la información necesaria para el QML (puede variar según los datos en tu archivo)
                symbol_id = data[0]
                color = data[3]
                symbol_name = data[5]

                # Escribe la información en el archivo QML
                qml_file.write(f'    <interval transparency="0" upper="0" lower="0" upperBoundInclusive="1" value="{symbol_id}">\n')
                qml_file.write(f'      <symbol alpha="1" clip_to_extent="1" type="marker" name="{symbol_name}">\n')
                qml_file.write(f'        <layer pass="0" class="SimpleMarker" locked="0">\n')
                qml_file.write(f'          <prop k="angle" v="0"/>\n')
                qml_file.write(f'          <prop k="color" v="{color}"/>\n')
                qml_file.write(f'          <prop k="horizontal_anchor_point" v="1"/>\n')
                qml_file.write(f'          <prop k="joinstyle" v="bevel"/>\n')
                qml_file.write(f'          <prop k="name" v="circle"/>\n')
                qml_file.write(f'          <prop k="offset" v="0,0"/>\n')
                qml_file.write(f'          <prop k="offset_unit" v="MM"/>\n')
                qml_file.write(f'          <prop k="outline_color" v="0,0,0,255"/>\n')
                qml_file.write(f'          <prop k="outline_style" v="solid"/>\n')
                qml_file.write(f'          <prop k="outline_width_unit" v="MM"/>\n')
                qml_file.write(f'          <prop k="outline_width" v="0"/>\n')
                qml_file.write(f'          <prop k="scale_method" v="diameter"/>\n')
                qml_file.write(f'          <prop k="size" v="2"/>\n')
                qml_file.write(f'          <prop k="size_unit" v="MM"/>\n')
                qml_file.write(f'          <prop k="vertical_anchor_point" v="1"/>\n')
                qml_file.write(f'        </layer>\n')
                qml_file.write(f'      </symbol>\n')
                qml_file.write(f'    </interval>\n')

        # Cierra el archivo QML
        qml_file.write('  </transparencyLevelIntervals>\n')
        qml_file.write('</qgis>\n')

file = 'E:\\QGIS\\TEMP.cls'

cls_to_qml(file)
print('fin')