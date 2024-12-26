odoo.define('pos_all_in_one.PartnerListScreen', function(require) {
	'use strict';

	const PartnerListScreen = require('point_of_sale.PartnerListScreen');
	const Registries = require('point_of_sale.Registries');
	const core = require('web.core');
	const _t = core._t;
	const { onMounted, onWillUnmount } = owl;

	const NewPartnerListScreen = PartnerListScreen => class extends PartnerListScreen {
		setup() {
        	super.setup();
			var self = this;

			onMounted(() => {
					self.searchPartner();
            });
		}
			
		registerPayment(partner){
			var self = this;
			
			if (!partner) {

				self.showPopup('ErrorPopup', {
					'title': _t('Unknown customer'),
					'body': _t('You cannot Register Payment. Select customer first.'),
				});
				return false;
			}

			self.showPopup('RegisterPaymentPopupWidget', {'partner':partner});
		}
	};

	Registries.Component.extend(PartnerListScreen, NewPartnerListScreen);

	return PartnerListScreen;

});