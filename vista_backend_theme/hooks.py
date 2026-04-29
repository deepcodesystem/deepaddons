# -*- coding: utf-8 -*-
import base64
from odoo.tools.misc import file_path


MENU_ICONS = {
    'Contacts': 'contacts.png',
    'Link Tracker': 'link-tracker.png',
    'Dashboards': 'dashboards.png',
    'Sales': 'sales.png',
    'Invoicing': 'accounting.png',
    'Inventory': 'inventory.png',
    'Purchase': 'purchase.png',
    'Calendar': 'calendar.png',
    'CRM': 'crm.png',
    'Note': 'notes.png',
    'Notes': 'notes.png',
    'Website': 'website.png',
    'Point of Sale': 'pos.png',
    'Manufacturing': 'manufacturing.png',
    'Repairs': 'repairs.png',
    'Email Marketing': 'email-marketing.png',
    'SMS Marketing': 'sms-marketing.png',
    'Project': 'project.png',
    'Surveys': 'surveys.png',
    'Employees': 'employee.png',
    'Recruitment': 'recruitment.png',
    'Attendances': 'attendance.png',
    'Time Off': 'timeoff.png',
    'Maintenance': 'maintenance.png',
    'Live Chat': 'live-chat.png',
    'Lunch': 'lunch.png',
    'Fleet': 'fleet.png',
    'Timesheets': 'timesheet.png',
    'Events': 'events.png',
    'eLearning': 'elearning.png',
    'Members': 'members.png',
    'Payroll': 'payroll.png',
    'To-do': 'to-do.png',
    'Knowledge': 'knowledge.png',
    'Expenses': 'expenses.png',
    'LLM': 'llm.png',
    'Job Queue': 'job-queue.png',
    'BI Dashboard': 'bi-dashboard.png',
    'Subscriptions': 'subscriptions.png',
    'Commissions': 'commissions.png',
}

POST_MENU_ICONS = dict(MENU_ICONS, **{'Accounting': 'accounting.png'})


def _get_icon(icon_name):
    path = file_path(f'vista_backend_theme/static/src/img/icons/{icon_name}')
    with open(path, 'rb') as f:
        return base64.b64encode(f.read())


def _apply_icons(env, icon_map):
    menus = env['ir.ui.menu'].search([('parent_id', '=', False)])
    for menu in menus:
        icon_file = icon_map.get(menu.name)
        if icon_file:
            try:
                menu.write({'web_icon_data': _get_icon(icon_file)})
            except (FileNotFoundError, ValueError):
                pass


def test_pre_init_hook(env):
    _apply_icons(env, MENU_ICONS)


def test_post_init_hook(env):
    _apply_icons(env, POST_MENU_ICONS)
