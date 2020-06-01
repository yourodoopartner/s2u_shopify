# -*- coding: utf-8 -*-

import datetime

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    shopify_id = fields.Char(string='Shopify ID', index=True)
    shopify_status_url = fields.Char(string='Shopify status url')

