# Banc de capteurs

Banc de test de capteurs, piloté en Python. Les bibliothèques des fabricants sont intégrées en sous-modules git :

| Matériel | Bibliothèque | Sous-module |
|---|---|---|
| Régulateurs/débitmètres Bronkhorst (EL-FLOW, CORI-FLOW, EL-PRESS…), protocole ProPar | [bronkhorst-propar](https://github.com/bronkhorst-developer/bronkhorst-propar) | `externe/bronkhorst-propar` |
| Hub Sensirion SEK-SensorBridge, pour les capteurs température/humidité (SHT4x, SHT3x, SHTC3) | [python-shdlc-sensorbridge](https://github.com/Sensirion/python-shdlc-sensorbridge) | `externe/python-shdlc-sensorbridge` |

## Arborescence

```
externe/bronkhorst-propar/          sous-module git : bibliothèque ProPar de Bronkhorst
externe/python-shdlc-sensorbridge/  sous-module git : pilote du SensorBridge Sensirion
src/banc_capteurs/                  code du banc
scripts/                            installation et outils (test de connexion)
tests/                              tests automatiques (sans matériel)
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

Si le dépôt a été cloné sans `--recurse-submodules`, le script d'installation récupère les sous-modules.

## Vérifier l'installation

```bash
pytest
```

## Tester la connexion à un instrument Bronkhorst

```bash
python scripts/test_connexion_propar.py --lister-ports
python scripts/test_connexion_propar.py --port COM3
python scripts/test_connexion_propar.py --port COM3 --scanner   # plusieurs instruments sur FLOW-BUS
```

## Tester le SensorBridge et le capteur température/humidité

Le script alimente la voie choisie, liste les adresses I2C détectées, puis fait une mesure si le modèle du capteur
est précisé (`sht4x`, `sht3x` ou `shtc3`).

```bash
python scripts/test_connexion_sensorbridge.py --lister-ports
python scripts/test_connexion_sensorbridge.py --port COM4
python scripts/test_connexion_sensorbridge.py --port COM4 --voie 1 --sht sht4x
```

Options : `--tension` (alimentation du capteur, 3,3 V par défaut), `--baudrate` (460800 par défaut).

Sous Linux, l'utilisateur doit avoir accès aux ports série (groupe `dialout`).

## Mettre à jour les bibliothèques des fabricants

```bash
git submodule update --remote
git add externe
git commit -m "Mise à jour des sous-modules"
```
