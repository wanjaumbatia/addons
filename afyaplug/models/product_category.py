# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AfyaPlugCategory(models.Model):
    _name = "afyaplug.category"
    _description = "Afyaplug Product Category"

    name = fields.Char(string='Category Name')
    enabled = fields.Boolean(default=False, string="Enabled")