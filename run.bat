@echo off
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

if not exist venv\Lib\site-packages\installed (
    if exist requirements.txt (
		echo installing wheel for faster installing
		pip install wheel
        echo Installing dependencies...
        pip install -r requirements.txt
        echo. > venv\Lib\site-packages\installed
    ) else (
        echo requirements.txt not found, skipping dependency installation.
    )
) else (
    echo Dependencies already installed, skipping installation.
)

if not exist proxy.txt (
	echo Copying configuration file
	copy proxy.example.txt proxy.txt
) else (
	echo Skipping proxy.txt copying
)

if not exist keys.txt (
	echo Copying configuration file
	copy keys.example.txt keys.txt
) else (
	echo Skipping keys.txt copying
)

echo Starting the bot...
:loop
python main.py
echo Restarting the program in 10 seconds...
timeout /t 10 /nobreak >nul
goto :loop
