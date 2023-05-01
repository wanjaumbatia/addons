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

    @api.model
    def create(self, vals):
        if vals.get('is_nurse'):
            print('Create Nurse Number')
            vals['nurse_id'] = self.env['ir.sequence'].next_by_code('afyaplug.nurse') or _('')
        res = super(NurseView, self).create(vals)
        return res

