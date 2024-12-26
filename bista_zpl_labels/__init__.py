# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2021 (https://www.bistasolutions.com)
#
##############################################################################
from . import controllers
from . import report
from . import model


def _generate_stock_barcode_action_pdf(cr, registry):
    from io import BytesIO
    from PyPDF2 import PdfFileReader, PdfFileMerger

    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.graphics.barcode import qr
    from os.path import join, dirname, realpath

    barcodes_actions_path = join(dirname(realpath(__file__)), 'static/img', 'barcodes_actions.pdf')
    OTHER_DEMO_FILENAME = barcodes_actions_path
    FONT = "Helvetica"
    TITLE_FONT_SIZE = 11
    PAGE_SIZE = A4

    def create_page(barcodes, font_size_and_texts):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=PAGE_SIZE)
        for barcode in barcodes:
            d = Drawing(PAGE_SIZE[0], PAGE_SIZE[1])
            qr_code = qr.QrCodeWidget(barcode[2])
            d.add(qr_code)
            renderPDF.draw(d, can, barcode[0], barcode[1])

        for font_size, texts in font_size_and_texts:
            can.setFont(FONT, font_size)
            for text in texts:
                can.drawString(text[0], text[1], text[2])
        can.save()
        packet.seek(0)
        return PdfFileReader(packet)

    barcodes = [
        (75, 680, 'O-CMD.MAIN-MENU'),
        (334, 680, "O-CMD.DISCARD"),
        (75, 572, 'O-BTN.validate'),
        (334, 572, 'O-CMD.cancel'),
        (75, 463, 'O-BTN.print-op'),
        (334, 463, 'O-BTN.print-slip'),
        (75, 356, 'O-BTN.pack'),
        (334, 356, 'O-BTN.scrap'),
        (75, 249, 'O-BTN.record-components'),
        (334, 249, 'O-CMD.PREV'),
        (75, 142, 'O-CMD.NEXT'),
        (334, 142, 'O-CMD.PAGER-FIRST'),
        (75, 35, 'O-CMD.PAGER-LAST'),
    ]

    barcode_titles = [
        (89, 768, "MAIN MENU"),
        (348, 768, "DISCARD"),
        (89, 660, "VALIDATE"),
        (348, 660, "CANCEL"),
        (89, 551, "PRINT PICKING OPERATION"),
        (348, 551, "PRINT DELIVERY SLIP"),
        (89, 444, "PUT IN PACK"),
        (348, 444, "SCRAP"),
        (89, 337, "RECORD COMPONENTS"),
        (348, 337, "PREVIOUS PAGE"),
        (89, 230, "NEXT PAGE"),
        (348, 230, "FIRST PAGE"),
        (89, 123, "LAST PAGE"),
    ]

    font_size_and_texts = [(TITLE_FONT_SIZE, barcode_titles)]
    page1 = create_page(barcodes, font_size_and_texts)

    merger = PdfFileMerger()
    merger.append(page1)
    merger.write(OTHER_DEMO_FILENAME)
