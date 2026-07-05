# -*- coding: utf-8 -*-
import base64
import logging
import re
from urllib.parse import urlparse
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AlbirruThemeController(http.Controller):
    """Controller for Albirru Backend Theme API endpoints"""

    def _is_safe_url(self, url):
        """Validate URL to prevent XSS attacks
        
        Only allows:
        - http:// and https:// URLs
        - Relative URLs starting with /
        - Hash URLs starting with #
        
        Blocks:
        - javascript: URLs
        - data: URLs
        - vbscript: URLs
        - Other potentially dangerous schemes
        
        Args:
            url: URL string to validate
            
        Returns:
            bool: True if URL is safe, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check for dangerous schemes (case-insensitive)
        dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:']
        url_lower = url.lower()
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return False
        
        # Allow relative URLs
        if url.startswith('/') or url.startswith('#'):
            return True
        
        # Parse and validate absolute URLs
        try:
            parsed = urlparse(url)
            # Only allow http and https schemes
            return parsed.scheme in ('http', 'https', '')
        except Exception:
            return False


    @http.route('/albirru_backend_theme/favicon', type='http', auth='public')
    def get_favicon(self, **kwargs):
        """Serve custom favicon from company settings"""
        company = request.env.company

        if company.albirru_favicon:
            favicon_data = base64.b64decode(company.albirru_favicon)
            return request.make_response(
                favicon_data,
                headers=[
                    ('Content-Type', 'image/x-icon'),
                    ('Cache-Control', 'public, max-age=86400'),
                ]
            )

        # Fallback to default Odoo favicon
        return request.redirect('/web/static/img/favicon.ico')

    @http.route('/albirru_backend_theme/menu_background', type='http', auth='user')
    def get_menu_background(self, **kwargs):
        """Serve menu background image from theme config (unified for sidebar and app drawer)"""
        config = request.env['albirru.theme.config'].get_current_config()
        
        if config.menu_background:
            img_data = base64.b64decode(config.menu_background)
            # Detect image type from content
            content_type = 'image/png'
            if img_data[:3] == b'\xff\xd8\xff':
                content_type = 'image/jpeg'
            elif img_data[:4] == b'\x89PNG':
                content_type = 'image/png'
            elif img_data[:6] in (b'GIF87a', b'GIF89a'):
                content_type = 'image/gif'
            elif img_data[:4] == b'RIFF':
                content_type = 'image/webp'
            
            return request.make_response(
                img_data,
                headers=[
                    ('Content-Type', content_type),
                    ('Cache-Control', 'public, max-age=86400'),
                ]
            )
        
        # No image set - return empty response
        return request.make_response('', status=404)



    @http.route('/albirru_backend_theme/theme_settings', type='json', auth='user')
    def get_theme_settings(self, **kwargs):
        """Get theme settings for current user/company"""
        config = request.env['albirru.theme.config'].get_current_config()
        return config.get_theme_values()

    @http.route('/albirru_backend_theme/save_setting', type='json', auth='user')
    def save_setting(self, field, value, **kwargs):
        """Save a theme setting.
        
        User-level settings (dark_mode, sidebar_pinned) are saved to res.users.
        Company-level settings are saved to albirru.theme.config.
        
        Args:
            field: Field name to update
            value: New value for the field
            
        Returns:
            dict: Success status
        """
        # User-level settings (stored on res.users)
        user_level_fields = ['dark_mode', 'sidebar_pinned']
        
        # Company-level settings (stored on albirru.theme.config)
        company_field_validators = {
            # Selection fields
            'theme_style': {'type': str, 'values': ['rounded', 'standard', 'square']},
            'color_scheme': {'type': str, 'values': [f'scheme_{i}' for i in range(1, 19)]},
            'sidebar_position': {'type': str, 'values': ['left', 'top']},

            'chatter_position': {'type': str, 'values': ['right', 'bottom']},
            'font_family': {'type': str, 'values': ['inter', 'roboto', 'poppins', 'open_sans', 'lato', 'nunito']},
            'font_size': {'type': str, 'values': ['small', 'medium', 'large']},
            'list_row_height': {'type': str, 'values': ['compact', 'comfortable']},
            'button_style': {'type': str, 'values': ['filled', 'outlined', 'soft']},
            'input_style': {'type': str, 'values': ['bordered', 'underlined', 'filled']},
            'loader_style': {'type': str, 'values': ['spinner', 'dots', 'bar']},
            # Boolean fields
            'use_custom_colors': {'type': bool},
            'list_sticky_header': {'type': bool},
            # Color fields (hex format)
            'primary_color': {'type': str, 'pattern': r'^#[0-9A-Fa-f]{6}$'},
            'secondary_color': {'type': str, 'pattern': r'^#[0-9A-Fa-f]{6}$'},
            'accent_color': {'type': str, 'pattern': r'^#[0-9A-Fa-f]{6}$'},
            # Integer fields
            'menu_bg_opacity': {'type': int, 'min': 0, 'max': 100},
            # Binary fields
            'menu_background': {'type': 'binary'}, 
        }
        
        # Handle user-level settings
        if field in user_level_fields:
            value = bool(value)
            user = request.env.user
            if user.save_albirru_user_setting(field, value):
                return {'success': True}
            return {'success': False, 'error': 'Failed to save user setting'}

        # Handle company-level settings
        if field not in company_field_validators:
            return {'success': False, 'error': 'Invalid field'}
        
        validator = company_field_validators[field]
        
        # Type check
        expected_type = validator['type']
        if expected_type == bool:
            # Accept boolean or truthy/falsy values
            value = bool(value)
        elif expected_type == int:
            # Accept integer or convert from number
            try:
                value = int(value)
            except (ValueError, TypeError):
                return {'success': False, 'error': f'Invalid integer for {field}'}
        elif expected_type == 'binary':
             # Accept string (base64) or boolean (False/True)
             if not isinstance(value, (str, bool)):
                 return {'success': False, 'error': f'Invalid binary value for {field}'}
        elif not isinstance(value, expected_type):
            return {'success': False, 'error': f'Invalid type for {field}'}
        
        # Value validation for selection fields
        if 'values' in validator and value not in validator['values']:
            return {'success': False, 'error': f'Invalid value for {field}'}
        
        # Pattern validation for color fields
        if 'pattern' in validator:
            if not re.match(validator['pattern'], str(value)):
                return {'success': False, 'error': f'Invalid format for {field}'}
        
        # Range validation for integer fields
        if 'min' in validator and value < validator['min']:
            return {'success': False, 'error': f'{field} must be at least {validator["min"]}'}
        if 'max' in validator and value > validator['max']:
            return {'success': False, 'error': f'{field} must be at most {validator["max"]}'}

        config = request.env['albirru.theme.config'].get_current_config()
        config.save_setting(field, value)
        return {'success': True}

    @http.route('/albirru_backend_theme/bookmarks', type='json', auth='user')
    def get_bookmarks(self, **kwargs):
        """Get user bookmarks"""
        user = request.env.user
        return user.albirru_bookmark_ids.get_bookmarks_data()

    @http.route('/albirru_backend_theme/add_bookmark', type='json', auth='user')
    def add_bookmark(self, name, url, icon='fa-bookmark', **kwargs):
        """Add a new bookmark
        
        Args:
            name: Display name for the bookmark
            url: URL to bookmark (must be http/https or relative path)
            icon: FontAwesome icon class (default: fa-bookmark)
        
        Returns:
            dict: Success status and bookmark data
        """
        # Validate URL to prevent XSS attacks
        if not self._is_safe_url(url):
            return {'success': False, 'error': 'Invalid URL. Only http, https, or relative URLs are allowed.'}
        
        # Sanitize name to prevent XSS
        import html
        safe_name = html.escape(name.strip()[:100]) if name else 'Untitled'
        
        user = request.env.user
        bookmark = request.env['albirru.bookmark'].create({
            'name': safe_name,
            'url': url.strip(),
            'icon': icon if icon and icon.startswith('fa-') else 'fa-bookmark',
            'user_id': user.id,
        })
        return {
            'success': True,
            'bookmark': {
                'id': bookmark.id,
                'name': bookmark.name,
                'url': bookmark.url,
                'icon': bookmark.icon,
            }
        }

    @http.route('/albirru_backend_theme/remove_bookmark', type='json', auth='user')
    def remove_bookmark(self, bookmark_id, **kwargs):
        """Remove a bookmark"""
        user = request.env.user
        bookmark = request.env['albirru.bookmark'].browse(bookmark_id)

        if bookmark.exists() and bookmark.user_id.id == user.id:
            bookmark.unlink()
            return {'success': True}

        return {'success': False, 'error': 'Bookmark not found'}

    @http.route('/albirru_backend_theme/app_groups', type='json', auth='user')
    def get_app_groups(self, **kwargs):
        """Get app groups and menu data for App Drawer"""
        AppGroup = request.env['albirru.app.group'].sudo()
        Menu = request.env['ir.ui.menu'] # Regular search to respect ACL

        # Get root menus (applications) that user has access to
        root_menus = Menu.search([
            ('parent_id', '=', False),
        ])
        accessible_root_ids = set(root_menus.ids)

        # Get all app groups sorted by sequence
        groups = AppGroup.search([], order='sequence, id')
        
        groups_data = []
        grouped_menu_ids = set()

        # First, collect all IDs of menus that are assigned to any group
        # This is done via sudo to ensure consistency across all users
        for group in groups:
            for menu in group.group_menu_list_ids:
                if not menu.parent_id:
                    grouped_menu_ids.add(menu.id)

        # Now build the display data for each group, respecting current user access
        for group in groups:
            group_menus = []
            # Only include menus the user has access to
            for menu in group.group_menu_list_ids:
                if not menu.parent_id and menu.id in accessible_root_ids:
                    group_menus.append(self._get_menu_data(menu))

            if group_menus:
                groups_data.append({
                    'id': group.id,
                    'name': group.name,
                    'sequence': group.sequence,
                    'use_group_icon': group.use_group_icon,
                    'group_icon_class_name': group.group_icon_class_name or '',
                    'has_group_icon': bool(group.group_menu_icon),
                    'menus': group_menus,
                })

        # Get ungrouped menus
        # Any root menu accessible to user that is NOT in any group
        ungrouped_menus = []
        for menu in root_menus:
            if menu.id not in grouped_menu_ids:
                # Include menu if it has an action or web_icon (standard app)
                # Some apps in Odoo 17+ might not have action directly at root
                if menu.action or menu.web_icon:
                    ungrouped_menus.append(self._get_menu_data(menu))

        return {
            'groups': groups_data,
            'ungrouped_menus': ungrouped_menus,
        }

    def _get_menu_data(self, menu):
        """Get menu data for frontend"""
        try:
            # Get xml_id properly
            xml_id_data = menu.get_external_id()
            xmlid = xml_id_data.get(menu.id, '') if xml_id_data else ''
            
            return {
                'id': menu.id,
                'name': menu.name,
                'action_id': menu.action.id if menu.action else None,
                'xmlid': xmlid,
                'web_icon': menu.web_icon or '',
                'use_icon': getattr(menu, 'use_icon', False),
                'icon_class_name': getattr(menu, 'icon_class_name', '') or '',
                'has_icon_img': bool(getattr(menu, 'icon_img', False)),
            }
        except Exception as e:
            _logger.error(f"Error getting menu data for menu {menu.id}: {e}")
            return {
                'id': menu.id,
                'name': menu.name,
                'action_id': menu.action.id if menu.action else None,
                'xmlid': '',
                'web_icon': menu.web_icon or '',
                'use_icon': False,
                'icon_class_name': '',
                'has_icon_img': False,
            }

