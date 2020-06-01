# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShopifyConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = "s2u.shopify.config.settings"

    shopify_user_id = fields.Many2one('res.users', string='Use salesperson')
    shopify_discount_id = fields.Many2one('product.product', string='Discount product')

    @api.model
    def default_get(self, fields):

        rec = super(ShopifyConfigSettings, self).default_get(fields)

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_shopify.salesperson')], limit=1)
        if exists:
            rec['shopify_user_id'] = int(exists.value)

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_shopify.discount_product')], limit=1)
        if exists:
            rec['shopify_discount_id'] = int(exists.value)

        return rec

    def execute(self):

        res = super(ShopifyConfigSettings, self).execute()

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_shopify.salesperson')], limit=1)
        if exists:
            if self.shopify_user_id:
                exists.write({
                    'value': str(self.shopify_user_id.id)
                })
            else:
                exists.unlink()
        elif self.shopify_user_id:
            self.env['ir.config_parameter'].sudo().create({
                'key': 's2u_shopify.salesperson',
                'value': str(self.shopify_user_id.id)
            })

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_shopify.discount_product')], limit=1)
        if exists:
            if self.shopify_discount_id:
                exists.write({
                    'value': str(self.shopify_discount_id.id)
                })
            else:
                exists.unlink()
        elif self.shopify_discount_id:
            self.env['ir.config_parameter'].sudo().create({
                'key': 's2u_shopify.discount_product',
                'value': str(self.shopify_discount_id.id)
            })

        return res
