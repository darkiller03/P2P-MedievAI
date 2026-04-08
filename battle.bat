@echo off
REM Battle CLI batch file
REM Usage: battle run square_scenario -d data.txt
REM        battle tourney -N 5 -d results.txt
REM        etc.

setlocal enabledelayedexpansion

REM Get the directory where this batch file is located
set SCRIPT_DIR=%~dp0

REM Run battle.py from the script directory
python "%SCRIPT_DIR%battle.py" %*

endlocal
