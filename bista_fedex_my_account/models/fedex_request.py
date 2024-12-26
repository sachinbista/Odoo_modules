# -*- encoding: utf-8 -*-
##############################################################################
#
#    Bista Solutions Pvt. Ltd
#    Copyright (C) 2022 (http://www.bistasolutions.com)
#
##############################################################################

from odoo.addons.delivery_fedex.models.fedex_request import FedexRequest
from odoo.tools import remove_accents

STATECODE_REQUIRED_COUNTRIES = ['US', 'CA', 'PR ', 'IN']


class FedexRequest(FedexRequest):

    def shipping_charges_payment(self, shipping_charges_payment_account, payment_type=None, customer=None):
        self.RequestedShipment.ShippingChargesPayment = self.factory.Payment()
        Payor = False
        if payment_type:
            self.RequestedShipment.ShippingChargesPayment.PaymentType = payment_type
            if customer:
                Payor = self.set_payor(customer)
            else:
                Payor = self.factory.Payor()
                Payor.ResponsibleParty = self.factory.Party()
        else:
            self.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER'
            Payor = self.factory.Payor()
            Payor.ResponsibleParty = self.factory.Party()
        Payor.ResponsibleParty.AccountNumber = shipping_charges_payment_account
        self.RequestedShipment.ShippingChargesPayment.Payor = Payor

    def set_payor(self, Payor_partner):
        Payor = self.factory.Payor()
        Contact = self.factory.Contact()
        Contact.PersonName = remove_accents(Payor_partner.name)
        # Contact.PhoneNumber = Payor_partner.phone or ''
        Contact.PhoneNumber = '800-505-2078' or ''
        # TODO fedex documentation asks for TIN number, but it seems to work
        # without

        Address = self.factory.Address()
        Address.StreetLines = [remove_accents(
            Payor_partner.street) or '', remove_accents(Payor_partner.street2) or '']
        Address.City = remove_accents(Payor_partner.city) or ''
        if Payor_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            Address.StateOrProvinceCode = Payor_partner.state_id.code or ''
        else:
            Address.StateOrProvinceCode = ''
        Address.PostalCode = Payor_partner.zip or ''
        Address.CountryCode = Payor_partner.country_id.code or ''

        Payor.ResponsibleParty = self.factory.Party()
        Payor.ResponsibleParty.Contact = Contact
        Payor.ResponsibleParty.Address = Address

        return Payor

    def set_recipient(self, recipient_partner):
        Contact = self.factory.Contact()
        if recipient_partner.is_company:
            if recipient_partner.name:
                Contact.PersonName = recipient_partner.name
            else:
                Contact.PersonName = ''
            Contact.CompanyName = remove_accents(recipient_partner.name)
        else:
            if recipient_partner.name:
                Contact.PersonName = remove_accents(recipient_partner.name)
                Contact.CompanyName = remove_accents(recipient_partner.name) or ''
            else:
                Contact.PersonName = remove_accents(recipient_partner.name)
                Contact.CompanyName = remove_accents(recipient_partner.commercial_company_name) or ''
        # Contact.PhoneNumber = recipient_partner.phone or ''
        Contact.PhoneNumber = '800-505-2078' or ''
        Address = self.factory.Address()
        Address.StreetLines = [remove_accents(recipient_partner.street) or '', remove_accents(recipient_partner.street2) or '']
        Address.City = remove_accents(recipient_partner.city) or ''
        if recipient_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            Address.StateOrProvinceCode = recipient_partner.state_id.code or ''
        else:
            Address.StateOrProvinceCode = ''
        Address.PostalCode = recipient_partner.zip or ''
        Address.CountryCode = recipient_partner.country_id.code or ''

        self.RequestedShipment.Recipient = self.factory.Party()
        self.RequestedShipment.Recipient.Contact = Contact
        self.RequestedShipment.Recipient.Address = Address
