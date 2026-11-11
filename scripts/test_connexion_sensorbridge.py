"""Vérifie la communication avec un Sensirion SEK-SensorBridge et son capteur T/HR.

Exemples :
    python scripts/test_connexion_sensorbridge.py --lister-ports
    python scripts/test_connexion_sensorbridge.py --port COM4
    python scripts/test_connexion_sensorbridge.py --port COM4 --voie 1 --sht sht4x
    python scripts/test_connexion_sensorbridge.py --port COM4 --sht sht4x --adresse-i2c 0x45
"""

import argparse
import sys
import time

from serial.tools import list_ports
from sensirion_shdlc_driver import ShdlcConnection, ShdlcSerialPort
from sensirion_shdlc_driver.errors import ShdlcError
from sensirion_shdlc_sensorbridge import SensorBridgePort, SensorBridgeShdlcDevice
from sensirion_shdlc_sensorbridge.definitions import VOLTAGES

VOIES = {1: SensorBridgePort.ONE, 2: SensorBridgePort.TWO}

# Capteurs Sensirion température/humidité : adresse I2C, commande de mesure
# (haute répétabilité), temps de mesure, formule d'humidité.
CAPTEURS_SHT = {
    "sht4x": {"adresse": 0x44, "commande": [0xFD], "attente_s": 0.010,
              "hr": lambda brut: -6.0 + 125.0 * brut / 65535.0},
    "sht3x": {"adresse": 0x44, "commande": [0x24, 0x00], "attente_s": 0.016,
              "hr": lambda brut: 100.0 * brut / 65535.0},
    "shtc3": {"adresse": 0x70, "commande": [0x78, 0x66], "attente_s": 0.013,
              "reveil": [0x35, 0x17],
              "hr": lambda brut: 100.0 * brut / 65535.0},
}


def crc8_sensirion(donnees):
    crc = 0xFF
    for octet in donnees:
        crc ^= octet
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def convertir_mesure_sht(octets, modele):
    """Convertit les 6 octets bruts (T, CRC, HR, CRC) en (°C, %HR)."""
    octets = bytearray(octets)
    for i in (0, 3):
        if crc8_sensirion(octets[i:i + 2]) != octets[i + 2]:
            raise ValueError("CRC invalide dans la réponse du capteur")
    brut_t = (octets[0] << 8) | octets[1]
    brut_hr = (octets[3] << 8) | octets[4]
    temperature = -45.0 + 175.0 * brut_t / 65535.0
    humidite = min(100.0, max(0.0, CAPTEURS_SHT[modele]["hr"](brut_hr)))
    return temperature, humidite


def mesurer_sht(bridge, voie, modele, adresse=None):
    capteur = CAPTEURS_SHT[modele]
    adresse = capteur["adresse"] if adresse is None else adresse
    if "reveil" in capteur:
        bridge.transceive_i2c(voie, adresse, capteur["reveil"], 0, 10e3)
        time.sleep(0.001)
    bridge.transceive_i2c(voie, adresse, capteur["commande"], 0, 10e3)
    time.sleep(capteur["attente_s"])
    octets = bridge.transceive_i2c(voie, adresse, [], 6, 100e3)
    return convertir_mesure_sht(octets, modele)


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
    parser.add_argument("--port", help="port série du SensorBridge (ex. COM4 ou /dev/ttyUSB1)")
    parser.add_argument("--baudrate", type=int, default=460800, help="vitesse (défaut : 460800)")
    parser.add_argument("--voie", type=int, choices=VOIES, default=1, help="voie du SensorBridge (1 ou 2)")
    parser.add_argument("--tension", type=float, default=3.3, choices=sorted(VOLTAGES),
                        help="tension d'alimentation du capteur en V (défaut : 3.3)")
    parser.add_argument("--sht", choices=CAPTEURS_SHT, help="modèle du capteur pour faire une mesure")
    parser.add_argument("--adresse-i2c", type=lambda x: int(x, 0),
                        help="adresse I2C du capteur si elle diffère de l'adresse habituelle "
                             "(0x44 pour SHT4x/SHT3x, 0x70 pour SHTC3)")
    args = parser.parse_args()

    if args.lister_ports or not args.port:
        lister_ports()
        return 0

    try:
        return tester(args)
    except (OSError, ShdlcError, ValueError) as erreur:
        print(f"Échec : {erreur}", file=sys.stderr)
        return 1


def tester(args):
    voie = VOIES[args.voie]
    with ShdlcSerialPort(port=args.port, baudrate=args.baudrate) as port:
        bridge = SensorBridgeShdlcDevice(ShdlcConnection(port), slave_address=0)
        print(f"Produit         : {bridge.get_product_name()}")
        print(f"Numéro de série : {bridge.get_serial_number()}")
        print(f"Version         : {bridge.get_version()}")

        bridge.set_i2c_frequency(voie, frequency=100e3)
        bridge.set_supply_voltage(voie, voltage=args.tension)
        bridge.switch_supply_on(voie)
        time.sleep(0.05)  # mise sous tension du capteur
        try:
            adresses = bridge.scan_i2c(voie)
            print(f"Voie {args.voie} — périphériques I2C : "
                  + (", ".join(f"0x{a:02X}" for a in adresses) or "aucun"))
            if args.sht:
                temperature, humidite = mesurer_sht(bridge, voie, args.sht, args.adresse_i2c)
                print(f"Température     : {temperature:.2f} °C")
                print(f"Humidité        : {humidite:.2f} %HR")
        finally:
            bridge.switch_supply_off(voie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
