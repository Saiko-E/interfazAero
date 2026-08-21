#!/usr/bin/env python3
 
"""
you must excecute the following command in a terminal to create a virtual serial port:
socat -d -d pty,raw,echo=0 pty,raw,echo=0
@author: saiko
"""

import serial
import time
import random

PUERTO = '/dev/pts/5'  
BAUD_RATE = 115200 

def generar_datos():
    accel_x = round(random.uniform(-1.0, 1.0), 2)
    accel_y = round(random.uniform(-1.0, 1.0), 2)
    accel_z = round(random.uniform(9.0, 10.5), 2) 
    giro_x = round(random.uniform(-5.0, 5.0), 2)
    giro_y = round(random.uniform(-5.0, 5.0), 2)
    giro_z = round(random.uniform(-5.0, 5.0), 2)
    altitud = round(random.uniform(2240.0, 2245.0), 1) 
    
    trama = f"{accel_x},{accel_y},{accel_z},{giro_x},{giro_y},{giro_z},{altitud}\n"
    return trama

def main():
    try:
        puerto_serial = serial.Serial(PUERTO, BAUD_RATE)
        print("¡Transmitiendo telemetría del avión...\n")
        while True:
            datos = generar_datos()
            puerto_serial.write(datos.encode('utf-8')) 
            print(f"Transmitiendo -> {datos.strip()}") 
            time.sleep(0.1) 
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()