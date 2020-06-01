# -*- coding: utf-8 -*-

import requests
import json
import logging
import datetime

from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ShopifyServices(models.TransientModel):

    _name = 's2u.shopify.services'

    @api.model
    def dict_to_params(self, d):
        if not d:
            return ''

        params = False

        for k, v in d.items():
            if params:
                params += '&%s=%s' % (k, v)
            else:
                params = '%s=%s' % (k, v)

        if params:
            return '?' + params
        else:
            return ''


class ShopifyInstance(models.Model):
    _name = 's2u.shopify.instance'
    _description = 'Shopify Instance'

    name = fields.Char(string='Instance', required=True)
    shopify_api_key = fields.Char(string='API Key', required=True)
    shopify_password = fields.Char(string='Password', required=True)
    shopify_secret = fields.Char(string='Secret', required=True)
    shopify_shop = fields.Char(string='Shop', required=True)
    shopify_signature = fields.Char(string='Signature')

    def get_url(self, res_object, res_id=False):

        self.ensure_one()

        if res_id:
            url = "https://%s:%s@%s.myshopify.com/admin/api/2020-04/%s/%s.json" % (self.shopify_api_key,
                                                                                   self.shopify_password,
                                                                                   self.shopify_shop,
                                                                                   res_object,
                                                                                   res_id)
        else:
            url = "https://%s:%s@%s.myshopify.com/admin/api/2020-04/%s.json" % (self.shopify_api_key,
                                                                                self.shopify_password,
                                                                                self.shopify_shop,
                                                                                res_object)

        return url

    def action_get_orders(self):

        self.get_orders()


class ShopifyMappingTemplate(models.Model):
    _name = 's2u.shopify.mapping.template'
    _description = 'Shopify Product Template Mapping'

    shopify_id = fields.Char(string='Shopify ID',
                             readonly=True, states={'draft': [('readonly', False)]})
    shopify_manual = fields.Boolean(string='Manual link ID', default=False,
                                    readonly=True, states={'draft': [('readonly', False)]})
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, ondelete='restrict',
                                      readonly=True, states={'draft': [('readonly', False)]})
    instance_id = fields.Many2one('s2u.shopify.instance', string='Instance', required=True, ondelete='restrict',
                                  readonly=True, states={'draft': [('readonly', False)]})
    mapping_product_ids = fields.One2many('s2u.shopify.mapping.product', 'mapping_template_id',
                                          string='Mapping products', copy=False,
                                          readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Concept'),
        ('link', 'Linked'),
        ('nomatch', 'No match')
    ], string='Status', index=True, default='draft', required=True, copy=False, track_visibility='onchange')
    use_odoo_inventory = fields.Boolean(string='Use Odoo inventory', default=False)
    shopify_location_id = fields.Char(string='Location ID', readonly=True, states={'draft': [('readonly', False)]})

    _sql_constraints = [
        ('instance_product_tmpl', 'unique (instance_id, product_tmpl_id)', 'Instance/Product must be unique!'),
    ]

    def shopify_process_product(self, product, default_mapping=None):

        vals = {
            'shopify_id': str(product['id']),
            'state': 'link'
        }

        if self.use_odoo_inventory:
            url = self.instance_id.get_url('locations')
            response = requests.get(url)
            try:
                res = json.loads(response.content.decode('utf-8'))
            except:
                res = False
            if not res or len(res['locations']) < 1:
                raise UserError(_('No locations found in shopify'))
            vals['shopify_location_id'] = res['locations'][0]['id']

        if default_mapping:
            vals.update(default_mapping)

        if len(product['variants']) == 1:
            variant = product['variants'][0]
            if variant['title'] == 'Default Title':
                vals_mapping_product = {
                    'mapping_template_id': self.id,
                    'product_id': self.product_tmpl_id.product_variant_id.id,
                    'shopify_id': str(variant['id']),
                    'inventory_item_id': str(variant['inventory_item_id']) if variant.get('inventory_item_id') else False
                }
                self.env['s2u.shopify.mapping.product'].create(vals_mapping_product)
                self.write(vals)
                return True
        else:
            variants_match = 0
            for variant in product['variants']:
                if not variant['sku']:
                    continue
                if not variant['sku'].startswith('ODOO'):
                    continue
                odoo_sku = variant['sku'].split('_')
                if len(odoo_sku) != 3:
                    continue

                product = self.env['product.product'].search([('id', '=', int(odoo_sku[2]))], limit=1)
                if not product:
                    continue
                if product.product_tmpl_id != self.product_tmpl_id:
                    continue

                vals_mapping_product = {
                    'mapping_template_id': self.id,
                    'product_id': product.id,
                    'shopify_id': str(variant['id']),
                    'inventory_item_id': str(variant['inventory_item_id']) if variant.get('inventory_item_id') else False
                }
                self.env['s2u.shopify.mapping.product'].create(vals_mapping_product)
                variants_match += 1
            if variants_match:
                self.write(vals)
                return True

        return False

    def shopify_process_product_result(self, res, default_mapping=None):

        if not res:
            return False

        if res.get('errors') or res.get('error'):
            fldname = 'errors' if res.get('errors') else 'error'
            if isinstance(res[fldname], str):
                raise UserError(res[fldname])
            else:
                raise UserError(json.dumps(res[fldname]))

        product = res.get('product')
        return self.shopify_process_product(product, default_mapping=default_mapping)

    def do_action_create(self):

        self.ensure_one()

        url = self.instance_id.get_url('products')

        if self.env.user.user_has_groups('product.group_product_variant') and self.product_tmpl_id.attribute_line_ids:
            if len(self.product_tmpl_id.attribute_line_ids) > 3:
                raise UserError(_('To many attributes on product template. Shopify accepts max. 3.'))
            data = {
                'product': {
                    'title': self.product_tmpl_id.name,
                    'barcode': self.product_tmpl_id.barcode,
                    'sku': 'ODOO_%s_%s' % (self.product_tmpl_id.id, 0),
                    'published': False,
                    'variants': [],
                    'options': []
                }
            }

            for line in self.product_tmpl_id.attribute_line_ids:
                option = {
                    'name': line.attribute_id.name,
                    'values': []
                }
                for value in line.value_ids:
                    option['values'].append(value.name)
                data['product']['options'].append(option)

            options_key = ['option1', 'option2', 'option3']
            for product in self.product_tmpl_id.product_variant_ids:
                idx = 0
                variant = {
                    'price': str(product.lst_price),
                    'inventory_management': 'shopify',
                    'sku': 'ODOO_%s_%s' % (self.product_tmpl_id.id, product.id),
                    'title': product.product_template_attribute_value_ids._get_combination_name(),
                    'weight': str(product.weight),
                    'weight_unit': 'kg',
                    'barcode': product.barcode
                }
                for attribute in product.product_template_attribute_value_ids:
                    if not attribute.ptav_active:
                        continue
                    variant[options_key[idx]] = attribute.name
                    idx += 1
                data['product']['variants'].append(variant)
        else:
            data = {
                'product': {
                    'title': self.product_tmpl_id.name,
                    'published': False,
                    'variants': [{
                        'barcode': self.product_tmpl_id.barcode,
                        'inventory_management': 'shopify',
                        'price': str(self.product_tmpl_id.lst_price),
                        'weight': str(self.product_tmpl_id.weight),
                        'weight_unit': 'kg'
                    }]
                }
            }

        response = requests.post(url,
                                 data=json.dumps(data),
                                 headers={
                                     "Content-Type": "application/json"
                                 })
        try:
            res = json.loads(response.content.decode('utf-8'))
        except:
            res = False

        if not res:
            raise UserError(_('No response from Shopify API.'))

        return self.shopify_process_product_result(res, default_mapping={
            'shopify_manual': False
        })

    def do_action_match(self):

        self.ensure_one()

        if self.shopify_manual:
            url = self.instance_id.get_url('products', res_id=self.shopify_id)
            response = requests.get(url)
            try:
                res = json.loads(response.content.decode('utf-8'))
            except:
                res = False

            if not res:
                raise UserError(_('Shopify product #%s not found.') % self.shopify_id)

            return self.shopify_process_product_result(res)
        else:
            url = self.instance_id.get_url('products')
            response = requests.get(url)
            try:
                res = json.loads(response.content.decode('utf-8'))
            except:
                res = False

            if not res:
                raise UserError(_('No Shopify products found.'))

            for product in res['products']:
                if len(product['variants']) == 1 and product['variants'][0]['title'].lower() == 'default title':
                    sku = product['variants'][0]['sku']
                    if sku and sku.startswith('ODOO') and len(sku.split('_')) == 3:
                        sku = sku.split('_')
                        if sku[1] == str(self.product_tmpl_id.id):
                            return self.shopify_process_product(product, default_mapping={
                                'shopify_manual': False
                            })
                    barcode = product['variants'][0]['barcode']
                    if barcode and barcode == self.product_tmpl_id.barcode:
                        return self.shopify_process_product(product, default_mapping={
                            'shopify_manual': False
                        })
                    if product['title'] == self.product_tmpl_id.name:
                        return self.shopify_process_product(product, default_mapping={
                            'shopify_manual': False
                        })
                else:
                    for variant in product['variants']:
                        if variant['sku'] and variant['sku'].startswith('ODOO') and len(variant['sku'].split('_')) == 3:
                            sku = variant['sku'].split('_')
                            if sku[1] == str(self.product_tmpl_id.id):
                                return self.shopify_process_product(product, default_mapping={
                                    'shopify_manual': False
                                })
                        match_product = self.env['product.product'].search([('product_tmpl_id', '=', self.product_tmpl_id.id),
                                                                            ('barcode', '=', variant['barcode'])])
                        if match_product:
                            return self.shopify_process_product(product, default_mapping={
                                'shopify_manual': False
                            })
                    if product['title'] == self.product_tmpl_id.name:
                        return self.shopify_process_product(product, default_mapping={
                            'shopify_manual': False
                        })

    def do_action_inventory(self):

        self.ensure_one()

        if not self.use_odoo_inventory:
            raise UserError(_('Product is not using Odoo inventory!'))
        if not self.shopify_location_id:
            raise UserError(_('Please define Shopify location for this product!'))
        if self.product_tmpl_id.type != 'product':
            raise UserError(_('Product is not storable!'))

        url = self.instance_id.get_url('inventory_levels/set')
        if self.product_tmpl_id.attribute_line_ids:
            for mapping_product in self.mapping_product_ids:
                try:
                    data = {
                        'location_id': int(self.shopify_location_id),
                        'inventory_item_id': int(mapping_product.inventory_item_id),
                        'available': int(mapping_product.product_id.qty_available)
                    }
                except Exception as e:
                    raise UserError(_('Please check your values!\n[%s]') % e)
                response = requests.post(url,
                                         data=json.dumps(data),
                                         headers={
                                             "Content-Type": "application/json"
                                         })
                try:
                    res = json.loads(response.content.decode('utf-8'))
                except:
                    res = False

                if not res:
                    raise UserError(_('No response from Shopify API.'))

                if res.get('errors') or res.get('error'):
                    fldname = 'errors' if res.get('errors') else 'error'
                    if isinstance(res[fldname], str):
                        raise UserError(res[fldname])
                    else:
                        raise UserError(json.dumps(res[fldname]))

                mapping_product.write({
                    'shopify_qty': mapping_product.product_id.qty_available,
                    'last_sync_done': fields.Datetime.now()
                })
        else:
            try:
                data = {
                    'location_id': int(self.shopify_location_id),
                    'inventory_item_id': int(self.mapping_product_ids[0].inventory_item_id),
                    'available': int(self.product_tmpl_id.qty_available)
                }
            except Exception as e:
                raise UserError(_('Please check your values!\n[%s]') % e)
            response = requests.post(url,
                                     data=json.dumps(data),
                                     headers={
                                         "Content-Type": "application/json"
                                     })
            try:
                res = json.loads(response.content.decode('utf-8'))
            except:
                res = False

            if not res:
                raise UserError(_('No response from Shopify API.'))

            if res.get('errors') or res.get('error'):
                fldname = 'errors' if res.get('errors') else 'error'
                if isinstance(res[fldname], str):
                    raise UserError(res[fldname])
                else:
                    raise UserError(json.dumps(res[fldname]))

            self.mapping_product_ids[0].write({
                'shopify_qty': self.product_tmpl_id.qty_available,
                'last_sync_done': fields.Datetime.now()
            })

    def do_action_back(self):

        self.ensure_one()

        self.mapping_product_ids.unlink()

        self.write({
            'state': 'draft'
        })

    @api.model
    def cron_synchronize_inventory(self):
        """WARNING: meant for cron usage only - will commit() after each validation!"""

        _logger.info('Start synchronize inventory with Shopify ...')

        self._cr.commit()

        todos = self.env['s2u.shopify.mapping.product'].search([('use_odoo_inventory', '=', True)])
        for t in todos:
            # skip not storable
            if t.product_id.type != 'product':
                continue
            if not t.inventory_item_id:
                continue
            if not t.mapping_template_id.shopify_location_id:
                continue
            if not t.last_sync_done or (t.shopify_qty != t.product_id.qty_available):
                try:
                    data = {
                        'location_id': int(t.mapping_template_id.shopify_location_id),
                        'inventory_item_id': int(t.inventory_item_id),
                        'available': int(t.product_id.qty_available)
                    }
                except:
                    data = False
                if not data:
                    continue

                url = t.mapping_template_id.instance_id.get_url('inventory_levels/set')

                try:
                    response = requests.post(url,
                                             data=json.dumps(data),
                                             headers={
                                                 "Content-Type": "application/json"
                                             })
                    res = json.loads(response.content.decode('utf-8'))

                    if not res:
                        _logger.error('Shopify synchronization inventory failed for product: [%s] with id: [%d] -> No response from API' % (t.product_id.name, t.product_id.id))
                    elif res.get('errors') or res.get('error'):
                        fldname = 'errors' if res.get('errors') else 'error'
                        if isinstance(res[fldname], str):
                            _logger.error('Shopify synchronization inventory failed for product: [%s] with id: [%d] -> %s' % (t.product_id.name, t.product_id.id, res[fldname]))
                        else:
                            _logger.error('Shopify synchronization inventory failed for product: [%s] with id: [%d] -> %s' % (t.product_id.name, t.product_id.id, json.dumps(res[fldname])))
                    else:
                        t.write({
                            'shopify_qty': t.product_id.qty_available,
                            'last_sync_done': fields.Datetime.now()
                        })
                    self._cr.commit()
                except Exception as e:
                    self._cr.rollback()
                    _logger.error('Shopify synchronization inventory failed for product: [%s] with id: [%d]' % (t.product_id.name, t.product_id.id))


class ShopifyMappingProduct(models.Model):
    _name = 's2u.shopify.mapping.product'
    _description = 'Shopify Product Mapping'

    mapping_template_id = fields.Many2one('s2u.shopify.mapping.template', string='Mapping template', required=True,
                                          ondelete='cascade')
    shopify_id = fields.Char(string='Shopify ID')
    inventory_item_id = fields.Char(string='Inventory Item ID')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    instance_id = fields.Many2one('s2u.shopify.instance', string='Instance', related='mapping_template_id.instance_id')
    shopify_manual = fields.Boolean(string='Manual link ID', related='mapping_template_id.shopify_manual')
    state = fields.Selection([
        ('draft', 'Concept'),
        ('link', 'Linked'),
        ('nomatch', 'No match')
    ], string='Status', related='mapping_template_id.state')
    shopify_qty = fields.Float(string='Qty to Shopify')
    use_odoo_inventory = fields.Boolean(string='Use Odoo inventory', related='mapping_template_id.use_odoo_inventory')
    last_sync_done = fields.Datetime(string='Last sync.')


class ShopifyEvent(models.Model):
    _name = 's2u.shopify.event'
    _description = 'Shopify Product Mapping'
    _order = 'id desc'

    name = fields.Char(string='Event', required=True)
    res_id = fields.Char(string='Res. ID', required=True)
    state = fields.Selection([
        ('new', 'New'),
        ('retry', 'Retry'),
        ('processed', 'Processed'),
        ('error', 'Error')
    ], string='Status', required=True, default='new', index=True)
    shopify_test = fields.Boolean(string='Test Event')
    event_datetime = fields.Datetime(string='Received', default=lambda self: fields.Datetime.now(), required=True)
    process_message = fields.Text(string='Message')
    instance_id = fields.Many2one('s2u.shopify.instance', string='Instance', ondelete='cascade')

    def do_action_retry(self):

        self.ensure_one()

        self.write({
            'state': 'retry'
        })

    def do_action_process_event(self):

        self.ensure_one()

        if self.name == 'order_creation':
            self.process_event_order_creation_update()
        if self.name == 'order_update':
            self.process_event_order_creation_update(update_order=True)
        if self.name == 'order_cancelation':
            self.process_event_order_cancelation()
        if self.name == 'order_deletion':
            self.process_event_order_deletion()
        if self.name == 'order_payment':
            self.process_event_order_payment()

    def check_same_address(self, partner, customer):

        def compare_fields(fld1, fld2):

            if not fld1:
                fld1 = False
            if not fld2:
                fld2 = False

            if fld1 != fld2:
                return False

            return True

        if not partner:
            return False

        if partner.name != customer['name']:
            return False

        if partner.country_id.code != customer['country_code']:
            return False

        if not compare_fields(partner.street, customer['address1']):
            return False

        if not compare_fields(partner.street2, customer['address2']):
            return False

        if not compare_fields(partner.zip, customer['zip']):
            return False

        if not compare_fields(partner.city, customer['city']):
            return False

        if customer['company']:
            if not partner.parent_id:
                return False
            if customer['company'] != partner.parent_id.name:
                return False
            if not partner.parent_id.is_company:
                return False
        elif partner.parent_id:
            return False

        return True

    def match_partner(self, email_address, customer, partner=False, type=False):

        if partner and self.check_same_address(partner, customer):
            return partner

        country = self.env['res.country'].search([('code', '=', customer['country_code'])], limit=1)
        if not country:
            raise UserError(_('Country with code [%s] not found.') % customer['country_code'])
        country_state = False
        if customer['province_code']:
            country_state = self.env['res.country.state'].search([('country_id', '=', country.id),
                                                                  ('code', '=', customer['province_code'])], limit=1)
            if not country_state:
                country_state = self.env['res.country.state'].create({
                    'country_id': country.id,
                    'code': customer['province_code'],
                    'name': customer['province']
                })

        customer_id = customer.get('customer_id')

        vals = {
            'shopify_id': str(customer['customer_id']) if customer_id else False,
            'type': type if type else 'contact',
            'name': customer['name'],
            'email': email_address if email_address else False,
            'phone': customer['phone'] if customer['phone'] else False,
            'street': customer['address1'] if customer['address1'] else False,
            'street2': customer['address2'] if customer['address2'] else False,
            'zip': customer['zip'] if customer['zip'] else False,
            'city': customer['city'] if customer['city'] else False,
            'country_id': country.id,
            'state_id': country_state.id if country_state else False
        }

        if customer_id:
            match = self.env['res.partner'].search([('shopify_id', '=', str(customer['customer_id']))], limit=1)
        else:
            match = False

        if match:
            if customer['company']:
                if match.parent_id:
                    match.parent_id.write({
                        'name': customer['company']
                    })
                else:
                    parent = self.env['res.partner'].create({
                        'is_company': True,
                        'name': customer['company'],
                    })
                    vals['parent_id'] = parent.id
            match.write(vals)
            return match
        else:
            if customer['company']:
                parent = self.env['res.partner'].create({
                    'is_company': True,
                    'name': customer['company'],
                })
                vals['parent_id'] = parent.id
            return self.env['res.partner'].create(vals)

    def prepare_fiscal_position(self, partner):

        if partner and partner.property_account_position_id:
            return partner.property_account_position_id

        if not partner.country_id:
            # do nothing, let Odoo decide
            return False

        position = self.env['s2u.shopify.fiscal.position'].search([('country_id', '=', partner.country_id.id)])
        if not position:
            # do nothing, let Odoo decide
            return False

        return position.position_id

    def process_event_order_creation_update(self, update_order=False):

        self.ensure_one()

        if not self.instance_id:
            self.write({
                'state': 'error',
                'process_message': _('No instance present')
            })
            return False

        url = self.instance_id.get_url('orders', res_id=self.res_id)
        response = requests.get(url)
        try:
            res = json.loads(response.content.decode('utf-8'))
        except:
            res = False

        if not res:
            # do nothing, try fetch order in next cron
            return False

        if res.get('errors') or res.get('error'):
            fldname = 'errors' if res.get('errors') else 'error'
            if isinstance(res[fldname], str):
                self.write({
                    'state': 'error',
                    'process_message': res[fldname]
                })
                return False
            else:
                self.write({
                    'state': 'error',
                    'process_message': json.dumps(res[fldname])
                })
                return False

        delivery_product = self.env['product.product'].search([('default_code', '=', 'delivery')])
        if not delivery_product:
            self.write({
                'state': 'error',
                'process_message': _('No product \'delivery\' defined!')
            })
            return False

        if len(delivery_product) > 1:
            self.write({
                'state': 'error',
                'process_message': _('Multiple products \'delivery\' present!')
            })
            return False

        order = res['order']

        customer = order['customer']['default_address']
        partner = self.match_partner(order['customer']['email'], customer)

        customer = order['billing_address']
        partner_invoice = self.match_partner(False, customer, partner=partner, type='invoice')
        customer = order['shipping_address']
        partner_shipping = self.match_partner(False, customer, partner=partner, type='delivery')

        fiscal_position = self.prepare_fiscal_position(partner_shipping)

        if update_order:
            odoo_order = self.env['sale.order'].search([('shopify_id', '=', str(order['id']))], limit=1)
            if not odoo_order:
                raise UserError(_('Order with shopify_id [%s] not found.') % order['id'])
            if odoo_order.state != 'draft':
                odoo_order.action_cancel()
                odoo_order.action_draft()
            odoo_order.order_line.unlink()


        vals = {
            'shopify_id': order['id'],
            'partner_id': partner.id,
            'partner_invoice_id': partner_invoice.id,
            'partner_shipping_id': partner_shipping.id,
            'note': order['note'] if order['note'] else False,
            'origin': 'Shopify',
            'reference': order['name'],
            'fiscal_position_id': fiscal_position.id if fiscal_position else False
        }

        salesperson = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_shopify.salesperson')], limit=1)
        if salesperson:
            vals['user_id'] = int(salesperson.value)

        order_lines = []
        for line in order['line_items']:
            mapping_product = self.env['s2u.shopify.mapping.product'].search([('shopify_id', '=', str(line['variant_id']))], limit=1)
            if not mapping_product:
                raise UserError(_('Mapping product [%s / %s] not found.') % (line['variant_id'], line['title']))
            order_lines.append((0, 0, {
                'name': line['name'],
                'price_unit': float(line['price']),
                'discount': float(line['total_discount']),
                'product_id': mapping_product.product_id.id,
                'product_uom_qty': line['quantity']
            }))

        try:
            tot_discounts = float(order['total_discounts'])
        except:
            tot_discounts = 0.0
        if tot_discounts:
            discount_product = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_shopify.discount_product')], limit=1)
            if not discount_product:
                self.write({
                    'state': 'error',
                    'process_message': _('No discount product defined!')
                })
                return False
            discount_product = self.env['product.product'].browse(int(discount_product.value))
            order_lines.append((0, 0, {
                'name': discount_product.name,
                'price_unit': -1.0 * tot_discounts,
                'product_id': discount_product.id,
                'product_uom_qty': 1
            }))

        for line in order['shipping_lines']:
            order_lines.append((0, 0, {
                'name': line['title'],
                'price_unit': float(line['price']),
                'product_id': delivery_product.id,
                'product_uom_qty': 1
            }))

        vals['order_line'] = order_lines

        if update_order:
            odoo_order.write(vals)
        else:
            odoo_order = self.env['sale.order'].create(vals)

        if round(odoo_order.amount_total, 2) != round(float(order['total_price']), 2):
            raise UserError(_('Total amount mismatch! Checks VAT\'s.'))

        odoo_order.action_confirm()

        self.write({
            'state': 'processed',
            'process_message': odoo_order.name
        })

        return order

    def process_event_order_cancelation(self):

        self.ensure_one()

        if not self.instance_id:
            self.write({
                'state': 'error',
                'process_message': _('No instance present')
            })
            return False

        url = self.instance_id.get_url('orders', res_id=self.res_id)
        response = requests.get(url)
        try:
            res = json.loads(response.content.decode('utf-8'))
        except:
            res = False

        if not res:
            # do nothing, try fetch order in next cron
            return False

        if res.get('errors') or res.get('error'):
            fldname = 'errors' if res.get('errors') else 'error'
            if isinstance(res[fldname], str):
                self.write({
                    'state': 'error',
                    'process_message': res[fldname]
                })
                return False
            else:
                self.write({
                    'state': 'error',
                    'process_message': json.dumps(res[fldname])
                })
                return False

        order = res['order']

        odoo_order = self.env['sale.order'].search([('shopify_id', '=', str(order['id']))], limit=1)
        if not odoo_order:
            raise UserError(_('Order with shopify_id [%s] not found.') % order['id'])

        odoo_order.action_cancel()

        self.write({
            'state': 'processed',
            'process_message': odoo_order.name
        })

        return odoo_order

    def process_event_order_deletion(self):

        self.ensure_one()

        if not self.instance_id:
            self.write({
                'state': 'error',
                'process_message': _('No instance present')
            })
            return False

        url = self.instance_id.get_url('orders', res_id=self.res_id)
        response = requests.get(url)
        try:
            res = json.loads(response.content.decode('utf-8'))
        except:
            res = False

        if not res:
            # do nothing, try fetch order in next cron
            return False

        if res.get('errors') or res.get('error'):
            fldname = 'errors' if res.get('errors') else 'error'
            if isinstance(res[fldname], str):
                self.write({
                    'state': 'error',
                    'process_message': res[fldname]
                })
                return False
            else:
                self.write({
                    'state': 'error',
                    'process_message': json.dumps(res[fldname])
                })
                return False

        order = res['order']

        odoo_order = self.env['sale.order'].search([('shopify_id', '=', str(order['id']))], limit=1)
        if not odoo_order:
            raise UserError(_('Order with shopify_id [%s] not found.') % order['id'])

        if odoo_order.state != 'draft':
            order.action_draft()

        odoo_order.unlink()

        self.write({
            'state': 'processed'
        })

        return True

    def process_event_order_payment(self):

        self.ensure_one()

        if not self.instance_id:
            self.write({
                'state': 'error',
                'process_message': _('No instance present')
            })
            return False

        url = self.instance_id.get_url('orders', res_id=self.res_id)
        response = requests.get(url)
        try:
            res = json.loads(response.content.decode('utf-8'))
        except:
            res = False

        if not res:
            # do nothing, try fetch order in next cron
            return False

        if res.get('errors') or res.get('error'):
            fldname = 'errors' if res.get('errors') else 'error'
            if isinstance(res[fldname], str):
                self.write({
                    'state': 'error',
                    'process_message': res[fldname]
                })
                return False
            else:
                self.write({
                    'state': 'error',
                    'process_message': json.dumps(res[fldname])
                })
                return False

        order = res['order']

        odoo_order = self.env['sale.order'].search([('shopify_id', '=', str(order['id']))], limit=1)
        if not odoo_order:
            raise UserError(_('Order with shopify_id [%s] not found.') % order['id'])

        for invoice in odoo_order.invoice_ids:
            if invoice.amount_residual <= 0.0:
                continue
            payment_vals = self.env['account.payment'].with_context(active_ids=[invoice.id],
                                                                    active_model='account.move').default_get({})
            if invoice.is_inbound():
                domain = [('payment_type', '=', 'inbound')]
            else:
                domain = [('payment_type', '=', 'outbound')]
            payment_vals['payment_method_id'] = self.env['account.payment.method'].search(domain, limit=1).id
            payment_vals['journal_id'] = self.env['account.journal'].search([('type', 'in', ('bank', 'cash'))], limit=1).id
            payment_vals['amount'] = invoice.amount_residual
            payment_vals['payment_date'] = fields.Date.today()
            payment = self.env['account.payment'].create(payment_vals)
            payment.post()

        self.write({
            'state': 'processed'
        })

        return odoo_order

    @api.model
    def cron_process_events(self):
        """WARNING: meant for cron usage only - will commit() after each validation!"""

        _logger.info('Start process Shopify events ...')

        self._cr.commit()

        todos = self.env['s2u.shopify.event'].search([('state', 'in', ['new', 'retry'])], order='id')
        for t in todos:
            try:
                if t.shopify_test:
                    t.write({
                        'state': 'processed',
                        'process_message': 'TEST EVENT'
                    })
                else:
                    if t.name == 'order_creation':
                        t.process_event_order_creation_update()
                    if t.name == 'order_update':
                        t.process_event_order_creation_update(update_order=True)
                    if t.name == 'order_cancelation':
                        t.process_event_order_cancelation()
                    if t.name == 'order_deletion':
                        t.process_event_order_deletion()
                    if t.name == 'order_payment':
                        t.process_event_order_payment()
                self._cr.commit()
            except Exception as e:
                self._cr.rollback()
                _logger.error('Shopify process event failed: [%s] with id: [%s]' % (t.name, t.res_id))
                t.write({
                    'state': 'error',
                    'process_message': e
                })
                self._cr.commit()


class ShopifyFiscalPosition(models.Model):
    _name = 's2u.shopify.fiscal.position'
    _description = 'Shopify Fiscal Position'
    _order = 'country_id'

    country_id = fields.Many2one('res.country', string='Country', ondelete='cascade', required=True)
    position_id = fields.Many2one('account.fiscal.position', string='Position', ondelete='restrict', required=True)

    _sql_constraints = [
        ('country_position', 'unique (country_id)', 'Country must be unique!'),
    ]
