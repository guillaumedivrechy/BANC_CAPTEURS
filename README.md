# Banc de capteurs

Banc de test de capteurs. Les régulateurs/débitmètres Bronkhorst (EL-FLOW, CORI-FLOW, EL-PRESS…)
sont pilotés en Python via le protocole ProPar, avec la bibliothèque officielle
[bronkhorst-propar](https://github.com/bronkhorst-developer/bronkhorst-propar), intégrée ici en sous-module git.

## Arborescence

```
externe/bronkhorst-propar/   sous-module git : bibliothèque ProPar de Bronkhorst
src/banc_capteurs/           code du banc
scripts/                     installation et outils (test de connexion)
tests/                       tests automatiques (sans matériel)
```

## Installation

Prérequis : Python 3.9 ou plus récent, et git.

```bash
git clone --recurse-submodules https://github.com/guillaumedivrechy/BANC_CAPTEURS.git
cd BANC_CAPTEURS
```

Linux / macOS :

```bash
./scripts/installer.sh
source .venv/bin/activate
```

Windows (PowerShell) :

```powershell
.\scripts\installer.ps1
.\.venv\Scripts\Activate.ps1
```

Si le dépôt a été cloné sans `--recurse-submodules`, le script d'installation récupère le sous-module.

## Vérifier l'installation

```bash
pytest
```

## Tester la connexion à un instrument

```bash
python scripts/test_connexion_propar.py --lister-ports
python scripts/test_connexion_propar.py --port COM3
python scripts/test_connexion_propar.py --port COM3 --scanner   # plusieurs instruments sur FLOW-BUS
```

Sous Linux, l'utilisateur doit avoir accès au port série (groupe `dialout`).

## Mettre à jour propar

```bash
git submodule update --remote externe/bronkhorst-propar
git add externe/bronkhorst-propar
git commit -m "Mise à jour de bronkhorst-propar"
```
