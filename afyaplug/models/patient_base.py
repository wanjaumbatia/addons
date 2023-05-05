# # -*- coding: utf-8 -*-
# # Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# from ast import literal_eval
#
# from pytz import timezone, UTC, utc
# from datetime import timedelta
#
# from odoo import _, api, fields, models
# from odoo.exceptions import UserError
# from odoo.tools import format_time
#
#
# class AfyaPlugPatientBase(models.AbstractModel):
#     _name = "afyaplug.patient_base"
#     _description = "Basic Patient"
#     _order = 'name'
#
#     name = fields.Char()
#     active = fields.Boolean("Active")
#     company_id = fields.Many2one('res.company', 'Company')
#     address_id = fields.Many2one('res.partner', 'Work Address', compute="_compute_address_id", store=True, readonly=False,
#         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
#     phone = fields.Char('Work Phone', store=True, readonly=False)
#     email = fields.Char('Email Address', store=True, readonly=False)
#     contact_id = fields.Many2one('res.partner', 'Contact', copy=False)
#     related_contact_ids = fields.Many2many('res.partner', 'Related Contacts', compute='_compute_related_contacts')
#     related_contacts_count = fields.Integer('Number of related contacts', compute='_compute_related_contacts_count')
#     user_id = fields.Many2one('res.users')
#     resource_id = fields.Many2one('resource.resource')
#     resource_calendar_id = fields.Many2one('resource.calendar', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
#     parent_id = fields.Many2one('hr.employee', 'Assigned Nurse', compute="_compute_parent_id", store=True, readonly=False,
#         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
#     coach_id = fields.Many2one(
#         'hr.employee', 'Follow Up Nurse', compute='_compute_coach', store=True, readonly=False,
#         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
#         help='Select the "Employee" who is the coach of this patient.\n'
#              'The "Coach" has no specific rights or responsibilities by default.')
#     department_id = fields.Many2one('hr.department', 'Department',
#                                     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
#     tz = fields.Selection(
#         string='Timezone', related='resource_id.tz', readonly=False,
#         help="This field is used in order to define in which timezone the resources will work.")
#     last_activity = fields.Date(compute="_compute_last_activity")
#     last_activity_time = fields.Char(compute="_compute_last_activity")
#
#     @api.depends('user_id')
#     def _compute_last_activity(self):
#         presences = self.env['bus.presence'].search_read([('user_id', 'in', self.mapped('user_id').ids)], ['user_id', 'last_presence'])
#         # transform the result to a dict with this format {user.id: last_presence}
#         presences = {p['user_id'][0]: p['last_presence'] for p in presences}
#
#         for patient in self:
#             tz = patient.tz
#             last_presence = presences.get(patient.user_id.id, False)
#             if last_presence:
#                 last_activity_datetime = last_presence.replace(tzinfo=UTC).astimezone(timezone(tz)).replace(tzinfo=None)
#                 patient.last_activity = last_activity_datetime.date()
#                 if patient.last_activity == fields.Date.today():
#                     patient.last_activity_time = format_time(self.env, last_presence, time_format='short')
#                 else:
#                     patient.last_activity_time = False
#             else:
#                 patient.last_activity = False
#                 patient.last_activity_time = False
#
#     @api.depends('parent_id')
#     def _compute_coach(self):
#         for patient in self:
#             manager = patient.parent_id
#             previous_manager = patient._origin.parent_id
#             if manager and (patient.coach_id == previous_manager or not patient.coach_id):
#                 patient.coach_id = manager
#             elif not patient.coach_id:
#                 patient.coach_id = False
#
#     @api.depends('contact_id')
#     def _compute_related_contacts(self):
#         for patient in self:
#             patient.related_contact_ids = patient.contact_id
#
#     @api.depends('related_contact_ids')
#     def _compute_related_contacts_count(self):
#         for patient in self:
#             patient.related_contacts_count = len(patient.related_contact_ids)
#
#     def action_related_contacts(self):
#         self.ensure_one()
#         return {
#             'name': _("Related Contacts"),
#             'type': 'ir.actions.act_window',
#             'view_mode': 'kanban,tree,form',
#             'res_model': 'res.partner',
#             'domain': [('id', 'in', self.related_contact_ids.ids)]
#         }
#
#     @api.depends('company_id')
#     def _compute_address_id(self):
#         for patient in self:
#             address = patient.company_id.partner_id.address_get(['default'])
#             patient.address_id = address['default'] if address else False
#
#     @api.depends('department_id')
#     def _compute_parent_id(self):
#         for patient in self.filtered('department_id.manager_id'):
#             patient.parent_id = patient.department_id.manager_id
#
#
