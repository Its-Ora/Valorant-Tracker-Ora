# Tracker By Eaurah

Un tracker VALORANT qui tourne sur ton PC et que tu ouvres où tu veux : sur l'écran, sur ton
téléphone posé à côté du clavier. Tu lances le truc, la fenêtre s'ouvre toute seule, et tu vois
les rangs et les stats de tout le monde pendant la sélection d'agents.

## Ce que ça fait

Trois onglets, c'est tout.

**Partie** — les 10 joueurs, les deux équipes côte à côte sur grand écran. Pour chacun : rang
actuel et RR, peak avec l'acte, niveau de compte, KD / ACS / HS% / winrate sur ses dernières
ranked, sa forme récente, et ses skins équipés. Les duos sont repérés par une bande de couleur —
ceux de ton côté viennent du chat Riot, ceux d'en face sont déduits de leur historique commun.
Il y a aussi un détecteur de smurf, et un rappel si tu as déjà croisé quelqu'un.

**Moi** — ta courbe de RR, tes derniers matchs, ta boutique du jour et les réglages.

**Journal** — tous les joueurs que tu as croisés, avec une recherche. Tu peux leur mettre une
note privée et un drapeau.

Clique sur n'importe qui pour ouvrir sa fiche complète.

## Installation

Il te faut Python (coche **"Add Python to PATH"** pendant l'installation), puis :

```
pip install requests
```

## Lancement

Lance Valorant, puis double-clique sur `server.py`. La fenêtre du tracker s'ouvre seule.

Une fois lancé :

- **F6** — mode fond : plus de fenêtre noire, et ça démarre avec Windows
- **F7** — ouvrir le tracker et tout rafraîchir
- **F8** — quitter
- **F9** — redémarrage complet

## Sur ton téléphone

Le terminal affiche une adresse du genre `http://192.168.1.42:8080`. Tape-la dans ton navigateur,
téléphone sur le même Wi-Fi.

Si ça ne passe pas, c'est le pare-feu Windows neuf fois sur dix. Ouvre un cmd **en administrateur** :

```
netsh advfirewall firewall add rule name="Tracker Eaurah" dir=in action=allow protocol=TCP localport=8080
```

## Réglages

Ils sont en haut de `server.py`, dans le bloc `Config`. Les plus utiles :

- `WEB_PORT` — le port de la page (8080 par défaut)
- `STATS_MATCHES` — combien de matchs sont analysés par joueur. Plus tu montes, plus les stats
  sont fiables, mais plus tu risques de te faire brider par Riot.
- `RESPECT_STREAMER_MODE` — mets-le à `True` pour afficher un alias aux joueurs qui ont masqué
  leur pseudo, au lieu de le révéler. C'est plus correct.
- `FORCE_REGION` — si ta région n'est pas détectée, mets `("eu", "eu")` par exemple

## Les fichiers qui apparaissent à côté

Tout se crée tout seul, tu n'as rien à faire.

`seen_players.json` c'est ton journal des rencontres, `known_names.json` le cache des pseudos,
`notes.json` et `flags.json` tes notes et tes drapeaux, `tracker.log` ce qui a planté, et
`tracker_config.json` tes réglages. Si un de ces fichiers devient illisible, il est mis de côté
en `.corrompu-<date>` au lieu d'être écrasé.

Aucun ne part sur GitHub, ils sont dans le `.gitignore`.

## En faire un .exe

Double-clique sur `build_exe.bat`. Le résultat est dans `dist\TrackerByEaurah\`.

Pour le partager, zippe **tout le dossier**, pas juste l'exe — il a besoin du `_internal` à côté.
Et prépare-toi à ce que SmartScreen râle : c'est basé sur le nombre de téléchargements, pas sur
le contenu, ça se calme tout seul.

## Sous le capot, deux ou trois trucs

Tout passe par l'API locale du client Riot, avec tes propres identifiants. Pas de clé à demander.

Riot bride sévèrement, sans jamais dire à partir de quand. Un deathmatch, c'est 14 joueurs à
analyser d'un coup, donc le débit se règle tout seul : il se divise par deux quand Riot râle, et
remonte doucement quand ça repasse. Et comme les rangs coûtent bien moins cher que les stats de
match, le tableau s'affiche dès que les rangs sont là et se complète après.

Si ça ne marche plus, regarde `tracker.log`.

## À savoir

Ce projet n'a rien à voir avec Riot Games et n'est approuvé par personne.

Il lit des données via l'API interne du client, ce que la politique développeur de Riot
n'autorise pas vraiment. Un ban de compte reste possible. Le tracker est en **lecture seule** :
il ne touche jamais au client, ne modifie rien dans le jeu et ne lit pas sa mémoire. Il n'y aura
jamais de verrouillage d'agent automatique ni rien de ce genre — c'est exactement ce qui a fait
fermer d'autres projets.

## Licence

MIT, fais-en ce que tu veux.

---

Dev by **eaurah** (G_F_)
