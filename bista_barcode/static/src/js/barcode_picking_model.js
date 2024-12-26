/** @odoo-module **/

import {patch} from 'web.utils';
import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import {_t} from "web.core";
import {sprintf} from "@web/core/utils/strings";


patch(BarcodePickingModel.prototype, 'bista_barcode/static/src/js/barcode_picking_model.js', {
    lot_created: [],

    getDisplayDecrementBtn() {
        console.log("Display btn")
        return this.record.picking_type_id.decrement_btn || this.groups.group_stock_manager;
    },

    getDisplayIncrementBtn() {
        return this.record.picking_type_id.increment_btn || this.groups.group_stock_manager;
    },

    get displayPutInPackButton() {
        return !this.record.picking_type_id.is_package &&
            this.groups.group_tracking_lot && this.config.restrict_put_in_pack !== 'no';
    },

    async _processBarcode(barcode) {
        let _super = this._super,
            args = arguments,
            barcodeData = {};

        console.log("=====================================")
        console.log("Barcode Scanned: ", barcode)
        await this._init_param()
        this.barcode = barcode;
        return await _super.apply(this, arguments);
    },

    async _processSerial(scannedLine) {
        console.log("Barcode: Processing Serial ", this)
        // Update serial location if not same
        if (scannedLine) {
            await this._validate_lot_location(scannedLine)
        }
    },

    async _processLot(scannedLine) {
        console.log("Barcode: Processing Lot ", this)
        if (this.record.picking_type_id.scan_full_lot && scannedLine) {
            await this._validate_lot_location(scannedLine)
            let result = await this._validate_lot_quantity(scannedLine)
            if (result.message) {
                return this._raise_warning(result.message)
            } else if (result.qty) {
                return result.qty
            }
        }
    },

    _processProduct(scannedLine) {
        console.log("Barcode: Processing Product", this)
        if (this.record.picking_type_id.scan_full_qty && scannedLine['reserved_uom_qty']) {
            return scannedLine['reserved_uom_qty']
        }
    },

    async _init_param() {
        console.log("Barcode Model: ", this)
    },

    _raise_warning(message) {
        const msg = sprintf(_t(message));
        console.log("Warning: ", msg)
        this.notification.add(msg, {type: 'danger', 'sticky': true});
        return false
    },

    get_qty_done: function (product_id) {
        return this.currentState.lines.reduce((total, line) => {
            if (line.product_id.id === product_id) {
                return total + line.qty_done
            }
            return total
        }, 0);
    },
    get_reserved_done: function (product_id) {
        return this.currentState.lines.reduce((total, line) => {
            if (line.product_id.id === product_id) {
                return total + line.reserved_uom_qty
            }
            return total
        }, 0);
    },

    async _validate_lot_location(scannedLine) {
        let location_id = scannedLine.location_id ? scannedLine.location_id.id : this.record.location_id
        let response = await this.orm.call("stock.move.line", "replace_move_lot", [scannedLine.id], {
            'lot_id': scannedLine.lot_id.id,
            'location_id': location_id
        })

        if (response && response.message) {
            scannedLine.location_id = response.location_id;
            var pathArray = response.location_id.parent_path.split('/').map(function (item) {
                return parseInt(item, 0); // Convert each item to an integer
            });
            if ($.inArray(location_id, pathArray) === -1) {
                this._raise_warning(response.message)
            }

        }
    },
    async _validate_lot_quantity(line) {
        if (!line) {
            return false
        }

        let done_qty = this.get_qty_done(line.product_id.id)
        let reserved_qty = this.get_reserved_done(line.product_id.id)
        let factor = 1
        if (line.product_uom_id) {
            factor = line.product_uom_id.factor
        }
        let lot_uom_qty = line.lot_id.product_qty * factor
        let total_qty = done_qty + lot_uom_qty
        if (!this.record.immediate_transfer && total_qty > reserved_qty) {
            let message = "Lot quantity is greater than demand quantity. Lot quantity: " + lot_uom_qty + " Demand quantity: " + reserved_qty
            return {'message': message}
        }
        return {qty: lot_uom_qty}

    },

    get printButtons() {
        let res = this._super.apply()

        for (let button in res) {
            if (res[button].method === 'action_print_barcode_pdf') {
                res.splice(button, 1)
            }
        }
        res.splice(2, 0, {
                name: _t("Print Label"),
                class: 'o_picking_label',
                method: 'print_label',
            },
        )
        return res;
    },

    async createNewLine(params) {
        let _super = this._super
        let field_params = params.fieldsParams
        if (!this.record.immediate_transfer) {
            let lot_id = field_params.lot_id
            if (lot_id && this.lot_created.indexOf(lot_id.id) === -1) {
                this.lot_created.push(lot_id.id)
            }

            if (field_params.product_id.tracking === 'lot') {
                let result = await this._validate_lot_quantity(field_params)
                if (result && result.message) {
                    return this._raise_warning(result.message)
                }
            }

        }

        if (['lot', 'serial'].includes(field_params.product_id.tracking)) {
            await this._validate_lot_location(field_params)
        }
        return _super.apply(this, arguments)
    },


    _getDefaultMessageType() {
        if (!this.record.immediate_transfer) {
            this.config.restrict_scan_source_location = false
        }
        return this._super.apply(this, arguments);
    },

    async _updateLineQty(line, args) {
        let _super = this._super
        if (line.product_id.tracking === 'serial') {
            this._processProduct(line)
        } else if (line.product_id.tracking === 'lot') {
            let lot_qty = await this._processLot(line)
            if (lot_qty) {
                args['qty_done'] = lot_qty
            } else {
                return
            }
        } else {
            args['qty_done'] = this._processProduct(line)
        }
        let res = _super.apply(this, arguments)
        this.trigger("update")
        return res
    },

    async validate() {
        let _super = this._super
        let picking_id = this.record.id;

        let initial_lot_ids = Object.values(this.initialState.lines)
            .map(line => line.lot_id?.id)
            .filter(id => id);

        let added_lots = Object.values(this.currentState.lines)
            .map(line => line.lot_id?.id)
            .filter(id => id && !initial_lot_ids.includes(id));

        let picking = []
        if (added_lots.length) {
            let move_lines = await this.orm.searchRead("stock.move.line",
                [['lot_id', 'in', added_lots],
                    ['state', 'not in', ['done', 'cancel', 'draft']],
                    ['picking_id', 'not in', [false, picking_id]]], ['picking_id'])
            picking = move_lines.map(function (move) {
                return move.picking_id[0]
            })


        }
        let ret = await _super.apply(this, arguments)
        await this.orm.call("stock.move.line", "trigger_check_availability", [0], {
            'picking_ids': picking,
        })
        return ret
    },

    async _processPackage(barcodeData) {
        if (!this.record.picking_type_id.scan_package) {
            return
        }
        return await this._super.apply(this, arguments)
    },

    edit() {
        if (!this.record.picking_type_id.allow_edit) {
            return this.notification.add("Editing line is restricted for this operation type", {
                type: 'danger',
                'sticky': false
            });
        }
        console.log("Editing")
        return this._super.apply(this, arguments)
    }

});
