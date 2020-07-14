# -*- coding: utf-8 -*-
{
    'name': "Service Station",

    'summary': """
        Manage service station.""",

    'description': """
        This module should manage ...
    """,

    'author': "Eric@kylixs",
    'website': "http://www.kylix.online",

    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr', 'sale', 'account'],
    'installable': True,
    'application': True,

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/sequence.xml',

        'views/station_menu.xml',
        'wizards/wizard.xml',

        'views/station_sales.xml',
        'views/station_misc.xml',
        'views/service_station.xml',
        'views/mpesa_records.xml',

        'reports/station_sale_report.xml',
        'reports/report.xml',

        # 'views/station_settings.xml',
    ],

}
