# -*- coding: utf-8 -*-
##############################################################################
#
#    Globalteckz
#    Copyright (C) 2013-Today Globalteckz (http://www.globalteckz.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Product Auto Sku',
    'version': '1.0',
    'website': 'https://www.globalteckz.com',
    'category': 'product_auto_sku',
    'description': """
    This module will create auto sku with respect to supplier name,product name,attributes options or 
    sequence.


""",
    'author': 'Globalteckz',
    # 'depends': ['base','stock','account','sale','purchase','product'],
    'depends': ['base', 'account', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/sku_config_data.xml',
        'views/product_sku_conf.xml',
        'views/product_squ.xml',
        'views/product_category_view.xml',

    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
