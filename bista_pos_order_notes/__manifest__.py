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
  "name"                 :  "POS Order Notes",
  "summary"              :  """Allows the  add note to the complete order in POS.""",
  "category"             :  "Point Of Sale",
  "version"              :  "1.0.0",
  "sequence"             :  1,
  "author"               :  "Bistasolutions",
  "license"              :  "Other proprietary",
  "website"              :  "https://www.bistasolutions.com/",
  "description"          :  """Add note to the complete order in POS""",
  "depends"              :  ['point_of_sale'],
  "data"                 :  [
                             'views/pos_config_view.xml'],
  "assets": {
        "point_of_sale.assets": [
            'bista_pos_order_notes/static/src/xml/pos_order_note.xml',
            'bista_pos_order_notes/static/src/js/*.*',
        ],
    },
  "qweb"                 :  [],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
}