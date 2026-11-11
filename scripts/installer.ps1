# Cree l'environnement virtuel .venv et installe propar, le pilote SensorBridge et le projet
# (Windows / PowerShell). Si l'execution des scripts est bloquee, lancer :
#   powershell -ExecutionPolicy Bypass -File scripts\installer.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Verifier($etape) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Echec : $etape" -ForegroundColor Red
        exit 1
    }
}

git submodule update --init --recursive
Verifier "recuperation des sous-modules git"

if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
Verifier "creation de l'environnement virtuel (Python 3.9 ou plus recent est-il installe ?)"

.\.venv\Scripts\python.exe -m pip install --upgrade pip
Verifier "mise a jour de pip"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Verifier "installation des dependances"

Write-Host ""
Write-Host "Environnement pret. Pour l'activer :  .\.venv\Scripts\Activate.ps1"
