# Crée l'environnement virtuel .venv et installe propar + le projet (Windows / PowerShell).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

git submodule update --init --recursive
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host ""
Write-Host "Environnement pret. Pour l'activer :  .\.venv\Scripts\Activate.ps1"
