# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Extension of res.config.settings for Albirru theme configuration.
    
    Exposes company-level branding fields in the General Settings
    interface for easy configuration of backend logos, favicon,
    tab name, login page appearance, and menu backgrounds.
    """
    _inherit = 'res.config.settings'

    # Branding (stored in res.company)
    albirru_backend_logo = fields.Binary(
        related='company_id.albirru_backend_logo',
        readonly=False,
        string='Backend Logo'
    )
    albirru_backend_logo_icon = fields.Binary(
        related='company_id.albirru_backend_logo_icon',
        readonly=False,
        string='Backend Logo Icon'
    )
    albirru_favicon = fields.Binary(
        related='company_id.albirru_favicon',
        readonly=False,
        string='Favicon'
    )
    albirru_tab_name = fields.Char(
        related='company_id.albirru_tab_name',
        readonly=False,
        string='Browser Tab Name'
    )

    # Login Page Branding
    albirru_login_background = fields.Binary(
        related='company_id.albirru_login_background',
        readonly=False,
        string='Login Background'
    )
    albirru_login_background_color = fields.Char(
        related='company_id.albirru_login_background_color',
        readonly=False,
        string='Login Background Color'
    )
    albirru_login_style = fields.Selection(
        related='company_id.albirru_login_style',
        readonly=False,
        string='Login Layout Style',
        required=True
    )



