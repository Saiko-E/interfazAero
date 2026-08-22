import subprocess
import sys
import re

print("🚀 Iniciando Sistema ")
socat = subprocess.Popen(
    ['socat', '-d', '-d', 'pty,raw,echo=0', 'pty,raw,echo=0'],
    stderr=subprocess.PIPE,
    text=True
)

puertos = []
while len(puertos) < 2:
    linea = socat.stderr.readline()
    if not linea: break
    match = re.search(r'PTY is (/dev/pts/\d+)', linea)
    if match: puertos.append(match.group(1))

if len(puertos) == 2:
    print(f" Enlace establecido: {puertos[0]} (Avión) <---> {puertos[1]} (Tierra)")
else:
    print("Error al crear puertos. Instala socat (sudo apt install socat / sudo pacman -S socat)")
    socat.terminate()
    sys.exit(1)

simulador = subprocess.Popen([sys.executable, 'simulacion.py', puertos[0]])

interfaz = subprocess.Popen([sys.executable, 'original.py', puertos[1]])

try:
    interfaz.wait()
except KeyboardInterrupt:
    pass
finally:
    print("\nApagando")
    simulador.terminate()
    interfaz.terminate()
    socat.terminate()
    print("Apagado completo")