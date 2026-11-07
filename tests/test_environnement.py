"""Vérifie que l'environnement est correctement installé (sans matériel)."""

import importlib.util
import pathlib

import propar
import sensirion_shdlc_sensorbridge

import banc_capteurs

RACINE = pathlib.Path(__file__).resolve().parents[1]


def _charger_script(nom):
    spec = importlib.util.spec_from_file_location(nom, RACINE / "scripts" / f"{nom}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_banc_capteurs():
    assert banc_capteurs.__version__


def test_propar_installe_depuis_sous_module():
    assert "externe" in propar.__file__ and "bronkhorst-propar" in propar.__file__


def test_base_parametres_propar():
    db = propar.database()
    mesure = db.get_parameter(8)
    assert mesure["proc_nr"] == 1 and mesure["parm_nr"] == 0


def test_sensorbridge_installe_depuis_sous_module():
    chemin = sensirion_shdlc_sensorbridge.__file__
    assert "externe" in chemin and "python-shdlc-sensorbridge" in chemin


def test_crc_sensirion():
    # Exemple de la fiche technique Sensirion : CRC(0xBEEF) = 0x92
    sb = _charger_script("test_connexion_sensorbridge")
    assert sb.crc8_sensirion([0xBE, 0xEF]) == 0x92


def test_conversion_sht4x():
    sb = _charger_script("test_connexion_sensorbridge")
    brut_t, brut_hr = 0x6666, 0x8000
    octets = [brut_t >> 8, brut_t & 0xFF, sb.crc8_sensirion([0x66, 0x66]),
              brut_hr >> 8, brut_hr & 0xFF, sb.crc8_sensirion([0x80, 0x00])]
    temperature, humidite = sb.convertir_mesure_sht(octets, "sht4x")
    assert abs(temperature - 25.0) < 0.01
    assert abs(humidite - 56.5) < 0.01
