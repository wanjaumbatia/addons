# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AfyaPlugAppointment(models.Model):
    _name = "afyaplug.appointment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Afyalug Appointment"
    _order = "nurse_id,reference,contact_id"

    reference = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    contact_id = fields.Many2one('res.partner', string="Patient", required=True)
    phone = fields.Char(string='Phone Number', compute='_compute_info', tracking=True, store=True)
    email = fields.Char(string='Email Address', compute='_compute_info', tracking=True, store=True)
    nurse_id = fields.Many2one('hr.employee', string="Nurse", required=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'),
                              ('done', 'Done'), ('cancel', 'Cancelled')], default='draft',
                             string="Status", tracking=True)
    note = fields.Text(string='Description')
    date_appointment = fields.Date(string="Date")
    date_checkup = fields.Datetime(string="Check Up Time")
    prescription = fields.Text(string="Prescription")
    prescription_line_ids = fields.One2many('appointment.prescription.lines', 'appointment_id',
                                            string="Prescription Lines")

    @api.depends('contact_id')
    def _compute_mobile(self):
        """ compute the new values when partner_id has changed """
        for record in self:
            if not record.phone:
                record.phone = record.contact_id.phone
            if not record.email:
                record.email = record.contact_id.email

    def action_confirm(self):
        self.state = 'confirm'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('afyaplug.appointment') or _('New')
        res = super(AfyaPlugAppointment, self).create(vals)
        return res

    @api.onchange('patient_id')
    def onchange_patient_id(self):
        if self.contact_id:
            if self.contact_id.phone:
                self.phone = self.contact_id.phone

            if self.contact_id.note:
                self.note = self.contact_id.note
        else:
            self.phone = ''
            self.note = ''

    def unlink(self):
        if self.state == 'done':
            raise ValidationError(_("You Cannot Delete %s as it is in Done State" % self.name))
        return super(AfyaPlugAppointment, self).unlink()

class AppointmentPrescriptionLines(models.Model):
    _name = "appointment.prescription.lines"
    _description = "Appointment Prescription Lines"

    name = fields.Char(string="Medicine", required=True)
    qty = fields.Integer(string="Quantity")
    appointment_id = fields.Many2one('afyaplug.appointment', string="Appointment")
