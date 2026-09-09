# Tracker By Eaurah

Un tracker VALORANT qui tourne sur ton PC et que tu ouvres où tu veux : sur l'écran, ou sur ton
téléphone posé à côté du clavier. Tu le lances, la fenêtre s'ouvre toute seule, et tu vois les
rangs et les stats de tout le monde dès la sélection d'agents.

## Ce que ça fait

**Partie** — les 10 joueurs, les deux équipes côte à côte. Rang et RR, peak, niveau de compte,
KD / ACS / HS% / winrate, forme récente, skins équipés. Les duos sont repérés par une bande de
couleur, y compris chez l'adversaire (déduits de leur historique commun). Plus un détecteur de
smurf et un rappel quand tu recroises quelqu'un.

**Moi** — ta courbe de RR, tes derniers matchs, ta boutique du jour, les réglages.

**Journal** — tous les joueurs croisés, avec recherche, notes privées et drapeaux.

Clique sur n'importe qui pour ouvrir sa fiche complète.

## Installation

Python avec **"Add Python to PATH"** coché, puis :

```
pip install requests
```

## Lancement

Lance Valorant, double-clique sur `server.py`. La fenêtre s'ouvre seule.

**F6** mode fond (plus de cmd, démarre avec Windows) · **F7** ouvrir + rafraîchir ·
**F8** quitter · **F9** redémarrer

## Sur ton téléphone

Récupère l'IP locale de ton PC et ajoute `:8080`, ça donne un truc du genre
`http://192.168.1.42:8080`. Le port reste 8080 tant que tu n'as pas touché au code.

## Réglages

En haut de `server.py`, dans le bloc `Config`. `STATS_MATCHES` pour le nombre de matchs analysés
par joueur (plus c'est haut, plus tu risques de te faire brider par Riot), `WEB_PORT` pour le
port, `FORCE_REGION` si ta région n'est pas détectée, et `RESPECT_STREAMER_MODE` à `True` pour
afficher un alias aux joueurs qui ont masqué leur pseudo au lieu de le révéler.

## Les fichiers à côté

`seen_players.json` (journal), `known_names.json` (cache des pseudos), `notes.json`, `flags.json`,
`tracker_config.json` et `tracker.log`. Tout se crée tout seul, rien ne part sur GitHub.

Si ça déconne, regarde `tracker.log`.

## En faire un .exe

`build_exe.bat`. Le résultat est dans `dist\TrackerByEaurah\` — pour le partager, zippe **tout le
dossier**, l'exe a besoin du `_internal` à côté.

## À savoir

Rien à voir avec Riot Games, approuvé par personne. Ça lit des données via l'API interne du
client, ce que la politique développeur de Riot n'autorise pas vraiment — un ban reste possible.

C'est en **lecture seule** : ça ne touche jamais au client, ne modifie rien dans le jeu et ne lit
pas sa mémoire. Pas de lock d'agent automatique ni rien de ce genre, c'est exactement ce qui a
fait fermer d'autres projets.

## Licence

MIT, fais-en ce que tu veux.

---

Vibe codé avec Claude. Je sais, et je m'en tape.

Dev by **eaurah** (G_F_)
