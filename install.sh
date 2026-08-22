#!/bin/bash

echo "iniciando instalacion"

if ! command -v socat &> /dev/null; then
    echo "Instalar socat"
    echo "  - Ubuntu/Debian: sudo apt install socat"
    echo "  - Manjaro/Arch: sudo pacman -S socat"
    exit 1
fi

echo " Creando entorno virtual aislado (venv)..."
python3 -m venv venv

echo "📥 Instalando librerías..."
./venv/bin/pip install --upgrade pip > /dev/null 2>&1
./venv/bin/pip install pyserial PySide6 pyqtgraph > /dev/null 2>&1

echo "Acceso Directo"
DIRECTORIO_ACTUAL=$(pwd)

cat <<EOF > AeroDesign.desktop
[Desktop Entry]
Type=Application
Name=AeroDesign HUD
Comment=Estación Terrena de Telemetría SAE
Exec=$DIRECTORIO_ACTUAL/venv/bin/python $DIRECTORIO_ACTUAL/main.py
Icon=$DIRECTORIO_ACTUAL/icono.png
Terminal=true
Categories=Development;Science;
EOF

cp AeroDesign.desktop ~/.local/share/applications/
chmod +x AeroDesign.desktop

