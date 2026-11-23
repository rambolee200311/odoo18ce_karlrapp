# Ginlong 与 Odoo 的接口模块清单；模型通过 worlddepot 提供的 WMS 能力集成。
{
    'name': 'Ginlong APIs',
    'summary': 'Ginlong API integration for World Depot',
    'version': '18.0.2.0.40',
    'category': 'Inventory/Inventory',
    'depends': ['worlddepot'],
    'data': [
        'data/product_attribute.xml',
        'security/ginlong_security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/ginlong_callback_views.xml',
        'views/ginlong_management_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
