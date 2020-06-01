# -*- coding: utf-8 -*-

from datetime import timedelta

import io
from io import BytesIO
import base64
import xlsxwriter

from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _, tools


class Partner(models.Model):
    _inherit = "res.partner"

    shopify_id = fields.Char(string='Moneybird Id.', index=True)

