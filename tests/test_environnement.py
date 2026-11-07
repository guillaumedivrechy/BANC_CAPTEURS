"""Vérifie que l'environnement est correctement installé (sans matériel)."""

import propar

import banc_capteurs


def test_import_banc_capteurs():
    assert banc_capteurs.__version__


def test_propar_installe_depuis_sous_module():
    assert "externe" in propar.__file__ and "bronkhorst-propar" in propar.__file__


def test_base_parametres_propar():
    db = propar.database()
    mesure = db.get_parameter(8)
    assert mesure["proc_nr"] == 1 and mesure["parm_nr"] == 0
