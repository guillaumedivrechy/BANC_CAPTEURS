"""Tests du pilote 34970A avec un faux appareil (sans matériel)."""

import datetime as dt

import pytest

from banc_capteurs.equipements.keysight_34970a import (
    Keysight34970A,
    Keysight34970AErreur,
    TransportSerie,
    decoder_mesures,
)


class FauxTransport:
    """Simule le 34970A : enregistre les commandes et renvoie des réponses prévues."""

    def __init__(self, reponses=None, muet=False):
        self.muet = muet
        self.envoye = []
        self.reponses = dict(reponses or {})
        self.erreurs = []
        self.ferme = False
        self._a_lire = []

    def write(self, donnees):
        assert donnees.endswith(b"\n")
        commande = donnees.decode("ascii").strip()
        self.envoye.append(commande)
        if self.muet:
            if commande.endswith("?") or "? " in commande:
                self._a_lire.append(b"")
        elif commande == "SYST:ERR?":
            code, msg = self.erreurs.pop(0) if self.erreurs else (0, "No error")
            self._a_lire.append(f'{code:+d},"{msg}"\n'.encode())
        elif commande.endswith("?") or "? " in commande:
            reponse = self.reponses.get(commande)
            self._a_lire.append(b"" if reponse is None else (reponse + "\n").encode())

    def readline(self):
        return self._a_lire.pop(0)

    def close(self):
        self.ferme = True


def test_ouverture_et_fermeture_mode_distant():
    t = FauxTransport({"*IDN?": "HEWLETT-PACKARD,34970A,0,13-2-2"})
    with Keysight34970A(t) as daq:
        assert daq.identifier().startswith("HEWLETT-PACKARD,34970A")
    assert t.envoye[0] == "SYST:REM"
    assert t.envoye[-1] == "SYST:LOC"
    assert t.ferme


def test_verrouillage_face_avant():
    t = FauxTransport()
    with Keysight34970A(t, verrouiller_face_avant=True):
        pass
    assert t.envoye[0] == "SYST:RWL"


def test_ouverture_impose_le_format_des_mesures():
    t = FauxTransport()
    Keysight34970A(t).ouvrir()
    for commande in ("FORM:READ:CHAN ON", "FORM:READ:TIME ON", "FORM:READ:TIME:TYPE ABS",
                     "FORM:READ:UNIT OFF", "FORM:READ:ALAR OFF"):
        assert commande in t.envoye


def test_liaison_refermee_si_appareil_muet_a_l_ouverture():
    t = FauxTransport(muet=True)
    with pytest.raises(TimeoutError, match="null-modem"):
        with Keysight34970A(t):
            pass
    assert t.ferme


def test_mesure_immediate():
    t = FauxTransport({"MEAS:TEMP? TC,K,(@101:102)":
                       "+2.13000000E+01,2026,11,07,14,30,15.250,101,"
                       "+2.15000000E+01,2026,11,07,14,30,15.270,102"})
    daq = Keysight34970A(t)
    assert daq.mesurer("TEMP", "101:102", "TC,K") == [21.3, 21.5]
    assert [m.voie for m in daq.mesurer_detail("TEMP", "101:102", "TC,K")] == [101, 102]


def test_mesure_immediate_sans_voie_ni_horodatage():
    t = FauxTransport({"MEAS:RES? (@101:102)": "+1.20000000E+03,+9.90000000E+37"})
    daq = Keysight34970A(t)
    daq.configurer_format(voie=False, horodatage=False)
    assert daq.mesurer("RES", "101:102") == [1200.0, 9.9e37]
    assert t.envoye[-1] == "SYST:ERR?"  # erreurs vérifiées après la mesure


@pytest.mark.parametrize("voies", ["101:105", "@101:105", "(@101:105)"])
def test_notation_des_voies(voies):
    t = FauxTransport()
    Keysight34970A(t).configurer("VOLT:DC", voies, "10,0.001")
    assert t.envoye[0] == "CONF:VOLT:DC 10,0.001,(@101:105)"


def test_erreur_appareil_avec_aide():
    t = FauxTransport()
    t.erreurs = [(550, "Command not allowed in local")]
    with pytest.raises(Keysight34970AErreur) as exc:
        Keysight34970A(t).configurer("TEMP", "101", "TC,K")
    assert exc.value.erreurs == [(550, "Command not allowed in local")]
    assert "SYST:REM" in str(exc.value)


def test_absence_de_reponse():
    t = FauxTransport(muet=True)
    with pytest.raises(TimeoutError, match="null-modem"):
        Keysight34970A(t).identifier()


def test_requete_refusee_par_l_appareil():
    # L'appareil ne répond pas à une requête refusée : le pilote lit alors l'erreur.
    t = FauxTransport()  # aucune réponse prévue pour MEAS:TEMP?
    t.erreurs = [(550, "Command not allowed in local")]
    with pytest.raises(Keysight34970AErreur, match="SYST:REM"):
        Keysight34970A(t).mesurer("TEMP", "101", "TC,K")


def test_requete_trop_longue():
    t = FauxTransport()  # l'appareil répond aux erreurs mais pas encore à la mesure
    with pytest.raises(TimeoutError, match="timeout_s"):
        Keysight34970A(t).mesurer("RES", "101:120")


def test_type_carte():
    t = FauxTransport({"SYST:CTYP? 100": "HEWLETT-PACKARD,34901A,0,1.0"})
    assert "34901A" in Keysight34970A(t).type_carte(1)


def test_scan_et_lecture_memoire():
    t = FauxTransport({
        "DATA:POINTS?": "+2",
        "DATA:REMOVE? 2": ("+2.13000000E+01,2026,11,07,14,30,15.250,101,"
                           "+2.15000000E+01,2026,11,07,14,30,15.270,102"),
    })
    daq = Keysight34970A(t)
    daq.demarrer_scan("101:102", intervalle_s=10)
    commandes = [c for c in t.envoye if c != "SYST:ERR?"]
    assert commandes[0] == "ROUT:SCAN (@101:102)"
    assert "TRIG:SOUR TIMER" in commandes and "TRIG:TIMER 10" in commandes
    assert "TRIG:COUNT INFINITY" in commandes
    assert commandes[-1] == "INIT"

    mesures = daq.lire_memoire()
    assert [m.voie for m in mesures] == [101, 102]
    assert mesures[0].valeur == 21.3
    assert mesures[0].horodatage == dt.datetime(2026, 11, 7, 14, 30, 15, 250000)


def test_memoire_vide():
    t = FauxTransport({"DATA:POINTS?": "+0"})
    assert Keysight34970A(t).lire_memoire() == []


def test_decodage_sans_horodatage():
    mesures = decoder_mesures("+1.0E+00,101,+2.0E+00,102", voie=True, horodatage=False)
    assert [(m.valeur, m.voie) for m in mesures] == [(1.0, 101), (2.0, 102)]


def test_decodage_reponse_incoherente():
    with pytest.raises(ValueError):
        decoder_mesures("+1.0E+00,101,+2.0E+00", voie=True, horodatage=False)


def test_transport_refuse_vitesse_elevee_sans_controle_de_flux():
    with pytest.raises(ValueError, match="9600"):
        TransportSerie("COM_INEXISTANT", baudrate=57600, controle_flux="aucun")
