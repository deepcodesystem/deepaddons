# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Extend session info with Albirru theme data"""
        result = super().session_info()

        try:
            if request and request.session.uid and self.env.user.has_group('base.group_user'):
                user = self.env.user
                company = self.env.company

                # Get theme settings from albirru.theme.config
                try:
                    theme_settings = user.get_albirru_theme_settings()
                except Exception as e:
                    _logger.warning('Failed to get theme settings: %s', e)
                    theme_settings = self._get_default_theme_settings()

                # Get bookmarks
                try:
                    bookmarks = user.albirru_bookmark_ids.get_bookmarks_data() if user.albirru_bookmark_ids else []
                except Exception as e:
                    _logger.warning('Failed to get bookmarks: %s', e)
                    bookmarks = []

                # Get branding info from company
                try:
                    branding = {
                        'company_id': company.id,
                        'tab_name': getattr(company, 'albirru_tab_name', None) or 'DeepOS',
                        'has_logo': bool(getattr(company, 'albirru_backend_logo', False)),
                        'has_logo_icon': bool(getattr(company, 'albirru_backend_logo_icon', False)),
                        'has_favicon': bool(getattr(company, 'albirru_favicon', False)),
                    }
                except Exception as e:
                    _logger.warning('Failed to get branding: %s', e)
                    branding = {
                        'tab_name': 'Odoo',
                        'has_logo': False,
                        'has_logo_icon': False,
                        'has_favicon': False,
                    }

                result.update({
                    'albirru_theme_installed': True,
                    'albirru_theme_settings': theme_settings,
                    'albirru_bookmarks': bookmarks,
                    'albirru_branding': branding,
                    'albirru_is_admin': user.has_group('base.group_system'),
                })
        except Exception as e:
            _logger.error('Failed to add Albirru theme session info: %s', e)
            result['albirru_theme_installed'] = True
            result['albirru_theme_settings'] = self._get_default_theme_settings()
            result['albirru_bookmarks'] = []
            result['albirru_branding'] = {
                'tab_name': 'Odoo',
                'has_logo': False,
                'has_logo_icon': False,
                'has_favicon': False
            }
            result['albirru_is_admin'] = False

        return result

    def _get_default_theme_settings(self):
        """Return default theme settings"""
        return {
            'theme_style': 'rounded',
            'color_scheme': 'scheme_1',
            'dark_mode': False,
            'sidebar_pinned': True,
            'sidebar_position': 'left',

            'font_family': 'inter',
            'font_size': 'medium',
            'chatter_position': 'right',
            'list_row_height': 'comfortable',
            'list_sticky_header': True,
            'use_custom_colors': False,
            'primary_color': '#714B67',
            'secondary_color': '#ffffff',
            'accent_color': '#017e84',
            'button_style': 'filled',
            'input_style': 'bordered',
            'loader_style': 'spinner',
        }
