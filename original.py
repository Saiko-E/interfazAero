import sys
import serial
import serial.tools.list_ports  
import json
import time
import csv
from datetime import datetime 

from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QPushButton, QComboBox, QLabel, QDialog, 
                               QCheckBox, QFileDialog)
from PySide6.QtCore import QThread, Signal
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock

NOMBRES_SENALES = [
    "Aceleración X (m/s²)", "Aceleración Y (m/s²)", "Aceleración Z (m/s²)",
    "Giroscopio X (°/s)", "Giroscopio Y (°/s)", "Giroscopio Z (°/s)", "Altitud (Barómetro - m)"
]
COLORES = ['r', 'g', 'b', 'c', 'm', 'y', 'w']

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
                            registro = {
                                "timestamp": time.time(),
                                "aceleracion": {"x": valores[0], "y": valores[1], "z": valores[2]},
                                "giroscopio": {"x": valores[3], "y": valores[4], "z": valores[5]},
                                "altitud": valores[6]
                            }
                            with open("caja_negra_vuelo.json", "a") as f:
                                f.write(json.dumps(registro) + "\n")
                    except ValueError:
                        pass 
        except Exception as e:
            print(f"Error de conexión Serial: {e}")

    def detener(self):
        self.corriendo = False
        if self.conexion and self.conexion.is_open:
            self.conexion.close()
        self.wait()

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
            checkbox.setChecked(estados_actuales[i])
            layout.addWidget(checkbox)
            self.casillas.append(checkbox)
        btn_cerrar = QPushButton("Aplicar Cambios")
        btn_cerrar.clicked.connect(self.accept) 
        layout.addStretch()
        layout.addWidget(btn_cerrar)
        self.setLayout(layout)

class InterfazDAS(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAS HUD - SAE AeroDesign")
        self.resize(1200, 700) 
        
        self.tiempo_inicio = time.time()
        self.historial_x = []
        self.historiales = [[] for _ in range(7)] 
        self.estados_graficas = [False, False, True, False, False, False, True]
        self.graficas = []
        self.lineas = []
        self.docks = [] 
        self.checks_individuales = [] 
        self.lector = None
        self.init_ui()

    def init_ui(self):
        widget_central = QWidget()
        layout_principal = QVBoxLayout()
        layout_controles = QHBoxLayout()
        self.combo_puertos = QComboBox()
        self.combo_puertos.setEditable(True) 
        
        if len(sys.argv) > 1:
             
            self.combo_puertos.addItem(sys.argv[1])
            self.combo_puertos.setCurrentText(sys.argv[1])
        else:
             
            puertos_fisicos = [puerto.device for puerto in serial.tools.list_ports.comports()]
            if puertos_fisicos:
                self.combo_puertos.addItems(puertos_fisicos)
            else:
                self.combo_puertos.addItem("No se detectó antena USB")
                
        self.btn_conectar = QPushButton("Conectar")
        self.btn_conectar.clicked.connect(self.toggle_conexion)
        self.btn_opciones = QPushButton("+")
        self.btn_opciones.setFixedSize(30, 30)
        self.btn_opciones.clicked.connect(self.abrir_ventana_senales)
        self.btn_ordenar = QPushButton("Auto-Organizar")
        self.btn_ordenar.clicked.connect(self.organizar_graficas)
        self.chk_autoscroll = QCheckBox("Seguir Tiempo Real (Global)")
        self.chk_autoscroll.setChecked(True)
        self.btn_exportar = QPushButton("Exportar 💾")
        self.btn_exportar.clicked.connect(self.exportar_datos)
        self.chk_ambos = QCheckBox("Exportar al Reiniciar")
        self.btn_reiniciar = QPushButton("Reiniciar Vuelo 🔄")
        self.btn_reiniciar.clicked.connect(self.reiniciar_vuelo)
        self.btn_limpiar = QPushButton("Limpiar Pantalla 🧹")
        self.btn_limpiar.clicked.connect(self.limpiar_graficas)
        
        layout_controles.addWidget(QLabel("Puerto:"))
        layout_controles.addWidget(self.combo_puertos)
        layout_controles.addWidget(self.btn_conectar)
        layout_controles.addWidget(self.btn_opciones)
        layout_controles.addWidget(self.btn_ordenar)
        layout_controles.addSpacing(15) 
        layout_controles.addWidget(self.chk_autoscroll)
        layout_controles.addWidget(self.btn_exportar)
        layout_controles.addWidget(self.chk_ambos)
        layout_controles.addWidget(self.btn_reiniciar)
        layout_controles.addWidget(self.btn_limpiar)
        layout_controles.addStretch()
        layout_principal.addLayout(layout_controles)
        
        self.area = DockArea()
        layout_principal.addWidget(self.area)
        
        for i in range(7):
            widget_dock = QWidget()
            layout_dock = QVBoxLayout(widget_dock)
            layout_dock.setContentsMargins(0, 0, 0, 0)
            layout_dock.setSpacing(0)
            
            chk_ind = QCheckBox("Seguir en vivo")
            chk_ind.setChecked(True)
            chk_ind.setStyleSheet("color: gray; margin-left: 5px;")
            self.checks_individuales.append(chk_ind)
            
            graf = pg.PlotWidget() 
            graf.setBackground('#1e1e1e')
            graf.showGrid(x=True, y=True)
            graf.setLabel('bottom', "Tiempo de Vuelo", units="s")
            graf.setMouseEnabled(x=True, y=True)
            linea = graf.plot(self.historial_x, self.historiales[i], pen=pg.mkPen(COLORES[i], width=2))
            
            layout_dock.addWidget(chk_ind)
            layout_dock.addWidget(graf)
            dock = Dock(NOMBRES_SENALES[i], size=(400, 200))
            dock.addWidget(widget_dock)
            
            self.docks.append(dock)
            self.graficas.append(graf)
            self.lineas.append(linea)
            
            if self.estados_graficas[i]:
                self.area.addDock(dock, 'right')
                
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

    def registrar_evento_json(self, tipo_evento):
        evento = {
            "evento_sistema": tipo_evento,
            "timestamp": time.time(),
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        try:
            with open("caja_negra_vuelo.json", "a") as f:
                f.write(json.dumps(evento) + "\n")
        except:
            pass 

    def limpiar_graficas(self):
        self.historial_x = []
        self.historiales = [[] for _ in range(7)]
        for i in range(7):
            if self.estados_graficas[i]:
                self.lineas[i].setData(self.historial_x, self.historiales[i])
        self.registrar_evento_json("LIMPIEZA_DE_PANTALLA_VISUAL")

    def reiniciar_vuelo(self):
        if self.chk_ambos.isChecked():
            guardado_exitoso = self.exportar_datos()
            if not guardado_exitoso: return 
        self.tiempo_inicio = time.time() 
        self.historial_x = []
        self.historiales = [[] for _ in range(7)]
        for i in range(7):
            if self.estados_graficas[i]:
                self.lineas[i].setData(self.historial_x, self.historiales[i])
        self.registrar_evento_json("REINICIO_DE_VUELO_CRONOMETRO")

    def exportar_datos(self):
        ruta_archivo, filtro = QFileDialog.getSaveFileName(
            self, "Exportar Datos en Pantalla", "", "CSV para Excel (*.csv);;Formato JSON (*.json)"
        )
        
        if not ruta_archivo: 
            return False 
            
        if "csv" in filtro.lower() and not ruta_archivo.lower().endswith('.csv'):
            ruta_archivo += '.csv'
        elif "json" in filtro.lower() and not ruta_archivo.lower().endswith('.json'):
            ruta_archivo += '.json'

        num_muestras = len(self.historial_x)
        
        if ruta_archivo.endswith(".csv"):
            with open(ruta_archivo, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Tiempo (s)"] + NOMBRES_SENALES)
                for iteracion in range(num_muestras):
                    fila = [self.historial_x[iteracion]] + [self.historiales[sensor][iteracion] for sensor in range(7)]
                    writer.writerow(fila)
        else:
            datos_json = {"Tiempo (s)": self.historial_x}
            for j in range(7):
                datos_json[NOMBRES_SENALES[j]] = self.historiales[j]
            with open(ruta_archivo, mode='w', encoding='utf-8') as f:
                json.dump(datos_json, f, indent=4, ensure_ascii=False)
                
        self.registrar_evento_json("EXPORTACION_MANUAL_GUARDADA")
        return True

    def toggle_conexion(self):
        if self.btn_conectar.text() == "Conectar":
            seleccion = self.combo_puertos.currentText()
            self.tiempo_inicio = time.time()
            self.historial_x = []
            self.historiales = [[] for _ in range(7)]
            
            self.lector = LectorSerial(seleccion, 115200)
            self.lector.datos_recibidos.connect(self.actualizar_graficas)
            self.lector.start()
            self.btn_conectar.setText("Desconectar")
            self.btn_conectar.setStyleSheet("background-color: #ff4c4c; color: white;")
            self.registrar_evento_json("INICIO_DE_VUELO_SERIAL")
        else:
            if self.lector: self.lector.detener()
            self.btn_conectar.setText("Conectar")
            self.btn_conectar.setStyleSheet("")
            self.registrar_evento_json("FIN_DE_VUELO_DESCONEXION")
    
    def abrir_ventana_senales(self):
        ventana = VentanaSenales(self.estados_graficas, self)
        if ventana.exec(): 
            for i, cb in enumerate(ventana.casillas):
                estaba_activa = self.estados_graficas[i]
                esta_activa = cb.isChecked()
                self.estados_graficas[i] = esta_activa
                if esta_activa and not estaba_activa:
                    self.area.addDock(self.docks[i], 'bottom')
                elif not esta_activa and estaba_activa:
                    self.docks[i].close()
                    
    def organizar_graficas(self):
        docks_activos = []
        for i in range(7):
            if self.estados_graficas[i]: docks_activos.append(self.docks[i])
        if not docks_activos: return 
        referencia = docks_activos[0]
        for dock in docks_activos[1:]:
            self.area.moveDock(dock, 'bottom', referencia)
            referencia = dock
        for i in range(1, len(docks_activos), 2):
            self.area.moveDock(docks_activos[i], 'right', docks_activos[i-1])
            
    def actualizar_graficas(self, valores):
        tiempo_actual = time.time() - self.tiempo_inicio
        self.historial_x.append(tiempo_actual)
        for i in range(7):
            self.historiales[i].append(valores[i])
            if self.estados_graficas[i]:
                self.lineas[i].setData(self.historial_x, self.historiales[i])
                if self.chk_autoscroll.isChecked() and self.checks_individuales[i].isChecked():
                    tiempo_minimo = max(0, tiempo_actual - 10)
                    self.graficas[i].setXRange(tiempo_minimo, tiempo_actual)

if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    ventana = InterfazDAS()
    ventana.show()
    app.exec()