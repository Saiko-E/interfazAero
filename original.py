import sys
import serial
import json
import time

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QComboBox, QLabel, QDialog, QCheckBox, QScrollArea)
from PySide6.QtCore import QThread, Signal
import pyqtgraph as pg

NOMBRES_SENALES = [
    "Aceleración X (m/s²)", "Aceleración Y (m/s²)", "Aceleración Z (m/s²)",
    "Giroscopio X (°/s)", "Giroscopio Y (°/s)", "Giroscopio Z (°/s)", "Altitud (Barómetro - m)"
]
COLORES = ['r', 'g', 'b', 'c', 'm', 'y', 'w']

# Listener and json writer thread
class LectorSerial(QThread):
    datos_recibidos = Signal(list)

    def __init__(self, puerto, baudrate):
        super().__init__()
        self.puerto = puerto
        self.baudrate = baudrate
        self.corriendo = True
        self.conexion = None

    def run(self):
        try:
            self.conexion = serial.Serial(self.puerto, self.baudrate)
            while self.corriendo:
                if self.conexion.in_waiting > 0:
                    linea = self.conexion.readline().decode('utf-8').strip()
                    try:
                        valores = [float(x) for x in linea.split(',')]
                        if len(valores) == 7: 
                            self.datos_recibidos.emit(valores)
                            
                            # Quemamos los datos en el archivo JSON
                            registro = {
                                "timestamp": time.time(),
                                "aceleracion": {"x": valores[0], "y": valores[1], "z": valores[2]},
                                "giroscopio": {"x": valores[3], "y": valores[4], "z": valores[5]},
                                "altitud": valores[6]
                            }
                            with open("caja_negra_vuelo.json", "a") as archivo:
                                archivo.write(json.dumps(registro) + "\n")
                                
                    except ValueError:
                        pass 
        except Exception as e:
            print(f"Error de conexión: {e}")

    def detener(self):
        self.corriendo = False
        if self.conexion and self.conexion.is_open:
            self.conexion.close()
        self.wait()


# signal configuration window
class VentanaSenales(QDialog):
    def __init__(self, estados_actuales, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Señales")
        self.resize(300, 350)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Selecciona las gráficas a mostrar:</b>"))
        
        self.casillas = []
        for i, senal in enumerate(NOMBRES_SENALES):
            checkbox = QCheckBox(senal)
            checkbox.setChecked(estados_actuales[i]) # Lee si estaba activa o no
            layout.addWidget(checkbox)
            self.casillas.append(checkbox)
            
        btn_cerrar = QPushButton("Aplicar Cambios")
        btn_cerrar.clicked.connect(self.accept) 
        
        layout.addStretch()
        layout.addWidget(btn_cerrar)
        self.setLayout(layout)


# HUD main interface
class InterfazDAS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAS HUD - SAE AeroDesign")
        self.resize(900, 700)
        
        self.historial_x = list(range(100))
        # Creamos 7 listas de 100 ceros (una para cada señal)
        self.historiales = [[0] * 100 for _ in range(7)] 
        
        # Z accel axis and altitud are visible by default, the rest are hidden
        self.estados_graficas = [False, False, True, False, False, False, True]
        
        self.graficas = []
        self.lineas = []
        self.lector = None
        self.init_ui()

    def init_ui(self):
        widget_central = QWidget()
        layout_principal = QVBoxLayout()
        
        # Panel superior
        layout_controles = QHBoxLayout()
        self.combo_puertos = QComboBox()
        self.combo_puertos.setEditable(True) 
        self.combo_puertos.addItems(["/dev/pts/2", "/dev/pts/3", "COM10"]) 
        
        self.btn_conectar = QPushButton("Conectar")
        self.btn_conectar.clicked.connect(self.toggle_conexion)
        
        self.btn_opciones = QPushButton("+")
        self.btn_opciones.setFixedSize(30, 30)
        self.btn_opciones.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.btn_opciones.clicked.connect(self.abrir_ventana_senales)
        
        layout_controles.addWidget(QLabel("Puerto Virtual:"))
        layout_controles.addWidget(self.combo_puertos)
        layout_controles.addWidget(self.btn_conectar)
        layout_controles.addWidget(self.btn_opciones)
        layout_controles.addStretch()
        
        layout_principal.addLayout(layout_controles)
        
        # Panel de Gráficas (con scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        widget_scroll = QWidget()
        self.layout_graficas = QVBoxLayout(widget_scroll)
        
       
        for i in range(7):
            graf = pg.PlotWidget(title=NOMBRES_SENALES[i])
            graf.setBackground('#1e1e1e')
            graf.showGrid(x=True, y=True)
            graf.setXRange(0, 100) 
            graf.setMouseEnabled(x=False, y=True)
            graf.setMinimumHeight(200) 
            
            linea = graf.plot(self.historial_x, self.historiales[i], pen=pg.mkPen(COLORES[i], width=2))
            
            self.graficas.append(graf)
            self.lineas.append(linea)
            self.layout_graficas.addWidget(graf)
            
            if not self.estados_graficas[i]:
                graf.hide()
                
        scroll.setWidget(widget_scroll)
        layout_principal.addWidget(scroll)
        
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

    def toggle_conexion(self):
        if self.btn_conectar.text() == "Conectar":
            puerto = self.combo_puertos.currentText()
            self.lector = LectorSerial(puerto, 115200)
            self.lector.datos_recibidos.connect(self.actualizar_graficas)
            self.lector.start()
            self.btn_conectar.setText("Desconectar")
            self.btn_conectar.setStyleSheet("background-color: #ff4c4c; color: white;")
        else:
            if self.lector:
                self.lector.detener()
            self.btn_conectar.setText("Conectar")
            self.btn_conectar.setStyleSheet("")
    
    def abrir_ventana_senales(self):
        ventana = VentanaSenales(self.estados_graficas, self)
        
        if ventana.exec(): 
            for i, cb in enumerate(ventana.casillas):
                self.estados_graficas[i] = cb.isChecked()
                # Mostramos u ocultamos la gráfica según la casilla
                if self.estados_graficas[i]:
                    self.graficas[i].show()
                else:
                    self.graficas[i].hide()
    
    def actualizar_graficas(self, valores):
        for i in range(7):
            self.historiales[i] = self.historiales[i][1:] + [valores[i]]
            
            if self.estados_graficas[i]:
                self.lineas[i].setData(self.historial_x, self.historiales[i])

if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        
    ventana = InterfazDAS()
    ventana.show()
    app.exec()