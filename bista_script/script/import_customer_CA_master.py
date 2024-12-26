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
file_upload = "CA master supplier list V2.xlsx"
book = xlrd.open_workbook(current_path + "/sheet/" + file_upload)
sheet = book.sheet_by_index(0)
credentials = (dbname, uid, password)


def create_customer(partner_vals_list):
    for partner_details in partner_vals_list:
        partner_id = sock.execute(*credentials, "res.partner", "create", partner_details)

    print("---------------------script end----------------------------")


def prepare_contact_vals(row_values):
    partner_vals = {
        "name": row_values[0],
        "supplier_rank": 1,
        "company_type": "person",
    }

    payment_term = False
    data_term_days = isinstance(row_values[1], float) and str(int(row_values[1])) or row_values[1]
    print("aaaaaaaaaaaaaaaaaaaaaa",data_term_days)
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

print("---------------------script start----------------------------")
create_customer(main_contact)