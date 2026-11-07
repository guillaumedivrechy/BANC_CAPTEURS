# Communication RS-232 avec le Keysight 34970A

Guide de mise en œuvre pour piloter la centrale d'acquisition **Keysight (ex-Agilent) 34970A** par liaison série RS-232, depuis Python.

> Source : *Keysight 34970A/34972A User's Guide* (34972-90001, édition 6, nov. 2019) et fiche technique 5965-5290EN.

---

## 1. Matériel nécessaire

| Élément | Détail |
|---|---|
| Câble | Câble série RS-232 **null-modem** (croisé), DB-9. Un câble droit ne fonctionne pas. Le câble livré dans le Quick Start Kit convient. |
| Longueur max | 15 m |
| Côté PC | Port COM natif ou adaptateur USB-RS232 (puce FTDI recommandée) |
| Logiciel | Python 3 + `pyvisa` (avec NI-VISA ou Keysight IO Libraries) **ou** `pyserial` seul |

Le port RS-232 se trouve à l'arrière de l'appareil.

---

## 2. Configuration de l'appareil (face avant)

Le 34970A sort d'usine **en GPIB**. Une seule interface est active à la fois : il faut donc d'abord sélectionner le RS-232.

Touche **Interface**, puis :

| Paramètre | Choix possibles | Valeur d'usine | Recommandé |
|---|---|---|---|
| Interface | GPIB / RS-232 | GPIB | **RS-232** |
| Vitesse (baud) | 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200 | 57600 | 57600 (ou 115200 une fois validé) |
| Parité / bits | None (8 bits), Even (7 bits), Odd (7 bits) | None, 8 bits | None, 8 bits |
| Contrôle de flux | None, XON/XOFF, DTR/DSR, RTS/CTS, Modem | **XON/XOFF** | XON/XOFF |

Remarques :

- Ces réglages se font **uniquement en face avant**. Ils sont conservés à l'extinction et ne sont pas modifiés par `*RST` ni par `SYST:PRES`.
- Avec le contrôle de flux **None**, rester à ≤ 9600 bauds et ne pas envoyer plus de 128 caractères sans lire de réponse.
- Le nombre de bits de stop n'est pas réglable sur l'appareil : utiliser **1** côté PC. En cas d'erreur 511 (framing), essayer 2.

---

## 3. Installation côté PC

```bash
pip install pyvisa        # option 1 (nécessite une couche VISA installée)
pip install pyserial      # option 2 (aucune dépendance externe)
```

Repérer le port :

```python
import pyvisa
print(pyvisa.ResourceManager().list_resources())   # ex. 'ASRL3::INSTR' = COM3
```

---

## 4. Premier contact

### 4.1 Avec PyVISA

```python
import pyvisa
from pyvisa.constants import StopBits, Parity, ControlFlow

rm = pyvisa.ResourceManager()
daq = rm.open_resource("ASRL3::INSTR")       # COM3 sous Windows

daq.baud_rate = 57600
daq.data_bits = 8
daq.parity = Parity.none
daq.stop_bits = StopBits.one
daq.flow_control = ControlFlow.xon_xoff      # réglage d'usine
daq.write_termination = "\n"
daq.read_termination = "\n"
daq.timeout = 10000                          # ms

daq.write("SYST:REM")                        # OBLIGATOIRE en RS-232
print(daq.query("*IDN?").strip())
print(daq.query("SYST:ERR?").strip())        # attendu : +0,"No error"

daq.write("SYST:LOC")                        # rend la main à la face avant
daq.close()
```

### 4.2 Avec pyserial

```python
import serial

daq = serial.Serial("COM3", 57600, bytesize=8, parity="N",
                    stopbits=1, xonxoff=True, timeout=5)
# Linux : "/dev/ttyUSB0"

def write(cmd):
    daq.write((cmd + "\n").encode())

def query(cmd):
    write(cmd)
    return daq.readline().decode().strip()

write("SYST:REM")
print(query("*IDN?"))
write("SYST:LOC")
daq.close()
```

### 4.3 Test sans code

Avec PuTTY ou Tera Term configuré avec les mêmes paramètres : taper `SYST:REM`, puis `*IDN?`. L'appareil doit renvoyer son identification.

---

## 5. Commandes propres au RS-232

| Commande | Rôle |
|---|---|
| `SYST:REM` | Passe en mode distant. Sans elle, `READ?` / `MEAS?` renvoient l'erreur **550**. |
| `SYST:LOC` | Retour en mode local (face avant active) |
| `SYST:RWL` | Mode distant avec verrouillage de la face avant |

Ces trois commandes n'existent qu'en RS-232 (erreur 514 en GPIB).

---

## 6. Commandes SCPI essentielles

### Adressage des voies

Format `(@scc)` : `s` = slot (1, 2, 3), `cc` = voie.

- `(@103)` : voie 3 du slot 1
- `(@101:110)` : voies 1 à 10 du slot 1
- `(@105:110,215)` : plage + voie isolée

### Configuration et mesure

| Commande | Rôle |
|---|---|
| `*RST` | Réinitialisation usine (vide la liste de scan et la mémoire) |
| `*IDN?` | Identification + versions firmware |
| `SYST:CTYP? 100` | Type de carte présente dans le slot 1 |
| `MEAS:VOLT:DC? (@101)` | Mesure immédiate |
| `CONF:VOLT:DC 10,0.001,(@301)` | Tension DC, calibre 10 V, résolution 1 mV |
| `CONF:TEMP TC,K,(@101:105)` | Thermocouples type K |
| `CONF:TEMP RTD,85,(@103)` | RTD α = 0,00385 (Pt100) |
| `CONF:TEMP THER,5000,(@104)` | Thermistance 5 kΩ |
| `CONF:RES (@106)` / `CONF:FRES (@107)` | Résistance 2 fils / 4 fils |
| `UNIT:TEMP C,(@101:105)` | Unité °C, °F ou K |
| `SENS:VOLT:DC:NPLC 10,(@301)` | Temps d'intégration (PLC) |
| `ROUT:CHAN:DELAY 0.1,(@101)` | Délai entre fermeture relais et mesure |
| `ROUT:SCAN (@101:110)` | Définit la liste de scan |
| `ROUT:SCAN:SIZE?` | Nombre de voies dans la liste |

### Déclenchement du scan

| Commande | Rôle |
|---|---|
| `TRIG:SOUR TIMER` | Scan périodique (aussi `BUS`, `EXT`, `ALARM1..4`, `IMM`) |
| `TRIG:TIMER 5` | Intervalle entre scans (s) |
| `TRIG:COUNT 20` | Nombre de scans (`INFINITY` = continu) |
| `INIT` | Lance le scan, mesures stockées en mémoire |
| `ABOR` | Arrête le scan |

### Format des données renvoyées

```
FORM:READ:CHAN ON         numéro de voie
FORM:READ:TIME ON         horodatage
FORM:READ:TIME:TYPE ABS   heure absolue (REL = depuis le début du scan)
FORM:READ:UNIT ON         unités
FORM:READ:ALAR ON         état d'alarme
```

### Lecture de la mémoire

| Commande | Rôle |
|---|---|
| `DATA:POINTS?` | Nombre de mesures en mémoire |
| `DATA:REMOVE? n` | Lit **et efface** les n plus anciennes |
| `FETCH?` | Lit toute la mémoire sans l'effacer |
| `DATA:LAST? (@301)` | Dernière mesure d'une voie |
| `CALC:AVER:MIN? / MAX? / AVER? (@105)` | Statistiques par voie |

---

## 7. Acquisition longue durée (méthode recommandée)

En RS-232, il vaut mieux laisser l'appareil stocker dans sa mémoire interne (50 000 mesures horodatées, non volatile) et récupérer les données par blocs, plutôt qu'interroger chaque mesure en direct.

```python
import time

daq.write("*RST")
daq.write("CONF:TEMP TC,K,(@101:105)")
daq.write("ROUT:SCAN (@101:105)")
daq.write("FORM:READ:CHAN ON")
daq.write("FORM:READ:TIME ON")
daq.write("TRIG:SOUR TIMER")
daq.write("TRIG:TIMER 10")
daq.write("TRIG:COUNT INFINITY")
daq.write("INIT")

while True:
    n = int(float(daq.query("DATA:POINTS?")))
    if n > 0:
        brut = daq.query(f"DATA:REMOVE? {n}")
        valeurs = brut.split(",")
        # traiter / enregistrer ici
    time.sleep(5)
```

Si la mémoire est pleine, les mesures les plus anciennes sont écrasées. `DATA:REMOVE?` évite ce problème en vidant la mémoire au fil de l'eau.

Débits typiques en RS-232 à 115 kbaud (fiche technique) :

- mesures sur une voie vers le PC : ~440 lectures/s
- vidage mémoire (`FETCH?`) : ~600 lectures/s, ~320 lectures/s avec horodatage
- scan : ~60 voies/s (34901A, 34908A), jusqu'à ~210 voies/s (34902A)

---

## 8. Diagnostic

Lire les erreurs avec `SYST:ERR?`. La file garde **10 erreurs** au maximum, qui sont effacées à la lecture.

| Code | Signification | Action |
|---|---|---|
| (timeout) | Aucune réponse | Câble null-modem ? Bon port COM ? Interface RS-232 sélectionnée ? |
| 511 | Erreur de trame | Vitesse ou bits de stop différents |
| 512 | Débordement | Activer le contrôle de flux ou baisser la vitesse |
| 513 | Erreur de parité | Aligner la parité PC / appareil |
| 521 / 522 | Buffer d'entrée / sortie plein | Lire les réponses avant d'envoyer d'autres commandes |
| 550 | Commande refusée en mode local | Envoyer `SYST:REM` |
| -113 | Commande inconnue | Faute de frappe dans la commande SCPI |
| -221 | Conflit de réglages | Souvent limite basse > limite haute pour les alarmes |
| -410 / -420 | Requête interrompue / non terminée | Toujours lire la réponse d'une requête `?` |
| 113 | Liste de scan vide | Définir les voies avec `CONF` ou `ROUT:SCAN` |
| 748 | Configuration RS-232 perdue | Pile interne probablement à remplacer |

---

## 9. Points d'attention sur les cartes

| Carte | Voies | Remarques |
|---|---|---|
| 34901A | 20 + 2 | Multiplexeur généraliste, 60 voies/s. Seule carte à mesurer du **courant** en direct (voies 21 et 22). 4 fils : voie n appariée avec n+10. |
| 34902A | 16 | Relais reed, rapide (250 voies/s). Courant : shunt externe nécessaire. 4 fils : voie n appariée avec n+8. |
| 34908A | 40 | Une seule borne commune (LO commun). **Thermocouples déconseillés**, pas de mesure 4 fils. |
| 34903A | 20 | Relais inverseurs (actionneurs), pas de mesure. |
| 34904A | 4 × 8 | Matrice de commutation. |
| 34905A / 34906A | 2 × 4 | Multiplexeurs RF 50 Ω / 75 Ω. |
| 34907A | — | E/S numériques, compteur, 2 sorties analogiques ±12 V. Sa présence annule la garantie de précision des thermocouples. |

---

## 10. Intégration dans le projet GitHub

Il n'existe pas de dépôt officiel Keysight pour le 34970A. Il faut donc créer son propre module pilote dans le dépôt :

```
mon-logiciel/
├── src/
├── equipements/
│   └── keysight_34970a/
│       ├── __init__.py
│       ├── driver.py        ← classe de pilotage (connexion, mesures, scan)
│       └── README.md        ← ce document
├── requirements.txt         ← pyvisa ou pyserial
└── README.md
```

Bonnes pratiques :

- **Isoler la couche de communication** (RS-232, GPIB, LAN) dans la classe : le passage à un 34972A (LAN/USB, même jeu de commandes) ne demandera alors qu'un changement d'adresse.
- Mettre le port COM et la vitesse dans un **fichier de configuration**, pas dans le code.
- Toujours envoyer `SYST:REM` à l'ouverture et `SYST:LOC` à la fermeture.
- Vérifier `SYST:ERR?` après chaque configuration.

Alternatives communautaires : **PyMeasure** et **QCoDeS** proposent des pilotes pour cette famille d'appareils.

---

## 11. Références

- *Keysight 34970A/34972A User's Guide*, réf. 34972-90001
- *Keysight 34970A/34972A Programmer's Reference Help* (jeu complet de commandes SCPI)
- Fiche technique 5965-5290EN
- Page produit : <https://www.keysight.com/find/34970A>

> Le 34970A n'est plus commercialisé depuis le 31 mai 2021. Le support Keysight était annoncé pour 5 ans et a donc probablement pris fin.
