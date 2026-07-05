# -*- coding: utf-8 -*-
# Albirru Backend Theme - App Group Model
# Compatible with Odoo 19

from odoo import models, fields, api
from odoo.exceptions import UserError


class AlbirruAppGroup(models.Model):
    """App Group model for organizing applications in the App Drawer.
    
    App Groups allow administrators to categorize applications into
    logical groups for better organization and navigation in the
    Albirru theme's App Drawer.
    
    Attributes:
        name: Display name of the group
        group_menu_icon: Binary field for custom group icon
        group_menu_list_ids: Applications assigned to this group
        use_group_icon: Whether to use FontAwesome icon class
        group_icon_class_name: FontAwesome icon class name
        sequence: Order of the group in the App Drawer
        active: Whether the group is active
    """
    _name = 'albirru.app.group'
    _description = 'Albirru App Group'
    _order = 'sequence, id'

    name = fields.Char(string='Group Name', required=True, translate=True)
    group_menu_icon = fields.Binary(string='Group Icon')
    group_menu_list_ids = fields.One2many(
        'ir.ui.menu', 'albirru_app_group_id',
        string='Applications',
        domain=[('parent_id', '=', False)]
    )
    use_group_icon = fields.Boolean(string='Use Icon Class', default=False)
    group_icon_class_name = fields.Char(
        string='Icon Class',
        help='FontAwesome or other icon class (e.g., fa-folder, fa-users)'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.onchange('group_menu_list_ids')
    def _onchange_group_menu_list_ids(self):
        """Prevent assigning the same menu to multiple groups"""
        if not self.group_menu_list_ids:
            return

        current_menu_ids = self.group_menu_list_ids.ids
        other_groups = self.env['albirru.app.group'].search([
            ('id', 'not in', self.ids if self.ids else [0]),
            ('group_menu_list_ids', 'in', current_menu_ids)
        ])

        if other_groups:
            raise UserError(
                "Some menus are already assigned to another group. "
                "Please select unique menus for each group."
            )

    def get_group_data(self):
        """Return group data for frontend.
        
        Returns:
            dict: Group data including id, name, sequence, icon settings,
                  and list of menu IDs belonging to this group.
        """
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'sequence': self.sequence,
            'use_group_icon': self.use_group_icon,
            'group_icon_class_name': self.group_icon_class_name or '',
            'has_group_icon': bool(self.group_menu_icon),
            'menu_ids': self.group_menu_list_ids.ids,
        }
