#!/bin/bash

if ! python3 -m venv venv 2>/dev/null; then
    echo "error please install python3-venv："
    echo "  sudo apt install python3-venv"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

if [ ! -f "venv/installed" ]; then
    if [ -f "requirements.txt" ]; then
		echo "Installing wheel for faster installing"
		pip3 install wheel
        echo "Installing dependencies..."
        pip3 install -r requirements.txt
        touch venv/installed
    else
        echo "requirements.txt not found, skipping dependency installation."
    fi
else
    echo "Dependencies already installed, skipping installation."
fi

if [ ! -f "proxy.txt" ]; then
	echo "Copying configuration file"
	cp proxy.example.txt proxy.txt
else
	echo "Skipping proxy.txt copying"
fi

if [ ! -f "keys.txt" ]; then
	echo "Copying configuration file"
	cp keys.example.txt keys.txt
else
	echo "Skipping keys.txt copying"
fi

while true
do
	python3 main.py
	echo Restarting the program in 10 seconds...
	sleep 10
done
