# -*- coding: utf-8 -*-

try:
    from xlrd import xlsx
except ImportError:
    pass
else:
    from lxml import etree

    xlsx.ET = etree
    xlsx.ET_has_iterparse = True
    xlsx.Element_has_iter = True

import xmlrpc.client as xmlrpclib
import xlrd
import os
import ssl
import sys

username = "admin"  # the user
password = "admin"  # the password of the user
dbname = 'v17_slip'  # the database
url = "http://localhost:8017/"

if not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(
    ssl, "_create_unverified_context", None
):
    ssl._create_default_https_context = ssl._create_unverified_context
os.chdir("../")
current_path = os.getcwd()
sys.path.append(current_path)

sock_common = xmlrpclib.ServerProxy(url + "/xmlrpc/common")
uid = sock_common.login(dbname, username, password)
sock = xmlrpclib.ServerProxy(url + "/xmlrpc/object")

output = open(current_path + "/Errors.txt", "w")

"""Create Product."""
file_upload = "US master supplier list V2.xlsx"
book = xlrd.open_workbook(current_path + "/sheet/" + file_upload)
sheet = book.sheet_by_index(0)
credentials = (dbname, uid, password)


def create_customer(partner_vals_list):
    print("333333333333333333333333333333333", partner_vals_list)
    for partner_details in partner_vals_list:
        delivery_address = partner_details['delivery_address']
        del partner_details['delivery_address']
        partner_id = sock.execute(*credentials, "res.partner", "create", partner_details)
        if delivery_address:
            delivery_address['type'] = 'delivery'
            delivery_address['parent_id'] = partner_id
            sock.execute(*credentials, "res.partner", "create", delivery_address)


def prepare_contact_vals(row_values):
    zip = isinstance(row_values[10], float) and str(int(row_values[10])) or row_values[10]
    vat = (
        isinstance(row_values[24], float) and str(int(row_values[24])) or row_values[24]
    )
    partner_vals = {
        "name": row_values[0],
        'ref' : row_values[1],
        "email": row_values[2],
        "street": row_values[5],
        "street2": row_values[6] + row_values[7],
        "city": row_values[8],
        "zip": zip,
        "phone": row_values[18],
        'tax_exemption' : True if row_values[25] else False,
        'website' : row_values[26],
        "supplier_rank": 1,
        "company_type": "person",
    }
    delivery_address = {}

    if row_values[12]:
        delivery_address['street'] = row_values[12]
    
    if row_values[13]:
        delivery_address['street2'] = row_values[13]
    if row_values[14]:
        delivery_address['city'] = row_values[14]
    if row_values[16]:
        delivery_address['zip'] = isinstance(row_values[16], float) and str(int(row_values[16])) or row_values[16]
    if row_values[17]:
        del_country_id = sock.execute(
            *credentials,
            "res.country",
            "search",
            [("name", "=", row_values[17])],
        )
        if del_country_id:
            delivery_address["country_id"] = del_country_id[0]
            if row_values[15]:
                del_state_id = sock.execute(
                    *credentials,
                    "res.country.state",
                    "search",
                    [("code", "=", row_values[15]), ("country_id", "=", del_country_id[0])],
                )
                if del_state_id:
                    delivery_address["state_id"] = del_state_id[0]
                else:
                    delivery_address["city"] += row_values[14]
    partner_vals['delivery_address'] = delivery_address
    # if row_values[21]:
    #     acc_number = (
    #         isinstance(row_values[21], float) and int(row_values[21]) or row_values[21]
    #     )
    #     bsbn = (
    #         isinstance(row_values[22], float) and int(row_values[22]) or row_values[22]
    #     )
    #     partner_bank_data = {
    #         "acc_number": acc_number,
    #         "aba_bsb": bsbn,
    #         "acc_holder_name": row_values[20],
    #     }
    #     partner_vals["bank_ids"] = [(0, 0, partner_bank_data)]

    if row_values[17]:
        partner_vals["property_payment_term_id"] = 4
    else:
        partner_vals["property_payment_term_id"] = 1

    if row_values[11]:
        country_id = sock.execute(
            *credentials,
            "res.country",
            "search",
            [("name", "=", row_values[11])],
        )
        if country_id:
            partner_vals["country_id"] = country_id[0]
            if row_values[5]:
                state_id = sock.execute(
                    *credentials,
                    "res.country.state",
                    "search",
                    [("code", "=", row_values[9]), ("country_id", "=", country_id[0])],
                )
                if state_id:
                    partner_vals["state_id"] = state_id[0]
                else:
                    partner_vals["city"] += row_values[8]
    payment_term = False
    data_term_days = isinstance(row_values[29], float) and str(int(row_values[29])) or row_values[29]
    term_lines = sock.execute(
        *credentials,
        "account.payment.term.line",
        "search",
        [("nb_days", "=", data_term_days)],
    )
    term_fields = ['payment_id']
    payment_term = sock.execute(
        *credentials,
        "account.payment.term.line",
        "read",
        term_lines,
        term_fields
    )
    if payment_term:
        partner_vals['property_payment_term_id'] = payment_term[0]['payment_id'][0]
    return partner_vals


main_contact = []
child_contact_details = []
for row_no in range(1, sheet.nrows):
    row_values = sheet.row_values(row_no)
    main_contact.append(prepare_contact_vals(row_values))

create_customer(main_contact)