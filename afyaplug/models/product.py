from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class NurseView(models.Model):
    _inherit = 'product.template'
    category_id = fields.Many2one('afyaplug.category', string='Category')