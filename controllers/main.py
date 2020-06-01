# -*- coding: utf-8 -*-

import json
import base64
import hmac
import hashlib
import logging

from odoo import http
from odoo.http import request
from odoo.http import Response

_logger = logging.getLogger(__name__)

class ShopifyController(http.Controller):

    def verify_webhook(self, data, hmac_header):

        headers = request.httprequest.headers

        if 'X-Shopify-Shop-Domain' not in headers:
            return False

        parts = headers['X-Shopify-Shop-Domain'].split('.')
        if not parts:
            return False

        instance = request.env['s2u.shopify.instance'].sudo().search([('shopify_shop', '=', parts[0])], limit=1)
        if not instance:
            return False
        if not instance.shopify_signature:
            return False

        digest = hmac.new(instance.shopify_signature.encode('utf-8'), data, hashlib.sha256).digest()
        computed_hmac = base64.b64encode(digest)

        if hmac.compare_digest(computed_hmac, hmac_header.encode('utf-8')):
            return instance
        else:
            return False

    @http.route(['/shopify/webhook/order_creation'], type='json', methods=['POST'], auth='public', website=True, csrf=False)
    def shopify_order_creation(self, **post):

        headers = request.httprequest.headers

        data = request.httprequest.get_data()
        verified = self.verify_webhook(data, headers.get('X-Shopify-Hmac-SHA256'))

        if headers.get('X-Shopify-Test', False) == 'true':
            if verified:
                _logger.debug('Webhook order_creation tested by Spotify. Working Ok.')
                request.env['s2u.shopify.event'].sudo().create({
                    'instance_id': verified.id,
                    'name': 'order_creation',
                    'res_id': headers['X-Shopify-Order-Id'],
                    'shopify_test': True
                })
            else:
                _logger.debug('Webhook order_creation tested by Spotify. Not verified.')
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        if not verified:
            # do nothing
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        request.env['s2u.shopify.event'].sudo().create({
            'instance_id': verified.id,
            'name': 'order_creation',
            'res_id': headers['X-Shopify-Order-Id'],
            'shopify_test': False
        })

        return Response("Ok", content_type='text/html;charset=utf-8', status=200)

    @http.route(['/shopify/webhook/order_cancelation'], type='json', methods=['POST'], auth='public', website=True,
                csrf=False)
    def shopify_order_cancelation(self, **post):

        headers = request.httprequest.headers

        data = request.httprequest.get_data()
        verified = self.verify_webhook(data, headers.get('X-Shopify-Hmac-SHA256'))

        if headers.get('X-Shopify-Test', False) == 'true':
            if verified:
                _logger.debug('Webhook order_cancelation tested by Spotify. Working Ok.')
                request.env['s2u.shopify.event'].sudo().create({
                    'instance_id': verified.id,
                    'name': 'order_cancelation',
                    'res_id': headers['X-Shopify-Order-Id'],
                    'shopify_test': True
                })
            else:
                _logger.debug('Webhook order_cancelation tested by Spotify. Not verified.')
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        if not verified:
            # do nothing
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        request.env['s2u.shopify.event'].sudo().create({
            'instance_id': verified.id,
            'name': 'order_cancelation',
            'res_id': headers['X-Shopify-Order-Id'],
            'shopify_test': False
        })

        return Response("Ok", content_type='text/html;charset=utf-8', status=200)

    @http.route(['/shopify/webhook/order_deletion'], type='json', methods=['POST'], auth='public', website=True,
                csrf=False)
    def shopify_order_deletion(self, **post):

        headers = request.httprequest.headers

        data = request.httprequest.get_data()
        verified = self.verify_webhook(data, headers.get('X-Shopify-Hmac-SHA256'))

        if headers.get('X-Shopify-Test', False) == 'true':
            if verified:
                _logger.debug('Webhook order_deletion tested by Spotify. Working Ok.')
                request.env['s2u.shopify.event'].sudo().create({
                    'instance_id': verified.id,
                    'name': 'order_deletion',
                    'res_id': headers['X-Shopify-Order-Id'],
                    'shopify_test': True
                })
            else:
                _logger.debug('Webhook order_deletion tested by Spotify. Not verified.')
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        if not verified:
            # do nothing
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        request.env['s2u.shopify.event'].sudo().create({
            'instance_id': verified.id,
            'name': 'order_deletion',
            'res_id': headers['X-Shopify-Order-Id'],
            'shopify_test': False
        })

        return Response("Ok", content_type='text/html;charset=utf-8', status=200)

    @http.route(['/shopify/webhook/order_update'], type='json', methods=['POST'], auth='public', website=True,
                csrf=False)
    def shopify_order_update(self, **post):

        headers = request.httprequest.headers

        data = request.httprequest.get_data()
        verified = self.verify_webhook(data, headers.get('X-Shopify-Hmac-SHA256'))

        if headers.get('X-Shopify-Test', False) == 'true':
            if verified:
                _logger.debug('Webhook order_update tested by Spotify. Working Ok.')
                request.env['s2u.shopify.event'].sudo().create({
                    'instance_id': verified.id,
                    'name': 'order_update',
                    'res_id': headers['X-Shopify-Order-Id'],
                    'shopify_test': True
                })
            else:
                _logger.debug('Webhook order_update tested by Spotify. Not verified.')
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        if not verified:
            # do nothing
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        request.env['s2u.shopify.event'].sudo().create({
            'instance_id': verified.id,
            'name': 'order_update',
            'res_id': headers['X-Shopify-Order-Id'],
            'shopify_test': False
        })

        return Response("Ok", content_type='text/html;charset=utf-8', status=200)

    @http.route(['/shopify/webhook/order_payment'], type='json', methods=['POST'], auth='public', website=True,
                csrf=False)
    def shopify_order_payment(self, **post):

        headers = request.httprequest.headers

        data = request.httprequest.get_data()
        verified = self.verify_webhook(data, headers.get('X-Shopify-Hmac-SHA256'))

        if headers.get('X-Shopify-Test', False) == 'true':
            if verified:
                _logger.debug('Webhook order_payment tested by Spotify. Working Ok.')
                request.env['s2u.shopify.event'].sudo().create({
                    'instance_id': verified.id,
                    'name': 'order_payment',
                    'res_id': headers['X-Shopify-Order-Id'],
                    'shopify_test': True
                })
            else:
                _logger.debug('Webhook order_payment tested by Spotify. Not verified.')
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        if not verified:
            # do nothing
            return Response("Ok", content_type='text/html;charset=utf-8', status=200)

        request.env['s2u.shopify.event'].sudo().create({
            'instance_id': verified.id,
            'name': 'order_payment',
            'res_id': headers['X-Shopify-Order-Id'],
            'shopify_test': False
        })

        return Response("Ok", content_type='text/html;charset=utf-8', status=200)
