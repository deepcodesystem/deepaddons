# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Subscription OCA - Abonnement par variante produit",
    "summary": "Définir le modèle d'abonnement sur la variante produit pour générer automatiquement l'abonnement à la confirmation de commande.",
    "version": "18.0.1.0.0",
    "category": "Subscription Management",
    "author": "GetapPRO",
    "license": "AGPL-3",
    "depends": ["subscription_oca"],
    "data": [
        "views/product_product_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

