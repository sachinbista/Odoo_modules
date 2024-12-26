odoo.define('pos_all_in_one.PopupLocationWidget', function(require) {
	'use strict';

	const Popup = require('point_of_sale.ConfirmPopup');
	const Registries = require('point_of_sale.Registries');
	const PosComponent = require('point_of_sale.PosComponent');
	const { onMounted } = owl;

	class PopupLocationWidget extends Popup {
		setup() {
			super.setup();
			onMounted(() =>{
				var self = this;
				$('#select_ssn').hide();
				$('#select_loc').hide();
			});
		}

		go_back_screen() {
			this.showScreen('ProductScreen');
			this.env.posbus.trigger('close-popup', {
				popupId: this.props.id,
				response: { confirmed: false, payload: null },
				});

		}

		get pos_sessions(){
			let sessions = this.env.pos.pos_sessions;
			let pos_sessions = [];
			$.each(sessions, function( i, session ){
				if(session){
					pos_sessions.push(session)
				}
			});
			return pos_sessions;
		}

		get locations(){
			let pos_locations = this.env.pos.stocklocations;
			let locations = [];
			$.each(pos_locations, function( i, loc ){
				if(loc){
					locations.push(loc)
				}
			});

			return locations;
		}
		
		async print_location(){
			var self = this;
			var select_session = $('.select_session_id').val();
			var location = $('.summery_location_id').val();
			var order = self.env.pos.get_order();
			var summery_product = [];
			var tab1 = $('#tab1').is(':checked')
			var tab2 = $('#tab2').is(':checked')
			$('#select_ssn').hide();
			$('#select_loc').hide();
			var ram = false;
			if(tab1 == true)
			{
				ram = true;
				if(select_session){
					this.rpc({
						model: 'pos.order.location',
						method: 'update_location_summery',
						args: [location, location,select_session,tab1,tab2],
					}).then(function(output_summery_location){
						var summery_loc = output_summery_location;
						self.save_location_summery_details(output_summery_location,ram);
					
					});
				}
				else{
					$('#select_ssn').show();
					setTimeout(function() {$('#select_ssn').hide()},3000);
					$('#tab1').prop('checked', true);
				}
				
			}
			else{
				if(location){
					this.rpc({
						model: 'pos.order.location',
						method: 'update_location_summery',
						args: [location, location,select_session,tab1,tab2],
					}).then(function(output_summery_location){
						var summery_loc = output_summery_location;
						self.save_location_summery_details(output_summery_location,ram);
					
					});
				}
				else{
					$('#select_loc').show();
					setTimeout(function() {$('#select_loc').hide()},3000);
					$('#tab2').prop('checked', true);
				}
			}
		}
		
		save_location_summery_details(output_summery_location,ssn){
			var self = this;
			self.env.posbus.trigger('close-popup', {
                popupId: this.props.id });
			self.showScreen('LocationReceiptScreen',{output_summery_location:output_summery_location,ssn:ssn});
		}
	}
	
	PopupLocationWidget.template = 'PopupLocationWidget';

	Registries.Component.add(PopupLocationWidget);

	return PopupLocationWidget;

});