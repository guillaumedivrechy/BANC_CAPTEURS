"""Vérifie la communication avec un instrument Bronkhorst via ProPar.

Exemples :
    python scripts/test_connexion_propar.py --lister-ports
    python scripts/test_connexion_propar.py --port COM3
    python scripts/test_connexion_propar.py --port /dev/ttyUSB0 --scanner
"""

import argparse
import sys

from serial import SerialException
from serial.tools import list_ports

import propar

# Numéros de paramètres DDE Bronkhorst
DDE_MESURE = 8          # 0-32000 = 0-100 %
DDE_CONSIGNE = 9        # 0-32000 = 0-100 %
DDE_FLUIDE = 25
DDE_CAPACITE = 21
DDE_UNITE = 129
DDE_NUMERO_SERIE = 92


def lister_ports():
    ports = list(list_ports.comports())
    if not ports:
        print("Aucun port série détecté.")
    for p in ports:
        print(f"{p.device:15} {p.description}")


def tester_instrument(port, adresse, baudrate):
    instr = propar.instrument(port, address=adresse, baudrate=baudrate)
    numero_serie = instr.readParameter(DDE_NUMERO_SERIE)
    if numero_serie is None:
        print(f"Pas de réponse de l'instrument {adresse} sur {port} ({baudrate} bauds).")
        return False

    mesure = instr.readParameter(DDE_MESURE)
    consigne = instr.readParameter(DDE_CONSIGNE)
    print(f"Numéro de série : {numero_serie}")
    print(f"Fluide          : {instr.readParameter(DDE_FLUIDE)}")
    print(f"Capacité        : {instr.readParameter(DDE_CAPACITE)} {instr.readParameter(DDE_UNITE)}")
    print(f"Mesure          : {en_pourcent(mesure)}")
    print(f"Consigne        : {en_pourcent(consigne)}")
    return True


def en_pourcent(valeur):
    """Valeur brute 0-32000 et son équivalent en % ; « non disponible » sans réponse."""
    return "non disponible" if valeur is None else f"{valeur}  ({valeur / 320:.2f} %)"


def scanner_bus(port, baudrate):
    maitre = propar.master(port, baudrate)
    noeuds = maitre.get_nodes()
    if not noeuds:
        print("Aucun instrument trouvé sur le bus.")
    for n in noeuds:
        print(n)
    return bool(noeuds)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lister-ports", action="store_true", help="lister les ports série disponibles")
    parser.add_argument("--port", help="port série (ex. COM3 ou /dev/ttyUSB0)")
    parser.add_argument("--adresse", type=int, default=0x80,
                        help="adresse ProPar de l'instrument (défaut : 128 = instrument local)")
    parser.add_argument("--baudrate", type=int, default=38400, help="vitesse (défaut : 38400)")
    parser.add_argument("--scanner", action="store_true", help="lister les instruments du bus FLOW-BUS")
    args = parser.parse_args()

    if args.lister_ports or not args.port:
        lister_ports()
        return 0

    try:
        ok = scanner_bus(args.port, args.baudrate) if args.scanner \
            else tester_instrument(args.port, args.adresse, args.baudrate)
    except SerialException as erreur:
        print(f"Échec : {erreur}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
