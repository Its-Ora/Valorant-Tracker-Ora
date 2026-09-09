# -*- coding: utf-8 -*-
"""
　　✧･ﾟ: *✧･ﾟ:*  T R A C K E R   B Y   E A U R A H  *:･ﾟ✧*:･ﾟ✧

              ／l、
            （ﾟ､ ｡ ７        coucou toi ♡ (˶ᵔ ᵕ ᵔ˶)
              l  ~ヽ         tu lis mon code ? c'est trop mignon
              じしf_,)ノ       installe-toi, j'ai fait le ménage exprès~

Tracker VALORANT temps réel, servi sur une petite page web locale ♡

  ⋆｡°✩  comment on joue avec  ✩°｡⋆
    1. lance ce script sur le PC où Valorant tourne :  python server.py
    2. la fenêtre s'ouvre toute seule (sinon http://localhost:8080)
    3. depuis ton tel : http://<IP_DU_PC>:8080, même Wi-Fi, hein~

  ⋆｡°✩  les raccourcis  ✩°｡⋆
    F6  mode fond (plus de cmd) + démarrage avec Windows
    F7  ouvrir le tracker + refresh complet
    F8  quitter        F9  redémarrage complet

  ⋆｡°✩  dépendances  ✩°｡⋆
    pip install requests   (et urllib3, qui vient avec)

  ⋆｡°✩  petite note sérieuse au milieu des paillettes  ✩°｡⋆
    lecture seule, toujours. on ne touche JAMAIS au client, on ne modifie
    rien dans le jeu, on ne lit pas sa mémoire. on regarde, c'est tout ♡

              ~ dev by eaurah (G_F_), avec beaucoup trop d'amour ~
"""

import base64
import json
import os
import re
import sys
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ╭──────────────────────────────────────────────────────────────╮
# │  les petits réglages ♡
# │  tout ce que tu peux bidouiller sans rien casser~
# ╰──────────────────────────────────────────────────────────────╯
WEB_PORT = 8080          # port de la page web
STATS_MATCHES = 5        # nb de games ranked analysées pour KD / ACS / HS% / forme
STATS_TTL = 900          # secondes avant de rafraîchir les stats d'un joueur
POLL_INTERVAL = 6        # cadence de repli (menus)
POLL_PREGAME = 2         # sélection d'agents : ça bouge vite, on suit au plus près
POLL_INGAME = 3          # en partie : score / agents
SSE_PING = 15            # battement de coeur du flux temps réel (secondes)

# ✿ le petit robinet vers Riot ✿
# un deathmatch = 14 joueurs à analyser d'un coup, faut y aller tout doux~
# Riot ne publie pas ses quotas et ils changent selon l'endpoint, donc le débit
# se règle tout seul : divisé par deux quand ça râle, remonté gentiment sinon ♡
REQ_PER_SEC = 3          # débit de départ, requêtes/seconde vers Riot
REQ_MIN_RATE = 0.7       # plancher
REQ_MAX_RATE = 6         # plafond
REQ_BURST = 6            # rafale autorisée
REQ_CONCURRENCY = 3      # requêtes simultanées max
MAX_RETRY_AFTER = 20     # on ne dort jamais plus longtemps que ça sur un 429
WORKERS = 4              # threads d'analyse des joueurs
BIG_LOBBY = 10           # au-delà (deathmatch), on réduit le nb de matchs analysés
BIG_LOBBY_MATCHES = 3
FORCE_REGION = None      # ex: ("eu", "eu") si la détection auto échoue
LANG = "fr-FR"           # langue des noms de rang / skin
STATS_FALLBACK_UNRATED = False  # UNIQUEMENT du ranked : pas de repli sur les autres modes
RESPECT_STREAMER_MODE = False   # True = affiche un alias anonyme pour les pseudos masqués

VANDAL_ID = "9c82e19d-4575-0200-1a81-3eacf00cf872"
GHOST_ID = "1baa85b4-4c70-1284-64bb-6481dfc3bb4e"
SHOWN_WEAPONS = ("vandal", "ghost", "phantom", "operator", "sheriff", "spectre",
                 "classic", "judge", "odin", "guardian", "bulldog", "marshal")
# celles qu'on montre direct dans la liste, dans cet ordre-là ♡
SKIN_SHOWCASE = ("vandal", "phantom", "operator", "sheriff", "ghost", "spectre",
                 "classic", "judge", "guardian", "marshal", "bulldog", "odin")
MELEE_ID = "2f59173c-4bed-b6c3-2191-dea9b58be9c7"
SOCKET_SKIN = "bcef87d6-209b-46c6-8b19-fbe40bd95abc"
SOCKET_SKIN_LEVEL = "e7c63390-eda7-46e0-bb7a-a6abdacd2433"
SOCKET_CHROMA = "3ad1b2b2-acdb-4524-852f-954a76ddae0a"

CURRENCIES = {
    "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741": {"code": "VP", "name": "Valorant Points"},
    "e59aa87c-4cbf-517a-5983-6e81511be9b7": {"code": "RAD", "name": "Radianite"},
    "85ca954a-41f2-ce94-9b45-8ca3dd39a00d": {"code": "KC", "name": "Crédits du royaume"},
}

CLIENT_PLATFORM = base64.b64encode(json.dumps({
    "platformType": "PC",
    "platformOS": "Windows",
    "platformOSVersion": "10.0.19042.1.256.64bit",
    "platformChipset": "Unknown",
}).encode()).decode()

# on marche aussi bien en .py qu'en .exe ♡ (RES_DIR = les fichiers embarqués,
# APP_DIR = à côté de l'exe, là où vivent tes données)
if getattr(sys, "frozen", False):
    RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))  # fichiers embarqués (index.html)
    APP_DIR = os.path.dirname(sys.executable)                            # à côté de l'exe (journal)
else:
    RES_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = RES_DIR
SEEN_FILE = os.path.join(APP_DIR, "seen_players.json")
NOTES_FILE = os.path.join(APP_DIR, "notes.json")
NAMES_FILE = os.path.join(APP_DIR, "known_names.json")
FLAGS_FILE = os.path.join(APP_DIR, "flags.json")
LOG_FILE = os.path.join(APP_DIR, "tracker.log")
INSTANCE_LOCK = os.path.join(APP_DIR, "tracker.lock")

PLAYER_CACHE_MAX = 400   # joueurs gardes en memoire (stats, rangs, historiques)
NAME_CACHE_MAX = 20000   # pseudos connus ; au-dela les plus anciens sortent
MATCH_CACHE_MAX = 600    # matchs gardes en memoire (LRU)

_io_lock = threading.Lock()
_log_lock = threading.Lock()
_instance_handle = None


def claim_single_instance():
    """On pose une petite patte sur le dossier pour dire « c'est à moi » ♡

    Ton test port_in_use() couvre déjà le cas courant, mais pas deux lancements
    rapprochés : les deux passent le test avant que le premier n'ait pris le port,
    puis écrivent journal, notes et caches en même temps — et le dernier qui
    enregistre efface tranquillement le travail de l'autre (｡•́︿•̀｡)
    """
    global _instance_handle
    try:
        f = open(INSTANCE_LOCK, "a+", encoding="utf-8")
    except Exception:
        return True, None            # dossier en lecture seule : on ne bloque pas pour ca
    try:
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.seek(0)
        info = f.read(300).strip()
        f.close()
        return False, info
    except Exception:
        f.close()                    # verrouillage indisponible : on continue sans
        return True, None
    _instance_handle = f
    try:
        f.seek(0)
        f.truncate(0)
        f.write(json.dumps({"pid": os.getpid(), "port": WEB_PORT,
                            "depuis": time.strftime("%Y-%m-%d %H:%M:%S")}))
        f.flush()
    except Exception:
        pass
    return True, None


def release_single_instance():
    """On retire la patte et on range le verrou en partant ♡"""
    global _instance_handle
    f, _instance_handle = _instance_handle, None
    if not f:
        return
    try:
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        f.close()
        os.remove(INSTANCE_LOCK)
    except Exception:
        pass


def journal(msg, echo=True):
    """Note un petit mot dans tracker.log, avec l'heure ♡"""
    line = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    if echo:
        try:
            print(line)
        except Exception:
            pass
    try:
        with _log_lock:
            if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 512000:
                try:
                    os.replace(LOG_FILE, LOG_FILE + ".1")
                except Exception:
                    pass
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass


def atomic_write_json(path, data, indent=None):
    """On écrit dans un brouillon, PUIS on échange les deux fichiers ♡

    Pourquoi tant de précautions : une coupure de courant pile pendant l'écriture
    laisserait le vrai fichier à moitié écrit, donc illisible. Là, le pire des cas
    c'est un brouillon orphelin, et lui on s'en fiche complètement~

    Le fsync avant l'échange compte aussi : sans lui Windows peut avoir déjà
    remplacé le NOM alors que le CONTENU dort encore dans le cache disque.
    Coupure à cet instant précis = fichier vide. On veut pas ça T_T
    """
    tmp = "%s.%d.tmp" % (path, os.getpid())
    try:
        with _io_lock:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
                f.flush()
                os.fsync(f.fileno())
            for essai in range(3):
                try:
                    os.replace(tmp, path)
                    return True
                except PermissionError:
                    time.sleep(0.15 * (essai + 1))   # antivirus / explorateur Windows
            return False
    except Exception as e:
        journal("ecriture impossible : %s (%s)" % (os.path.basename(path), e))
        return False
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def load_json(path, default):
    """Ouvre un JSON avec plein de délicatesse ♡

    Si le fichier est abîmé, on ne l'écrase JAMAIS : on le met de côté en
    `.corrompu-<date>` et on repart d'une base vide. Parce qu'un journal de
    3000 joueurs, ça ne se récupère pas, et écraser en silence c'est méchant.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, type(default)):
            raise ValueError("attendu %s, trouve %s"
                             % (type(default).__name__, type(data).__name__))
        return data
    except FileNotFoundError:
        return default
    except Exception as e:
        garde = "%s.corrompu-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        try:
            os.replace(path, garde)
            journal("%s illisible (%s) -> mis de cote dans %s"
                    % (os.path.basename(path), e, os.path.basename(garde)))
        except Exception:
            journal("%s illisible (%s)" % (os.path.basename(path), e))
        return default


def trim_cache(store, limit, lock=None):
    """Fait un peu de ménage dans un cache mémoire ♡ les plus vieux s'en vont d'abord

    Sans ça, un tracker laissé ouvert toute une soirée de deathmatch garde chaque
    joueur croisé en mémoire — quelques milliers d'entrées à la fin de la nuit~
    """
    def _do():
        if len(store) <= limit:
            return
        try:
            ordre = sorted(store, key=lambda k: store[k][0])
        except Exception:
            ordre = list(store)
        for k in ordre[:len(store) - limit]:
            store.pop(k, None)
    if lock:
        with lock:
            _do()
    else:
        _do()

# ╭──────────────────────────────────────────────────────────────╮
# │  coucou le client Riot ♡
# │  il laisse traîner ses clés, on les prend~
# ╰──────────────────────────────────────────────────────────────╯

def read_lockfile():
    """On chipe le port et le mot de passe que le client Riot laisse traîner ♡

    Il réécrit ce petit fichier à chaque lancement, et on peut tomber PILE pendant
    qu'il écrit — on lit alors une ligne coupée en deux. Du coup on retente
    gentiment au lieu de râler avec une erreur incompréhensible~
    """
    path = os.path.join(os.getenv("LOCALAPPDATA", ""), "Riot Games",
                        "Riot Client", "Config", "lockfile")
    dernier = None
    for essai in range(3):
        with open(path, "r", encoding="utf-8") as f:
            brut = f.read().strip()
        bouts = brut.split(":")
        if len(bouts) >= 5 and bouts[2].isdigit():
            return bouts[2], bouts[3]
        dernier = brut[:60]
        time.sleep(0.2)
    raise RuntimeError("lockfile illisible (%r) — le client Riot demarre peut-etre" % dernier)


def lockfile_signature():
    """Change dès que le client Riot redémarre ♡

    Et donc dès que le jeton qu'on gardait n'est plus le bon. C'est notre petit
    détecteur de « tiens, il s'est passé quelque chose ».
    """
    try:
        return read_lockfile()
    except Exception:
        return None


def local_get(path):
    """On demande un truc à l'API locale du client ♡"""
    port, password = read_lockfile()
    r = requests.get(
        f"https://127.0.0.1:{port}{path}",
        auth=("riot", password),
        verify=False,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

# ╭──────────────────────────────────────────────────────────────╮
# │  les vrais serveurs de Riot ♡
# │  là où vivent les rangs et les stats
# ╰──────────────────────────────────────────────────────────────╯

def jwt_expiry(token):
    """Quand est-ce que ce jeton devient une citrouille ? ♡ (claim `exp`)

    On décode juste la charge utile, on ne vérifie pas la signature — c'est pas
    notre boulot ici, on veut juste la date.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except Exception:
        return None


ACCOUNT = {"puuid": None, "epoch": 0, "since": time.time()}


def on_account_change(ancien, nouveau):
    """Oh ! on a changé de compte Riot ♡ (déconnexion, ou tu passes sur ton smurf~)

    Ce qu'il faut vraiment jeter est bien plus court qu'on ne croit : presque tous
    les caches sont rangés par puuid, donc les données des AUTRES joueurs restent
    parfaitement valables.

    Par contre la RÉGION doit absolument être redevinée : un second compte peut
    très bien vivre sur un autre shard, et toutes les URL deviendraient fausses
    sans que rien ne vienne le dire. C'est le piège du truc (｡•́︿•̀｡)
    """
    premier = ancien is None
    ACCOUNT["puuid"] = nouveau
    ACCOUNT["epoch"] += 1
    ACCOUNT["since"] = time.time()
    if premier:
        journal("compte connecte : %s…" % nouveau[:8], echo=False)
        return
    try:
        with _latest_lock:
            _latest["data"] = {"state": "LOADING", "players": []}
    except Exception:
        pass
    journal("changement de compte : %s… -> %s… (region redetectee)"
            % (ancien[:8], nouveau[:8]))
    try:
        _wake.set()
    except Exception:
        pass


class Riot:
    def __init__(self):
        self.lock = threading.Lock()
        self.tokens = None          # (access, entitlement, puuid, expiry)
        self.region = None
        self.shard = None
        self.version = None
        self.lock_sig = None        # (port, mdp) du lockfile vu la derniere fois
        self.sess = requests.Session()

    def get_tokens(self):
        bascule = None
        with self.lock:
            # Le Riot Client a-t-il redemarre ? Son lockfile change a chaque
            # lancement. Sans ce test on garderait un jeton encore « valide »
            # selon sa date d'expiration, mais rattache au compte precedent.
            sig = lockfile_signature()
            if sig != self.lock_sig:
                self.lock_sig = sig
                self.tokens = None

            if self.tokens and time.time() < self.tokens[3]:
                return self.tokens
            data = local_get("/entitlements/v1/token")
            if not data.get("accessToken") or not data.get("subject"):
                raise RuntimeError("le client Riot ne renvoie pas de jeton (pas connecte ?)")
            exp = jwt_expiry(data["accessToken"])
            # on suit la VRAIE date d'expiration du jeton : Valorant le fait tourner
            # bien plus souvent que prévu, et un jeton périmé = 400 BAD_CLAIMS~
            expiry = (exp - 60) if exp else (time.time() + 900)
            self.tokens = (data["accessToken"], data["token"], data["subject"], expiry)

            if data["subject"] != ACCOUNT["puuid"]:
                bascule = (ACCOUNT["puuid"], data["subject"])
                self.region = self.shard = None       # redetection obligatoire
            jetons = self.tokens
        if bascule:
            on_account_change(*bascule)               # hors verrou : pas d'inter-blocage
        return jetons

    def invalidate(self, deep=False):
        """Force à tout redemander au prochain passage ♡

        deep=True oublie aussi la région et le shard : indispensable quand le tracker
        a démarré avant Valorant (région résolue à vide ou de travers).
        """
        with self.lock:
            self.tokens = None
            self.lock_sig = None
        self.version = None
        if deep:
            self.region = None
            self.shard = None
            try:
                self.sess.close()
            except Exception:
                pass
            self.sess = requests.Session()

    def get_version(self):
        """La version du client, pour que Riot nous reconnaisse ♡"""
        if not self.version:
            r = requests.get("https://valorant-api.com/v1/version", timeout=10)
            self.version = r.json()["data"]["riotClientVersion"]
        return self.version

    def get_region(self):
        """Sur quel serveur on joue ♡ (log de Valorant, sinon service PAS)"""
        if self.region:
            return self.region, self.shard
        if FORCE_REGION:
            self.region, self.shard = FORCE_REGION
            return self.region, self.shard
        # 1) via le log de Valorant
        try:
            log = os.path.join(os.getenv("LOCALAPPDATA", ""), "VALORANT", "Saved", "Logs", "ShooterGame.log")
            with open(log, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r"https://glz-(.+?)-1\.(.+?)\.a\.pvp\.net", f.read())
            if m:
                self.region, self.shard = m.group(1), m.group(2)
                return self.region, self.shard
        except Exception:
            pass
        # 2) via le service PAS de Riot
        access, _, _, _ = self.get_tokens()
        r = requests.put(
            "https://riot-geo.pas.si.riotgames.com/pas/v1/product/valorant",
            headers={"Authorization": f"Bearer {access}"},
            json={"id_token": local_get("/entitlements/v1/token").get("idToken", "")},
            timeout=10,
        )
        aff = r.json()["affinities"]["live"]
        shard_map = {"latam": "na", "br": "na"}
        self.region, self.shard = aff, shard_map.get(aff, aff)
        return self.region, self.shard

    def headers(self):
        """Les en-têtes qu'un vrai client enverrait ♡"""
        access, ent, _, _ = self.get_tokens()
        return {
            "Authorization": f"Bearer {access}",
            "X-Riot-Entitlements-JWT": ent,
            "X-Riot-ClientPlatform": CLIENT_PLATFORM,
            "X-Riot-ClientVersion": self.get_version(),
        }

    def pd(self):
        _, shard = self.get_region()
        return f"https://pd.{shard}.a.pvp.net"

    def glz(self):
        region, shard = self.get_region()
        return f"https://glz-{region}-1.{shard}.a.pvp.net"

    def shared(self):
        _, shard = self.get_region()
        return f"https://shared.{shard}.a.pvp.net"

    def _request(self, method, url, body=None, ok404=False, ok405=False):
        last = None
        for attempt in range(3):
            RL.acquire()
            with RL.sem:
                r = self.sess.request(method, url, headers=self.headers(),
                                      json=body, verify=False, timeout=15)
            if r.status_code == 404 and ok404:
                return None
            if r.status_code == 405 and ok405:
                return None
            if r.status_code == 429:
                # TOUT LE MONDE fait une pause, pas juste le thread malchanceux~
                wait = min(int(r.headers.get("Retry-After", 5) or 5) + 1, MAX_RETRY_AFTER)
                RL.penalize(wait)
                last = f"429 (Retry-After {wait}s)"
                continue
            # 400/401 : le client a fait tourner son jeton, on va le rechercher ♡
            if r.status_code in (400, 401) and attempt < 2:
                last = f"{r.status_code} {r.text[:120]}"
                self.invalidate()
                time.sleep(1)
                continue
            r.raise_for_status()
            RL.reward()
            return r.json()
        raise RuntimeError(f"{last or 'échec'} sur {url}")

    def get(self, url, ok404=False):
        return self._request("GET", url, ok404=ok404)

    def put(self, url, body):
        return self._request("PUT", url, body=body)

    def post(self, url, body=None, ok404=False):
        return self._request("POST", url, body=body if body is not None else {},
                             ok404=ok404, ok405=ok404)


class RateLimiter:
    """Le petit robinet vers Riot ♡ on n'ouvre pas en grand, on dose

    Un deathmatch, c'est 14 joueurs × (1 historique + N détails de match). Sans
    robinet ça part en centaines de requêtes simultanées, Riot répond 429, chaque
    thread dort son Retry-After dans son coin et relance — et la construction ne
    finit JAMAIS. On a testé, c'est triste.

    Ici : débit global, concurrence bornée, et un 429 met TOUT LE MONDE en pause
    (pas juste le thread malchanceux). Le débit se règle tout seul en AIMD :
    divisé par deux quand ça râle, remonté doucement quand ça passe ♡
    """

    def __init__(self, rate, burst, concurrency):
        self.rate = rate          # ajusté en continu (AIMD) : Riot ne documente pas ses quotas
        self.burst = burst
        self.sem = threading.Semaphore(concurrency)
        self.lock = threading.Lock()
        self.tokens = burst
        self.last = time.monotonic()
        self.cooldown_until = 0.0
        self.streak = 0

    def acquire(self):
        """Attend gentiment son tour avant de parler à Riot ♡"""
        while True:
            with self.lock:
                now = time.monotonic()
                if now < self.cooldown_until:
                    delay = self.cooldown_until - now
                else:
                    self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
                    self.last = now
                    if self.tokens >= 1:
                        self.tokens -= 1
                        return
                    delay = (1 - self.tokens) / self.rate
            time.sleep(min(delay, 2))

    def penalize(self, seconds):
        """Riot a dit non : on ferme de moitié et tout le monde attend ♡"""
        with self.lock:
            self.cooldown_until = max(self.cooldown_until, time.monotonic() + seconds)
            self.rate = max(REQ_MIN_RATE, self.rate / 2)      # on ralentit franchement
            self.streak = 0

    def reward(self):
        """Après une belle série, on rouvre le robinet tout doucement ♡"""
        with self.lock:
            self.streak += 1
            if self.streak >= 15:
                self.streak = 0
                self.rate = min(REQ_MAX_RATE, self.rate + 0.25)

    def cooling(self):
        """Combien de secondes il reste à bouder, s'il boude ♡"""
        with self.lock:
            return max(0, self.cooldown_until - time.monotonic())


RL = RateLimiter(REQ_PER_SEC, REQ_BURST, REQ_CONCURRENCY)
riot = Riot()

# ╭──────────────────────────────────────────────────────────────╮
# │  les jolies images ♡
# │  noms d'agents, skins, icônes de rang~
# ╰──────────────────────────────────────────────────────────────╯

STATIC = {}

def load_static():
    """On va chercher toutes les jolies images et tous les jolis noms ♡"""
    def fetch(url):
        # valorant-api a parfois le hoquet : on réessaie plutôt que de démarrer à moitié~
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=20)
                r.raise_for_status()
                return r.json()["data"]
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f"impossible de charger {url} : {e}")
                time.sleep(2 * (attempt + 1))

    print("Chargement des données statiques (skins, rangs, agents, armes, cartes joueur)...")
    skinlevels = fetch(f"https://valorant-api.com/v1/weapons/skinlevels?language={LANG}")
    STATIC["skinlevels"] = {s["uuid"].lower(): s for s in skinlevels}

    skins = fetch(f"https://valorant-api.com/v1/weapons/skins?language={LANG}")
    STATIC["skins"] = {s["uuid"].lower(): s for s in skins}
    STATIC["chromas"] = {}
    STATIC["level_to_skin"] = {}
    for s in skins:
        for c in s.get("chromas") or []:
            c["_skinName"] = s["displayName"]
            c["_tier"] = s.get("contentTierUuid")
            STATIC["chromas"][c["uuid"].lower()] = c
        for lv in s.get("levels") or []:
            STATIC["level_to_skin"][lv["uuid"].lower()] = s

    weapons = fetch(f"https://valorant-api.com/v1/weapons?language={LANG}")
    STATIC["weapons"] = {}
    STATIC["weapon_order"] = []
    for w in weapons:
        wid = w["uuid"].lower()
        STATIC["weapons"][wid] = w["displayName"]
        STATIC["weapon_order"].append(wid)
    # le couteau tout à la fin, comme dans le jeu ♡
    if MELEE_ID in STATIC["weapon_order"]:
        STATIC["weapon_order"].remove(MELEE_ID)
        STATIC["weapon_order"].append(MELEE_ID)

    # on retrouve les armes par leur nom : plus solide qu'un UUID figé ♡
    STATIC["weapon_ids"] = {"vandal": VANDAL_ID, "ghost": GHOST_ID}
    for wid, wname in STATIC["weapons"].items():
        low = (wname or "").strip().lower()
        if low in SHOWN_WEAPONS:
            STATIC["weapon_ids"][low] = wid

    tiersets = fetch(f"https://valorant-api.com/v1/competitivetiers?language={LANG}")
    latest = tiersets[-1]["tiers"]
    STATIC["tiers"] = {t["tier"]: t for t in latest}

    agents = fetch(f"https://valorant-api.com/v1/agents?language={LANG}&isPlayableCharacter=true")
    STATIC["agents"] = {a["uuid"].lower(): a for a in agents}

    maps = fetch(f"https://valorant-api.com/v1/maps?language={LANG}")
    # les endpoints renvoient tantôt l'uuid, tantôt le mapUrl. selon leur humeur~
    STATIC["maps_by_id"] = {m["uuid"].lower(): m for m in maps}
    for m in maps:
        if m.get("mapUrl"):
            STATIC["maps_by_id"][m["mapUrl"].lower()] = m

    cards = fetch("https://valorant-api.com/v1/playercards")
    STATIC["cards"] = {c["uuid"].lower(): c for c in cards}

    titles = fetch(f"https://valorant-api.com/v1/playertitles?language={LANG}")
    STATIC["titles"] = {t["uuid"].lower(): t for t in titles}

    borders = fetch("https://valorant-api.com/v1/levelborders")
    STATIC["borders"] = {b["uuid"].lower(): b for b in borders}

    seasons = fetch("https://valorant-api.com/v1/seasons")
    by_uuid = {s["uuid"].lower(): s for s in seasons}
    STATIC["seasons"] = {}
    for s in seasons:
        label = s.get("title") or s.get("displayName") or ""
        parent = by_uuid.get((s.get("parentUuid") or "").lower())
        if not s.get("title") and parent:
            label = f"{parent.get('displayName')} {s.get('displayName')}"
        STATIC["seasons"][s["uuid"].lower()] = {
            "label": (label or "").replace(" // ", " "),
            "start": s.get("startTime"),
            "act": s.get("type") == "EAresSeasonType::Act",
        }

    ctiers = fetch(f"https://valorant-api.com/v1/contenttiers?language={LANG}")
    STATIC["contenttiers"] = {c["uuid"].lower(): c for c in ctiers}

    bundles = fetch(f"https://valorant-api.com/v1/bundles?language={LANG}")
    STATIC["bundles"] = {b["uuid"].lower(): b for b in bundles}

    buddies = fetch("https://valorant-api.com/v1/buddies/levels")
    STATIC["buddylevels"] = {b["uuid"].lower(): b for b in buddies}

    sprays = fetch(f"https://valorant-api.com/v1/sprays?language={LANG}")
    STATIC["sprays"] = {s["uuid"].lower(): s for s in sprays}

    print("Données statiques OK.")


def hexcol(c):
    """'868986ff' devient '#868986' ♡ petit coup de pinceau"""
    if not c:
        return None
    return "#" + c[:6]


def tier_info(tier):
    # STATIC.get : on est appelé depuis des `except`, interdiction de lever quoi que ce soit
    """Le rang joliment habillé : nom, icône, couleur ♡

    Le STATIC.get() n'est pas une coquetterie : on est appelé depuis des blocs
    `except`, donc interdiction absolue de lever quoi que ce soit~
    """
    t = STATIC.get("tiers", {}).get(tier)
    if not t or tier is None:
        return {"name": "Unranked", "icon": None, "tier": 0, "color": "#5b6b7b", "large": None}
    return {
        "name": t["tierName"].title(),
        "icon": t["smallIcon"],
        "large": t.get("largeIcon"),
        "tier": tier,
        "color": hexcol(t.get("color")),
    }

# ╭──────────────────────────────────────────────────────────────╮
# │  l'acte en cours ♡
# │  pour savoir de quelle saison on parle
# ╰──────────────────────────────────────────────────────────────╯

_season = {"id": None, "ts": 0}

def current_season_id():
    """L'acte en cours, avec un cache d'une heure ♡"""
    if _season["id"] and time.time() - _season["ts"] < 3600:
        return _season["id"]
    data = riot.get(f"{riot.shared()}/content-service/v3/content")
    for s in data.get("Seasons", []):
        if s.get("IsActive") and s.get("Type") == "act":
            _season["id"] = s["ID"]
            _season["ts"] = time.time()
            return s["ID"]
    return None


def season_label(sid):
    """Le joli nom d'une saison (« Episode 9 Acte 1 ») ♡"""
    return (STATIC.get("seasons", {}).get((sid or "").lower()) or {}).get("label") or "?"

# ╭──────────────────────────────────────────────────────────────╮
# │  les stats, bien rangées ♡
# │  avec plein de caches pour pas fatiguer Riot
# ╰──────────────────────────────────────────────────────────────╯

_mmr_cache = {}      # puuid -> (ts, data)
_stats_cache = {}    # puuid -> (ts, data)
_match_cache = OrderedDict()   # matchId -> {puuid: stats parsées}  (LRU)
_locker_cache = {}   # puuid -> (ts, locker, "Nom#TAG")
_hist_cache = {}     # puuid -> (ts, [matchIds])
_cache_lock = threading.Lock()


def cache_ttl(puuid):
    """Un petit décalage propre à chaque joueur ♡

    Sinon les 10 caches expirent PILE en même temps et relancent 100 requêtes d'un
    coup au milieu d'une partie. Là ils se réveillent chacun leur tour~
    """
    return STATS_TTL + (hash(puuid) % 240)


def get_mmr_raw(puuid):
    """Le gros paquet de MMR brut d'un joueur, tel que Riot le crache ♡"""
    with _cache_lock:
        hit = _mmr_cache.get(puuid)
    if hit and time.time() - hit[0] < cache_ttl(puuid):
        return hit[1]
    data = riot.get(f"{riot.pd()}/mmr/v1/players/{puuid}", ok404=True) or {}
    with _cache_lock:
        _mmr_cache[puuid] = (time.time(), data)
    trim_cache(_mmr_cache, PLAYER_CACHE_MAX, _cache_lock)
    return data


def get_ranks(puuid):
    """Rang actuel, peak (avec son acte), RR, leaderboard, winrate de l'acte ♡"""
    try:
        data = get_mmr_raw(puuid)
        comp = (data.get("QueueSkills", {}) or {}).get("competitive", {}) or {}
        seasonal = comp.get("SeasonalInfoBySeasonID") or {}
        season = current_season_id()
        latest = data.get("LatestCompetitiveUpdate") or {}

        cur_info = seasonal.get(season) or {}
        cur = cur_info.get("CompetitiveTier", 0) or 0
        rr = cur_info.get("RankedRating")
        if not cur:
            cur = latest.get("TierAfterUpdate", 0) or 0
            if rr is None:
                rr = latest.get("RankedRatingAfterUpdate")

        # le peak : le plus haut palier jamais atteint, toutes saisons confondues ♡
        peak, peak_season = 0, None
        for sid, info in seasonal.items():
            tiers = [int(k) for k in (info.get("WinsByTier") or {}).keys()]
            tiers.append(info.get("CompetitiveTier", 0) or 0)
            best = max(tiers) if tiers else 0
            if best > peak:
                peak, peak_season = best, sid
        if cur > peak:
            peak, peak_season = cur, season

        wins = cur_info.get("NumberOfWins", 0) or 0
        games = cur_info.get("NumberOfGames", 0) or 0
        lb = cur_info.get("LeaderboardRank", 0) or 0

        # l'historique des actes, pour la jolie courbe et la fiche joueur~
        acts = []
        for sid, info in seasonal.items():
            t = info.get("CompetitiveTier", 0) or 0
            tiers = [int(k) for k in (info.get("WinsByTier") or {}).keys()] or [t]
            meta = STATIC.get("seasons", {}).get((sid or "").lower()) or {}
            if not meta.get("act"):
                continue
            acts.append({
                "season": meta.get("label") or "?",
                "start": meta.get("start"),
                "rank": tier_info(t)["name"],
                "peak": tier_info(max(tiers + [t]))["name"],
                "peakTier": max(tiers + [t]),
                "wins": info.get("NumberOfWins", 0) or 0,
                "games": info.get("NumberOfGames", 0) or 0,
            })
        acts.sort(key=lambda a: a.get("start") or "", reverse=True)

        result = {
            "rank": tier_info(cur),
            "peak": tier_info(max(peak, cur)),
            "peakSeason": season_label(peak_season),
            "rr": rr,
            "rrChange": latest.get("RankedRatingEarned"),
            "leaderboard": lb or None,
            "actWins": wins,
            "actGames": games,
            "actWinrate": round(100 * wins / games) if games else None,
            "acts": acts[:12],
            "hiddenRank": bool(data.get("IsActRankBadgeHidden")),
        }
    except Exception as e:
        result = {"rank": tier_info(0), "peak": tier_info(0), "peakSeason": None, "rr": None,
                  "rrChange": None, "leaderboard": None, "actWins": 0, "actGames": 0,
                  "actWinrate": None, "acts": [], "error": str(e)}
    return result


def parse_match(details):
    """Résume UNE partie pour TOUS ses joueurs d'un coup ♡

    Mutualisé exprès : si cinq personnes du lobby ont joué la même game, on ne la
    télécharge et on ne l'analyse qu'une seule fois. Riot nous remercie~
    """
    info = details.get("matchInfo") or {}
    teams = {t.get("teamId"): t for t in details.get("teams") or []}

    dmg = {}
    for rnd in details.get("roundResults") or []:
        for ps in rnd.get("playerStats") or []:
            pu = ps.get("subject")
            d = dmg.setdefault(pu, [0, 0, 0, 0])
            for x in ps.get("damage") or []:
                d[0] += x.get("headshots", 0)
                d[1] += x.get("bodyshots", 0)
                d[2] += x.get("legshots", 0)
                d[3] += x.get("damage", 0)

    out = {}
    for p in details.get("players") or []:
        pu = p.get("subject")
        if not pu:
            continue
        st = p.get("stats") or {}
        team = teams.get(p.get("teamId")) or {}
        rounds = st.get("roundsPlayed") or team.get("roundsPlayed") or 0
        h, b, l, dd = dmg.get(pu, [0, 0, 0, 0])
        won = team.get("won")
        out[pu] = {
            "matchId": info.get("matchId"),
            "start": info.get("gameStartMillis"),
            "length": info.get("gameLengthMillis"),
            "mapId": (info.get("mapId") or ""),
            "queue": info.get("queueID") or "",
            "ranked": bool(info.get("isRanked")),
            "agent": (p.get("characterId") or "").lower(),
            "tier": p.get("competitiveTier"),
            "name": p.get("gameName"),
            "tag": p.get("tagLine"),
            "team": p.get("teamId"),
            "kills": st.get("kills", 0), "deaths": st.get("deaths", 0),
            "assists": st.get("assists", 0), "score": st.get("score", 0),
            "rounds": rounds, "head": h, "body": b, "leg": l, "dmg": dd,
            "won": None if won is None else bool(won),
            "roundsWon": team.get("roundsWon"),
            "roundsLost": (team.get("roundsPlayed") or 0) - (team.get("roundsWon") or 0),
        }
    return out


def get_match_players(match_id):
    """Les stats de tous les joueurs d'un match (avec un joli cache LRU) ♡"""
    with _cache_lock:
        if match_id in _match_cache:
            _match_cache.move_to_end(match_id)
            return _match_cache[match_id]
    data = riot.get(f"{riot.pd()}/match-details/v1/matches/{match_id}", ok404=True)
    parsed = parse_match(data) if data else {}
    with _cache_lock:
        _match_cache[match_id] = parsed
        _match_cache.move_to_end(match_id)
        # on evince la plus ancienne entree, pas TOUT le cache : vider d'un coup
        # jetait aussi les matchs du lobby en cours, a retelecharger aussitot
        while len(_match_cache) > MATCH_CACHE_MAX:
            _match_cache.popitem(last=False)
    return parsed


def get_history(puuid, queue="competitive", n=None):
    """La liste des derniers matchIDs d'un joueur (avec un cache court) ♡"""
    n = n or STATS_MATCHES
    key = (puuid, queue, n)
    with _cache_lock:
        hit = _hist_cache.get(key)
    if hit and time.time() - hit[0] < STATS_TTL:
        return hit[1]
    q = f"&queue={queue}" if queue else ""
    try:
        hist = riot.get(
            f"{riot.pd()}/match-history/v1/history/{puuid}?startIndex=0&endIndex={n}{q}"
        ) or {}
        ids = [h["MatchID"] for h in (hist.get("History") or [])[:n] if h.get("MatchID")]
    except Exception as e:
        # Un 429 passager mettait cet historique VIDE en cache pour 15 minutes :
        # le joueur restait affiche sans aucune stat alors que tout remarchait.
        # On ne memorise donc PAS un echec, le prochain cycle reessaiera.
        journal("historique indisponible pour %s… (%s)" % (puuid[:8], e), echo=False)
        return (hit[1] if hit else [])
    with _cache_lock:
        _hist_cache[key] = (time.time(), ids)
    trim_cache(_hist_cache, PLAYER_CACHE_MAX, _cache_lock)
    return ids


def get_recent_stats(puuid, n_matches=None):
    """KD / KDA / ACS / ADR / HS% / winrate / forme / agents ♡

    Le tout sur les X dernières parties classées. C'est LA fonction qui coûte cher
    (environ 6 requêtes par joueur), d'où tous les caches autour~
    """
    n_matches = n_matches or STATS_MATCHES
    with _cache_lock:
        hit = _stats_cache.get(puuid)
    if hit and time.time() - hit[0] < cache_ttl(puuid):
        return hit[1]

    result = {"kd": None, "kda": None, "hs": None, "acs": None, "adr": None,
              "games": 0, "wins": 0, "winrate": None, "form": [], "topAgents": [],
              "matchIds": [], "queueUsed": None}
    try:
        ids = get_history(puuid, "competitive", n_matches)
        queue_used = "competitive"
        if not ids and STATS_FALLBACK_UNRATED:
            ids = get_history(puuid, None, n_matches)
            queue_used = "all"

        k = d = a = sc = rounds = head = body = leg = dmg = wins = games = 0
        form, agents = [], {}
        for mid in ids:
            players = get_match_players(mid)
            me = players.get(puuid)
            if not me:
                continue
            games += 1
            k += me["kills"]; d += me["deaths"]; a += me["assists"]
            sc += me["score"]; rounds += me["rounds"]
            head += me["head"]; body += me["body"]; leg += me["leg"]; dmg += me["dmg"]
            if me["won"] is True:
                wins += 1
                form.append("W")
            elif me["won"] is False:
                form.append("L")
            else:
                form.append("-")
            if me["agent"]:
                ag = agents.setdefault(me["agent"], {"games": 0, "wins": 0})
                ag["games"] += 1
                ag["wins"] += 1 if me["won"] else 0

        shots = head + body + leg
        top = []
        for aid, v in sorted(agents.items(), key=lambda x: -x[1]["games"])[:3]:
            meta = STATIC["agents"].get(aid) or {}
            top.append({
                "name": meta.get("displayName") or "?",
                "icon": meta.get("displayIcon"),
                "games": v["games"],
                "wins": v["wins"],
            })

        result = {
            "kd": round(k / max(d, 1), 2) if games else None,
            "kda": round((k + a) / max(d, 1), 2) if games else None,
            "hs": round(100 * head / shots, 1) if shots else None,
            "acs": round(sc / rounds) if rounds else None,
            "adr": round(dmg / rounds) if rounds else None,
            "games": games,
            "wins": wins,
            "winrate": round(100 * wins / games) if games else None,
            "form": form,
            "topAgents": top,
            "matchIds": ids,
            "queueUsed": queue_used if games else None,
        }
    except Exception as e:
        result["error"] = str(e)
        # echec = on ne garde le resultat vide que 20 s, sinon un simple hoquet
        # reseau prive le joueur de ses stats pendant tout le quart d'heure
        with _cache_lock:
            _stats_cache[puuid] = (time.time() - cache_ttl(puuid) + 20, result)
        return result
    with _cache_lock:
        _stats_cache[puuid] = (time.time(), result)
    trim_cache(_stats_cache, PLAYER_CACHE_MAX, _cache_lock)
    return result


def smurf_score(level, rank_tier, peak_tier, st):
    """Petit détecteur de smurf ♡ ce sont des INDICES, pas une accusation

    Niveau bas + KD haut + ACS haut + gros écart avec le peak. Ça se trompe, et
    c'est normal : on affiche « smurf probable », jamais « smurf ». Sois sympa~
    """
    reasons = []
    score = 0
    if level and level < 60:
        score += 2
        reasons.append(f"niveau {level} très bas")
    elif level and level < 120:
        score += 1
        reasons.append(f"niveau {level} bas")
    if st.get("kd") and st["kd"] >= 1.4:
        score += 2
        reasons.append(f"KD {st['kd']}")
    elif st.get("kd") and st["kd"] >= 1.2:
        score += 1
        reasons.append(f"KD {st['kd']}")
    if st.get("acs") and st["acs"] >= 260:
        score += 2
        reasons.append(f"ACS {st['acs']}")
    elif st.get("acs") and st["acs"] >= 230:
        score += 1
        reasons.append(f"ACS {st['acs']}")
    if st.get("hs") and st["hs"] >= 28:
        score += 1
        reasons.append(f"HS {st['hs']}%")
    if peak_tier and rank_tier and peak_tier - rank_tier >= 6:
        score += 1
        reasons.append("gros écart avec le peak")
    return {"score": score, "flag": score >= 4, "reasons": reasons}

# ╭──────────────────────────────────────────────────────────────╮
# │  qui est qui, et avec qui ♡
# │  pseudos, duos, et les jolis skins~
# ╰──────────────────────────────────────────────────────────────╯

_name_cache = {}  # puuid -> (nom, tag) — résolus par le name-service
_names_dirty = False
_names_lock = threading.Lock()


def _load_known_names():
    """On ressort le carnet de pseudos d'à côté ♡"""
    data = load_json(NAMES_FILE, {})
    with _names_lock:
        for pu, v in data.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                _name_cache[pu] = (v[0], v[1])


def _save_known_names():
    """On COPIE sous verrou avant de sérialiser ♡ (oui, c'est important)

    Sérialiser le dictionnaire pendant qu'un autre thread y glisse un pseudo lève
    « dictionary changed size during iteration » — l'exception était avalée et
    l'enregistrement perdu en silence. Mesuré sur l'ancienne version : 46 pertes
    en 2,5 s. Résultat : tout le monde en « Anonyme-XXXX » au redémarrage T_T
    """
    global _names_dirty
    with _names_lock:
        if not _names_dirty:
            return
        snap = {k: list(v) for k, v in _name_cache.items()}
        _names_dirty = False
    if not atomic_write_json(NAMES_FILE, snap):
        with _names_lock:
            _names_dirty = True          # on retentera au prochain passage


def get_names(puuids):
    """Demande au name-service qui est qui ♡ avec retries et repli sur le carnet

    Petite note honnête : le name-service renvoie le pseudo MÊME quand le joueur a
    coché « masquer mon nom » (c'est un réglage d'affichage côté client, pas une
    protection). Mets RESPECT_STREAMER_MODE = True si tu préfères respecter son
    choix et afficher un alias — et franchement, c'est plus mignon comme ça ♡
    """
    global _names_dirty
    puuids = list(puuids)
    ok = False
    for attempt in range(3):
        try:
            data = riot.put(f"{riot.pd()}/name-service/v2/players", puuids)
            with _names_lock:
                for d in data or []:
                    nm = (d.get("GameName") or "").strip()
                    if nm and d.get("Subject"):
                        paire = (nm, d.get("TagLine", ""))
                        if _name_cache.get(d["Subject"]) != paire:
                            _name_cache[d["Subject"]] = paire
                            _names_dirty = True
            trim_cache(_name_cache, NAME_CACHE_MAX, _names_lock)
            ok = True
            break
        except Exception:
            time.sleep(1 + attempt)
    if ok:
        _save_known_names()
    with _names_lock:
        return {pu: _name_cache[pu] for pu in puuids if pu in _name_cache}


def anon_alias(puuid):
    """Un petit surnom stable et lisible pour quelqu'un qui se cache ♡"""
    return "Anonyme-" + (puuid or "0000").replace("-", "")[-4:].upper()


def resolve_name(puuid, names, incognito):
    """(nom, tag, d'où ça vient) ♡

    Dans l'ordre : réponse fraîche du name-service → carnet sur disque (ça couvre
    un timeout ou un 429 passager, la cause des vieux « Joueur caché ») → alias
    anonyme stable en dernier recours, pour que deux inconnus ne portent jamais
    le même petit nom~
    """
    if RESPECT_STREAMER_MODE and incognito:
        return anon_alias(puuid), "", "hidden"
    if puuid in names:
        return names[puuid][0], names[puuid][1], "api"
    if puuid in _name_cache:
        return _name_cache[puuid][0], _name_cache[puuid][1], "cache"
    return anon_alias(puuid), "", "unknown"


def get_parties():
    """Qui est en groupe avec qui ♡ (via les présences du chat local)

    Attention : ça ne marche QUE pour tes amis et ton groupe. Pour les ennemis,
    c'est guess_parties() qui prend le relais avec ses petites déductions~
    """
    out = {}
    try:
        data = local_get("/chat/v4/presences")
        for p in data.get("presences", []):
            if p.get("product") not in (None, "valorant"):
                continue
            priv = p.get("private")
            if not priv:
                continue
            try:
                blob = json.loads(base64.b64decode(priv + "==").decode("utf-8", "ignore"))
                pid = blob.get("partyId")
                if pid:
                    out[p["puuid"]] = pid
            except Exception:
                continue
    except Exception:
        pass
    return out


def my_presence(my_puuid):
    """Ta propre présence : score en direct, état de session, temps en file ♡"""
    try:
        data = local_get("/chat/v4/presences")
        for p in data.get("presences", []):
            if p.get("puuid") != my_puuid:
                continue
            priv = p.get("private")
            if not priv:
                return {}
            return json.loads(base64.b64decode(priv + "==").decode("utf-8", "ignore"))
    except Exception:
        pass
    return {}


def guess_parties(puuids, stats):
    """Les duos probables chez l'adversaire ♡ notre petite enquête

    L'astuce : deux joueurs qui reviennent dans les mêmes parties récentes ET dans
    la même équipe sont très probablement ensemble. On demande au moins deux
    coïncidences avant d'oser le dire~ (¬‿¬)
    """
    sets = {}
    for pu in puuids:
        ids = set((stats.get(pu) or {}).get("matchIds") or [])
        if ids:
            sets[pu] = ids
    groups = {}
    keys = list(sets)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            shared = sets[a] & sets[b]
            if len(shared) < 2:
                continue
            # étaient-ils dans la même équipe ? c'est ça qui compte ♡
            same = 0
            for mid in shared:
                pl = _match_cache.get(mid) or {}
                if pl.get(a) and pl.get(b) and pl[a]["team"] == pl[b]["team"]:
                    same += 1
            if same >= 2:
                g = groups.setdefault(a, {a})
                g.add(b)
                groups[b] = g
    out = {}
    for pu, g in groups.items():
        if len(g) >= 2:
            out[pu] = "|".join(sorted(g))
    return out


def skin_from_sockets(weapon_entry):
    """On déballe le skin équipé sur une arme ♡

    C'est le coin le plus obscur de l'API Riot : chaque arme a des « sockets »
    identifiés par uuid (skin de base, niveau, chroma). On lit les trois et on
    recolle tout ça en quelque chose de présentable~
    """
    sockets = (weapon_entry or {}).get("Sockets") or {}

    def sock(sid):
        s = sockets.get(sid)
        return (s or {}).get("Item", {}).get("ID", "").lower() or None

    chroma_id = sock(SOCKET_CHROMA)
    level_id = sock(SOCKET_SKIN_LEVEL)
    skin_id = sock(SOCKET_SKIN)

    name = icon = None
    ch = STATIC["chromas"].get(chroma_id) if chroma_id else None
    lv = STATIC["skinlevels"].get(level_id) if level_id else None
    sk = STATIC["skins"].get(skin_id) if skin_id else None
    if not sk and level_id:
        sk = STATIC["level_to_skin"].get(level_id)
    if ch:
        name = ch.get("_skinName") or (sk or {}).get("displayName")
        icon = ch.get("fullRender") or ch.get("displayIcon")
    if not name and lv:
        name = lv.get("displayName")
    if not icon and lv:
        icon = lv.get("displayIcon")
    if not name and sk:
        name = sk.get("displayName")
    if not icon and sk:
        icon = sk.get("displayIcon") or ((sk.get("chromas") or [{}])[0]).get("fullRender")
    if not name:
        return None

    tier = STATIC["contenttiers"].get(((sk or {}).get("contentTierUuid") or "").lower())
    # le niveau et le chroma équipés (« Niv. 4 », « Var. 2 ») ♡
    variant = None
    if sk:
        lvls = [l["uuid"].lower() for l in (sk.get("levels") or [])]
        chs = [c["uuid"].lower() for c in (sk.get("chromas") or [])]
        if level_id in lvls and len(lvls) > 1:
            variant = f"Niv. {lvls.index(level_id) + 1}"
        if chroma_id in chs and chs.index(chroma_id) > 0:
            variant = (variant + " · " if variant else "") + f"Var. {chs.index(chroma_id) + 1}"

    # et le petit porte-clés, s'il y en a un ♡
    buddy = None
    for s in sockets.values():
        bid = ((s or {}).get("Item") or {}).get("ID", "").lower()
        b = STATIC["buddylevels"].get(bid)
        if b:
            buddy = {"name": b.get("displayName"), "icon": b.get("displayIcon")}
            break

    return {
        "name": name, "icon": icon, "variant": variant, "buddy": buddy,
        "tier": tier.get("displayName") if tier else None,
        "tierIcon": tier.get("displayIcon") if tier else None,
        "tierColor": hexcol(tier.get("highlightColor")) if tier else None,
    }


def weapon_skin(items, weapon):
    """Le skin posé sur une arme précise ('vandal', 'ghost') ♡"""
    wanted = (STATIC.get("weapon_ids") or {}).get(weapon)
    if not wanted:
        return None
    for k, v in (items or {}).items():
        if k.lower() == wanted.lower():
            return skin_from_sockets(v)
    return None


def showcase_skins(items, limit=6):
    """Les skins qu'on montre direct dans la liste des joueurs ♡

    Uniquement ceux qui sont vraiment possédés (on saute les armes en apparence
    d'origine), couteau compris, dans l'ordre des armes qui comptent. Vide en
    pregame et en lobby : Riot n'y renvoie pas de loadout fiable, alors autant
    ne rien promettre~
    """
    if not items:
        return []
    ids = STATIC.get("weapon_ids") or {}
    order = [(n, (ids.get(n) or "").lower()) for n in SKIN_SHOWCASE]
    order.append(("melee", MELEE_ID.lower()))
    low = {str(k).lower(): v for k, v in items.items()}
    out = []
    for name, wid in order:
        if not wid or wid not in low:
            continue
        sk = skin_from_sockets(low[wid])
        if not sk or not sk.get("name"):
            continue
        plain = sk["name"].strip().lower()
        if plain.startswith("standard") or plain.startswith("par défaut"):
            continue
        out.append({
            "weapon": STATIC["weapons"].get(wid) or name.title(),
            "skin": sk["name"],
            "icon": sk.get("icon"),
            "variant": sk.get("variant"),
            "buddy": (sk.get("buddy") or {}).get("name") if sk.get("buddy") else None,
            "tier": sk.get("tier"),
            "tierColor": sk.get("tierColor"),
        })
        if len(out) >= limit:
            break
    return out


def vandal_from_items(items):
    return weapon_skin(items, "vandal")


def locker_from_items(items):
    """Tous les skins équipés, rangés dans l'ordre du jeu ♡"""
    out = []
    for wid, w in (items or {}).items():
        wid_l = wid.lower()
        wname = STATIC["weapons"].get(wid_l)
        if not wname:
            continue
        sk = skin_from_sockets(w)
        try:
            order = STATIC["weapon_order"].index(wid_l)
        except ValueError:
            order = 99
        out.append({
            "weapon": wname,
            "order": order,
            "skin": sk["name"] if sk else "Standard",
            "icon": sk["icon"] if sk else None,
            "variant": sk.get("variant") if sk else None,
            "buddy": sk.get("buddy") if sk else None,
            "tier": sk.get("tier") if sk else None,
            "tierIcon": sk.get("tierIcon") if sk else None,
            "tierColor": sk.get("tierColor") if sk else None,
        })
    out.sort(key=lambda x: x["order"])
    for o in out:
        o.pop("order", None)
    return out


def extract_loadouts(raw, pregame):
    """Les loadouts, dans le même ordre que la liste des joueurs ♡"""
    out = []
    for entry in (raw or {}).get("Loadouts", []):
        if pregame:
            items = entry.get("Items") or (entry.get("Loadout") or {}).get("Items")
        else:
            items = (entry.get("Loadout") or {}).get("Items") or entry.get("Items")
        out.append(items or {})
    return out

# ╭──────────────────────────────────────────────────────────────╮
# │  le carnet de rencontres ♡
# │  « ah bah tiens, encore lui » (¬‿¬)
# ╰──────────────────────────────────────────────────────────────╯

_seen_lock = threading.Lock()


def _load_seen():
    return load_json(SEEN_FILE, {})


def _save_seen(data):
    atomic_write_json(SEEN_FILE, data)


def log_and_check_seen(puuids, names, my_puuid, match_id, map_name, queue_name,
                       agents=None, my_agent=None, teams=None, ranks=None):
    """On note tout le monde dans le carnet, et on regarde si on les connaît ♡

    Retourne puuid -> petit récap des fois où vous vous êtes déjà croisés.
    """
    agents = agents or {}
    teams = teams or {}
    ranks = ranks or {}
    out = {}
    now = time.time()
    with _seen_lock:
        data = _load_seen()
        for pu in puuids:
            if pu == my_puuid:
                continue
            rec = data.get(pu)
            if rec:
                prev = [s for s in rec.get("seen", []) if s.get("match") != match_id]
                if prev:
                    last = prev[-1]
                    allies = sum(1 for s in prev if s.get("team") == "ally")
                    out[pu] = {
                        "ts": last.get("ts"),
                        "map": last.get("map"),
                        "queue": last.get("queue"),
                        "agent": last.get("agent"),
                        "myAgent": last.get("myAgent"),
                        "team": last.get("team"),
                        "count": len(prev),
                        "asAlly": allies,
                        "asEnemy": len(prev) - allies,
                    }
            rec = data.setdefault(pu, {"seen": []})
            name, tag = names.get(pu, (None, None))
            if name:
                rec["name"] = f"{name}#{tag}"
            if ranks.get(pu):
                rec["rank"] = ranks[pu]
            cur = next((s for s in rec["seen"] if s.get("match") == match_id), None)
            if cur is None:
                rec["seen"].append({
                    "ts": now, "match": match_id, "map": map_name, "queue": queue_name,
                    "agent": agents.get(pu), "myAgent": my_agent, "team": teams.get(pu),
                })
                rec["seen"] = rec["seen"][-25:]
            else:
                # on complète les agents dès qu'on les connaît (les picks arrivent en retard~)
                if agents.get(pu) and not cur.get("agent"):
                    cur["agent"] = agents.get(pu)
                if my_agent and not cur.get("myAgent"):
                    cur["myAgent"] = my_agent
                if teams.get(pu) and not cur.get("team"):
                    cur["team"] = teams.get(pu)
        _save_seen(data)
    return out


def backfill_names():
    """Rattrape les vieilles entrées du carnet enregistrées sans pseudo ♡"""
    with _seen_lock:
        data = _load_seen()
    todo = [pu for pu, rec in data.items()
            if (not rec.get("name") or rec["name"].startswith("?#")) and pu not in _name_cache]
    if not todo:
        return
    found = 0
    for i in range(0, len(todo), 40):
        chunk = todo[i:i + 40]
        names = get_names(chunk)
        with _seen_lock:
            data = _load_seen()
            for pu, (nm, tg) in names.items():
                if pu in data:
                    data[pu]["name"] = f"{nm}#{tg}"
                    found += 1
            _save_seen(data)
    if found:
        print(f"Journal : {found} pseudo(s) manquant(s) récupéré(s).")


def journal_list(query="", limit=300):
    """Le carnet de rencontres en entier, du plus récent au plus ancien ♡"""
    with _seen_lock:
        data = _load_seen()
    rows = []
    q = (query or "").lower()
    for pu, rec in data.items():
        seen = rec.get("seen") or []
        if not seen:
            continue
        name = rec.get("name") or ""
        if not name or name.startswith("?#"):   # vieilles entrées sans pseudo résolu
            known = _name_cache.get(pu)
            name = f"{known[0]}#{known[1]}" if known else anon_alias(pu)
        if q and q not in name.lower():
            continue
        last = seen[-1]
        allies = sum(1 for s in seen if s.get("team") == "ally")
        rows.append({
            "puuid": pu,
            "name": name,
            "rank": rec.get("rank"),
            "count": len(seen),
            "asAlly": allies,
            "asEnemy": len(seen) - allies,
            "last": last,
            "agents": sorted({s.get("agent") for s in seen if s.get("agent")}),
        })
    rows.sort(key=lambda r: r["last"].get("ts") or 0, reverse=True)
    return rows[:limit]

# ╭──────────────────────────────────────────────────────────────╮
# │  tes petits mots ♡
# │  « toxique », « bon duelist », « à éviter »~
# ╰──────────────────────────────────────────────────────────────╯

_notes_lock = threading.Lock()


def load_notes():
    """Tes petits mots sur les gens ♡"""
    return load_json(NOTES_FILE, {})


def set_note(puuid, text, tag=None):
    """Écrit (ou efface) ta note sur quelqu'un ♡"""
    with _notes_lock:
        notes = load_notes()
        text = (text or "").strip()[:500]
        if not text and not tag:
            notes.pop(puuid, None)
        else:
            notes[puuid] = {"text": text, "tag": tag, "ts": time.time()}
        atomic_write_json(NOTES_FILE, notes)
        return notes.get(puuid)

# ╭──────────────────────────────────────────────────────────────╮
# │  les petits drapeaux ♡
# │  devinés avec soin, jamais au hasard
# ╰──────────────────────────────────────────────────────────────╯
# aucune API ne donne la nationalité des joueurs — même chez tracker.gg le
# drapeau vient d'un réglage volontaire du profil. alors on devine, avec soin :
#   1. le drapeau que TU as posé (mémorisé pour toujours) ← gagne toujours ♡
#   2. le code pays dans le tag Riot (#FR, #BRA…)
#   3. l'alphabet du pseudo (하글, かな, ไทย, кириллица…)

COUNTRIES = {
    "fr": "France", "be": "Belgique", "ch": "Suisse", "ca": "Canada", "lu": "Luxembourg",
    "mc": "Monaco", "de": "Allemagne", "at": "Autriche", "nl": "Pays-Bas", "gb": "Royaume-Uni",
    "ie": "Irlande", "es": "Espagne", "pt": "Portugal", "it": "Italie", "gr": "Grèce",
    "pl": "Pologne", "cz": "Tchéquie", "sk": "Slovaquie", "hu": "Hongrie", "ro": "Roumanie",
    "bg": "Bulgarie", "hr": "Croatie", "si": "Slovénie", "rs": "Serbie", "ba": "Bosnie-Herzégovine",
    "mk": "Macédoine du Nord", "al": "Albanie", "me": "Monténégro", "xk": "Kosovo",
    "se": "Suède", "no": "Norvège", "dk": "Danemark", "fi": "Finlande", "is": "Islande",
    "ee": "Estonie", "lv": "Lettonie", "lt": "Lituanie", "ru": "Russie", "ua": "Ukraine",
    "by": "Biélorussie", "md": "Moldavie", "ge": "Géorgie", "am": "Arménie", "az": "Azerbaïdjan",
    "kz": "Kazakhstan", "uz": "Ouzbékistan", "tr": "Turquie", "cy": "Chypre", "mt": "Malte",
    "il": "Israël", "sa": "Arabie saoudite", "ae": "Émirats arabes unis", "qa": "Qatar",
    "kw": "Koweït", "bh": "Bahreïn", "om": "Oman", "jo": "Jordanie", "lb": "Liban",
    "iq": "Irak", "ir": "Iran", "eg": "Égypte", "ma": "Maroc", "dz": "Algérie",
    "tn": "Tunisie", "ly": "Libye", "sn": "Sénégal", "ci": "Côte d'Ivoire", "cm": "Cameroun",
    "ng": "Nigeria", "gh": "Ghana", "ke": "Kenya", "za": "Afrique du Sud",
    "us": "États-Unis", "mx": "Mexique", "br": "Brésil", "ar": "Argentine", "cl": "Chili",
    "co": "Colombie", "pe": "Pérou", "uy": "Uruguay", "py": "Paraguay", "bo": "Bolivie",
    "ec": "Équateur", "ve": "Venezuela", "cr": "Costa Rica", "pa": "Panama", "gt": "Guatemala",
    "hn": "Honduras", "sv": "Salvador", "ni": "Nicaragua", "do": "République dominicaine",
    "cu": "Cuba", "pr": "Porto Rico", "jm": "Jamaïque",
    "jp": "Japon", "kr": "Corée du Sud", "cn": "Chine", "tw": "Taïwan", "hk": "Hong Kong",
    "sg": "Singapour", "my": "Malaisie", "id": "Indonésie", "th": "Thaïlande", "vn": "Viêt Nam",
    "ph": "Philippines", "in": "Inde", "pk": "Pakistan", "bd": "Bangladesh", "lk": "Sri Lanka",
    "np": "Népal", "mm": "Birmanie", "kh": "Cambodge", "mn": "Mongolie",
    "au": "Australie", "nz": "Nouvelle-Zélande",
}

# les surnoms : codes à 3 lettres, variantes usuelles, nations du Royaume-Uni ♡
TAG_ALIASES = {
    "fra": "fr", "frr": "fr", "deu": "de", "ger": "de", "esp": "es", "spa": "es",
    "ita": "it", "prt": "pt", "por": "pt", "gbr": "gb", "eng": "gb", "sco": "gb",
    "wal": "gb", "uk": "gb", "irl": "ie", "bel": "be", "nld": "nl", "ned": "nl",
    "hol": "nl", "che": "ch", "sui": "ch", "aut": "at", "swe": "se", "nor": "no",
    "den": "dk", "dnk": "dk", "fin": "fi", "isl": "is", "pol": "pl", "cze": "cz",
    "svk": "sk", "hun": "hu", "rou": "ro", "rom": "ro", "bul": "bg", "bgr": "bg",
    "hrv": "hr", "cro": "hr", "srb": "rs", "ser": "rs", "svn": "si", "alb": "al",
    "grc": "gr", "gre": "gr", "tur": "tr", "trk": "tr", "rus": "ru", "ukr": "ua",
    "blr": "by", "kaz": "kz", "geo": "ge", "arm": "am", "aze": "az", "isr": "il",
    "ksa": "sa", "sau": "sa", "uae": "ae", "are": "ae", "qat": "qa", "kwt": "kw",
    "leb": "lb", "lbn": "lb", "jor": "jo", "irq": "iq", "irn": "ir", "egy": "eg",
    "mar": "ma", "mor": "ma", "dza": "dz", "alg": "dz", "tun": "tn", "lby": "ly",
    "sen": "sn", "civ": "ci", "cmr": "cm", "nga": "ng", "gha": "gh", "ken": "ke",
    "zaf": "za", "rsa": "za", "usa": "us", "mex": "mx", "mx1": "mx", "bra": "br",
    "bre": "br", "br1": "br", "arg": "ar", "chi": "cl", "chl": "cl", "col": "co",
    "per": "pe", "ury": "uy", "uru": "uy", "pry": "py", "bol": "bo", "ecu": "ec",
    "ven": "ve", "crc": "cr", "pan": "pa", "gua": "gt", "dom": "do", "pri": "pr",
    "jpn": "jp", "jp1": "jp", "jap": "jp", "kor": "kr", "kr1": "kr", "chn": "cn",
    "twn": "tw", "tw2": "tw", "hkg": "hk", "sgp": "sg", "sg2": "sg", "mys": "my",
    "idn": "id", "ina": "id", "tha": "th", "th2": "th", "vnm": "vn", "vie": "vn",
    "vn2": "vn", "phl": "ph", "ph2": "ph", "phi": "ph", "ind": "in", "pak": "pk",
    "ban": "bd", "bgd": "bd", "lka": "lk", "npl": "np", "aus": "au", "nzl": "nz",
    "tr1": "tr", "ru1": "ru", "eg1": "eg", "ma1": "ma",
}

# ceux-là désignent un serveur, pas un pays. on ne se fait pas avoir~
REGION_TAGS = {"euw", "eune", "eun", "eu", "eu1", "eu2", "na", "na1", "na2", "nae", "naw",
               "apac", "ap", "ap1", "oce", "oc", "sea", "latam", "lan", "las", "mena",
               "emea", "americas", "pacific", "china", "asia", "world", "global"}

# ceux-là sont aussi de vrais mots anglais : on n'y croit que si la région colle~
AMBIGUOUS = {"us", "it", "in", "me", "no", "so", "to", "on", "or", "if", "at", "be",
             "do", "my", "is", "as", "am", "by", "he", "we", "go", "la", "re", "sh",
             "st", "va", "ye", "ai", "id", "li", "um", "an", "ar", "co", "pe", "pa"}

# la région qu'on s'attend à voir pour ces codes ambigus ♡
AMB_SHARD = {
    "us": {"na"}, "ca": {"na"},
    "it": {"eu"}, "no": {"eu"}, "is": {"eu"}, "at": {"eu"}, "be": {"eu"}, "me": {"eu"},
    "by": {"eu"}, "li": {"eu"}, "va": {"eu"}, "al": {"eu"}, "am": {"eu"}, "ye": {"eu"},
    "my": {"ap"}, "in": {"ap"}, "id": {"ap"}, "la": {"ap"}, "sh": {"ap"},
    "ar": {"br", "na", "latam"}, "co": {"br", "na", "latam"}, "pe": {"br", "na", "latam"},
    "pa": {"br", "na", "latam"}, "do": {"br", "na", "latam"},
}

# les alphabets qui ne trompent pas ♡
SCRIPTS = [
    ("kr", ((0xAC00, 0xD7A3), (0x1100, 0x11FF))),          # hangul
    ("jp", ((0x3040, 0x309F), (0x30A0, 0x30FF))),          # hiragana / katakana
    ("th", ((0x0E00, 0x0E7F),)),                            # thaï
    ("il", ((0x0590, 0x05FF),)),                            # hébreu
    ("gr", ((0x0370, 0x03FF),)),                            # grec
    ("in", ((0x0900, 0x097F),)),                            # devanagari
    ("ru", ((0x0400, 0x04FF),)),                            # cyrillique (défaut Russie)
]
UA_LETTERS = set("їієґЇІЄҐ")

_flags_lock = threading.Lock()


def load_flags():
    """Les drapeaux que tu as posés à la main ♡"""
    return load_json(FLAGS_FILE, {})


def set_flag(puuid, code):
    """Un drapeau posé par toi : il gagne toujours, et on s'en souvient ♡"""
    code = (code or "").strip().lower()
    with _flags_lock:
        flags = load_flags()
        if not code or code not in COUNTRIES:
            flags.pop(puuid, None)
            code = None
        else:
            flags[puuid] = {"code": code, "ts": time.time()}
        atomic_write_json(FLAGS_FILE, flags)
    return code


def country_from_tag(tag, shard):
    """Le pays deviné depuis le tag Riot (#FR, #BRA…) ♡ prudemment"""
    t = (tag or "").strip().lower()
    if not t or t in REGION_TAGS:
        return None
    code = t if t in COUNTRIES else TAG_ALIASES.get(t)
    if not code:
        return None
    if t in AMBIGUOUS and code in AMB_SHARD and shard not in AMB_SHARD[code]:
        return None      # « us », « it », « my »… sans la bonne région : trop risqué
    return code


def country_from_name(name):
    """Le pays deviné depuis l'alphabet du pseudo (하글, かな, ไทย…) ♡"""
    txt = name or ""
    if any(c in UA_LETTERS for c in txt):
        return "ua"
    for code, ranges in SCRIPTS:
        for ch in txt:
            o = ord(ch)
            if any(lo <= o <= hi for lo, hi in ranges):
                return code
    return None


def country_for(pu, name, tag, shard, flags):
    """Le petit drapeau de quelqu'un ♡ trois sources, de la plus sûre à la plus large

      1. celui que TU as posé à la main   ← gagne toujours
      2. le code pays dans le tag Riot
      3. l'alphabet du pseudo

    Aucune API ne donne la nationalité des joueurs — même chez tracker.gg le
    drapeau vient d'un réglage volontaire du profil. Donc on devine, avec soin~
    """
    code = source = None
    manual = (flags or {}).get(pu)
    if manual and manual.get("code") in COUNTRIES:
        code, source = manual["code"], "manual"
    if not code:
        code = country_from_tag(tag, shard)
        source = "tag" if code else None
    if not code:
        code = country_from_name(name)
        source = "script" if code else None
    if not code:
        return None
    return {"code": code, "name": COUNTRIES.get(code, code.upper()), "source": source}


# ╭──────────────────────────────────────────────────────────────╮
# │  l'état de la partie ♡
# │  le cœur du truc, en vrai
# ╰──────────────────────────────────────────────────────────────╯

PARTY_COLORS = ["#d0d0d0", "#9a9a9a", "#c1a98c", "#8fae9c", "#b39aa4", "#a3a98f", "#8e9aa8", "#c0b6a2"]

QUEUE_NAMES = {
    "competitive": "Compétitif", "unrated": "Non classé", "swiftplay": "Swiftplay",
    "spikerush": "Spike Rush", "deathmatch": "Deathmatch", "hurm": "Deathmatch par équipe",
    "ggteam": "Escalade", "onefa": "Réplication", "snowball": "Combat de boules de neige",
    "premier": "Premier", "newmap": "Nouvelle carte", "": "Partie perso",
}


def stats_for(puuids, on_ranks=None, n_matches=None):
    """Les rangs d'abord, les stats ensuite, en parallèle ♡

    Les rangs coûtent 1 requête par joueur, les stats environ 6. Donc `on_ranks`
    permet d'afficher le tableau (pseudos, agents, rangs) DÈS qu'il est prêt, sans
    attendre l'analyse des matchs. En deathmatch à 14, ça change tout~
    """
    puuids = list(puuids)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        ranks = dict(zip(puuids, ex.map(get_ranks, puuids)))
        if on_ranks:
            try:
                on_ranks(ranks)
            except Exception:
                pass
        stats = dict(zip(puuids, ex.map(lambda p: get_recent_stats(p, n_matches), puuids)))
    return ranks, stats


def identity_extras(identity):
    """Carte de joueur, titre, bordure de niveau ♡ la déco, quoi"""
    card = STATIC["cards"].get((identity.get("PlayerCardID") or "").lower())
    title = STATIC["titles"].get((identity.get("PlayerTitleID") or "").lower())
    border = STATIC["borders"].get((identity.get("PreferredLevelBorderID") or "").lower())
    return {
        "cardWide": card.get("wideArt") if card else None,
        "cardSmall": card.get("smallArt") if card else None,
        "cardName": card.get("displayName") if card else None,
        "title": (title or {}).get("titleText") or None,
        "border": (border or {}).get("smallPlayerCardAppearance"),
    }


_flags_mem = {"data": None, "ts": 0}


def _flags_now():
    if _flags_mem["data"] is None or time.time() - _flags_mem["ts"] > 5:
        _flags_mem["data"] = load_flags()
        _flags_mem["ts"] = time.time()
    return _flags_mem["data"]


def _shard_now():
    try:
        return riot.get_region()[1]
    except Exception:
        return ""


def base_player(pu, my_puuid, name, tag, source, identity, ranks, stats, notes):
    """Le petit dossier complet d'un joueur, prêt à partir vers la page ♡"""
    st = stats.get(pu) or {}
    rk = ranks.get(pu) or {}
    level = identity.get("AccountLevel")
    if identity.get("HideAccountLevel"):
        level = None
    extras = identity_extras(identity)
    note = notes.get(pu) or {}
    return {
        "puuid": pu,
        "name": name,
        "tag": tag,
        "nameSource": source,
        "me": pu == my_puuid,
        "level": level,
        "levelHidden": bool(identity.get("HideAccountLevel")),
        "incognito": bool(identity.get("Incognito")),
        "rank": rk.get("rank") or tier_info(0),
        "peak": rk.get("peak") or tier_info(0),
        "peakSeason": rk.get("peakSeason"),
        "rr": rk.get("rr"),
        "rrChange": rk.get("rrChange"),
        "leaderboard": rk.get("leaderboard"),
        "actWins": rk.get("actWins"),
        "actGames": rk.get("actGames"),
        "actWinrate": rk.get("actWinrate"),
        "kd": st.get("kd"), "kda": st.get("kda"), "hs": st.get("hs"),
        "acs": st.get("acs"), "adr": st.get("adr"),
        "games": st.get("games"), "winrate": st.get("winrate"),
        "form": st.get("form") or [],
        "topAgents": st.get("topAgents") or [],
        "smurf": smurf_score(level, (rk.get("rank") or {}).get("tier"),
                             (rk.get("peak") or {}).get("tier"), st),
        "note": note.get("text") or None,
        "noteTag": note.get("tag"),
        "country": country_for(pu, name, tag, _shard_now(), _flags_now()),
        **extras,
    }


def build_lobby_state(my_puuid, glz):
    """Tout ton lobby dans les menus ♡ même si t'es tout seul~"""
    pdata = riot.get(f"{glz}/parties/v1/players/{my_puuid}", ok404=True)
    if not pdata or not pdata.get("CurrentPartyID"):
        return {"state": "MENUS", "players": []}
    party = riot.get(f"{glz}/parties/v1/parties/{pdata['CurrentPartyID']}", ok404=True)
    if not party:
        return {"state": "MENUS", "players": []}

    members = party.get("Members", [])
    puuids = [m["Subject"] for m in members]
    names = get_names(puuids)
    ranks, stats = stats_for(puuids)
    notes = load_notes()

    players = []
    for m in members:
        pu = m["Subject"]
        identity = m.get("PlayerIdentity") or {}
        name, tag, src = resolve_name(pu, names, identity.get("Incognito"))
        p = base_player(pu, my_puuid, name, tag, src, identity, ranks, stats, notes)
        p.update({
            "team": "lobby", "agent": None, "agentIcon": None, "agentRole": None,
            "vandal": None, "ghost": None, "partyColor": None, "lastSeen": None,
            "ready": bool(m.get("IsReady")), "owner": pu == party.get("Owner"),
            "lockState": None,
        })
        players.append(p)
    players.sort(key=lambda x: (not x["me"], -(x["rank"]["tier"] or 0)))

    mm = party.get("MatchmakingData") or {}
    queue = mm.get("QueueID", "")

    # les pings vers les serveurs — visibles seulement dans les menus~
    me_member = next((m for m in members if m["Subject"] == my_puuid), {})
    pings = []
    for p in (me_member.get("Pings") or []):
        pod = (p.get("GamePodID") or "").split(".")[-1].replace("eu-gp-", "").replace("-", " ")
        pings.append({"ping": p.get("Ping"), "pod": pod.title()})
    pings.sort(key=lambda x: x["ping"] if x["ping"] is not None else 999)

    return {
        "state": "LOBBY",
        "queue": QUEUE_NAMES.get(queue, queue or None),
        "partyState": party.get("State"),
        "queueEntryTime": party.get("QueueEntryTime"),
        "queueEta": party.get("EstimatedQueueTimeSeconds"),
        "penalty": party.get("RestrictedSeconds") or None,
        "inviteCode": party.get("InviteCode") or None,
        "pings": pings[:4],
        "players": players,
    }


def build_game_state(publish=None):
    """LE gros morceau : à quoi ressemble ta partie, là, maintenant ♡

    `publish` reçoit un état intermédiaire (les rangs, sans les stats de match)
    dès que possible, pour que la page affiche QUELQUE CHOSE tout de suite au lieu
    de faire tourner un joli spinner pendant dix secondes~
    """
    _, _, my_puuid, _ = riot.get_tokens()
    glz = riot.glz()

    state, match_id, pregame = None, None, False
    core = riot.get(f"{glz}/core-game/v1/players/{my_puuid}", ok404=True)
    if core and core.get("MatchID"):
        state, match_id = "INGAME", core["MatchID"]
    else:
        pre = riot.get(f"{glz}/pregame/v1/players/{my_puuid}", ok404=True)
        if pre and pre.get("MatchID"):
            state, match_id, pregame = "PREGAME", pre["MatchID"], True

    if not state:
        return build_lobby_state(my_puuid, glz)

    phase = None
    if pregame:
        match = riot.get(f"{glz}/pregame/v1/matches/{match_id}", ok404=True)
        if not match:
            return build_lobby_state(my_puuid, glz)
        players_raw = []
        for team in match.get("Teams") or [match.get("AllyTeam") or {}]:
            for p in team.get("Players", []):
                p["TeamID"] = team.get("TeamID", "Blue")
                players_raw.append(p)
        map_id = match.get("MapID", "")
        queue_id = match.get("QueueID", "")
        mode_id = match.get("Mode", "")
        phase = {"remaining": round((match.get("PhaseTimeRemainingNS") or 0) / 1e9)}
    else:
        match = riot.get(f"{glz}/core-game/v1/matches/{match_id}", ok404=True)
        if not match:
            return build_lobby_state(my_puuid, glz)
        players_raw = match.get("Players", [])
        map_id = match.get("MapID", "")
        queue_id = (match.get("MatchmakingData") or {}).get("QueueID", "")
        mode_id = match.get("ModeID", "")

    map_meta = STATIC["maps_by_id"].get(map_id.split("?")[0].lower())
    map_name = (map_meta or {}).get("displayName") or (map_id.rsplit("/", 1)[-1] if map_id else "?")
    queue_name = QUEUE_NAMES.get(queue_id, queue_id or None)

    # FFA (deathmatch) : pas d'équipes, ou plus de 2 TeamID qui traînent ♡
    team_ids = set()
    for p in players_raw:
        team_ids.add(p.get("TeamID", "Blue"))
    ffa = ("deathmatch" in (mode_id or "").lower() and "hurm" not in (queue_id or "").lower()) \
        or queue_id == "deathmatch" or len(team_ids) > 2

    loadout_path = "pregame" if pregame else "core-game"
    # en pregame, Riot renvoie des loadouts qui ne correspondent PAS à ce que les
    # joueurs auront vraiment en jeu. donc on préfère ne rien montrer du tout~
    if pregame:
        loadouts = []
    else:
        loadout_raw = riot.get(f"{glz}/{loadout_path}/v1/matches/{match_id}/loadouts", ok404=True)
        loadouts = extract_loadouts(loadout_raw, pregame)

    puuids = [p["Subject"] for p in players_raw]
    names = get_names(puuids)
    parties = get_parties()
    notes = load_notes()

    my_team_id = next((p.get("TeamID") for p in players_raw if p["Subject"] == my_puuid), "Blue")

    def team_of(p):
        """Alliés, ennemis, ou tout le monde ensemble (deathmatch) ♡"""
        if ffa:
            return "all"
        return "ally" if p.get("TeamID", "Blue") == my_team_id else "enemy"

    # on note tout le monde dans le carnet (avec l'agent joué) ♡
    agents_by_pu, team_by_pu = {}, {}
    for p in players_raw:
        ag = STATIC["agents"].get((p.get("CharacterID") or "").lower())
        agents_by_pu[p["Subject"]] = ag["displayName"] if ag else None
        team_by_pu[p["Subject"]] = team_of(p)
    my_agent = agents_by_pu.get(my_puuid)

    def assemble(ranks, stats, partial):
        """On assemble la réponse ♡ appelée deux fois exprès

        Une 1re fois sans les stats de match (affichage immédiat des rangs), puis une
        2e fois avec tout. C'est ce qui rend le tracker vif en deathmatch~
        """
        last_seen = log_and_check_seen(
            puuids, names, my_puuid, match_id, map_name, queue_name,
            agents_by_pu, my_agent, team_by_pu,
            {pu: ((ranks.get(pu) or {}).get("rank") or {}).get("name") for pu in puuids},
        )

        # les duos : ceux qu'on sait (présences) + ceux qu'on devine (historique) ♡
        counts = {}
        for pu in puuids:
            pid = parties.get(pu)
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
        guessed = {} if partial else guess_parties(
            [pu for pu in puuids if pu not in parties], stats)
        for pu, pid in guessed.items():
            counts[pid] = counts.get(pid, 0) + 1

        party_color, ci = {}, 0
        for pid, n in counts.items():
            if n >= 2:
                party_color[pid] = PARTY_COLORS[ci % len(PARTY_COLORS)]
                ci += 1

        players = []
        for i, p in enumerate(players_raw):
            pu = p["Subject"]
            agent = STATIC["agents"].get((p.get("CharacterID") or "").lower())
            identity = p.get("PlayerIdentity") or {}
            name, tag, src = resolve_name(pu, names, identity.get("Incognito"))
            items = loadouts[i] if i < len(loadouts) else {}
            if items:
                with _cache_lock:
                    _locker_cache[pu] = (time.time(), locker_from_items(items), f"{name}#{tag}")
                    trim_cache(_locker_cache, PLAYER_CACHE_MAX)
            pid = parties.get(pu) or guessed.get(pu)
            pl = base_player(pu, my_puuid, name, tag, src, identity, ranks, stats, notes)
            pl.update({
                "team": team_of(p),
                "agent": agent["displayName"] if agent else None,
                "agentIcon": agent["displayIcon"] if agent else None,
                "agentRole": ((agent or {}).get("role") or {}).get("displayName"),
                "agentColor": hexcol(((agent or {}).get("backgroundGradientColors") or [None])[0]),
                "vandal": weapon_skin(items, "vandal"),
                "ghost": weapon_skin(items, "ghost"),
                "skins": showcase_skins(items),
                "hasLocker": bool(items),
                "partyColor": party_color.get(pid),
                "partyGuessed": bool(pu in guessed and pu not in parties),
                "lockState": p.get("CharacterSelectionState") or None,
                "lastSeen": last_seen.get(pu),
            })
            players.append(pl)

        if ffa:
            players.sort(key=lambda x: (not x["me"], -(x["rank"]["tier"] or 0)))
        else:
            players.sort(key=lambda x: (x["team"] != "ally", -(x["rank"]["tier"] or 0)))

        def avg(group, key):
            vals = [p[key] for p in players if p["team"] == group and p.get(key)]
            return round(sum(vals) / len(vals), 2) if vals else None

        teams_summary = {}
        for grp in ("ally", "enemy", "all"):
            grp_members = [p for p in players if p["team"] == grp]
            if not grp_members:
                continue
            tiers = [p["rank"]["tier"] for p in grp_members if p["rank"]["tier"]]
            teams_summary[grp] = {
                "count": len(grp_members),
                "avgTier": round(sum(tiers) / len(tiers), 1) if tiers else None,
                "avgTierName": tier_info(round(sum(tiers) / len(tiers))) if tiers else None,
                "avgKd": avg(grp, "kd"),
                "avgAcs": avg(grp, "acs"),
                "avgLevel": avg(grp, "level"),
            }

        pres = my_presence(my_puuid)
        score = None
        if pres.get("partyOwnerMatchScoreAllyTeam") is not None and state == "INGAME":
            score = {
                "ally": pres.get("partyOwnerMatchScoreAllyTeam"),
                "enemy": pres.get("partyOwnerMatchScoreEnemyTeam"),
            }

        return {
            "state": state,
            "ffa": ffa,
            "queue": queue_name,
            "map": map_name,
            "mapIcon": (map_meta or {}).get("listViewIcon"),
            "mapSplash": (map_meta or {}).get("splash"),
            "matchId": match_id,
            "phase": phase,
            "score": score,
            "teams": teams_summary,
            "partial": partial,
            "players": players,
        }

    # gros lobby (deathmatch) : on analyse moins de matchs par joueur, sinon
    # 14 × 5 requêtes de détails, et Riot nous ferme la porte au nez~
    n_matches = BIG_LOBBY_MATCHES if len(puuids) > BIG_LOBBY else STATS_MATCHES
    empty = {pu: {} for pu in puuids}
    ranks, stats = stats_for(
        puuids,
        on_ranks=(lambda rk: publish(assemble(rk, empty, True))) if publish else None,
        n_matches=n_matches,
    )
    return assemble(ranks, stats, False)

# ╭──────────────────────────────────────────────────────────────╮
# │  la boutique ♡
# │  pour souffrir devant les prix ensemble T_T
# ╰──────────────────────────────────────────────────────────────╯

def build_store():
    """La boutique du jour, le marché nocturne et les bundles ♡ courage"""
    _, _, puuid, _ = riot.get_tokens()
    out = {"wallet": {}, "daily": [], "bundles": [], "night": [], "accessory": []}

    try:
        w = riot.get(f"{riot.pd()}/store/v1/wallet/{puuid}") or {}
        for cid, amount in (w.get("Balances") or {}).items():
            meta = CURRENCIES.get(cid.lower())
            if meta:
                out["wallet"][meta["code"]] = amount
    except Exception as e:
        out["walletError"] = str(e)

    def offer_item(level_id, cost=None, base=None, discount=None):
        """Un article de la boutique, joliment emballé ♡"""
        lid = (level_id or "").lower()
        sk = STATIC["level_to_skin"].get(lid) or {}
        lv = STATIC["skinlevels"].get(lid) or {}
        tier = STATIC["contenttiers"].get((sk.get("contentTierUuid") or "").lower())
        return {
            "name": sk.get("displayName") or lv.get("displayName") or "?",
            "icon": lv.get("displayIcon") or sk.get("displayIcon"),
            "cost": cost, "base": base, "discount": discount,
            "tier": (tier or {}).get("displayName"),
            "tierIcon": (tier or {}).get("displayIcon"),
            "tierColor": hexcol((tier or {}).get("highlightColor")),
        }

    try:
        # v3 (POST) depuis 2024, v2 (GET) en secours sur les vieux shards ♡
        sf = riot.post(f"{riot.pd()}/store/v3/storefront/{puuid}", {}, ok404=True)
        if sf is None:
            sf = riot.get(f"{riot.pd()}/store/v2/storefront/{puuid}") or {}
    except Exception as e:
        out["error"] = str(e)
        return out

    panel = sf.get("SkinsPanelLayout") or {}
    costs = {}
    for o in panel.get("SingleItemStoreOffers") or []:
        rid = ((o.get("Rewards") or [{}])[0]).get("ItemID", "")
        costs[rid.lower()] = list((o.get("Cost") or {}).values())[0] if o.get("Cost") else None
    for lid in panel.get("SingleItemOffers") or []:
        out["daily"].append(offer_item(lid, costs.get(lid.lower())))
    out["dailyRemaining"] = panel.get("SingleItemOffersRemainingDurationInSeconds")

    fb = sf.get("FeaturedBundle") or {}
    for b in (fb.get("Bundles") or ([fb["Bundle"]] if fb.get("Bundle") else [])):
        meta = STATIC["bundles"].get((b.get("DataAssetID") or "").lower()) or {}
        disc = b.get("TotalDiscountPercent")
        if disc is not None and disc <= 1:   # Riot renvoie 0.4 ici, 44 pour le night market
            disc = round(disc * 100)
        out["bundles"].append({
            "name": meta.get("displayName") or "Bundle",
            "icon": meta.get("displayIcon2") or meta.get("displayIcon"),
            "cost": b.get("TotalDiscountedCost", {}).get("85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741")
                    or list((b.get("TotalDiscountedCost") or {}).values() or [None])[0],
            "base": list((b.get("TotalBaseCost") or {}).values() or [None])[0],
            "discount": disc,
            "remaining": b.get("DurationRemainingInSeconds"),
            "items": len(b.get("Items") or []),
        })

    night = sf.get("BonusStore") or {}
    for o in night.get("BonusStoreOffers") or []:
        off = o.get("Offer") or {}
        rid = ((off.get("Rewards") or [{}])[0]).get("ItemID", "")
        out["night"].append(offer_item(
            rid,
            list((o.get("DiscountCosts") or {}).values() or [None])[0],
            list((off.get("Cost") or {}).values() or [None])[0],
            o.get("DiscountPercent"),
        ))
    out["nightRemaining"] = night.get("BonusStoreRemainingDurationInSeconds")

    acc = sf.get("AccessoryStore") or {}
    for o in acc.get("AccessoryStoreOffers") or []:
        off = o.get("Offer") or {}
        rid = ((off.get("Rewards") or [{}])[0]).get("ItemID", "").lower()
        cost = list((off.get("Cost") or {}).values() or [None])[0]
        meta = (STATIC["sprays"].get(rid) or STATIC["buddylevels"].get(rid)
                or STATIC["cards"].get(rid) or STATIC["titles"].get(rid) or {})
        out["accessory"].append({
            "name": meta.get("displayName") or meta.get("titleText") or "Accessoire",
            "icon": meta.get("fullTransparentIcon") or meta.get("displayIcon") or meta.get("smallArt"),
            "cost": cost,
        })
    out["accessoryRemaining"] = acc.get("AccessoryStoreRemainingDurationInSeconds")
    return out


def build_match_list(puuid, queue="competitive", n=15):
    """L'historique détaillé d'un joueur (le tien par défaut) ♡"""
    ids = get_history(puuid, queue or None, n)
    rr_by_match = {}
    try:
        cu = riot.get(f"{riot.pd()}/mmr/v1/players/{puuid}/competitiveupdates"
                      f"?startIndex=0&endIndex=20&queue=competitive") or {}
        for m in cu.get("Matches") or []:
            rr_by_match[m.get("MatchID")] = {
                "earned": m.get("RankedRatingEarned"),
                "after": m.get("RankedRatingAfterUpdate"),
                "tier": m.get("TierAfterUpdate"),
                "ts": m.get("MatchStartTime"),
            }
    except Exception:
        pass

    def one(mid):
        pl = get_match_players(mid)
        me = pl.get(puuid)
        if not me:
            return None
        agent = STATIC["agents"].get(me["agent"]) or {}
        mp = STATIC["maps_by_id"].get(me["mapId"].split("?")[0].lower()) or {}
        shots = me["head"] + me["body"] + me["leg"]
        rr = rr_by_match.get(mid) or {}
        return {
            "matchId": mid,
            "ts": me["start"],
            "map": mp.get("displayName") or "?",
            "mapIcon": mp.get("listViewIcon"),
            "queue": QUEUE_NAMES.get(me["queue"], me["queue"] or "Perso"),
            "agent": agent.get("displayName"),
            "agentIcon": agent.get("displayIcon"),
            "won": me["won"],
            "roundsWon": me["roundsWon"], "roundsLost": me["roundsLost"],
            "k": me["kills"], "d": me["deaths"], "a": me["assists"],
            "kd": round(me["kills"] / max(me["deaths"], 1), 2),
            "acs": round(me["score"] / me["rounds"]) if me["rounds"] else None,
            "adr": round(me["dmg"] / me["rounds"]) if me["rounds"] else None,
            "hs": round(100 * me["head"] / shots, 1) if shots else None,
            "rr": rr.get("earned"),
            "rrAfter": rr.get("after"),
            "tier": tier_info(rr.get("tier")) if rr.get("tier") else None,
        }

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        rows = [r for r in ex.map(one, ids) if r]
    rows.sort(key=lambda r: r["ts"] or 0, reverse=True)
    return rows


def build_rr_graph(puuid):
    """Les points de la jolie courbe de RR ♡"""
    try:
        cu = riot.get(f"{riot.pd()}/mmr/v1/players/{puuid}/competitiveupdates"
                      f"?startIndex=0&endIndex=20&queue=competitive") or {}
    except Exception:
        return []
    pts = []
    for m in reversed(cu.get("Matches") or []):
        if m.get("TierAfterUpdate") is None:
            continue
        pts.append({
            "ts": m.get("MatchStartTime"),
            "rr": m.get("RankedRatingAfterUpdate"),
            "earned": m.get("RankedRatingEarned"),
            "tier": m.get("TierAfterUpdate"),
            "tierName": tier_info(m.get("TierAfterUpdate"))["name"],
        })
    return pts


def build_player_detail(puuid):
    """La fiche complète d'un joueur, pour le panneau qui glisse ♡"""
    names = get_names([puuid])
    name, tag, src = resolve_name(puuid, names, False)
    ranks = get_ranks(puuid)
    stats = get_recent_stats(puuid)
    notes = load_notes().get(puuid) or {}
    with _seen_lock:
        rec = _load_seen().get(puuid) or {}
    seen = list(reversed(rec.get("seen") or []))
    return {
        "puuid": puuid,
        "name": name, "tag": tag, "nameSource": src,
        "rank": ranks.get("rank"), "peak": ranks.get("peak"),
        "peakSeason": ranks.get("peakSeason"),
        "rr": ranks.get("rr"), "rrChange": ranks.get("rrChange"),
        "leaderboard": ranks.get("leaderboard"),
        "actWins": ranks.get("actWins"), "actGames": ranks.get("actGames"),
        "actWinrate": ranks.get("actWinrate"), "acts": ranks.get("acts") or [],
        "stats": stats,
        "rrGraph": build_rr_graph(puuid),
        "matches": build_match_list(puuid, "competitive", 10),
        "encounters": seen,
        "note": notes.get("text"), "noteTag": notes.get("tag"),
        "country": country_for(puuid, name, tag, _shard_now(), _flags_now()),
        "tierNames": {str(t): tier_info(t)["name"] for t in STATIC["tiers"]},
    }

# ╭──────────────────────────────────────────────────────────────╮
# │  la petite boucle ♡
# │  elle tourne toute seule, sans faire de bruit
# ╰──────────────────────────────────────────────────────────────╯

_latest = {"data": {"state": "LOADING", "players": []}, "ts": 0, "version": 0, "building": False}
_latest_lock = threading.Lock()
_update_cv = threading.Condition(_latest_lock)   # réveille les flux SSE / long-poll
_wake = threading.Event()

GOOD_STATES = ("LOBBY", "MENUS", "PREGAME", "INGAME")
STALE_GRACE = 45          # secondes pendant lesquelles on garde le dernier état valide


def publish_partial(data):
    """On montre déjà les rangs pendant que les stats arrivent ♡"""
    with _update_cv:
        _latest["data"] = data
        _latest["ts"] = time.time()
        _latest["version"] += 1
        _update_cv.notify_all()


def snapshot():
    """Une photo de l'état actuel ♡"""
    with _latest_lock:
        return (_latest["data"], _latest["ts"], _latest["version"], _latest["building"])


def wait_for_change(since, timeout):
    """Attend sagement qu'il se passe quelque chose (ou abandonne) ♡"""
    deadline = time.monotonic() + timeout
    with _update_cv:
        while _latest["version"] <= since:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            _update_cv.wait(left)
        return (_latest["data"], _latest["ts"], _latest["version"], _latest["building"])


def envelope(data, ts, ver, building):
    """On emballe l'état avec quelques métadonnées avant l'envoi ♡"""
    return {**data, "_ts": ts, "_version": ver, "_building": building,
            "_cooldown": round(RL.cooling()) or None,
            "_age": round(time.time() - ts) if ts else None}


def refresh_loop():
    """La petite boucle qui tourne en fond, sans jamais se plaindre ♡"""
    last_ok = 0
    while True:
        with _latest_lock:
            _latest["building"] = True
        try:
            data = build_game_state(publish=publish_partial)
        except FileNotFoundError:
            data = {"state": "OFFLINE", "players": [],
                    "error": "Client Riot fermé (lockfile introuvable)."}
        except Exception as e:
            data = {"state": "ERROR", "players": [], "error": str(e)}

        with _update_cv:
            ok = data.get("state") in GOOD_STATES
            if ok:
                last_ok = time.time()
                _latest["data"] = data
            elif (data.get("state") == "ERROR"
                  and _latest["data"].get("state") in GOOD_STATES
                  and time.time() - last_ok < STALE_GRACE):
                # hoquet réseau ou jeton en pleine rotation : on garde l'affichage
                # au lieu de tout effacer. clignoter pour rien, c'est pénible~
                _latest["data"] = {**_latest["data"], "warning": data.get("error"), "stale": True}
            else:
                _latest["data"] = data
            _latest["ts"] = time.time()
            _latest["version"] += 1
            _latest["building"] = False
            _update_cv.notify_all()
        # on regarde plus souvent quand il se passe des choses ♡
        st = data.get("state")
        delay = POLL_PREGAME if st == "PREGAME" else POLL_INGAME if st == "INGAME" else POLL_INTERVAL
        _wake.wait(delay)
        _wake.clear()

# ╭──────────────────────────────────────────────────────────────╮
# │  le serveur web ♡
# │  il sert la page et répond gentiment
# ╰──────────────────────────────────────────────────────────────╯

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"   # keep-alive : indispensable au flux temps réel

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode())

    def _read_body(self):
        """Lit le corps de la requête, y compris en Transfer-Encoding: chunked.

        Sans ça, un client qui n'envoie pas de Content-Length laisse ses octets
        dans le tampon : la requête suivante part sur des données décalées et la
        connexion keep-alive se désynchronise.
        """
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            chunks = []
            while True:
                line = self.rfile.readline(65536).strip().split(b";")[0]
                try:
                    size = int(line, 16)
                except ValueError:
                    break
                if size == 0:
                    self.rfile.readline(65536)      # ligne vide de fin
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.readline(65536)          # CRLF de séparation
            return b"".join(chunks)
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_POST(self):
        try:
            body = json.loads(self._read_body() or b"{}")
            if self.path.startswith("/api/flag"):
                pu = body.get("puuid")
                if not pu:
                    return self._json({"error": "puuid manquant"}, 400)
                code = set_flag(pu, body.get("code"))
                _flags_mem["ts"] = 0          # invalide le cache
                _wake.set()                   # et on repousse un état à jour
                return self._json({"ok": True, "code": code})
            if self.path.startswith("/api/note"):
                pu = body.get("puuid")
                if not pu:
                    return self._json({"error": "puuid manquant"}, 400)
                return self._json({"ok": True, "note": set_note(pu, body.get("text"), body.get("tag"))})
            self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            self.close_connection = True
            try:
                self._json({"error": str(e)}, 500)
            except Exception:
                pass

    def do_GET(self):
        try:
            u = urlparse(self.path)
            path, q = u.path, parse_qs(u.query)

            if path == "/api/game":
                if q.get("hard"):
                    hard_reset()
                if q.get("refresh") or q.get("hard"):
                    _wake.set()
                try:
                    since = int((q.get("since") or [-1])[0])
                except (TypeError, ValueError):
                    since = -1
                if since >= 0:      # long-poll : la réponse n'arrive qu'au changement
                    data, ts, ver, building = wait_for_change(since, 25)
                else:
                    data, ts, ver, building = snapshot()
                self._json(envelope(data, ts, ver, building))

            elif path == "/api/stream":
                # Server-Sent Events : le serveur pousse chaque nouvel état, sans délai
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-transform")
                self.send_header("X-Accel-Buffering", "no")
                self.send_header("Connection", "close")
                self.end_headers()
                last = -1
                self.wfile.write(b"retry: 2000\n\n")
                self.wfile.flush()
                while True:
                    data, ts, ver, building = wait_for_change(last, SSE_PING)
                    if ver != last:
                        last = ver
                        payload = json.dumps(envelope(data, ts, ver, building))
                        self.wfile.write(b"data: " + payload.encode() + b"\n\n")
                    else:
                        self.wfile.write(b": ping\n\n")   # garde la connexion vivante
                    self.wfile.flush()

            elif path.startswith("/api/locker/"):
                pu = unquote(path.rsplit("/", 1)[-1])
                with _cache_lock:
                    hit = _locker_cache.get(pu)
                self._json({"name": hit[2], "locker": hit[1], "age": int(time.time() - hit[0])}
                           if hit else {"name": None, "locker": None})

            elif path.startswith("/api/player/"):
                pu = unquote(path.rsplit("/", 1)[-1])
                self._json(build_player_detail(pu))

            elif path == "/api/history":
                pu = (q.get("puuid") or [None])[0]
                if not pu:
                    _, _, pu, _ = riot.get_tokens()
                queue = (q.get("queue") or ["competitive"])[0]
                n = min(int((q.get("n") or [15])[0]), 25)
                self._json({"puuid": pu, "matches": build_match_list(pu, queue, n),
                            "rrGraph": build_rr_graph(pu),
                            # noms des paliers : la courbe RR les affiche en fond
                            "tierNames": {str(t): tier_info(t)["name"] for t in STATIC["tiers"]}})

            elif path == "/api/countries":
                self._json({"countries": [{"code": c, "name": n}
                                          for c, n in sorted(COUNTRIES.items(), key=lambda x: x[1])]})

            elif path == "/api/store":
                self._json(build_store())

            elif path == "/api/journal":
                self._json({"rows": journal_list((q.get("q") or [""])[0])})

            elif path == "/api/me":
                _, _, pu, _ = riot.get_tokens()
                names = get_names([pu])
                name, tag, _src = resolve_name(pu, names, False)
                region, shard = riot.get_region()
                self._json({"puuid": pu, "name": name, "tag": tag,
                            "region": region, "shard": shard,
                            "version": riot.get_version(),
                            "season": season_label(current_season_id())})

            elif path in ("/", "/index.html"):
                with open(os.path.join(RES_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            else:
                self._send(404, b'{"error":"not found"}')
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            try:
                self._json({"error": str(e)}, 500)
            except Exception:
                pass


def lan_ip():
    """Notre adresse sur le réseau local, pour le lien du téléphone ♡"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "IP_DU_PC"


BANNER = r"""
   _____          ______
  / ____|        |  ____|
 | |  __         | |__
 | | |_ |        |  __|
 | |__| |        | |
  \_____| ____   |_|  ____
          |____|      |____|
"""


def hard_reset():
    """On repart de zéro sans redémarrer le processus ♡

    Nouveau lockfile, nouveau jeton, nouvelle région, et rechargement des données
    statiques si elles manquent (démarrage de Windows sans réseau, ça arrive~)
    """
    try:
        riot.invalidate(deep=True)
    except Exception:
        pass
    try:
        if not STATIC.get("maps_by_id"):
            load_static()
    except Exception:
        pass
    try:
        _wake.set()
    except Exception:
        pass


# ╭──────────────────────────────────────────────────────────────╮
# │  le mode discret ♡
# │  plus de vilaine fenêtre noire (๑˃ᴗ˂)ﻭ
# ╰──────────────────────────────────────────────────────────────╯
# Raccourcis globaux (Windows) :
#   F6  active le mode fond (+ démarrage auto avec Windows)
#   F7  ouvre la fenêtre du tracker + refresh complet de la session Riot
#   F8  quitte le tracker
#   F9  redémarre complètement le tracker
# En mode fond le tracker est relancé sans console : rien à l'écran, rien
# dans la barre des tâches, il tourne juste en tâche de fond.

CONFIG_FILE = os.path.join(APP_DIR, "tracker_config.json")
STARTUP_NAME = "TrackerByEaurah"
HIDDEN_ARG = "--hidden"
CREATE_NO_WINDOW = 0x08000000


def cfg_load():
    """Tes réglages, relus depuis le petit fichier de config ♡"""
    return load_json(CONFIG_FILE, {})


def cfg_save(cfg):
    """On range tes réglages, tout doucement ♡"""
    atomic_write_json(CONFIG_FILE, cfg, indent=2)


def _pythonw():
    """pythonw.exe, celui qui n'ouvre pas de console ♡"""
    exe = sys.executable or ""
    for a in ("python.exe", "python3.exe"):
        cand = exe.replace(a, "pythonw.exe")
        if cand != exe and os.path.isfile(cand):
            return cand
    return None


def _launch_cmd():
    """La commande pour se relancer soi-même (script ou .exe) ♡"""
    if getattr(sys, "frozen", False):
        return [sys.executable, HIDDEN_ARG]
    return [_pythonw() or sys.executable, os.path.abspath(__file__), HIDDEN_ARG]


def startup_set(on):
    """On se met (ou on s'enlève) du démarrage de Windows ♡"""
    if os.name != "nt":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as key:
            if on:
                cmd = " ".join('"%s"' % c if " " in c else c for c in _launch_cmd())
                winreg.SetValueEx(key, STARTUP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, STARTUP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


def notify(title, msg):
    """Un petit toast Windows pour dire ce qu'on vient de faire ♡"""
    def _go():
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, title, 0x40 | 0x1000)
        except Exception:
            print("\n%s : %s\n" % (title, msg))
    threading.Thread(target=_go, daemon=True).start()


def hide_console():
    """Hop, la vilaine fenêtre noire disparaît ♡"""
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE
            return True
    except Exception:
        pass
    return False


def port_in_use():
    """Un tracker tourne-t-il déjà ? ♡ (évite deux instances sur le même port)"""
    import socket
    s = socket.socket()
    s.settimeout(0.4)
    try:
        s.connect(("127.0.0.1", WEB_PORT))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def relaunch_hidden():
    """On se relance en douce, sans console ♡"""
    import subprocess
    try:
        kw = {"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}
        subprocess.Popen(_launch_cmd(), stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, **kw)
        return True
    except Exception:
        return False


def restart_tracker():
    """F9 — on relance tout, dans le même mode qu'actuellement ♡"""
    import subprocess
    hidden = HIDDEN_ARG in sys.argv or bool(cfg_load().get("background"))
    if hidden:
        cmd = _launch_cmd() + ["--restart"]
        kw = {"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}
    else:
        cmd = [sys.executable, os.path.abspath(__file__), "--restart"]
        kw = {"creationflags": 0x00000010} if os.name == "nt" else {}   # CREATE_NEW_CONSOLE
    try:
        subprocess.Popen(cmd, close_fds=True, **kw)
    except Exception:
        return
    time.sleep(0.3)
    os._exit(0)


def enable_background():
    """F6 — mode fond + démarrage avec Windows ♡"""
    cfg = cfg_load()
    cfg["background"] = True
    cfg_save(cfg)
    ok = startup_set(True)
    notify("Tracker By Eaurah",
           "MODE FOND ACTIVÉ.\n\n"
           "Au prochain lancement — et à chaque démarrage de Windows — le tracker\n"
           "tourne en tâche de fond : pas de fenêtre cmd, rien dans la barre des tâches.\n\n"
           "Démarrage automatique avec Windows : %s\n\n"
           "F7  ouvrir le tracker\n"
           "F8  quitter le tracker\n\n"
           "Pour revenir en mode normal : passer \"background\" à false dans\n"
           "tracker_config.json (à côté de server.py)."
           % ("oui" if ok else "impossible à écrire"))


def hotkey_loop():
    """La petite oreille qui écoute F6, F7, F8 et F9 ♡"""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        MODS = 0x4000                          # MOD_NOREPEAT : touche seule
        def _open():
            hard_reset()
            open_app_window("http://localhost:%d" % WEB_PORT)

        binds = [
            (1, 0x75, enable_background),   # F6 : mode fond + démarrage auto
            (2, 0x76, _open),               # F7 : ouvrir + rafraîchir à fond
            (3, 0x77, lambda: os._exit(0)), # F8 : quitter
            (4, 0x78, restart_tracker),     # F9 : redémarrage complet
        ]
        actions = {}
        for hid, vk, fn in binds:
            if u32.RegisterHotKey(None, hid, MODS, vk):
                actions[hid] = fn
        if not actions:
            return
        msg = wintypes.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312 and msg.wParam in actions:   # WM_HOTKEY
                try:
                    actions[msg.wParam]()
                except Exception:
                    pass
    except Exception:
        pass


# ╭──────────────────────────────────────────────────────────────╮
# │  la vraie fenêtre ♡
# │  comme une vraie appli, sans barre d'adresse~
# ╰──────────────────────────────────────────────────────────────╯

APP_WINDOW = True        # False -> ne rien ouvrir au demarrage (mode serveur seul)
APP_WIN_SIZE = (1500, 950)


def _browser_candidates():
    """Où se cachent Chrome et Edge sur cette machine ♡"""
    import shutil
    cands = []
    if os.name == "nt":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        rel = [
            r"Microsoft\Edge\Application\msedge.exe",
            r"Google\Chrome\Application\chrome.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        for base in (pf, pf86, local):
            if not base:
                continue
            for r in rel:
                cands.append(os.path.join(base, r))
    else:
        for n in ("microsoft-edge", "google-chrome", "chromium", "brave-browser"):
            w = shutil.which(n)
            if w:
                cands.append(w)
    return [c for c in cands if os.path.isfile(c) or os.path.sep not in c]


def open_app_window(url):
    """On ouvre une vraie fenêtre d'appli ♡

    Chrome/Edge en mode --app : pas de barre d'adresse, pas d'onglets, ça a l'air
    d'un vrai logiciel. Si aucun navigateur ne se laisse faire, on retombe
    gentiment sur le navigateur par défaut~
    """
    import subprocess
    w, h = APP_WIN_SIZE
    profile = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
        "TrackerByEaurah", "window",
    )
    try:
        os.makedirs(profile, exist_ok=True)
    except Exception:
        profile = None
    args_common = [
        f"--app={url}",
        f"--window-size={w},{h}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=Translate,ChromeWhatsNewUI",
    ]
    if profile:
        args_common.insert(1, f"--user-data-dir={profile}")
    for exe in _browser_candidates():
        try:
            kw = {}
            if os.name == "nt":
                kw["creationflags"] = 0x00000008  # DETACHED_PROCESS
            subprocess.Popen([exe] + args_common,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
            return True
        except Exception:
            continue
    try:
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception:
        return False


def _launch_window_when_ready(url, timeout=12.0):
    """On attend que le serveur réponde avant d'ouvrir la fenêtre ♡

    Sinon on tombe sur une page blanche pendant deux secondes, et ça fait
    tout de suite moins sérieux~
    """
    import socket as _s
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            c = _s.create_connection(("127.0.0.1", WEB_PORT), 0.4)
            c.close()
            break
        except Exception:
            time.sleep(0.2)
    open_app_window(url)


if __name__ == "__main__":
    try:   # évite les crashs d'encodage console (cp1252) sur les accents / traits
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    HIDDEN = HIDDEN_ARG in sys.argv
    RESTART = "--restart" in sys.argv
    CFG = cfg_load()

    if RESTART:
        # relancé par F9 : on laisse gentiment l'ancien rendre le port~
        for _ in range(40):
            if not port_in_use():
                break
            time.sleep(0.25)
    elif port_in_use():
        # un tracker est déjà là : on ouvre juste sa fenêtre et on file ♡
        open_app_window("http://localhost:%d" % WEB_PORT)
        sys.exit(0)

    # Filet de securite : deux lancements rapproches passent tous les deux le
    # test port_in_use() avant que le premier n'ait pris le port, puis ecrivent
    # journal, notes et caches en meme temps. Le verrou porte sur le DOSSIER.
    # Sur --restart on patiente : l'ancien processus est en train de mourir.
    _seul, _detenteur = claim_single_instance()
    if not _seul and RESTART:
        for _ in range(40):
            time.sleep(0.25)
            _seul, _detenteur = claim_single_instance()
            if _seul:
                break
    if not _seul:
        journal("demarrage annule : un tracker tient deja le dossier (%s)" % _detenteur,
                echo=False)
        open_app_window("http://localhost:%d" % WEB_PORT)
        sys.exit(0)

    # mode fond demandé : on repart sans console et on ferme celle-ci ♡
    if CFG.get("background") and not HIDDEN and os.name == "nt":
        if relaunch_hidden():
            sys.exit(0)
        hide_console()          # au pire on masque celle qu'on a sous la main~
        HIDDEN = True
    if HIDDEN:
        hide_console()

    threading.Thread(target=hotkey_loop, daemon=True).start()
    print(BANNER)
    print("  Tracker By Eaurah  (G_F_)")
    print("  Discord : eaurah\n")
    try:
        load_static()
    except Exception as e:
        print(f"\n⚠ Chargement des données statiques impossible : {e}")
        print("  (démarrage de Windows : le réseau n'est peut-être pas encore prêt)")
        print("  Nouvelle tentative en arrière-plan toutes les 20 s.")

        def _retry_static():
            """On retente le chargement des images toutes les 20 s ♡"""
            while True:
                time.sleep(20)
                try:
                    load_static()
                    print("✔ Données statiques chargées.")
                    _wake.set()
                    return
                except Exception:
                    pass
        threading.Thread(target=_retry_static, daemon=True).start()
    _load_known_names()
    try:
        riot.get_tokens()
        print(f"Connecté neuille que tu es. Région : {riot.get_region()}")
    except FileNotFoundError:
        print("⚠ Pas de client Riot — lance Valorant puis refresh la page.")
    except Exception as e:
        print(f"⚠ Client Riot injoiniable : {e}")

    threading.Thread(target=refresh_loop, daemon=True).start()
    def _backfill():
        time.sleep(2)
        try:
            backfill_names()
        except Exception:
            pass
    threading.Thread(target=_backfill, daemon=True).start()

    ip = lan_ip()
    print("\n──────────────────────────────────────────────")
    print(f"  Tracker ")
    print(f"  La fenetre du tracker s'ouvre toute seule (sinon : http://localhost:{WEB_PORT})")
    print(f"  Sur un tel (doit être sur le réseau local) : http://{ip}:{WEB_PORT}")
    print("  F6 : mode fond (plus de cmd) + démarrage avec Windows")
    print("  F7 : ouvrir le tracker + refresh complet")
    print("  F8 : quitter   ·   F9 : redémarrage complet du tracker")
    print("──────────────────────────────────────────────\n")
    if APP_WINDOW and not HIDDEN and "--no-window" not in sys.argv:
        threading.Thread(target=_launch_window_when_ready,
                         args=(f"http://localhost:{WEB_PORT}",), daemon=True).start()

    srv = None
    for essai in range(12):
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Handler)
            break
        except OSError as e:
            print(f"Port {WEB_PORT} pas encore libre ({e}) — nouvelle tentative…")
            time.sleep(1)
    try:
        if srv is None:
            raise RuntimeError(f"impossible d'ouvrir le port {WEB_PORT}")
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nErreur fatale rip : {e}")
        journal("arret sur erreur : %s" % e, echo=False)
        if not HIDDEN:
            try:
                input("Appuie sur Entrée pour fermer...")
            except Exception:
                pass
    finally:
        # F9 passe par os._exit() et saute ce bloc : ce n'est pas grave, l'OS
        # rend le verrou a la fermeture du processus de toute facon.
        try:
            _save_known_names()
        except Exception:
            pass
        release_single_instance()
