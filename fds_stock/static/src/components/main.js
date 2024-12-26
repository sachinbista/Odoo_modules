/** @odoo-module **/

import BarcodePickingMoveBoxBalletModel from '@fds_stock/models/barcode_picking_model';
import MainComponent from '@stock_barcode/components/main';

import { patch } from 'web.utils';

patch(MainComponent.prototype, 'fds_stock_box_pallet', {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getModel: function (params) {
        var self = this;
        if (params.model === 'stock.picking') {
            const { rpc, orm, notification } = this;
            return new BarcodePickingMoveBoxBalletModel(params, { rpc, orm, notification });
        }
        return self._super(...arguments);
    },
});
