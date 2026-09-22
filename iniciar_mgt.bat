@echo off
setlocal
cd /d "%~dp0"
title MGT Sys

if not exist ".venv\Scripts\python.exe" (
    echo ================================================
    echo  Primeira execucao - preparando o MGT Sys...
    echo  Isso pode levar um minuto. Por favor, aguarde.
    echo ================================================
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERRO: nao encontrei o Python instalado.
        echo Instale em https://www.python.org/downloads/
        echo e marque a opcao "Add python.exe to PATH" durante a instalacao.
        echo.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Abrindo o MGT Sys no navegador...
echo Para FECHAR o sistema, apenas feche esta janela.
echo.

start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"

python run.py

pause
