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
  "name"                 :  "FreightView Shipping Integration",
  "summary"              :  """The Odoo FreightView Shipping Integration module lets you add a shipping method on your odoo store from the backend, and you can manage the shipping of orders along with their tracking number and shipment labels. Admin can also manage stages of their order shipment from the odoo backend. """,
  "category"             :  "Website",
  "version"              :  "1.0.2",
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo/Shipping.html",
  "description"          :  """The FreightView Shipping Integration with Odoo allows customers to place orders on the website and will be shipped using Freightview and delivered to them. The module also allows the real-time tracking of the order as it generates the shipment label along with the tracking number. Once a sales order is created with its packaging the admin can compare and select the shipping carrier from the list and the rate will be calculated accordingly. Then a shipment label will be generated for the order and a tracking number will be allocated for the order.  Products are checked for dimensions and weight, and any overweight or oversized shipments can be quoted separately.  Also, at every stage of shipment, the admin can set/change the status from the odoo backend.
                            
                            Odoo, odoo admin, odoo apps, odoo app, 
                            odoo shipping, FreightView shipping in odoo, 
                            FreightView in odoo, odoo FreightView shipping, 
                            Odoo FreightView Shipping Integration, Shipping Integration, 
                            odoo shipping, shipping label in odoo, manage freight in odoo, 
                            freight management, generate shipping label, shipping, 
                            shipping label, shipment details, shipment, freightview, 
                            shipment tracking, track shipment in odoo
  """,
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=freightview_delivery_carrier",
  "depends"              :  [
                             'odoo_shipping_service_apps',
                            ],
  "data"                 :  [
                              'security/ir.model.access.csv',
                              'data/data.xml',
                              'data/delivery_demo.xml',
                              'views/freightview_delivery_carrier.xml',
                              'views/freightview_stock_picking.xml',
                              'views/freightview_cron.xml',
                            ],
  "demo"                 :  [],
  "images"               :  ['static/description/Banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  "price"                :  199,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
  "external_dependencies": {}
}
