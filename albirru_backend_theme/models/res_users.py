# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResUsers(models.Model):
    """Extension of res.users for user-specific Albirru theme preferences.
    
    User-level settings override company-level settings for:
    - Dark/Light mode
    - Sidebar pinned state
    - Bookmarks (always user-specific)
    """
    _inherit = 'res.users'

    # User-specific theme preferences
    albirru_dark_mode = fields.Boolean(
        string='Dark Mode',
        default=False,
        help='Enable dark mode for this user'
    )
    albirru_sidebar_pinned = fields.Boolean(
        string='Sidebar Pinned',
        default=True,
        help='Keep sidebar pinned/expanded for this user'
    )
    
    # User Bookmarks
    albirru_bookmark_ids = fields.One2many(
        'albirru.bookmark',
        'user_id',
        string='Bookmarks'
    )

    # Allow users to update their own theme preferences
    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'albirru_dark_mode',
            'albirru_sidebar_pinned',
        ]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'albirru_dark_mode',
            'albirru_sidebar_pinned',
        ]

    def get_albirru_theme_settings(self):
        """Get combined theme settings (company + user overrides).
        
        Returns:
            dict: Theme settings merged from company config with user preferences.
                  User preferences (dark_mode, sidebar_pinned) override company settings.
        """
        self.ensure_one()
        # Get company-level settings
        config = self.env['albirru.theme.config'].get_current_config()
        settings = config.get_theme_values()
        
        # Override with user-specific preferences
        settings['dark_mode'] = self.albirru_dark_mode
        settings['sidebar_pinned'] = self.albirru_sidebar_pinned
        
        return settings

    def save_albirru_user_setting(self, field, value):
        """Save user-specific setting.
        
        Args:
            field: Field name ('dark_mode' or 'sidebar_pinned')
            value: Boolean value
            
        Returns:
            bool: True if saved successfully
        """
        self.ensure_one()
        field_map = {
            'dark_mode': 'albirru_dark_mode',
            'sidebar_pinned': 'albirru_sidebar_pinned',
        }
        if field in field_map:
            self.sudo().write({field_map[field]: value})
            return True
        return False


class AlbirruBookmark(models.Model):
    """User bookmarks for quick navigation.
    
    Bookmarks are user-specific and stored per user. Each bookmark
    contains a name, URL, and optional icon class.
    """
    _name = 'albirru.bookmark'
    _description = 'User Bookmarks'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='URL', required=True)
    icon = fields.Char(string='Icon', default='fa-bookmark')
    sequence = fields.Integer(string='Sequence', default=10)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')

    def get_bookmarks_data(self):
        """Return bookmarks as list of dicts for frontend.
        
        Returns:
            list: List of bookmark dictionaries with id, name, url, and icon.
        """
        return [{
            'id': bookmark.id,
            'name': bookmark.name,
            'url': bookmark.url,
            'icon': bookmark.icon,
        } for bookmark in self]

