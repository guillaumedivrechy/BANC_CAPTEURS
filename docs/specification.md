# Spécification du logiciel du banc de capteurs

Document de travail : il consigne les décisions prises au fil de la spécification.
Les points encore ouverts sont listés en fin de document.

## 1. Instruments du banc

| Instrument | Rôle | Liaison | Pilote |
|---|---|---|---|
| Régulateurs de débit Bronkhorst | Consignes et mesures de débit de gaz | RS-232 / FLOW-BUS (ProPar) | `externe/bronkhorst-propar` |
| Sensirion SEK-SensorBridge + capteur SHT | Température et humidité | USB (port COM virtuel, SHDLC) | `externe/python-shdlc-sensorbridge` |
| Keysight 34970A | Mesure des 20 capteurs résistifs | RS-232 (SCPI) | `src/banc_capteurs/equipements/keysight_34970a` |

## 2. Mesure des capteurs résistifs (Keysight 34970A)

| Sujet | Décision |
|---|---|
| Voies | 20 capteurs résistifs, en 2 fils, voies 101 à 120 (une carte 34901A en slot 1) |
| Plage | 1 Ω à 100 MΩ ; un même capteur peut parcourir toute la plage au cours d'une campagne |
| Calibre | Le calibre en cours lors de la mesure est consigné avec chaque valeur. Calibres possibles : 100 Ω, 1 kΩ, 10 kΩ, 100 kΩ, 1 MΩ, 10 MΩ, 100 MΩ. Le calibre de chaque voie est choisi par le logiciel (voir § 2.1), il est donc connu exactement |
| Cadence | 30 s par défaut, réglable |
| Précision | Celle du 2 fils (câbles et relais inclus, ~0,1 à 1 Ω), jugée suffisante |
| Intégration | 10 PLC (200 ms à 50 Hz) : meilleure résolution, rejet du 50 Hz |
| Horloge | Le PC cadence les scans et horodate les mesures (même horloge que les autres instruments) |
| Durée de scan | Chronométrée à chaque scan ; avertissement si elle dépasse la cadence réglée |
| Hors plage | Une valeur de dépassement (`+9.9E+37`, au-delà d'environ 120 MΩ ou capteur débranché) est enregistrée « hors plage », jamais comme une valeur numérique |

### 2.1 Gestion du calibre

En calibre automatique, le 34970A ne renvoie pas le calibre utilisé avec la mesure. Pour que le
calibre consigné soit certain, c'est le logiciel qui le choisit, voie par voie :

1. Chaque voie est mesurée sur un calibre fixe, celui retenu au scan précédent
   (100 MΩ au premier scan).
2. Si la mesure est en dépassement, la voie est remesurée sur le calibre 100 MΩ.
3. Si la valeur est inférieure à 10 % du calibre (sauf sur 100 Ω), la voie est remesurée
   directement sur le plus petit calibre qui contient la valeur.
4. La valeur enregistrée est celle de la dernière mesure, avec son calibre.

Une voie demande au plus deux mesures supplémentaires par scan, ce que la cadence de 30 s permet largement.

### 2.2 Données enregistrées à chaque mesure

| Champ | Contenu |
|---|---|
| Horodatage | Heure du PC au moment du scan |
| Voie | 101 à 120 |
| Résistance | Valeur en Ω (vide si hors plage) |
| Calibre | Calibre utilisé pour cette mesure, en Ω |
| État | `ok` ou `hors plage` |

## 3. Points ouverts

- **À vérifier sur le banc** : carte 34901A bien en slot 1, durée réelle d'un scan des 20 voies.
- **Bronkhorst** : modèles, nombre de régulateurs, gaz, pleines échelles, consigne en unités réelles ou en %, rampes.
- **Capteur T/HR** : référence du SHT, cadence.
- **Déroulé d'un essai** : paliers de consigne, durées, conditions d'enchaînement.
- **Fichiers de résultats** : format, organisation (un fichier par campagne ?).
- **Interface** : ligne de commande, interface graphique, courbes en direct.
- **Sécurité** : comportement en cas de perte de communication ou de valeur hors limites.
