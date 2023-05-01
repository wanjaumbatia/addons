import base64
from pytz import UTC
from datetime import datetime, time
from random import choice
from string import digits
from werkzeug.urls import url_encode
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import format_date, Query


class AfyaplugPatient(models.Model):
    _name = 'afyaplug.patient'
    _description = "Patient"
    _inherit = ['afyaplug.patient_base', 'mail.thread', 'mail.activity.mixin', 'resource.mixin', 'avatar.mixin']
    _order = "id desc"

    @api.model
    def default_get(self, fields):
        res = super(AfyaplugPatient, self).default_get(fields)
        return res

    name = fields.Char(string="Employee Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    patient_id = fields.Char(string='Patient No.', required=True, readonly=True,
                             default=lambda self: _('New'))
    age = fields.Integer(string="Age")  # cal value
    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id')
    user_partner_id = fields.Many2one(related='user_id.partner_id', string="User's partner")
    company_id = fields.Many2one('res.company', string="Company")
    company_country_id = fields.Many2one('res.country', 'Company Country', related='company_id.country_id',
                                         readonly=True)
    company_country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True)
    # private partner
    address_home_id = fields.Many2one(
        'res.partner', 'Address',
        help='Enter here the private address of the patient, not the one linked to your company.',
        groups="hr.group_hr_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    is_address_home_a_company = fields.Boolean(
        'The patients address has a company linked',
        compute='_compute_is_address_home_a_company',
    )
    private_email = fields.Char(related='address_home_id.email', string="Private Email", groups="hr.group_hr_user")
    lang = fields.Selection(related='address_home_id.lang', string="Lang", groups="hr.group_hr_user", readonly=False)
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)

    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], tracking=True)
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', default='single', tracking=True)
    birthday = fields.Date('Date of Birth', tracking=True)
    insurance_number = fields.Char('Insurance No.', help='Insurance Number', tracking=True)
    identification_id = fields.Char(string='Identification No', tracking=True)
    passport_id = fields.Char('Passport No', tracking=True)
    notes = fields.Text('Notes', groups="hr.group_hr_user")
    barcode = fields.Char(string="Badge ID", help="ID used for patient identification.", groups="hr.group_hr_user",
                          copy=False)
    id_card = fields.Binary(string="ID Card Copy", groups="hr.group_hr_user")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    residence = fields.Char(string="Residence")
    street = fields.Char(string="Street")
    town = fields.Char(string="Town")
    county = fields.Char(string="County")

    _sql_constraints = [
        ('barcode_uniq', 'unique (barcode)',
         "The Badge ID must be unique, this one is already assigned to another patient."),
        ('user_uniq', 'unique (user_id, company_id)',
         "A user cannot be linked to multiple patients in the same company.")
    ]

    @api.depends('name', 'user_id.avatar_1920', 'image_1920')
    def _compute_avatar_1920(self):
        super()._compute_avatar_1920()

    @api.depends('name', 'user_id.avatar_1024', 'image_1024')
    def _compute_avatar_1024(self):
        super()._compute_avatar_1024()

    @api.depends('name', 'user_id.avatar_512', 'image_512')
    def _compute_avatar_512(self):
        super()._compute_avatar_512()

    @api.depends('name', 'user_id.avatar_256', 'image_256')
    def _compute_avatar_256(self):
        super()._compute_avatar_256()

    @api.depends('name', 'user_id.avatar_128', 'image_128')
    def _compute_avatar_128(self):
        super()._compute_avatar_128()

    def _compute_avatar(self, avatar_field, image_field):
        for patient in self:
            avatar = patient._origin[image_field]
            if not avatar:
                if patient.user_id:
                    avatar = patient.user_id[avatar_field]
                else:
                    avatar = base64.b64encode(patient._avatar_get_placeholder())
            patient[avatar_field] = avatar

    def action_create_user(self):
        self.ensure_one()
        if self.user_id:
            raise ValidationError(_("This patient already has an user."))
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'view_id': self.env.ref('hr.view_users_simple_form').id,
            'target': 'new',
            'context': {
                'default_create_patient_id': self.id,
                'default_name': self.name,
                'default_phone': self.phone,
                'default_login': self.email,
            }
        }

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id:
            self.update(self._sync_user(self.user_id, (bool(self.image_1920))))
            if not self.name:
                self.name = self.user_id.name

    @api.onchange('resource_calendar_id')
    def _onchange_timezone(self):
        if self.resource_calendar_id and not self.tz:
            self.tz = self.resource_calendar_id.tz

    def _sync_user(self, user, patient_has_image=False):
        vals = dict(
            contact_id=user.partner_id.id,
            user_id=user.id,
        )
        if not patient_has_image:
            vals['image_1920'] = user.image_1920
        if user.tz:
            vals['tz'] = user.tz
        return vals

    def _prepare_resource_values(self, vals, tz):
        resource_vals = super()._prepare_resource_values(vals, tz)
        vals.pop('name')  # Already considered by super call but no popped
        # We need to pop it to avoid useless resource update (& write) call
        # on every newly created resource (with the correct name already)
        user_id = vals.pop('user_id', None)
        if user_id:
            resource_vals['user_id'] = user_id
        active_status = vals.get('active')
        if active_status is not None:
            resource_vals['active'] = active_status
        return resource_vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('user_id'):
                user = self.env['res.users'].browse(vals['user_id'])
                vals.update(self._sync_user(user, bool(vals.get('image_1920'))))
                vals['name'] = vals.get('name', user.name)
        patients = super().create(vals_list)

        onboarding_notes_bodies = {}
        hr_root_menu = self.env.ref('hr.menu_hr_root')
        for patient in patients:
            patient._message_subscribe(patient.address_home_id.ids)
            onboarding_notes_bodies[patient.id] = _(
                '<b>Congratulations!</b> Patient File created successfully.'
            )
        patients._message_log_batch(onboarding_notes_bodies)
        return patients

    @api.model
    def create(self, vals):
        if vals.get('patient_id', _('New')) == _('New'):
            vals['patient_id'] = self.env['ir.sequence'].next_by_code('afyaplug.patient') or _('New')
        res = super(AfyaplugPatient, self).create(vals)
        return res

    def write(self, vals):
        print('here')
        if 'address_home_id' in vals:
            self.message_unsubscribe(self.address_home_id.ids)
            if vals['address_home_id']:
                self._message_subscribe([vals['address_home_id']])
        if vals.get('user_id'):
            # Update the profile pictures with user, except if provided
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id']),
                                        (bool(self.image_1920))))
        res = super(AfyaplugPatient, self).write(vals)
        return res

    def unlink(self):
        resources = self.mapped('resource_id')
        super(AfyaplugPatient, self).unlink()
        return resources.unlink()

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self._origin:
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "To avoid multi company issues (losing the access to your previous contracts, leaves, ...), you should create another patient in the new company instead.")
            }}

    def generate_random_barcode(self):
        for patient in self:
            patient.barcode = '041' + "".join(choice(digits) for i in range(9))

    @api.depends('address_home_id', 'user_partner_id')
    def _compute_related_contacts(self):
        super()._compute_related_contacts()
        for patient in self:
            patient.related_contact_ids |= patient.address_home_id | patient.user_partner_id

    @api.depends('address_home_id.parent_id')
    def _compute_is_address_home_a_company(self):
        """Checks that chosen address (res.partner) is not linked to a company.
        """
        for patient in self:
            try:
                patient.is_address_home_a_company = patient.address_home_id.parent_id.id is not False
            except AccessError:
                patient.is_address_home_a_company = False

    def _get_tz(self):
        # Finds the first valid timezone in his tz, his work hours tz,
        #  the company calendar tz or UTC and returns it as a string
        self.ensure_one()
        return self.tz or \
            self.resource_calendar_id.tz or \
            self.company_id.resource_calendar_id.tz or \
            'UTC'

    def _get_tz_batch(self):
        return {emp.id: emp._get_tz() for emp in self}


    def _post_author(self):
        real_user = self.env.context.get('binary_field_real_user')
        if self.env.is_superuser() and real_user:
            self = self.with_user(real_user)
        return self


    def _get_unusual_days(self, date_from, date_to=None):
        if not self:
            return {}
        self.ensure_one()
        return self.resource_calendar_id._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=UTC),
            datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=UTC)
        )

    # ---------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------

    def _message_log(self, **kwargs):
        return super(AfyaplugPatient, self._post_author())._message_log(**kwargs)

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        return super(AfyaplugPatient, self._post_author()).message_post(**kwargs)

    def _sms_get_partner_fields(self):
        return ['user_partner_id']

    def _sms_get_number_fields(self):
        return ['phone']