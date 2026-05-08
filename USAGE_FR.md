# One Page Rules — Guide d'Utilisation du Bot de Matchmaking

## Table des Matières

1. [Pour Commencer](#pour-commencer)
2. [Aperçu des Commandes](#aperçu-des-commandes)
3. [Rejoindre la File d'Attente](#rejoindre-la-file-dattente)
4. [Défier un Rival](#défier-un-rival)
5. [Consulter le Statut](#consulter-le-statut)
6. [Quitter une File d'Attente ou un Match](#quitter-une-file-dattente-ou-un-match)
7. [Rejoindre pour N'importe quel Adversaire](#rejoindre-pour-nimporte-quel-adversaire)
8. [Réinitialisation par l'Administrateur](#réinitialisation-par-ladministrateur)
9. [Questions Fréquemment Posées](#questions-fréquemment-posées)

---

## Pour Commencer

Le **Bot de Matchmaking One Page Rules** vous aide à trouver des adversaires pour vos parties. Vous pouvez :

- **Rejoindre une file d'attente** avec votre système et votre valeur de points — le bot vous associe automatiquement à un adversaire compatible.
- **Défier un joueur spécifique** directement via la commande `/matchmaking Rival`.
- **Rejoindre sans préférence** avec `/matchmaking_any` si le système et les points vous importent peu.

Toutes les données sont persistées entre les redémarrages du bot, vous ne perdrez donc pas votre place dans la file si le bot redémarre.

---

## Aperçu des Commandes

| Commande | Description | Qui Peut l'Utiliser |
|---------|-------------|---------------------|
| `/matchmaking action:Join` | Rejoindre la file avec un système et des points | Tout le monde |
| `/matchmaking action:Rival` | Défier un joueur spécifique | Tout le monde |
| `/matchmaking action:Status` | Voir tous les matchs actifs et les joueurs en file | Tout le monde |
| `/matchmaking action:Leave` | Quitter la file ou un match confirmé | Tout le monde |
| `/matchmaking_any` | File pour n'importe quel adversaire (système/points quelconques) | Tout le monde |
| `/matchmaking_reset` | Effacer toutes les files et matchs | Administrateurs uniquement |

---

## Rejoindre la File d'Attente

Utilisez cette commande lorsque vous souhaitez être **automatiquement associé** à un adversaire ayant le même système et la même valeur de points.

### Comment l'Utiliser

1. Tapez `/matchmaking` dans n'importe quel canal où le bot est actif.
2. Sélectionnez **Action → Join**.
3. Choisissez votre **System** :
   - **AOF** — Army of the Federation
   - **GDF** — Global Defense Force
4. Choisissez votre valeur de **Points** :
   - **1000**
   - **1500**
   - **2000**
   - **3000+**
5. Appuyez sur Entrée.

### Ce qui se Passe Ensuite

- **Si un adversaire compatible attend** — Le bot crée immédiatement un match et l'annonce dans le canal.
- **Si personne n'attend** — Vous êtes ajouté à la file d'attente. Le bot vous associera quand quelqu'un de compatible rejoindra.

### Exemple

```
/matchmaking action:Join system:AOF points:1500
```

**Réponse du bot (match trouvé) :**
> ⚔️ **MATCH FOUND!** @PlayerA vs @Player B!
> System: **AOF** • Points: **1500**

**Réponse du bot (pas de match, en file) :**
> 🕰️ @PlayerA a rejoint la file avec le système **AOF** (1500 pts). En attente d'un adversaire…

---

## Défier un Rival

Utilisez cette commande lorsque vous souhaitez **défier un joueur spécifique** directement, en contournant la file d'attente.

### Comment l'Utiliser

1. Tapez `/matchmaking` dans n'importe quel canal.
2. Sélectionnez **Action → Rival**.
3. Choisissez un **Opponent** (un membre du serveur).
4. Choisissez votre **System** : AOF ou GDF.
5. Choisissez votre valeur de **Points** : 1000, 1500, 2000 ou 3000+.
6. Appuyez sur Entrée.

### Ce qui se Passe Ensuite

1. Le joueur défié reçoit un message dans le canal avec les boutons **Accept** et **Decline**.
2. Il reçoit également une **notification en message privé** l'informant du défi.
3. **S'il Accepte** — Un match est créé et annoncé. Le défieur reçoit également une confirmation en MP.
4. **S'il Décline** — Le défi est annulé. Le défieur reçoit une notification en MP.

> **Remarque :** Seul le joueur défié peut cliquer sur Accept ou Decline. Les boutons restent actifs indéfiniment jusqu'à utilisation.

### Exemple

```
/matchmaking action:Rival opponent:@PlayerB system:GDF points:2000
```

**Réponse du bot (défi envoyé) :**
> @PlayerB, you have been challenged!
> 
> ⚔️ **Rival Challenge**
> **PlayerA** challenges **PlayerB**!
> System: **GDF** • Points: **2000**
> Do you accept?
> [✅ Accept] [❌ Decline]

---

## Consulter le Statut

Utilisez cette commande pour voir **tous les matchs en cours** et **tous les joueurs en file d'attente**.

### Comment l'Utiliser

1. Tapez `/matchmaking` dans n'importe quel canal.
2. Sélectionnez **Action → Status**.
3. Appuyez sur Entrée.

### Ce que Vous Verrez

Le bot répond avec un embed affichant :

- **Active Matches** — Tous les matchs confirmés avec les noms des joueurs, systèmes et points.
- **Waiting in Queue** — Tous les joueurs actuellement en attente, avec leur système et leurs points.

### Exemple

```
/matchmaking action:Status
```

**Réponse du bot :**

> **📋 Matchmaking Status**
>
> **Active Matches**
> ⚔️ **PlayerA** (AOF, 1500 pts) vs **PlayerB** (AOF, 1500 pts)
> ⚔️ **PlayerC** (GDF, 2000 pts) vs **PlayerD** (GDF, 2000 pts)
>
> **Waiting in Queue**
> 🕰️ **PlayerE** (AOF, 1000 pts): WAITING OPPONENT
> 🕰️ **PlayerF** (GDF, 3000+ pts): WAITING OPPONENT

---

## Quitter une File d'Attente ou un Match

Utilisez cette commande pour **vous retirer** de la file d'attente ou d'un match confirmé.

### Comment l'Utiliser

1. Tapez `/matchmaking` dans n'importe quel canal.
2. Sélectionnez **Action → Leave**.
3. Choisissez **Leave Target** :
   - **Queue** — Vous retirer de la file d'attente de matchmaking (si vous êtes en attente).
   - **Match** — Quitter un match confirmé (votre adversaire sera notifié).
4. Appuyez sur Entrée.

### Ce qui se Passe Ensuite

- **Quitter la File d'Attente** — Vous êtes retiré silencieusement. Vous recevez une confirmation éphémère.
- **Quitter un Match** — Votre adversaire est **mentionné** et notifié que vous avez quitté. Il devra peut-être trouver un nouvel adversaire.

### Exemple

```
/matchmaking action:Leave leave_target:Queue
```

**Réponse du bot (file) :**
> 👋 You have been removed from the matchmaking queue.

```
/matchmaking action:Leave leave_target:Match
```

**Réponse du bot (match) :**
> @PlayerB — **PlayerB**, your opponent has left the match.
> 👋 @PlayerA has been removed from their confirmed match.

---

## Rejoindre pour N'importe quel Adversaire

Utilisez `/matchmaking_any` lorsque vous souhaitez **jouer indépendamment du système ou des points**. C'est le moyen le plus rapide d'obtenir un match.

### Comment l'Utiliser

1. Tapez `/matchmaking_any` dans n'importe quel canal.
2. Appuyez sur Entrée.

### Ce qui se Passe Ensuite

- **Si quelqu'un est déjà dans la file** — Vous êtes immédiatement associé à lui. Vous adoptez **ses** paramètres de système et de points.
- **Si personne n'attend** — Vous êtes ajouté à la file en tant que **ANY**. La prochaine personne qui utilisera `/matchmaking_any` sera associée avec vous.

### Exemple

```
/matchmaking_any
```

**Réponse du bot (match trouvé) :**
> ⚔️ **MATCH FOUND!** @PlayerA vs @Player B!
> System: **AOF** • Points: **1500**
> *(matched using their settings via **Any**)*

**Réponse du bot (pas de match, en file) :**
> 🕰️ @PlayerA a rejoint la file en tant que **ANY** (any system, any points). En attente d'un adversaire…

---

## Réinitialisation par l'Administrateur

Les administrateurs du serveur peuvent manuellement **effacer toutes les files d'attente et tous les matchs** à tout moment.

### Comment l'Utiliser

1. Tapez `/matchmaking_reset` dans n'importe quel canal.
2. Appuyez sur Entrée.

> **Nécessite :** La permission Administrateur sur le serveur.

### Ce qui se Passe Ensuite

- Tous les joueurs en file d'attente sont retirés.
- Tous les matchs actifs sont supprimés.
- Un message de confirmation est publié dans le canal.

### Exemple

```
/matchmaking_reset
```

**Réponse du bot :**
> 🧹 **MATCHMAKING RESET** — All queues and matches have been cleared.

---

## Questions Fréquemment Posées

### Puis-je être dans la file d'attente et dans un match en même temps ?

Non. Si vous êtes déjà dans un match confirmé, vous ne pouvez pas rejoindre la file d'attente. Vous devez d'abord quitter votre match actuel.

### Que se passe-t-il si je quitte un match ?

Votre adversaire est notifié via une mention dans le canal. Le match est supprimé de la liste des matchs actifs.

### Puis-je me défier moi-même ?

Non. Le bot empêche les auto-défis.

### Puis-je défier un bot ?

Non. Le bot empêche de défier d'autres bots.

### Que faire si je rate les boutons Accept/Decline sur un défi ?

Les boutons **n'expirent jamais**. Ils restent actifs sur le message jusqu'à ce que quelqu'un clique dessus. Faites défiler vers le haut pour retrouver le message du défi.

### Le bot se souvient-il de ma position dans la file après un redémarrage ?

Oui. Toutes les données sont sauvegardées dans un fichier JSON et persistent entre les redémarrages.

### Quelle est la différence entre `/matchmaking Join` et `/matchmaking_any` ?

- `/matchmaking Join` vous oblige à choisir un **système et des points spécifiques**. Vous ne serez associé qu'à quelqu'un ayant choisi les mêmes paramètres.
- `/matchmaking_any` vous associe à **n'importe qui** dans la file. Vous héritez de leur système et de leurs points.

### J'ai rejoint la file mais personne ne m'associe. Que dois-je faire ?

Consultez `/matchmaking Status` pour voir si quelqu'un d'autre attend. Si la file est vide, vous devrez attendre qu'un autre joueur rejoigne avec le même système et les mêmes points — ou utilisez `/matchmaking_any` pour jouer avec whoever se présente ensuite.

### Puis-je changer de système ou de points après avoir rejoint la file ?

Pas directement. Vous devez d'abord `/matchmaking Leave` la file, puis la rejoindre à nouveau avec de nouveaux paramètres.
