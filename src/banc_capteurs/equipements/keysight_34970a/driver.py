"""Pilotage du Keysight 34970A par commandes SCPI.

La communication est isolée dans un objet « transport » (méthodes ``write``,
``readline`` et ``close``). ``TransportSerie`` implémente le RS-232 avec
pyserial ; un autre transport (VISA, LAN pour un 34972A…) peut être passé à
``Keysight34970A`` sans rien changer d'autre.

Voir README.md (dans ce dossier) pour le câblage et la configuration de l'appareil.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Codes d'erreur fréquents (README.md, section 8) et action conseillée.
ERREURS_CONNUES = {
    511: "erreur de trame : vitesse ou bits de stop différents entre PC et appareil",
    512: "débordement : activer le contrôle de flux ou baisser la vitesse",
    513: "erreur de parité : aligner la parité PC / appareil",
    521: "buffer d'entrée plein : lire les réponses avant d'envoyer d'autres commandes",
    522: "buffer de sortie plein : lire les réponses avant d'envoyer d'autres commandes",
    550: "commande refusée en mode local : envoyer SYST:REM",
    -113: "commande inconnue : vérifier l'orthographe de la commande SCPI",
    -221: "conflit de réglages (souvent limite basse > limite haute pour les alarmes)",
    -410: "requête interrompue : toujours lire la réponse d'une requête '?'",
    -420: "requête non terminée : toujours lire la réponse d'une requête '?'",
    113: "liste de scan vide : définir les voies avec CONF ou ROUT:SCAN",
    748: "configuration RS-232 perdue : pile interne probablement à remplacer",
}

_AIDE_TIMEOUT = ("aucune réponse du 34970A. Vérifier : câble null-modem (croisé), port COM, "
                 "interface RS-232 sélectionnée en face avant (touche Interface), "
                 "vitesse et contrôle de flux identiques des deux côtés.")

# Correspondance contrôle de flux -> options pyserial
_CONTROLES_FLUX = {
    "xonxoff": {"xonxoff": True},
    "rtscts": {"rtscts": True},
    "dsrdtr": {"dsrdtr": True},
    "aucun": {},
}


class Keysight34970AErreur(RuntimeError):
    """Erreur(s) signalée(s) par l'appareil via SYST:ERR?."""

    def __init__(self, erreurs: List[Tuple[int, str]], commande: Optional[str] = None):
        self.erreurs = erreurs
        self.commande = commande
        lignes = []
        for code, message in erreurs:
            aide = ERREURS_CONNUES.get(code)
            lignes.append(f"{code} « {message} »" + (f" → {aide}" if aide else ""))
        prefixe = f"après « {commande} » : " if commande else ""
        super().__init__(prefixe + " ; ".join(lignes))


class TransportSerie:
    """Liaison RS-232 avec pyserial (réglages d'usine du 34970A par défaut)."""

    def __init__(self, port: str, baudrate: int = 57600, controle_flux: str = "xonxoff",
                 parite: str = "N", stopbits: int = 1, timeout: float = 10.0):
        import serial  # import local : le module reste importable sans pyserial

        if controle_flux not in _CONTROLES_FLUX:
            raise ValueError(f"contrôle de flux inconnu : {controle_flux!r} "
                             f"(choix : {', '.join(_CONTROLES_FLUX)})")
        if controle_flux == "aucun" and baudrate > 9600:
            raise ValueError("sans contrôle de flux, rester à 9600 bauds maximum (README, section 2)")
        # Parité « None » = 8 bits de données, « Even »/« Odd » = 7 bits (réglage de l'appareil)
        bytesize = 8 if parite == "N" else 7
        self._serie = serial.Serial(port, baudrate, bytesize=bytesize, parity=parite,
                                    stopbits=stopbits, timeout=timeout,
                                    **_CONTROLES_FLUX[controle_flux])

    def write(self, donnees: bytes) -> None:
        self._serie.write(donnees)

    def readline(self) -> bytes:
        return self._serie.readline()

    def close(self) -> None:
        self._serie.close()


@dataclass
class Mesure:
    valeur: float
    voie: Optional[int] = None
    horodatage: Optional[_dt.datetime] = None


def decoder_mesures(brut: str, voie: bool = True, horodatage: bool = True) -> List[Mesure]:
    """Décode une réponse FETCH? / DATA:REMOVE? / READ?.

    Format attendu (configuré par ``Keysight34970A.configurer_format``) : pour chaque
    mesure, la valeur, puis l'heure absolue (année, mois, jour, heure, minute, seconde)
    si ``horodatage``, puis le numéro de voie si ``voie``. Unités et alarmes désactivées.
    """
    brut = brut.strip()
    if not brut:
        return []
    champs = [c.strip() for c in brut.split(",")]
    taille = 1 + (6 if horodatage else 0) + (1 if voie else 0)
    if len(champs) % taille:
        raise ValueError(f"réponse incohérente : {len(champs)} champs pour des mesures de {taille} champs")

    mesures = []
    for i in range(0, len(champs), taille):
        bloc = champs[i:i + taille]
        mesure = Mesure(valeur=float(bloc[0]))
        pos = 1
        if horodatage:
            annee, mois, jour, heure, minute = (int(float(x)) for x in bloc[pos:pos + 5])
            secondes = float(bloc[pos + 5])
            mesure.horodatage = (_dt.datetime(annee, mois, jour, heure, minute)
                                 + _dt.timedelta(seconds=secondes))
            pos += 6
        if voie:
            mesure.voie = int(float(bloc[pos]))
        mesures.append(mesure)
    return mesures


class Keysight34970A:
    """Centrale d'acquisition Keysight 34970A.

    Utilisation recommandée, en gestionnaire de contexte (SYST:REM à l'ouverture,
    SYST:LOC à la fermeture) :

        with Keysight34970A.rs232("COM3") as daq:
            print(daq.identifier())
            print(daq.mesurer("VOLT:DC", "@101"))
    """

    def __init__(self, transport, verrouiller_face_avant: bool = False):
        self.transport = transport
        self.verrouiller_face_avant = verrouiller_face_avant
        self._horodatage = True
        self._voie = True

    @classmethod
    def rs232(cls, port: str, baudrate: int = 57600, controle_flux: str = "xonxoff",
              stopbits: int = 1, timeout: float = 10.0, **kwargs) -> "Keysight34970A":
        return cls(TransportSerie(port, baudrate, controle_flux, stopbits=stopbits,
                                  timeout=timeout), **kwargs)

    # --- Connexion -------------------------------------------------------------

    def ouvrir(self) -> None:
        """Passe en mode distant (obligatoire en RS-232) et vide la file d'erreurs."""
        self.write("SYST:RWL" if self.verrouiller_face_avant else "SYST:REM")
        self.lire_erreurs()

    def fermer(self) -> None:
        """Rend la main à la face avant et ferme la liaison."""
        try:
            self.write("SYST:LOC")
        finally:
            self.transport.close()

    def __enter__(self) -> "Keysight34970A":
        self.ouvrir()
        return self

    def __exit__(self, *exc) -> None:
        self.fermer()

    # --- Échanges SCPI de base -------------------------------------------------

    def write(self, commande: str) -> None:
        self.transport.write((commande + "\n").encode("ascii"))

    def query(self, commande: str) -> str:
        self.write(commande)
        reponse = self.transport.readline()
        if not reponse.endswith(b"\n"):
            raise TimeoutError(f"« {commande} » : {_AIDE_TIMEOUT}")
        return reponse.decode("ascii").strip()

    def lire_erreurs(self) -> List[Tuple[int, str]]:
        """Vide la file d'erreurs de l'appareil (10 au maximum)."""
        erreurs = []
        for _ in range(20):
            code, _, message = self.query("SYST:ERR?").partition(",")
            code = int(code)
            if code == 0:
                break
            erreurs.append((code, message.strip().strip('"')))
        return erreurs

    def verifier_erreurs(self, commande: Optional[str] = None) -> None:
        erreurs = self.lire_erreurs()
        if erreurs:
            raise Keysight34970AErreur(erreurs, commande)

    def commande(self, commande: str) -> None:
        """Envoie une commande de configuration puis vérifie SYST:ERR?."""
        self.write(commande)
        self.verifier_erreurs(commande)

    # --- Informations ----------------------------------------------------------

    def identifier(self) -> str:
        return self.query("*IDN?")

    def type_carte(self, slot: int) -> str:
        """Type de la carte présente dans le slot 1, 2 ou 3."""
        if slot not in (1, 2, 3):
            raise ValueError("slot : 1, 2 ou 3")
        return self.query(f"SYST:CTYP? {slot}00")

    def reinitialiser(self) -> None:
        """*RST : réglages d'usine, vide la liste de scan et la mémoire."""
        self.commande("*RST")

    # --- Mesures ---------------------------------------------------------------

    @staticmethod
    def _voies(voies: str) -> str:
        """Accepte « 101 », « @101:105 » ou « (@101:105) »."""
        voies = voies.strip().strip("()").lstrip("@")
        return f"(@{voies})"

    def mesurer(self, fonction: str, voies: str, parametres: str = "") -> List[float]:
        """Mesure immédiate (MEAS?), ex. ``mesurer("TEMP", "101:105", "TC,K")``."""
        args = f"{parametres},{self._voies(voies)}" if parametres else self._voies(voies)
        reponse = self.query(f"MEAS:{fonction}? {args}")
        self.verifier_erreurs(f"MEAS:{fonction}?")
        return [float(x) for x in reponse.split(",") if x.strip()]

    def configurer(self, fonction: str, voies: str, parametres: str = "") -> None:
        """CONF, ex. ``configurer("VOLT:DC", "301", "10,0.001")``."""
        args = f"{parametres},{self._voies(voies)}" if parametres else self._voies(voies)
        self.commande(f"CONF:{fonction} {args}")

    # --- Scan et mémoire -------------------------------------------------------

    def configurer_format(self, voie: bool = True, horodatage: bool = True) -> None:
        """Format des mesures renvoyées, cohérent avec ``decoder_mesures``."""
        self.commande(f"FORM:READ:CHAN {'ON' if voie else 'OFF'}")
        self.commande(f"FORM:READ:TIME {'ON' if horodatage else 'OFF'}")
        if horodatage:
            self.commande("FORM:READ:TIME:TYPE ABS")
        self.commande("FORM:READ:UNIT OFF")
        self.commande("FORM:READ:ALAR OFF")
        self._voie, self._horodatage = voie, horodatage

    def demarrer_scan(self, voies: str, intervalle_s: float, nombre: Optional[int] = None) -> None:
        """Scan périodique stocké dans la mémoire interne (méthode recommandée en RS-232).

        Les voies doivent avoir été configurées avec ``configurer``. ``nombre=None``
        lance un scan continu.
        """
        self.commande(f"ROUT:SCAN {self._voies(voies)}")
        self.configurer_format(self._voie, self._horodatage)
        self.commande("TRIG:SOUR TIMER")
        self.commande(f"TRIG:TIMER {intervalle_s}")
        self.commande(f"TRIG:COUNT {'INFINITY' if nombre is None else int(nombre)}")
        self.commande("INIT")

    def arreter_scan(self) -> None:
        self.commande("ABOR")

    def nombre_mesures(self) -> int:
        return int(float(self.query("DATA:POINTS?")))

    def lire_memoire(self) -> List[Mesure]:
        """Lit et efface les mesures en mémoire (DATA:REMOVE?)."""
        n = self.nombre_mesures()
        if n == 0:
            return []
        brut = self.query(f"DATA:REMOVE? {n}")
        return decoder_mesures(brut, voie=self._voie, horodatage=self._horodatage)
