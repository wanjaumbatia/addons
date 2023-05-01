# -*- coding: utf-8 -*-
{
    'name': "Afya Plug",
    'summary': """Module to Manage Nurses""",
    'description': """Management app to manage nurse scheduling and patient appointments""",
    'author': "Francis Mbatia",
    'website': "https://www.afyaplug.com",
    'sequence': -100,
    'version': '0.1',
    'license': '',
    'depends': [
        'base',
        'base_setup',
        'web',
        'mail',
        'hr',
        'portal',
        'product'
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/patient_view.xml',
        'views/nurse_view.xml',
        'views/portal_template.xml',
        'views/templates.xml',
        'data/data.xml'
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
