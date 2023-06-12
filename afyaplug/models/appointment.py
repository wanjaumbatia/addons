# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AfyaPlugAppointment(models.Model):
    _name = "afyaplug.appointment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Afyaplug Appointment"
    _order = "nurse_id,reference,contact_id"

    reference = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                            default=lambda self: _('New'))
    contact_id = fields.Many2one('res.partner', string="Patient", required=True)
    nurse_id = fields.Many2one('hr.employee', string="Nurse", required=True)
    product_id = fields.Many2one('product.product', string='Service Offered')
    street = fields.Char(string='Address')
    street2 = fields.Char(string='Area')
    landmark = fields.Char(string='Landmark')
    town = fields.Char(string='Town')
    county = fields.Char(string='County')
    longitude = fields.Float(string="Longitude")
    latitude = fields.Float(string="Latitude")

    note = fields.Text(string='Description')
    appointment_date = fields.Date(string="Date")
    appointment_time = fields.Datetime(string="Time")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('ongoing', 'InProgress'),
                              ('done', 'Done'), ('cancel', 'Cancelled')], default='draft',
                             string="Status", tracking=True)

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

    def action_start(self):
        #open sales order
        order = self.env['sale.order'].create({
            'partner_id': self.contact_id.id,
            'partner_invoice_id': self.contact_id.id,
            'partner_shipping_id': self.contact_id.id,
            'user_id': self.nurse_id.user_id.id,
            'state': 'draft',
            # Set any other required fields
        })

        product = self.env['product.product'].browse(self.product_id.id)
        print(product.id)
        order_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'name': product.name,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'price_unit': product.lst_price,
            # Set any other required fields
        })
        print(order_line)
        order.action_confirm()
        self.state = 'ongoing'

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
            raise ValidationError(_("You Cannot Delete %s as it is already Completed" % self.name))
        if self.state == 'ongoing':
            raise ValidationError(_("You Cannot Delete %s as it is On Going" % self.name))
        if self.state == 'confirm':
            raise ValidationError(_("You Cannot Delete %s as it is Confirmed" % self.name))
        return super(AfyaPlugAppointment, self).unlink()
