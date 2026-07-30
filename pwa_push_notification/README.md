# PWA Push Notifications for Odoo 18

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

---

## Description / Description

**EN** – This module adds Web Push Notification support to Odoo 18 PWA
(Progressive Web App) installations. Users can subscribe to push notifications
directly from their browser without requiring a native Android application.

**FR** – Ce module ajoute la prise en charge des Web Push Notifications pour
les installations Odoo 18 en mode PWA (Progressive Web App). Les utilisateurs
peuvent s'abonner aux notifications push directement depuis leur navigateur,
sans nécessiter d'application Android native.

---

## Fonctionnalités / Features

- ✅ Abonnement / désabonnement aux push notifications depuis le navigateur
- ✅ Envoi de notifications à un utilisateur ou à un groupe
- ✅ Interface d'administration pour gérer les abonnements
- ✅ Support multi-appareils par utilisateur
- ✅ Nettoyage automatique des abonnements expirés (HTTP 410)
- ✅ Clés VAPID configurables via les paramètres système
- ✅ Données personnalisées transmises au Service Worker
- ✅ Compatible Chrome 50+, Firefox 44+, Edge 17+, Safari 16+

---

## Prérequis / Prerequisites

### Python
```
pywebpush >= 1.14.0
py-vapid  >= 1.9.0
```

### Navigateur / Browser
- Les push notifications PWA nécessitent **HTTPS** en production.
- `localhost` fonctionne sans HTTPS pour le développement.

---

## Installation

### 1. Installer les dépendances Python / Install Python dependencies
```bash
pip install pywebpush py-vapid
```

### 2. Installer le module / Install the module
1. Copiez le dossier `pwa_push_notification` dans votre répertoire `addons`.
2. Mettez à jour la liste des modules (`Apps > Update Apps List`).
3. Recherchez **PWA Push Notifications** et cliquez sur **Installer**.

### 3. Générer les clés VAPID / Generate VAPID keys
```python
from py_vapid import Vapid

vapid = Vapid()
vapid.generate_keys()
print("Public :", vapid.public_key.decode())
print("Private:", vapid.private_key.decode())
```

Ou utilisez le générateur en ligne : https://vapidkeys.com/

### 4. Configurer les paramètres système / Configure system parameters
Allez dans **Paramètres > Technique > Paramètres système** et mettez à jour :

| Clé / Key                    | Valeur / Value                   |
|------------------------------|----------------------------------|
| `pwa_push.vapid_public_key`  | Votre clé publique VAPID         |
| `pwa_push.vapid_private_key` | Votre clé privée VAPID           |
| `pwa_push.vapid_email`       | `mailto:votre@email.com`         |

---

## Utilisation / Usage

### Activer les notifications (côté utilisateur) / Enable notifications (user side)

Ajoutez le bloc HTML suivant sur n'importe quelle page pour afficher le bouton
d'activation :

```html
<div id="pwa-push-container"></div>
```

Le fichier JavaScript `/pwa_push_notification/static/src/js/push_notification.js`
injectera automatiquement un bouton **Enable Push Notifications** dans ce
conteneur.

Les utilisateurs peuvent également gérer leurs abonnements dans leur profil :
**Préférences > Push Notifications**.

### Envoyer des notifications (côté développeur) / Send notifications (developer side)

```python
# Envoyer une notification à un utilisateur
user = self.env['res.users'].browse(uid)
user.send_push_notification(
    title='Nouvelle commande',
    message='Vous avez reçu une nouvelle commande #SO001',
    data={'url': '/web#action=sale.action_orders'},
)

# Envoyer à plusieurs utilisateurs
users = self.env['res.users'].search([
    ('groups_id', 'in', [group_sale_manager_id]),
])
for user in users:
    user.send_push_notification(
        title='Alerte stock',
        message='Le stock du produit XYZ est faible',
    )

# Envoyer à un abonnement spécifique
subscription = self.env['push.subscription'].browse(sub_id)
subscription.send_notification(
    title='Message direct',
    message='Cet appareil reçoit cette notification.',
)
```

---

## API Python

### `res.users.send_push_notification(title, message, data=None)`
Envoie une notification à **tous les abonnements actifs** de l'utilisateur.

| Paramètre | Type   | Description                                    |
|-----------|--------|------------------------------------------------|
| `title`   | `str`  | Titre de la notification                       |
| `message` | `str`  | Corps de la notification                       |
| `data`    | `dict` | Données optionnelles transmises au SW (ex: URL)|

Retourne le nombre de notifications envoyées avec succès.

### `push.subscription.send_notification(title, message, data=None)`
Envoie une notification à **cet abonnement spécifique**.

---

## Configuration HTTPS

> ⚠️ **Les Web Push Notifications nécessitent HTTPS en production.**
>
> `localhost` est autorisé sans HTTPS pour le développement local.
>
> Pour la production, configurez un certificat SSL (Let's Encrypt est gratuit).

---

## Troubleshooting

| Problème | Solution |
|----------|----------|
| `pywebpush` non trouvé | `pip install pywebpush py-vapid` |
| Clé VAPID non configurée | Mettre à jour les paramètres système |
| Notifications non reçues | Vérifier que HTTPS est actif |
| Abonnement inactif (410) | Le navigateur a révoqué l'abonnement ; l'utilisateur doit se réabonner |
| Permission refusée | L'utilisateur a bloqué les notifications dans les paramètres du navigateur |

### Vérifier les logs Odoo
```bash
tail -f /var/log/odoo/odoo.log | grep -i push
```

---

## Tests suggérés / Suggested Tests

1. **Test d'abonnement** – Cliquer sur le bouton et vérifier l'entrée dans
   `Paramètres > Push Subscriptions`.
2. **Test d'envoi** – Utiliser le bouton **Test Notification** dans la fiche
   d'abonnement ou le profil utilisateur.
3. **Test de désabonnement** – Cliquer à nouveau sur le bouton et vérifier que
   l'abonnement est désactivé.
4. **Test multi-appareils** – S'abonner depuis deux navigateurs différents et
   envoyer une notification.
5. **Test de nettoyage** – Simuler une réponse HTTP 410 pour vérifier la
   désactivation automatique.

---

## Licence / License

[LGPL-3](https://www.gnu.org/licenses/lgpl-3.0)

Copyright © 2024 [DeepCodeSystem](https://github.com/deepcodesystem/deepaddons)
