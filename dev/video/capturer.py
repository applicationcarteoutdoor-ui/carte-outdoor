"""
Capture les scènes de la vidéo de lancement, en VRAIES images de l'application.

    python tools/dev_server.py 8125        (dans un autre terminal)
    python dev/video/capturer.py

Pilote Chrome en headless via le protocole DevTools (CDP) : contrairement à
`chrome --screenshot`, on ATTEND que la scène soit prête (dev/video/scene.js
pose `data-scene-prete` quand la carte, la fiche ou le carnet sont affichés)
avant de photographier — sinon on obtient une page blanche.

Chrome tourne avec un profil JETABLE : les données de démonstration (la sortie
et le selfie du carnet) ne touchent jamais le navigateur de l'utilisateur.

Sortie : dev/video/captures/<scene>.png  (780 x 1688, format téléphone 9:16)
"""

import base64
import json
import pathlib
import shutil
import subprocess
import tempfile
import time
import urllib.request

import websocket  # pip install websocket-client

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
HOTE_APP = "http://localhost:8125"
TELEPHONE = (390, 844)  # 9:16, format des réseaux et du Play Store
TABLETTE = (1180, 820)  # paysage : le carnet s'ouvre alors en DOUBLE page

# (nom de la scène, taille du viewport)
SCENES = [
    ("carte", TELEPHONE),
    ("fiche-viaferrata", TELEPHONE),
    ("fiche-chateau", TELEPHONE),
    ("fiche-grotte", TELEPHONE),
    ("oracle", TELEPHONE),
    ("carnet-p1", TELEPHONE),
    ("carnet-p2", TELEPHONE),
    ("carnet-p3", TELEPHONE),
    ("carnet-photo", TELEPHONE),
    ("carnet-double", TABLETTE),
]

ECHELLE = 2  # image doublée : nette au montage
SORTIE = pathlib.Path(__file__).parent / "captures"


class Cdp:
    """Client minimal du protocole DevTools (un aller-retour à la fois)."""

    def __init__(self, ws_url):
        # suppress_origin : sans en-tête Origin, Chrome ne peut pas la rejeter
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.id = 0

    def envoyer(self, methode, **params):
        self.id += 1
        self.ws.send(json.dumps({"id": self.id, "method": methode, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.id:
                if "error" in msg:
                    raise RuntimeError(f"{methode} : {msg['error']}")
                return msg.get("result", {})

    def evaluer(self, expression):
        r = self.envoyer("Runtime.evaluate", expression=expression, returnByValue=True)
        return r.get("result", {}).get("value")

    def fermer(self):
        self.ws.close()


def demarrer_chrome(profil):
    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--mute-audio",
            "--no-first-run",
            # Chrome refuse les connexions DevTools d'une origine inconnue
            "--remote-allow-origins=*",
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={profil}",
            "--window-size=1280,900",  # la taille réelle vient de l'émulation
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):  # attend que DevTools réponde
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1):
                return proc
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("Chrome n'a pas ouvert son port DevTools.")


def url_page():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list", timeout=5) as r:
        cibles = json.load(r)
    for c in cibles:
        if c.get("type") == "page":
            return c["webSocketDebuggerUrl"]
    raise RuntimeError("Aucun onglet exploitable.")


def capturer(cdp, scene, taille):
    """Navigue, attend le signal de la scène, photographie."""
    largeur, hauteur = taille
    cdp.envoyer("Page.enable")
    cdp.envoyer(
        "Emulation.setDeviceMetricsOverride",
        width=largeur,
        height=hauteur,
        deviceScaleFactor=ECHELLE,
        mobile=largeur < 900,
    )
    cdp.envoyer("Page.navigate", url=f"{HOTE_APP}/dev/video/capture.html?scene={scene}")

    # scene.js pose le drapeau sur la page hôte quand tout est en place
    lu = None
    for _ in range(150):  # 60 s max
        time.sleep(0.4)
        try:
            lu = cdp.evaluer("document.documentElement.dataset.scenePrete || ''")
        except Exception:
            lu = None  # navigation en cours
        if lu == scene:
            break
    if lu != scene:
        return None

    time.sleep(0.8)  # laisse les dernières images arriver
    r = cdp.envoyer("Page.captureScreenshot", format="png")
    chemin = SORTIE / f"{scene}.png"
    chemin.write_bytes(base64.b64decode(r["data"]))
    return chemin


def main():
    # Sans argument : toutes les scènes. Sinon : celles nommées.
    voulues = [a for a in __import__("sys").argv[1:]]
    scenes = [s for s in SCENES if not voulues or s[0] in voulues]

    SORTIE.mkdir(parents=True, exist_ok=True)
    profil = tempfile.mkdtemp(prefix="carte-capture-")
    proc = demarrer_chrome(profil)
    cdp = Cdp(url_page())
    try:
        for scene, taille in scenes:
            chemin = capturer(cdp, scene, taille)
            if chemin:
                print(f"  OK    {scene:18s} -> {chemin.name} ({chemin.stat().st_size // 1024} Ko)")
            else:
                print(f"  ECHEC {scene:18s} (scène jamais prête)")
    finally:
        cdp.fermer()
        proc.terminate()
        proc.wait(timeout=10)
        shutil.rmtree(profil, ignore_errors=True)
    print(f"Terminé — images dans {SORTIE}")


if __name__ == "__main__":
    main()
