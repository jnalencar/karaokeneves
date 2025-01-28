#!/bin/bash

echo "Aguardando conexão com a internet..."
echo
while ! ping -c 1 -q google.com &>/dev/null; do
	sleep 5
done

echo "Conexão estabelecida."
echo
echo "Buscando atualizações."
cd ~/Desktop/Karaoke/karaokeneves
git pull

echo
echo "Iniciando programa..."
source venv/bin/activate
python3 app.py
