import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QVBoxLayout, QWidget, QLabel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        # Crear un QComboBox
        self.comboBox = QComboBox(self)

        # Agregar algunos elementos al QComboBox
        self.comboBox.addItem("Elemento 1")
        self.comboBox.addItem("Elemento 2")
        self.comboBox.addItem("Elemento 3")

        # Etiqueta para mostrar el evento de recibir foco
        self.label = QLabel(self)

        # Configurar la ventana principal
        vbox = QVBoxLayout()
        vbox.addWidget(self.comboBox)
        vbox.addWidget(self.label)

        central_widget = QWidget(self)
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

        self.setGeometry(100, 100, 400, 300)
        self.setWindowTitle('PyQt5 Evento de Recibir Foco en ComboBox')
        self.show()

    def focusInEvent(self, event):
        # Manejar el evento de recibir foco en el QComboBox
        if event.widget() == self.comboBox:
            self.label.setText("QComboBox ha recibido el foco")
        else:
            self.label.setText("Otro widget ha recibido el foco")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    sys.exit(app.exec_())
