from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class NurseView(models.Model):
    _inherit = 'hr.employee'

    category_ids = fields.Many2many(
        relation='employee_category_nurse',
        comodel_name='hr.employee.category',
        column1='emp_id',
        column2='category_id')

    nurse_license_number = fields.Char(string='License Number')
    nurse_id = fields.Char(string='Nurse Number', required=True, readonly=True,
                           default=lambda self: _('New'))
    specialty = fields.Char(string='Specialty')
    hourly_rate = fields.Float(string='Hourly Rate')
    is_nurse = fields.Boolean(default=False, string="Is Nurse")
    product_id = fields.Many2one('product.product', string='Service Offered')
    cost = fields.Float(compute="_get_price", string="Price")
    commission = fields.Float(compute="_get_price", string="Commision")
    location = fields.Char(string='Location')
    bio = fields.Char(string='Bio')

    @api.depends('product_id')
    def _get_price(self):
        for record in self:
            if record.product_id:
                record.cost = record.product_id.list_price
                record.commission = record.product_id.list_price * 0.35
            else:
                record.cost = 0.0
                record.commission = 0.0

    @api.model
    def create(self, vals):
        if vals.get('is_nurse'):
            vals['nurse_id'] = self.env['ir.sequence'].next_by_code('afyaplug.nurse') or _('')
        res = super(NurseView, self).create(vals)
        return res

    def write(self, vals):
        if self.is_nurse and self.nurse_id == 'New':
            vals['nurse_id'] = self.env['ir.sequence'].next_by_code('afyaplug.nurse') or _('')
        res = super(NurseView, self).write(vals)
        return res
