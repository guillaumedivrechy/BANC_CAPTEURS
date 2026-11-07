"""Vérifie la communication RS-232 avec la centrale Keysight 34970A.

Avant tout : sélectionner l'interface RS-232 en face avant (touche Interface) et
utiliser un câble null-modem. Voir src/banc_capteurs/equipements/keysight_34970a/README.md.

Exemples :
    python scripts/test_connexion_34970a.py --lister-ports
    python scripts/test_connexion_34970a.py --port COM3
    python scripts/test_connexion_34970a.py --port COM3 --fonction VOLT:DC --voies 101
    python scripts/test_connexion_34970a.py --port COM3 --fonction TEMP --parametres TC,K --voies 101:105
"""

import argparse
import sys

from serial.tools import list_ports

from banc_capteurs.equipements.keysight_34970a import Keysight34970A


def lister_ports():
    ports = list(list_ports.comports())
    if not ports:
        print("Aucun port série détecté.")
    for p in ports:
        print(f"{p.device:15} {p.description}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lister-ports", action="store_true", help="lister les ports série disponibles")
    parser.add_argument("--port", help="port série (ex. COM3 ou /dev/ttyUSB0)")
    parser.add_argument("--baudrate", type=int, default=57600, help="vitesse (défaut d'usine : 57600)")
    parser.add_argument("--flux", choices=["xonxoff", "rtscts", "dsrdtr", "aucun"], default="xonxoff",
                        help="contrôle de flux (défaut d'usine : xonxoff)")
    parser.add_argument("--stopbits", type=int, choices=[1, 2], default=1,
                        help="bits de stop (1 ; essayer 2 en cas d'erreur 511)")
    parser.add_argument("--fonction", help="fonction de mesure SCPI, ex. VOLT:DC, TEMP, RES, FRES")
    parser.add_argument("--parametres", default="", help="paramètres de la mesure, ex. TC,K ou RTD,85")
    parser.add_argument("--voies", default="101", help="voies, ex. 101 ou 101:105 (défaut : 101)")
    args = parser.parse_args()

    if args.lister_ports or not args.port:
        lister_ports()
        return 0

    with Keysight34970A.rs232(args.port, args.baudrate, args.flux, stopbits=args.stopbits) as daq:
        print(f"Identification  : {daq.identifier()}")
        for slot in (1, 2, 3):
            print(f"Slot {slot}          : {daq.type_carte(slot)}")
        if args.fonction:
            valeurs = daq.mesurer(args.fonction, args.voies, args.parametres)
            print(f"Mesure {args.fonction} (@{args.voies}) : "
                  + ", ".join(f"{v:.6g}" for v in valeurs))
        erreurs = daq.lire_erreurs()
        print("Erreurs         : " + (", ".join(f"{c} {m}" for c, m in erreurs) or "aucune"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
