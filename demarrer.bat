@echo off
cd /d "%~dp0"
call venv\Scripts\activate
set SECRET_KEY=Essai1234
start http://127.0.0.1:5000
waitress-serve --host=127.0.0.1 --port=5000 app:app