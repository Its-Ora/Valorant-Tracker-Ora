# Tracker By Eaurah

Tracker VALORANT temps réel sur page web locale, accessible depuis ton téléphone.

## Ce que ça affiche

L'interface tient en **3 onglets** : **Partie**, **Moi**, **Journal** — pensée pour rester ouverte sur un deuxième écran ou un téléphone, sans avoir à cliquer pendant une game.

- **Partie** : les 10 joueurs. Sur écran large, les deux équipes s'affichent **côte à côte** : tout est lisible d'un coup, sans défilement.
- **Moi** : courbe RR, tes derniers matchs, ta boutique du jour et les réglages, sur une seule page.
- **Journal** : tous les joueurs déjà croisés, avec recherche.

Cliquer une carte ouvre la fiche du joueur : **un seul défilement** (rang, stats, courbe RR, skins équipés, agents, rencontres, matchs, note privée, drapeau, lien tracker.gg) — plus aucun sous-onglet.

### Onglet Partie

Pour chaque joueur de la game (les 10) :

- **Pseudo + tag**, carte joueur en fond de carte, titre équipé, niveau de compte (`niv. ?` si le joueur le masque)
- **Rang actuel + RR** (`Diamant 1 · 35 RR +19`), **peak rank avec l'acte** où il a été atteint, et le **rang leaderboard** (`#123`) pour les Immortels/Radiants
- **KD, ACS, ADR, HS%, winrate** sur les X dernières ranked (voir `STATS_MATCHES`)
- **Forme récente** : barres vertes/rouges (V/D des dernières games)
- **Skin de Vandal** équipé (avec image, niveau et variante)
- **Bande de couleur** sur le bord de la carte pour les duos/groupes — plus les **duos probables déduits de l'historique** (deux joueurs qui reviennent ensemble dans les mêmes games récentes, même côté ennemi où la présence Riot ne dit rien)
- **🕵️** quand le joueur a activé "masquer mon nom"
- **Bandeau smurf** quand les indices s'accumulent (niveau bas + KD/ACS élevés + écart avec le peak)
- **Bandeau "déjà croisé"** avec le détail (map, mode, agents joués, combien de fois avec toi / contre toi)
- **Ta note privée** si tu en as écrit une
- En sélection d'agents : pastille verte (verrouillé) / jaune (en train de choisir)

Au-dessus des équipes, une **barre de comparaison** : rang moyen, KD moyen, ACS moyen, niveau moyen de chaque camp et une estimation de l'équilibre.

Le **score live** s'affiche dans le bandeau du haut quand il est disponible.

Dans les menus : ton **lobby** (toi + ta party, même seul), avec ton **ping vers les serveurs**, le code d'invitation, le temps de file estimé et une éventuelle pénalité de file.

**Clique sur un joueur** pour ouvrir sa fiche : rang en grand, courbe RR des 20 dernières games, stats détaillées, agents récents, historique acte par acte, toutes tes rencontres avec lui, et un champ de **note privée**. Deux autres onglets dans la fiche : **Skins** (locker complet, toutes armes, avec gun buddies et variantes) et **Matchs** (ses derniers matchs classés).

### Onglet Historique

Tes 20 derniers matchs classés : map, agent, score en rounds, K/D/A, ACS, HS%, **RR gagné/perdu** par game, plus la **courbe RR** de l'acte.

### Onglet Boutique

Ton **wallet** (VP / Radianite / Crédits du royaume), la **boutique du jour** (4 skins + prix + rareté), le **marché nocturne** avec les réductions, le **bundle** en cours et la **boutique d'accessoires**, avec les temps restants.

### Onglet Journal

Tous les joueurs que tu as croisés, avec recherche : nombre de rencontres, combien avec toi / contre toi, agents joués, dernière map. Clique pour ouvrir leur fiche.

## Drapeaux et lien tracker.gg

Un petit **↗** à côté de chaque pseudo ouvre le profil tracker.gg du joueur (aussi disponible en gros bouton dans sa fiche).

Le drapeau vient de trois sources, dans cet ordre :

1. **Manuel** — dans la fiche du joueur, choisis son pays : c'est enregistré dans `flags.json` et réaffiché à chaque fois que tu le recroises. Drapeau affiché en pleine opacité.
2. **Tag Riot** — si le tag est un code pays (`#FR`, `#BRA`, `#TR`, `#KR1`…). Les tags de région (`#EUW`, `#NA1`, `#LAN`…) sont ignorés, et les codes qui sont aussi des mots anglais (`#US`, `#IT`, `#MY`…) ne sont retenus que si ta région colle.
3. **Alphabet du pseudo** — hangul → Corée, kana → Japon, thaï → Thaïlande, cyrillique → Russie (ukrainien détecté à part), grec, hébreu, devanagari.

Les drapeaux déduits (2 et 3) sont légèrement transparents ; l'infobulle indique toujours d'où vient l'info. Un clic dans la fiche permet de corriger définitivement.

**Pourquoi pas automatiquement pour tout le monde ?** Aucune API ne publie la nationalité des joueurs Valorant : ni Riot, ni HenrikDev. Sur tracker.gg le drapeau vient d'un réglage volontaire du profil Tracker Network (confirmé par leur équipe), donc il n'existe que pour la minorité de joueurs inscrits chez eux — et leur API demande une clé avec approbation. La cascade ci-dessus est ce qui couvre le plus de monde sans compte ni clé.

## Temps réel

Le serveur surveille la game **en continu** (2 s en sélection d'agents, 3 s en partie) et **pousse** chaque changement vers la page (Server-Sent Events) : plus d'attente, plus de rechargement. Si le flux tombe, la page bascule automatiquement en interrogation longue puis revient au temps réel toute seule.

La pastille à côté de l'état indique la connexion : **verte** = temps réel, **jaune** = mode compatibilité, **rouge** = serveur injoignable.

Seules les cartes qui changent sont redessinées (pas de clignotement, les images ne se rechargent pas) ; une carte modifiée est signalée par un liseré bleu d'une seconde. Bouton ⟳ pour forcer une analyse, ⚙ pour les réglages (tri des joueurs, mode compact, détecteur de smurf).

## Installation (une seule fois)

1. Installe Python : https://www.python.org/downloads/ (coche **"Add Python to PATH"** à l'installation)
2. Ouvre un terminal (cmd) dans ce dossier et tape :
   ```
   pip install requests
   ```

## Lancement

1. Lance Valorant (le client Riot doit être ouvert)
2. Double-clique sur `server.py`, ou dans un cmd :
   ```
   python server.py
   ```
3. Le terminal affiche deux adresses :
   - sur le PC : `http://localhost:8080`
   - sur ton tel : `http://192.168.x.x:8080` (téléphone sur le **même Wi-Fi**)

## Si le téléphone n'arrive pas à se connecter

C'est presque toujours le pare-feu Windows. Autorise le port 8080 : ouvre un cmd **en administrateur** et tape :
```
netsh advfirewall firewall add rule name="Tracker Eaurah" dir=in action=allow protocol=TCP localport=8080
```

## Réglages (en haut de server.py)

- `WEB_PORT` : port de la page web (8080 par défaut)
- `STATS_MATCHES` : nombre de games analysées pour KD / ACS / HS% / forme (5 par défaut — monter augmente le risque de rate-limit)
- `BIG_LOBBY_MATCHES` : idem mais pour les gros lobbies (deathmatch, 14 joueurs), 3 par défaut
- `POLL_INTERVAL` : fréquence du rafraîchissement en tâche de fond (8 s)
- `REQ_PER_SEC` / `REQ_MIN_RATE` / `REQ_MAX_RATE` : bride anti-429 (voir plus bas)
- `STATS_FALLBACK_UNRATED` : si un joueur n'a aucune ranked, calcule ses stats sur toutes les queues
- `RESPECT_STREAMER_MODE` : à `True`, les joueurs qui ont activé "masquer mon nom" s'affichent avec un alias anonyme au lieu de leur pseudo
- `FORCE_REGION` : si la région n'est pas détectée, mets par ex. `("eu", "eu")`
- `LANG` : langue des noms de rangs / skins / agents

## Fichiers créés à côté du script

- `seen_players.json` — journal des rencontres. Ne le supprime pas si tu veux garder l'historique.
- `known_names.json` — cache des pseudos déjà résolus. C'est ce qui évite les "Joueur caché" quand le name-service de Riot répond mal (timeout, 429).
- `notes.json` — tes notes privées sur les joueurs.

## Compiler en .exe (pour publier)

1. Double-clique sur `build_exe.bat` (il installe PyInstaller et compile)
2. Résultat dans `dist\TrackerByEaurah\` → lance `TrackerByEaurah.exe`
3. Pour distribuer : **zippe tout le dossier** `dist\TrackerByEaurah` (l'exe a besoin du dossier `_internal` à côté). Les fichiers de données se créent à côté de l'exe.

### Antivirus / SmartScreen

Un exe ne montre jamais son code source à l'antivirus — open source ou pas, Defender ne "lit" pas le code dans l'exe. L'avertissement "fichier rarement téléchargé" (SmartScreen) est basé sur la **réputation** du fichier, pas son contenu. Pour minimiser les problèmes :

- Le build utilise le mode **dossier** (`--onedir`), beaucoup moins flaggé que le mode fichier unique
- Publie le **code source sur GitHub** avec l'exe en release : ça rassure les utilisateurs et les AV finissent par whitelister
- L'avertissement SmartScreen disparaît de lui-même quand le nombre de téléchargements monte
- Si Defender flagge à tort : soumets le fichier sur https://www.microsoft.com/wdsi/filesubmission (faux positif), ça se règle en quelques jours
- La solution radicale : un certificat de signature de code (payant, ~100-300 €/an)
- Évite les "packers" type UPX : c'est LE truc qui déclenche les AV

## API utilisées

Tout passe par l'API locale du client Riot — pas de clé API nécessaire.

| Donnée | Endpoint |
| --- | --- |
| Tokens / puuid | local `/entitlements/v1/token` |
| Présences, parties, score live | local `/chat/v4/presences` |
| Lobby / party / pings | `glz /parties/v1/...` |
| Sélection d'agents | `glz /pregame/v1/...` |
| Game en cours | `glz /core-game/v1/...` |
| Skins équipés | `glz /{pregame,core-game}/v1/matches/{id}/loadouts` |
| Pseudos | `pd /name-service/v2/players` |
| Rangs, RR, peak, actes | `pd /mmr/v1/players/{puuid}` |
| RR par match | `pd /mmr/v1/players/{puuid}/competitiveupdates` |
| Historique | `pd /match-history/v1/history/{puuid}` |
| Détail d'un match | `pd /match-details/v1/matches/{id}` |
| Boutique | `pd /store/v3/storefront/{puuid}` (POST) |
| Wallet | `pd /store/v1/wallet/{puuid}` |
| Acte en cours | `shared /content-service/v3/content` |
| Noms / images (skins, rangs, agents, cartes, titres, bundles) | valorant-api.com |

## Rate-limit de Riot (important)

Riot bride sévèrement `match-details`, et ne documente aucun quota. Analyser un lobby
coûte cher : 14 joueurs × (1 rang + 1 historique + N détails de match). Sans précaution,
ça part en centaines de requêtes simultanées, Riot répond 429, et plus rien ne s'affiche.

Trois mécanismes évitent ça :

1. **Débit auto-régulé** — un seau à jetons global limite les requêtes/seconde et la
   concurrence. À chaque 429 le débit est divisé par deux et **tous** les threads sont mis
   en pause ensemble ; il remonte doucement quand ça repasse. Pas de valeur magique à régler.
2. **Affichage progressif** — les rangs coûtent 1 requête par joueur, les stats de match
   environ 5. Le tableau (pseudos, agents, rangs) s'affiche donc dès les rangs obtenus,
   avec `…` à la place du KD/ACS, puis se complète. En deathmatch ça change tout.
3. **Caches décalés** — les stats sont gardées 15 min, avec un décalage propre à chaque
   joueur pour que les 10 caches n'expirent pas en même temps en pleine game.

Si tu vois le bandeau « Riot bride N s », c'est normal : ça se résorbe tout seul.

## Notes

- Les détails d'un match sont mutualisés entre tous ses joueurs, donc analyser 10 joueurs coûte bien moins de 10× le prix.
- Le token d'accès Riot est suivi via son expiration réelle, et un 400/401 déclenche une relecture automatique du lockfile — le tracker se remet tout seul quand le client fait tourner son token.
- Les pastilles de duo confirmées viennent des présences du chat Riot (amis + ta party). Les duos ennemis sont **déduits** de l'historique : deux joueurs vus ensemble dans au moins 2 games récentes du même côté. C'est une estimation, pas une certitude.
- Les peak ranks très anciens (avant l'ajout d'Ascendant, mi-2022) peuvent être décalés de 3 paliers.
- Le détecteur de smurf est une heuristique (niveau, KD, ACS, HS, écart avec le peak) — à prendre comme un indice, pas une preuve.
- Le score live n'est disponible que via ta propre présence Riot ; il n'apparaît donc qu'en game, pas en sélection d'agents.
- Le serveur ne doit tourner que sur le PC où Valorant est lancé, et la page n'est accessible que sur ton réseau local.
