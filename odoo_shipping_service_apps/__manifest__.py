# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name":  "Backbone For Shipping Api Integration",
    "summary":  """ODOO-Shipping Service API Integration: PROVIDE CORE SERVICE LAYER FOR API INTEGRATION With 
                    FedEx, USPS, UPS, DHL, Australia Post, Aramex etc.

                    MyDHL Shippo RoyalMail PostNL Deutsche USPS CanadaPost AusPost APC ParcelDE 
                    FreightView DPD Easyship Easypost Easyship Easypost GLS FedEx UPS DHL Aramex Shipstation Shipping Delivery 
            """,
    "category":  "Warehouse",
    "version":  "1.0.7",
    "author":  "Webkul Software Pvt. Ltd.",
    "website":  "https://store.webkul.com/Odoo/Shipping.html",
    "description":  """FedEx ,USPS,UPS,DHL,DHL Intraship, Australia Post and Aramex Shipping API Integration as Odoo Delivery Method .
                    Provide Shipping Label Generation and Shipping Rate Calculator For Website as Well Odoo BackEnd.
                """,  
    "live_test_url":  "https://odoodemo.webkul.com/?module=odoo_shipping_service_apps",
    "depends":  [
        'product',
        'wk_wizard_messages',
        'delivery',
    ],
    "data":  [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/carrier_history.xml',
        'views/delivery_view.xml',
        'views/product_packaging.xml',
        'views/res_config.xml',
        'views/sale.xml',
        'views/stock_picking.xml',
        'views/stock_quant.xml',
        'wizard/choose_delivery_package.xml',
    ],
    "images":  ['static/description/Banner.png'],
    "application":  True,
    "installable":  True,
    "auto_install":  False,
    "pre_init_hook":  "pre_init_check",
    "license":  "LGPL-3",
}
