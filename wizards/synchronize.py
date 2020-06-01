# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SynchronizeProducts(models.TransientModel):
    _name = "s2u.shopify.wizard.sync.products"
    _description = "Sync. Products to Shopify"

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    instance_id = fields.Many2one('s2u.shopify.instance', string='Instance', required=True, ondelete='cascade')

    def do_synchronize(self):

        instance = self.env['s2u.shopify.instance'].search([], limit=1)
        instance.get_products()
