# -*- coding: utf-8 -*-
##############################################################################
#
# Bista Solutions Pvt. Ltd
# Copyright (C) 2023 (http://www.bistasolutions.com)
#
##############################################################################

from odoo import models, fields, api, _


class MailMail(models.Model):
	_inherit = 'mail.mail'
	
	@api.model_create_multi
	def create(self, values_list):
		"""
		Set email from values in all the emails.
		"""
		for values in values_list:
			values['email_from'] = 'info@premierprintsinc.com'
		return super(MailMail, self).create(values_list)


class MailThread(models.AbstractModel):
	_inherit = 'mail.thread'

	def _message_auto_subscribe_notify(self, partner_ids, template):
		res = super(MailThread, self.with_context(mail_auto_subscribe_no_notify=True))._message_auto_subscribe_notify(
			partner_ids, template)
		if self.env.context.get('mail_auto_subscribe_no_notify'):
			return
		return res
