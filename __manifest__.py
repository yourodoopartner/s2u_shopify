{
    'name': 'Odoo Shopify',
    'version': '13.0.1.0',
    'author': 'Solutions2use',
    'price': 0.0,
    'currency': 'EUR',
    'maintainer': 'Solutions2use',
    'support': 'info@solutions2use.com',
    'images': ['static/description/app_logo.jpg'],
    'license': 'OPL-1',
    'website': 'https://www.solutions2use.com',
    'category':  'eCommerce',
    'summary': 'Shopify connector to handle orders',
    'description':
        """This module integrates Shopify with Odoo.
        """,
    'depends': ['base_setup', 'product', 'account', 'sale'],
    'data': [
        'security/res_groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/shopify_view.xml',
        'views_inherited/sale_view.xml',
        'wizards/views/synchronize_view.xml',
        'wizards/views/shopify_settings_view.xml',
        'data/crons.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
