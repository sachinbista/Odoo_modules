/** @odoo-module **/

import MainComponent from '@stock_barcode/components/main';
import { patch } from 'web.utils';
import inventory_adjustment_barcode from '../models/inventory_adjustment_barcode'

patch(MainComponent.prototype, "stock_inventory_main_component", {
    // get scanSetup () {
    //     return this.env.model.scan_setup;
    // },
    // _onChangeScanSetup (ev) {
    //     this.env.model.toggleScanSetup($('[name="scan_setup"]:checked').val())
    //     $('[name="scan_setup"]').blur()
    // },

    setup() {
        this._super(...arguments);
    },
    
    get info() {
        return this.env.model.barcodeInfo;
    },

    _getModel(params) {
        const { rpc, orm, notification } = this;
        if (params.model === 'stock.inventory') {
            return new inventory_adjustment_barcode(params, { rpc, orm, notification });
        }
        return this._super(...arguments);
    },
 
    async saveCountSheet (ev) {
        ev.stopPropagation();
        await this.env.model.saveCount();
    },

    get displaySettings () {
        return this.env.model.displaySettings;
    },
    get validateLabel () {
        return this.env.model.validateLabel;
    },

    get displayBarcodeLines() {
        if (this.info.class === 'already_done') {
            return false
        }
        return this.displayBarcodeApplication && this.env.model.canBeProcessed;
    },

    async _onEditLine(ev) {
        let { line } = ev;
        const virtualId = line.virtual_id;
        await this.env.model.save();
        // Updates the line id if it's missing, in order to open the line form view.
        if (!line.id && virtualId) {
            if (this.env.model.pageLines.find(l => l.dummy_id)) {
                line = this.env.model.pageLines.find(l => l.dummy_id === virtualId);
            }
            else {
                line = this.env.model.pageLines.find(l => l.virtual_id === virtualId+1);
            }
        }
        this._editedLineParams = this.env.model.getEditedLineParams(line);
        await this.openProductPage();
    },

    get highlightValidateButton() {
        return this.env.model.highlightValidateButton;
    },


});
