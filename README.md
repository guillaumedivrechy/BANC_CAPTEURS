# Banc de capteurs

Banc de test de capteurs, piloté en Python. Les bibliothèques des fabricants sont intégrées en sous-modules git :

| Matériel | Bibliothèque | Sous-module |
|---|---|---|
| Régulateurs/débitmètres Bronkhorst (EL-FLOW, CORI-FLOW, EL-PRESS…), protocole ProPar | [bronkhorst-propar](https://github.com/bronkhorst-developer/bronkhorst-propar) | `externe/bronkhorst-propar` |
| Hub Sensirion SEK-SensorBridge, pour les capteurs température/humidité (SHT4x, SHT3x, SHTC3) | [python-shdlc-sensorbridge](https://github.com/Sensirion/python-shdlc-sensorbridge) | `externe/python-shdlc-sensorbridge` |

La centrale d'acquisition **Keysight 34970A** (liaison RS-232) n'a pas de bibliothèque officielle : son pilote est
écrit dans ce projet, dans `src/banc_capteurs/equipements/keysight_34970a/`. Le
[guide RS-232](src/banc_capteurs/equipements/keysight_34970a/README.md) décrit le câblage, la configuration de
l'appareil et les codes d'erreur.

La spécification du logiciel est en cours de rédaction dans [docs/specification.md](docs/specification.md).

## Arborescence

```
docs/                               spécification du logiciel
externe/bronkhorst-propar/          sous-module git : bibliothèque ProPar de Bronkhorst
externe/python-shdlc-sensorbridge/  sous-module git : pilote du SensorBridge Sensirion
src/banc_capteurs/                  code du banc
  equipements/keysight_34970a/      pilote de la centrale d'acquisition Keysight 34970A
scripts/                            installation et outils (test de connexion)
tests/                              tests automatiques (sans matériel)
```

## Installation

Prérequis : Python 3.9 ou plus récent, git, et un accès à Internet pendant l'installation.

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

Si PowerShell refuse d'exécuter les scripts (« l'exécution de scripts est désactivée »), autoriser les scripts
pour la fenêtre en cours, puis relancer les deux commandes :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
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

Options : `--tension` (alimentation du capteur : 1,2 à 5,5 V par valeurs fixes, 3,3 V par défaut),
`--adresse-i2c` (si le capteur n'est pas à son adresse habituelle, ex. `0x45`), `--baudrate` (460800 par défaut).

## Tester la centrale Keysight 34970A

Au préalable, en face avant : touche **Interface** → RS-232 (l'appareil sort d'usine en GPIB). Utiliser un câble
**null-modem**. Les réglages d'usine (57600 bauds, 8 bits sans parité, XON/XOFF) sont ceux utilisés par défaut.

```bash
python scripts/test_connexion_34970a.py --lister-ports
python scripts/test_connexion_34970a.py --port COM3
python scripts/test_connexion_34970a.py --port COM3 --fonction VOLT:DC --voies 101
python scripts/test_connexion_34970a.py --port COM3 --fonction TEMP --parametres TC,K --voies 101:105
```

Options : `--baudrate`, `--flux` (`xonxoff`, `rtscts`, `dsrdtr`, `aucun`), `--stopbits` (essayer 2 en cas d'erreur 511).

Utilisation dans le code :

```python
from banc_capteurs.equipements.keysight_34970a import Keysight34970A

with Keysight34970A.rs232("COM3") as daq:          # SYST:REM ... SYST:LOC
    daq.configurer("TEMP", "101:105", "TC,K")
    daq.demarrer_scan("101:105", intervalle_s=10)  # mesures stockées dans l'appareil
    ...
    for m in daq.lire_memoire():                   # lit et vide la mémoire
        print(m.horodatage, m.voie, m.valeur)
```

Sous Linux, l'utilisateur doit avoir accès aux ports série (groupe `dialout`).

## Mettre à jour les bibliothèques des fabricants

```bash
git submodule update --remote
git add externe
git commit -m "Mise à jour des sous-modules"
```
