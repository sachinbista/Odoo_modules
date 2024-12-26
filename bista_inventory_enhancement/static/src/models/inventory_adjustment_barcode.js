/** @odoo-module **/

import BarcodeModel from '@stock_barcode/models/barcode_model';
import {_t} from "web.core";
import { sprintf } from '@web/core/utils/strings';
import session from 'web.session';
import {useService} from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const { onWillStart } = owl;

export default class BarcodeCountSheetModel extends BarcodeModel {
    constructor(params, services) {
        super(...arguments);
        this.lineModel = 'stock.inventory.line';
        this.validateMessage = _t("The count sheet has been done");
        this.validateMethod = 'action_submit';
        this.dialogService = useService("dialog");
        this.userGroup = useService('user');
        onWillStart(async () => {
            this.inventoryManager = await this.userGroup.hasGroup('stock.group_stock_manager')
        });
    }

    get barcodeInfo() {
        if (this.isCancelled || this.isDone || this.isDraft || this.isUserAllowed) {
            var message = '';
            if (this.isUserAllowed) {
                message = this.state === 'confirm' ? _t("First count sheet is already completed") :
                this.state === 'first_count' ? _t("Please Login with First Count User") : '';
            }
            if (!message) {
                message = this.isDone ? _t("This count sheet is already done") :
                this.isCanceled ? _t("This count sheet is cancelled") : _t("This count sheet is draft.");
            }
            return {
                class: this.isDone ? 'already_done' : 'already_cancelled',
                message: message,
                warning: true,
            };
        }
        let line = this._getParentLine(this.selectedLine) || this.selectedLine;
        if (!line && this.lastScanned.packageId) {
            const lines = this._moveEntirePackage() ? this.packageLines : this.pageLines;
            line = lines.find(l => l.package_id && l.package_id.id === this.lastScanned.packageId);
        }

        if (line) { // Message depends of the selected line's state.
            const { tracking } = line.product_id;
            const trackingNumber = (line.lot_id && line.lot_id.name) || line.lot_name;
            if (this._lineIsNotComplete(line)) {
                if (tracking === 'none') {
                    this.messageType = 'scan_product';
                } else {
                    this.messageType = tracking === 'lot' ? 'scan_lot' : 'scan_serial';
                }
            } else if (tracking !== 'none' && !trackingNumber) {
                // Line's quantity is fulfilled but still waiting a tracking number.
                this.messageType = tracking === 'lot' ? 'scan_lot' : 'scan_serial';
            } else { // Line's quantity is fulfilled.
                this.messageType = this.groups.group_stock_multi_locations && line.location_id.id === this.location.id ?
                    "scan_product_or_src" :
                    "scan_product";
            }
        } else { // Message depends if multilocation is enabled.
            this.messageType = this.groups.group_stock_multi_locations && !this.lastScanned.sourceLocation ?
                'scan_src' :
                'scan_product';
        }

        const barcodeInformations = { class: this.messageType, warning: false, icon: 'barcode' };
        switch (this.messageType) {
            case 'scan_product':
                barcodeInformations.message = this.groups.group_stock_multi_locations ?
                    sprintf(_t("Scan a product in %s or scan another location"), this.location.display_name) :
                    _t("Scan a product");
                break;
            case 'scan_src':
                barcodeInformations.message = _t("Scan a location");
                barcodeInformations.icon = 'sign-out';
                break;
            case 'scan_product_or_src':
                barcodeInformations.message = sprintf(
                    _t("Scan more products in %s or scan another location"),
                    this.location.display_name);
                break;
            case 'scan_product_or_dest':
                barcodeInformations.message = _t("Scan more products, or scan the destination location");
                barcodeInformations.icon = 'sign-in';
                break;
            case 'scan_lot':
                barcodeInformations.message = sprintf(
                    _t("Scan lot numbers for product %s to change their quantity"),
                    line.product_id.display_name
                );
                break;
            case 'scan_serial':
                barcodeInformations.message = sprintf(
                    _t("Scan serial numbers for product %s to change their quantity"),
                    line.product_id.display_name
                );
                break;
        }
        return barcodeInformations;
    }

    setData(data) {
        super.setData(...arguments);
        this.locationList = [];
        data.data.source_location_ids.forEach(id => {
            this.locationList.push(this.cache.getRecord('stock.location', id));
        });
        this.setLot = false;
        this.lotData = data.data.lot_data;
        this.productIds = data.data.product_ids;
        this.productLots = {};
        if (this.lotData && this.productIds) {
            this.setLotData(this.lotData, this.productIds);
        }
        this.filter = this.record.filter;
        this.lineFormViewId = data.data.line_view_id;
        if (this.record.state === 'first_count') {
            this.validateLabel =  _t("Submit")
        } else if (this.record.state === 'second_count') {
            this.validateLabel = _t("Second Count Done")
        } else if (this.record.state === 'confirm') {
            this.validateLabel = _t("Validate")
            this.validateMethod = 'action_validate';
        }
        this.commands = this._getCommands();

    }
    
    getDisplayIncrementBtn(line) {
        return true;
    }

    getDisplayDecrementBtn(line) {
        return this.getDisplayIncrementBtn(line);
    }
    
    updateLineQty(virtualId, qty = 1) {
        let quantities = {first_count_qty: qty};
        if (this.state === 'second_count') {
            quantities = {second_count_qty: qty};
        }
        this.actionMutex.exec(() => {
            const line = this.pageLines.find(l => l.virtual_id === virtualId);
            this.updateLine(line, quantities);
            this.trigger('update');
        });
    }

    _getCommands() {
        /**
        * Get the commands for the current context.
        *
        * @return {object} The commands for the current context
        */
        return {
            'O-CMD.MAIN-MENU': this._goToMainMenu.bind(this),
            'O-BTN.validate': () => {
                if (this.canBeValidate) {
                    this.validate();
                }
            },
        };
    }

    _getNewLineDefaultContext() {
        const stockInventory = this.cache.getRecord(this.params.model, this.params.id);
        return {
            default_company_id: stockInventory.company_id,
            default_location_id: stockInventory.location_id,
            default_inventory_id: this.params.id,
            default_product_qty: 1,
        };
    }

    _createCommandVals(line) {
        /**
         * Creates an object with processed values from the input line.
         *
         * @param {line} line - the input line object
         * @return {object} the object containing processed values
         */
        const values = {
            // dummy_id: line.virtual_id,
            location_id: line.location_id,
            lot_id: line.lot_id,
            package_id: line.package_id,
            product_id: line.product_id,
            first_count_qty: line.first_count_qty,
            second_count_qty: line.second_count_qty
        };
        for (const [key, value] of Object.entries(values)) {
            values[key] = this._fieldToValue(value);
        }
        return values;
    }

    async _createNewLine(params) {
        /**
         * Asynchronously creates a new line based on the provided parameters.
         *
         * @param {Object} params - The parameters for creating the new line.
         * @return {Object} The newly created line.
         */
        if (params.fieldsParams && params.fieldsParams.uom && params.fieldsParams.product_id) {
            let productUOM = this.cache.getRecord('uom.uom', params.fieldsParams.product_id.uom_id);
            let paramsUOM = params.fieldsParams.uom;
            if (paramsUOM.category_id !== productUOM.category_id) {
                // Not the same UoM's category -> Can't be converted.
                const message = sprintf(
                    _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the product's one (%s)."),
                    paramsUOM.name, productUOM.name
                );
                this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'danger'});
                return false;
            }
        }
        const newLine = Object.assign(
            {},
            params.copyOf,
            this._getNewLineDefaultValues(params.fieldsParams)
        );
        const previousIndex = (params.copyOf || this.selectedLine || {}).sortIndex;
        newLine.sortIndex = (previousIndex && previousIndex + "1") || this._getLineIndex();
        await this.updateLine(newLine, params.fieldsParams);
        this.currentState.lines.push(newLine);
        return newLine;
    }

    _convertDataToFieldsParams(args) {
        /**
         * Converts the given data to the parameters required for fields.
         *
         * @param {object} args - The input data object
         * @return {object} The parameters for fields
         */
        const params = {
            lot_id: args.lot,
            lot_name: args.lotName,
            // owner_id: args.owner,
            package_id: args.package || args.resultPackage,
            product_id: args.product,
            product_uom_id: args.product && args.product.uom_id,
            inventory_id: this.record.id,
            location_id: args.location_id
        };
        params[this.field] = args.quantity;
        return params;
    }

    _getNewLineDefaultValues(fieldsParams) {
        /**
        * Get the default values for a new line.
        *
        * @param {Object} fieldsParams - the parameters for the fields
        * @return {Object} the default values for a new line
        */
        const defaultValues = super._getNewLineDefaultValues(...arguments);
        return Object.assign(defaultValues, {
            // id: (fieldsParams && fieldsParams.id) || false,
            virtual_id: this._uniqueVirtualId,
            // location_id: fieldsParams.location_id || this._defaultLocation(),
            first_count_qty: 0,
            second_count_qty: 0,
            theoretical_qty: 0,
            inventory_id: this.params.id,
        });
   }

    async _goToMainMenu() {
        await this.save();
        this.trigger('do-action', {
            action: 'stock_barcode.stock_barcode_action_main_menu',
            options: {
                clear_breadcrumbs: true,
            },
        });
    }

    get _uniqueVirtualId() {
        this._lastVirtualId = this._lastVirtualId || 0;
        return ++this._lastVirtualId;
    }

    _markLineAsDirty(line) {
        if (!this.linesToSave.includes(line.virtual_id)) {
            this.linesToSave.push(line.virtual_id);
        }
    }

    _getFieldToWrite() {
        return [
            'location_id',
            'prod_lot_id',
            'package_id',
            'partner_id',
            'first_count_qty',
            'second_count_qty',
            'inventory_id'
        ];
    }

    _getSaveCommand() {
        const commands = this._getSaveLineCommand();
        let field = 'line_ids';
        if (commands.length) {
            return {
                route: '/stock_barcode/save_barcode_data',
                params: {
                    model: this.params.model,
                    res_id: this.params.id,
                    write_field: field,
                    write_vals: commands,
                },
            };
        }
        return {};
    }

    _getSaveLineCommand() {
        const commands = [];
        const fields = this._getFieldToWrite();
        for (const virtualId of this.linesToSave) {
            const line = this.currentState.lines.find(l => l.virtual_id === virtualId);
            if (line.id) { // Update an existing line.
                const initialLine = this.initialState.lines.find(l => l.virtual_id === line.virtual_id);
                const changedValues = {};
                let somethingToSave = false;
                for (const field of fields) {
                    const fieldValue = line[field];
                    const initialValue = initialLine ? initialLine[field] : undefined;
                    if (fieldValue !== undefined && (
                        (['boolean', 'number', 'string'].includes(typeof fieldValue) && fieldValue !== initialValue) ||
                        (typeof fieldValue === 'object' && fieldValue.id !== initialValue.id)
                    )) {
                        changedValues[field] = this._fieldToValue(fieldValue);
                        somethingToSave = true;
                    }
                }
                if (somethingToSave) {
                    commands.push([1, line.id, changedValues]);
                }
            } else { // Create a new line.
                commands.push([0, 0, this._createCommandVals(line)]);
            }
        }
        return commands;
    }

    
    _groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone) {
        if(this.state === 'second_count') {
            return Object.assign(super._groupSublines(...arguments), {
                second_count_qty: qtyDone,
            });
        }
        return Object.assign(super._groupSublines(...arguments), {
            first_count_qty: qtyDone,
        });
    }

    _lineIsNotComplete(line) {
        /**
         * Check if the line is complete based on the current state.
         *
         * @param {object} line - the line object containing theoretical and count quantities
         * @return {boolean} whether the line is complete or not
         */
        if(this.state === 'second_count') {
            return line.theoretical_qty <= line.second_count_qty;
        }
        return line.theoretical_qty <= line.first_count_qty;
    }

    async _processPackage(barcodeData) {
        const { packageType, packageName } = barcodeData;
        let recPackage = barcodeData.package;
        this.lastScanned.packageId = false;
        if (!recPackage && !packageType && !packageName) {
            return; // No Package data to process.
        }
        // Scan a new package and/or a package type -> Create a new package with those parameters.
        const currentLine = this.selectedLine || this.lastScannedLine;
        if (currentLine && currentLine.package_id && packageType &&
            !recPackage && ! packageName &&
            currentLine.package_id.id !== packageType) {
            // Changes the package type for the scanned one.
            await this.orm.write('stock.quant.package', [currentLine.package_id.id], {
                package_type_id: packageType.id,
            });
            const message = sprintf(
                _t("Package type %s was correctly applied to the package %s"),
                packageType.name, currentLine.package_id.name
            );
            barcodeData.stopped = true;
            return this.notification.add(message, { type: 'success' });
        }
        if (!recPackage) {
            if (currentLine && !currentLine.package_id) {
                const valueList = {};
                if (packageName) {
                    valueList.name = packageName;
                }
                if (packageType) {
                    valueList.package_type_id = packageType.id;
                }
                const newPackageData = await this.orm.call(
                    'stock.quant.package',
                    'action_create_from_barcode',
                    [valueList]
                );
                this.cache.setCache(newPackageData);
                recPackage = newPackageData['stock.quant.package'][0];
            }
        }
        if (!recPackage && packageName) {
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id) {
                const newPackageData = await this.orm.call(
                    'stock.quant.package',
                    'action_create_from_barcode',
                    [{ name: packageName }]
                );
                this.cache.setCache(newPackageData);
                recPackage = newPackageData['stock.quant.package'][0];
            }
        }
        // if (!recPackage || (
        //     recPackage.location_id && recPackage.location_id != this.location.id
        // )) {
        //     return;
        // }
        // TODO: can check if quants already in cache to avoid to make a RPC if
        // there is all in it (or make the RPC only on missing quants).
        const res = await this.orm.call(
            'stock.quant',
            'get_stock_barcode_data_records',
            [recPackage.quant_ids]
        );
        const quants = res.records['stock.quant'];
        if (!quants.length) { // Empty package => Assigns it to the last scanned line.
            const currentLine = this.selectedLine || this.lastScannedLine;
            if (currentLine && !currentLine.package_id && !currentLine.result_package_id) {
                const fieldsParams = this._convertDataToFieldsParams({
                    resultPackage: recPackage,
                });
                await this.updateLine(currentLine, fieldsParams);
                barcodeData.stopped = true;
                this.selectedLineVirtualId = false;
                this.lastScanned.packageId = recPackage.id;
                this.trigger('update');
            }
            return;
        }
        this.cache.setCache(res.records);

        // Checks if the package is already scanned.
        // let alreadyExisting = 0;
        // for (const line of this.pageLines) {
        //     if (line.package_id && line.package_id.id === recPackage.id &&
        //         this.getQtyDone(line) > 0) {
        //         alreadyExisting++;
        //     }
        // }
        // if (alreadyExisting === quants.length) {
        //     barcodeData.error = _t("This package is already scanned.");
        //     return;
        // }
        // For each quants, creates or increments a barcode line.
        for (const quant of quants) {
            const product = this.cache.getRecord('product.product', quant.product_id);
            const searchLineParams = Object.assign({}, barcodeData, { product });
            const currentLine = this._findLine(searchLineParams);
            if (currentLine) { // Updates an existing line.
                const fieldsParams = this._convertDataToFieldsParams({
                    quantity: quant.quantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: recPackage,
                    // owner: barcodeData.owner,
                });
                await this.updateLine(currentLine, fieldsParams);
            } else { // Creates a new line.
                const fieldsParams = this._convertDataToFieldsParams({
                    product,
                    quantity: quant.quantity,
                    lot: quant.lot_id,
                    package: quant.package_id,
                    resultPackage: quant.package_id,
                    // owner: quant.owner_id,
                });
                const newLine = await this._createNewLine({ fieldsParams });
                newLine.first_count_qty = quant.quantity;
            }
        }
        barcodeData.stopped = true;
        this.selectedLineVirtualId = false;
        this.lastScanned.packageId = recPackage.id;
        this.trigger('update');
    }

    getEditedLineParams(line) {
        return { currentId: line.id };
    }

    _updateLineQty(line, args) {
        /**
        * Update the quantity of a line based on the provided arguments.
        *
        * @param {object} line - the line to be updated
        * @param {object} args - the arguments used to update the line
        * @return {void} 
        */
        if (args[this.field]) { // Increments inventory quantity.
            if (args.uom) {
                const productUOM = this.cache.getRecord('uom.uom', line.product_id.uom_id);
                if (args.uom.category_id !== productUOM.category_id) {
                    const message = sprintf(
                        _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the product's one (%s)."),
                        args.uom.name, productUOM.name
                    );
                    return this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'warning' });
                } else if (args.uom.id !== productUOM.id) {
                    args[this.field] = (args[this.field] / args.uom.factor) * productUOM.factor;
                }
            }
            line[this.field] += args[this.field];
            if (line.product_id.tracking === 'serial' && (line.lot_name || line.lot_id)) {
                line[this.field] = Math.max(0, Math.min(1, line[this.field]));
            }
        }
    }
    
    _updateLotName(line, lotName) {
        line.lot_name = lotName;
   }

    setLotData(data, pids) {
        for(const line of data){
            let product_id = line.product_id[0].toString()
            if(!this.productLots.hasOwnProperty(product_id)){
                this.productLots[product_id] = [line.name]
            } else {
                this.productLots[product_id].push(line.name)
            }
        }
    }

    _createLinesState() {
        const lines = [];
        const stockInventory = this.cache.getRecord(this.params.model, this.params.id);
        let stockInventoryLine = stockInventory.line_ids;
        for (const id of stockInventoryLine) {
            const lineData = this.cache.getRecord('stock.inventory.line', id);
            const prevLine = this.currentState && this.currentState.lines.find(l => l.id === id);
            const previousVirtualId = prevLine && prevLine.virtual_id;
            lineData.virtual_id = lineData.dummy_id || previousVirtualId || this._uniqueVirtualId;
            lineData.product_id = this.cache.getRecord('product.product', lineData.product_id);
            lineData.lot_id = lineData.lot_id && this.cache.getRecord('stock.lot', lineData.prod_lot_id);
            lineData.product_uom_id = this.cache.getRecord('uom.uom', lineData.product_uom_id);
            lineData.location_id = this.cache.getRecord('stock.location', lineData.location_id);
            // lineData.location_dest_id = this.cache.getRecord('stock.location', lineData.location_dest_id);
            lineData.package_id = lineData.package_id && this.cache.getRecord('stock.quant.package', lineData.package_id);
            lineData.owner_id = lineData.owner_id && this.cache.getRecord('res.partner', lineData.owner_id);
            lines.push(Object.assign({}, lineData));
        }
        return lines;
    }

    async displayBarcodeLines(lineId) {
        this.view = 'barcodeLines';
        if (lineId) { // If we pass a record id checks if the record still exist.
            const res = await this.orm.search(this.lineModel, [['id', '=', lineId]]);
            if (!res.length) { // The record was deleted, we remove the corresponding line.
                const lineIndex = this.currentState.lines.findIndex(l => l.id == lineId);
                this.currentState.lines.splice(lineIndex, 1);
            } else { // If it still exist, selects the record's line.
                const line = this.currentState.lines.find(line => line.id === lineId);
                if (line) {
                    line.virtual_id = line.id;
                    this.selectLine(line);
                }
                
            }
        }
        this.trigger('update');
    }

    _defineLocationId() {
        super._defineLocationId();
        if (this.prevScannedLocationId) {
            this.currentLocationId = this.prevScannedLocationId;
        }
    }

    // Getters

    get isTransfer() {
        return false;
    }

    get displayApplyCountButton() {
        if (this.state === 'done' || (this.state === 'confirm' && !this.inventoryManager)){
            return false
        }
        return true;
    }

    get displaySaveCountButton() {
        if (this.state === 'done'){
            return false
        }
        return true;
    }

    get recordIds() {
        return [this.params.id];
    }

    get user() {
        if(this.state === 'second_count') {
            return this.record.second_count_user_ids;
        }
        return this.record.first_count_user_ids;
    }

    get field() {
        if(this.state === 'second_count') {
            return 'second_count_qty'
        }
        return 'first_count_qty';
    }

    get state() {
        return this.record.state;
    }

    get isDone() {
        return this.record.state === 'done';
    }

    get isCancelled() {
        return this.record.state === 'cancel';
    }

    get isDraft() {
        return this.record.state === 'draft';
    }

    get selectedLine() {
        const selectedLine = this.selectedLineVirtualId && this.currentState.lines.find(
            l => (l.dummy_id || l.virtual_id) === this.selectedLineVirtualId
        );
        return selectedLine;
    }

    get canBeProcessed() {
        // let canBeProcessed = !['draft', 'cancel', 'done'].includes(this.record.state) && !this.isUserAllowed;
        return true;
    }

    get canCreateNewLot() {
        return this.setLot;
    }

    get isUserAllowed() {
        if (!this.user.includes(session.uid)) {
            return true;
        }
        return false;
    }

    get highlightValidateButton() {
        if (this.state === 'confirm'){
            return true;
        } else {
            return false
        }
        
    }


    get displaySettings () {
        return true;
    }

    get groupedLines() {
        if (!this.groups.group_production_lot) {
            return this._sortLine(this.pageLines);
        }

        const lines = [...this.pageLines];
        const groupedLinesByKey = {};
        for (let index = lines.length - 1; index >= 0; index--) {
            const line = lines[index];
            if (line.product_id.tracking === 'none' || line.lines || line.location_id === this.location.id) {
                // Don't try to group this line if it's not tracked or already grouped.
                continue;
            }
            const key = this.groupKey(line);
            if (!groupedLinesByKey[key]) {
                groupedLinesByKey[key] = [];
            }
            groupedLinesByKey[key].push(...lines.splice(index, 1));
        }
        for (const [key, sublines] of Object.entries(groupedLinesByKey)) {
            if (sublines.length === 1) {
                lines.push(...sublines);
                continue;
            }
            const ids = [];
            const virtual_ids = [];
            let [qtyDemand, qtyDone] = [0, 0];
            var lineLocation = false;
            for (const subline of sublines) {
                ids.push(subline.id);
                virtual_ids.push(subline.virtual_id);
                qtyDemand += this.getQtyDemand(subline);
                qtyDone += this.getQtyDone(subline);
                if (this.location.id === subline.location_id) {
                    lineLocation = subline.location_id;
                }
            }
            const groupedLine = this._groupSublines(sublines, ids, virtual_ids, qtyDemand, qtyDone);
            if (lineLocation) {
                groupedLine.location_id = lineLocation;
            }
            lines.push(groupedLine);
        }
        // Before to return the line, we sort them to have new lines always on
        // top and complete lines always on the bottom.
        return this._sortLine(lines);
    }

    _getModelRecord() {
        return this.cache.getRecord(this.params.model, this.params.id);
    }

    _getName() {
        return this.cache.getRecord(this.params.model, this.params.id).name;
    }

    _defaultLocation() {
        return this.cache.getRecord('stock.location', this.record.location_id);
    }

    _defaultDestLocation() {
        return undefined;
    }

    getQtyDone(line) {
        return line[this.field];
    }

    getQtyDemand(line) {
        return false;
    }

    async saveCount() {
        await this.save();
        this.notification.add(_t("The count sheet has been saved."), { type: 'success' });
        this.trigger('history-back');
    }

    get printButtons() {
        return [{
            name: _t("Print Inventory"),
            class: 'o_print_inventory',
            method: 'action_print_inventory',
        }];
    }

    async print(action, method) {
        await this.save();
        const options = this._getPrintOptions();
        if (options.warning) {
            return this.notification.add(options.warning, { type: 'warning' });
        }
        if (!action && method) {
            action = await this.orm.call(
                this.params.model,
                method,
                [[this.params.id]]
            );
        }
        this.trigger('do-action', { action, options });
    }


    lineIsFaulty(line) {
        return false;
    }

    get location() {
        if (this.lastScanned.sourceLocation) { // Get last scanned location.
            return this.cache.getRecord('stock.location', this.lastScanned.sourceLocation.id);
        }
        // Get last defined source location (if applicable) or the default location.
        return this._currentLocation || this._defaultLocation();
    }

    set location(location) {
        this._currentLocation = location;
        this.lastScanned.sourceLocation = location;
    }

    async changeSourceLocation(id) {
        const currentPage = this.pages[this.pageIndex];
        this.currentLocationId = id;
        currentPage.sourceLocationId = id;
        this.prevScannedLocationId = id;
        this._sortLine(this.pageLines);
        if (this.pageLines.length) {
            this.selectLine(this.pageLines[0]);
        }
    }

    _setLocationFromBarcode(result, location) {
        if (this._checkLocation(location.id)) {
            result.location = location;
        } else {
            result.noLocation = true;
        }
        return result;
    }

    _checkLocation(locationId) {
        let childLocations = this.locationList && this.locationList.map(loc => loc.id);
        if(childLocations.includes(locationId)) {
            return true;
        }
        return false;
    }

    _findLine(barcodeData) {
        let foundLine = false;
        const {lot, lotName, product} = barcodeData;
        const quantPackage = barcodeData.package;
        const dataLotName = lotName || (lot && lot.name) || false;
        for (const line of this.pageLines) {
            const lineLotName = line.lot_name || (line.lot_id && line.lot_id.name) || false;
            if (line.product_id.id !== product.id) {
                continue; // Not the same product.
            }
            if (quantPackage && (!line.package_id || line.package_id.id !== quantPackage.id)) {
                continue; // Not the expected package.
            }
            if (dataLotName && lineLotName && dataLotName !== lineLotName && !this._canOverrideTrackingNumber(line)) {
                continue; // Not the same lot.
            }
            if (dataLotName && line.id && !line.lot_id && this.params.model === "stock.inventory.line") {
                continue; // Matches an existing quant without lot_id but this field can't be updated
            }
            if (line.product_id.tracking === 'serial') {
                if (this.getQtyDone(line) >= 1 && lineLotName) {
                    continue; // Line tracked by serial numbers with quantity & SN.
                } else if (dataLotName && this.getQtyDone(line) > 1) {
                    continue; // Can't add a SN on a line where multiple qty. was previously added.
                }
            }
            if ((
                    !dataLotName || !lineLotName || dataLotName !== lineLotName
                ) && (
                    line.qty_done && line.qty_done >= line.reserved_uom_qty &&
                    line.id && line.virtual_id != this.selectedLine.virtual_id
            )) {
                continue;
            }
            if (this._lineIsNotComplete(line) && this.lineCanBeTakenFromTheCurrentLocation(line)) {
                // Found a uncompleted compatible line, stop searching if it has the same location
                // than the scanned one (or if no location was scanned).
                foundLine = line;
                if (this.tracking === 'none' || !dataLotName || dataLotName === lineLotName) {
                    break;
                }
            }
            // The line matches but there could be a better candidate, so keep searching.
            // If multiple lines can match, prioritises the one at the right location (if a location
            // source was previously selected) or the selected one if relevant.
            const currentLocationId = this.lastScanned.sourceLocation && this.lastScanned.sourceLocation.id;
            if (this.selectedLine && this.selectedLine.virtual_id === line.virtual_id && (
                !currentLocationId || !foundLine || foundLine.location_id.id != currentLocationId)) {
                foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
            } else if (!foundLine || (currentLocationId &&
                       foundLine.location_id.id != currentLocationId &&
                       line.location_id.id == currentLocationId)) {
                foundLine = this.lineCanBeTakenFromTheCurrentLocation(line) ? line : foundLine;
            }
        }
        return foundLine;
    }

    isblind(line) {
        if (this.record.blind_count) {
            return false
        } else {
            return true
        }
    }

    _sortingMethod(l1, l2) {
        // New lines always on top.
        if (!l1.id && l2.id) {
            return -1;
        } else if (l1.id && !l2.id) {
            return 1;
        } else if (l1.id && l2.id) {
            // sort by display name of location and move lines at top
            const location1 = l1.id && this.cache.getRecord('stock.inventory.line', l1.id);
            const location2 = l2.id && this.cache.getRecord("stock.inventory.line", l2.id);
            const currLocation = this.location || false;
            // const l1IsPresent = location1 && currLocation && currLocation === location1.id
            // const l2IsPresent = location2 && currLocation && currLocation === location2.id
            // if (l1IsPresent && !l2IsPresent) {
            //     return -1;
            // } else if (!l1IsPresent && l2IsPresent) {
            //     return 1;
            // }

            if (location1.sort_sequence < location2.sort_sequence) {
                return -1;
            } else if (location1.sort_sequence > location2.sort_sequence) {
                return 1;
            }

        //     // Sort by display name of product.
        //     const product1 = l1.product_id.display_name;
        //     const product2 = l2.product_id.display_name;
        //     if (product1 < product2) {
        //         return -1;
        //     } else if (product1 > product2) {
        //         return 1;
        //     }

        //     // Sort by lot_name if possible
        //     const lot1 = l1.lot_id && l1.lot_id.name || '';
        //     const lot2 = l2.lot_id && l2.lot_id.name || '';
        //     if (lot1 < lot2) {
        //         return -1;
        //     } else if (lot1 > lot2) {
        //         return 1;
        //     }

        //     // Sort by picking name.
        //     const picking1 = l1.picking_id && l1.picking_id.name || '';
        //     const picking2 = l2.picking_id && l2.picking_id.name || '';
        //     if (picking1 < picking2) {
        //         return -1;
        //     } else if (picking1 > picking2) {
        //         return 1;
        //     }

        //     if (l1.id < l2.id) {
        //         return -1;
        //     } else if (l1.id > l2.id) {
        //         return 1;
        //     }
        // }
        // // Sort by id and/or virtual_id (creation of the line).
        // if (l1.virtual_id > l2.virtual_id) {
        //     return -1;
        // } else if (l1.virtual_id < l2.virtual_id) {
        //     return 1;
        }
        return 0;
    }

    _groupLinesByPage(state) {
        const pages = [];
        let lines = state.lines;
        if(lines.length) {
            const page = {
                index: pages.length,
                lines,
                sourceLocationId: lines[0].location_id,
                destinationLocationId: lines[0].location_dest_id,
            };
            pages.push(page);
        }
        if (pages.length === 0) { // If no pages, creates a default one.
            const page = {
                index: pages.length,
                lines: [],
                sourceLocationId: this.currentLocationId,
                destinationLocationId: this.currentLocationId,
            };
            pages.push(page);
        }
        this.pages = pages;
    }

    saveSheetData (field, value) {
        /**
         * Save sheet data to the server.
         *
         * @param {type} field - description of field parameter
         * @param {type} value - description of value parameter
         * @return {type} description of the return value
         */
        let params = {
                    model: this.params.model,
                    res_id: this.params.id,
                    write_field: field,
                    write_vals: value,
                }
        this.rpc('/stock_barcode/save_picking_barcode_data', params)
    }

    async _processBarcode(barcode) {
        /**
         * Process the barcode and update the line if needed.
         *
         * @param {string} barcode - the barcode to be processed
         * @return {Promise<void>} - a promise that resolves when the barcode is processed
         */
        let barcodeData = {};
        let currentLine = false;
        // Creates a filter if needed, which can help to get the right record
        // when multiple records have the same model and barcode.
        const filters = {};
        if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
            filters['stock.lot'] = {
                product_id: this.selectedLine.product_id.id,
            };
        }
        try {
            barcodeData = await this._parseBarcode(barcode, filters);
            if (!barcodeData.match && filters['stock.lot'] &&
                !this.canCreateNewLot && this.useExistingLots) {
                // Retry to parse the barcode without filters in case it matches an existing
                // record that can't be found because of the filters
                const lot = await this.cache.getRecordByBarcode(barcode, 'stock.lot');
                if (lot) {
                    Object.assign(barcodeData, { lot, match: true });
                }
            }
        } catch (parseErrorMessage) {
            barcodeData.error = parseErrorMessage;
        }

        // Process each data in order, starting with non-ambiguous data type.
        if (barcodeData.action) { // As action is always a single data, call it and do nothing else.
            return await barcodeData.action();
        }
        // Depending of the configuration, the user can be forced to scan a specific barcode type.
        const check = this._checkBarcode(barcodeData);
        if (check.error) {
            return this.notification.add(check.message, { title: check.title, type: "danger" });
        }

        if (barcodeData.packaging) {
            barcodeData.product = this.cache.getRecord('product.product', barcodeData.packaging.product_id);
            barcodeData.quantity = ("quantity" in barcodeData ? barcodeData.quantity : 1) * barcodeData.packaging.qty;
            barcodeData.uom = this.cache.getRecord('uom.uom', barcodeData.product.uom_id);
        }

        if (barcodeData.product) { // Remembers the product if a (packaging) product was scanned.
            this.lastScanned.product = barcodeData.product;
        }

        if (barcodeData.lot && !barcodeData.product) {
            barcodeData.product = this.cache.getRecord('product.product', barcodeData.lot.product_id);
        }

        await this._processLocation(barcodeData);
        await this._processPackage(barcodeData);
        if (barcodeData.stopped) {
            // TODO: Sometime we want to stop here instead of keeping doing thing,
            // but it's a little hacky, it could be better to don't have to do that.
            return;
        }

        if (barcodeData.weight) { // Convert the weight into quantity.
            barcodeData.quantity = barcodeData.weight.value;
        }

        // If no product found, take the one from last scanned line if possible.
        if (!barcodeData.product) {
            if (barcodeData.quantity) {
                currentLine = this.selectedLine || this.lastScannedLine;
            } else if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
                currentLine = this.selectedLine;
            } else if (this.lastScannedLine && this.lastScannedLine.product_id.tracking !== 'none') {
                currentLine = this.lastScannedLine;
            }
            if (currentLine) { // If we can, get the product from the previous line.
                const previousProduct = currentLine.product_id;
                // If the current product is tracked and the barcode doesn't fit
                // anything else, we assume it's a new lot/serial number.
                if (previousProduct.tracking !== 'none' &&
                    !barcodeData.match && this.canCreateNewLot) {
                    barcodeData.lotName = barcode;
                    barcodeData.product = previousProduct;
                }
                if (barcodeData.lot || barcodeData.lotName ||
                    barcodeData.quantity) {
                    barcodeData.product = previousProduct;
                }
            }
        }
        // if (barcodeData.package && !barcodeData.product) {
        //     const res = await this.orm.call(
        //         'stock.quant',
        //         'get_stock_barcode_data_records',
        //         [barcodeData.package.quant_ids]
        //     );
        //     const quants = res.records['stock.quant'];
        //     for (const quant of quants) {
        //         const product = await this.orm.call(
        //             'product.product',
        //             'search_read',
        //             [[['id', '=', quant.product_id]]]
        //         );
        //         const location = await this.orm.call(
        //             'stock.location',
        //             'search_read',
        //             [[['id', '=', quant.location_id]]]
        //         );
        //         const searchLineParams = Object.assign({}, barcodeData, { product : product[0] });
        //         const currentLine = this._findLine(searchLineParams);
        //         if (currentLine) { // Updates an existing line.
        //             const fieldsParams = this._convertDataToFieldsParams({
        //                 product: product[0],
        //                 location_id: location[0],
        //                 quantity: quant.quantity,
        //                 lot: quant.prod_lot_id,
        //                 package: quant.package_id,
        //                 resultPackage: quant.package_id,
        //                 // owner: quant.owner_id,
        //             });
        //             await this.updateLine(currentLine, fieldsParams);
        //             this.location.display_name = location[0].display_name;
        //             if (currentLine) {
        //                 this._selectLine(currentLine);
        //             }
        //         } else { // Creates a new line.
        //             const fieldsParams = this._convertDataToFieldsParams({
        //                 product: product[0],
        //                 location_id: location[0],
        //                 quantity: quant.quantity,
        //                 lot: quant.prod_lot_id,
        //                 package: quant.package_id,
        //                 resultPackage: quant.package_id,
        //                 // owner: quant.owner_id,
        //             });
        //             const newLine = await this._createNewLine({ fieldsParams });
        //             newLine.first_count_qty = quant.quantity;
        //             this.location.display_name = location[0].display_name;
        //             if (newLine) {
        //                 this._selectLine(newLine);
        //             }
        //         }
        //     }
        //     this.trigger('update');
        //     return;

        //     // var packageId = this.cache.getRecord('stock.quant', barcodeData.package.quant_ids[0]);
        //     // console.log("packageId", packageId)
        //     // const fieldsParams = this._convertDataToFieldsParams({
        //     //     product: packageId.product_id,
        //     //     quantity: packageId.quantity,
        //     //     // lot: packageId.lot_id,
        //     //     package: packageId.package_id,
        //     //     location_id: packageId.location_id
        //     // });
        //     // const newLine = await this._createNewLine({ fieldsParams });
        //     // if (newLine) {
        //     //     this._selectLine(newLine);
        //     // }
        //     // this.trigger('update');
        //     // return;
        //     // break;
        // } else {
            const {product} = barcodeData;
            if (!product) { // Product is mandatory, if no product, raises a warning.
                if (!barcodeData.error) {
                    if (this.groups.group_tracking_lot) {
                        barcodeData.error = _t("You are expected to scan one or more products or a package available at the picking location");
                    } else {
                        barcodeData.error = _t("You are expected to scan one or more products.");
                    }
                }
                return this.notification.add(barcodeData.error, { type: 'danger' });
            } else if (barcodeData.lot && barcodeData.lot.product_id !== product.id) {
                delete barcodeData.lot; // The product was scanned alongside another product's lot.
            }
            if (barcodeData.weight) { // the encoded weight is based on the product's UoM
                barcodeData.uom = this.cache.getRecord('uom.uom', product.uom_id);
            }

            // Searches and selects a line if needed.
            if (!currentLine || this._shouldSearchForAnotherLine(currentLine, barcodeData)) {
                currentLine = this._findLine(barcodeData);
            }

            // Default quantity set to 1 by default if the product is untracked or
            // if there is a scanned tracking number.
            if (product.tracking === 'none' || barcodeData.lot || barcodeData.lotName || this._incrementTrackedLine()) {
                const hasUnassignedQty = currentLine && currentLine.qty_done && !currentLine.lot_id && !currentLine.lot_name;
                const isTrackingNumber = barcodeData.lot || barcodeData.lotName;
                const defaultQuantity = isTrackingNumber && hasUnassignedQty ? 0 : 1;
                barcodeData.quantity = barcodeData.quantity || defaultQuantity;
                if (product.tracking === 'serial' && barcodeData.quantity > 1 && (barcodeData.lot || barcodeData.lotName)) {
                    barcodeData.quantity = 1;
                    this.notification.add(
                        _t(`A product tracked by serial numbers can't have multiple quantities for the same serial number.`),
                        { type: 'danger' }
                    );
                }
            }

            if ((barcodeData.lotName || barcodeData.lot) && product) {
                const lotName = barcodeData.lotName || barcodeData.lot.name;
                for (const line of this.currentState.lines) {
                    if (line.product_id.tracking === 'serial' && this.getQtyDone(line) !== 0 &&
                        ((line.lot_id && line.lot_id.name) || line.lot_name) === lotName) {
                        return this.notification.add(
                            _t("The scanned serial number is already used."),
                            { type: 'danger' }
                        );
                    }
                }
                // Prefills `owner_id` and `package_id` if possible.
                const prefilledOwner = (!currentLine || (currentLine && !currentLine.owner_id)) && this.groups.group_tracking_owner && !barcodeData.owner;
                const prefilledPackage = (!currentLine || (currentLine && !currentLine.package_id)) && this.groups.group_tracking_lot && !barcodeData.package;
                if (this.useExistingLots && (prefilledOwner || prefilledPackage)) {
                    const lotId = (barcodeData.lot && barcodeData.lot.id) || (currentLine && currentLine.lot_id && currentLine.lot_id.id) || false;
                    const res = await this.orm.call(
                        'product.product',
                        'prefilled_owner_package_stock_barcode',
                        [product.id],
                        {
                            lot_id: lotId,
                            lot_name: (!lotId && barcodeData.lotName) || false,
                        }
                    );
                    this.cache.setCache(res.records);
                    if (prefilledPackage && res.quant && res.quant.package_id) {
                        barcodeData.package = this.cache.getRecord('stock.quant.package', res.quant.package_id);
                    }
                    if (prefilledOwner && res.quant && res.quant.owner_id) {
                        barcodeData.owner = this.cache.getRecord('res.partner', res.quant.owner_id);
                    }
                }
            }

            // Updates or creates a line based on barcode data.
            if (currentLine) { // If line found, can it be incremented ?
                let exceedingQuantity = 0;
                if (product.tracking !== 'serial' && barcodeData.uom && barcodeData.uom.category_id == currentLine.product_uom_id.category_id) {
                    // convert to current line's uom
                    barcodeData.quantity = (barcodeData.quantity / barcodeData.uom.factor) * currentLine.product_uom_id.factor;
                    barcodeData.uom = currentLine.product_uom_id;
                }
                // Checks the quantity doesn't exceed the line's remaining quantity.
                if (currentLine.reserved_uom_qty && product.tracking === 'none') {
                    const remainingQty = currentLine.reserved_uom_qty - currentLine.qty_done;
                    if (barcodeData.quantity > remainingQty) {
                        // In this case, lowers the increment quantity and keeps
                        // the excess quantity to create a new line.
                        exceedingQuantity = barcodeData.quantity - remainingQty;
                        barcodeData.quantity = remainingQty;
                    }
                }
                if (barcodeData.quantity > 0 || barcodeData.lot || barcodeData.lotName) {
                    const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                    if (barcodeData.uom) {
                        fieldsParams.uom = barcodeData.uom;
                    }
                    await this.updateLine(currentLine, fieldsParams);
                }
                if (exceedingQuantity) { // Creates a new line for the excess quantity.
                    barcodeData.quantity = exceedingQuantity;
                    const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                    if (barcodeData.uom) {
                        fieldsParams.uom = barcodeData.uom;
                    }
                    currentLine = await this._createNewLine({
                        copyOf: currentLine,
                        fieldsParams,
                    });
                }
            } else { // No line found, so creates a new one.
                const fieldsParams = this._convertDataToFieldsParams(barcodeData);
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                currentLine = await this.createNewLine({fieldsParams});
            }

            // And finally, if the scanned barcode modified a line, selects this line.
            if (currentLine) {
                this._selectLine(currentLine);
            }
            this.trigger('update');
        // }
    }

    async updateLine(line, args) {
        /**
         * Updates a line with the provided arguments.
         *
         * @param {type} line - the line to be updated
         * @param {type} args - the arguments used to update the line
         * @return {void} 
         */
        let { location_id, lot_id, owner_id, package_id } = args;
        if (!line) {
            throw new Error('No line found');
        }
        if (!line.product_id && args.product_id) {
            line.product_id = args.product_id;
            line.product_uom_id = this.cache.getRecord('uom.uom', args.product_id.uom_id);
        }
        if (location_id) {
            if (typeof location_id === 'number') {
                location_id = this.cache.getRecord('stock.location', args.location_id);
            }
            line.location_id = location_id;
        }
        if (!location_id && this.lastScanned.sourceLocation) {
            line.location_id = this.lastScanned.sourceLocation;
        }
        if (lot_id) {
            if (typeof lot_id === 'number') {
                lot_id = this.cache.getRecord('stock.lot', args.lot_id);
            }
            line.lot_id = lot_id;
        }
        if (owner_id) {
            if (typeof owner_id === 'number') {
                owner_id = this.cache.getRecord('res.partner', args.owner_id);
            }
            line.owner_id = owner_id;
        }
        if (package_id) {
            if (typeof package_id === 'number') {
                package_id = this.cache.getRecord('stock.quant.package', args.package_id);
            }
            line.package_id = package_id;
        }
        if (args.lot_name) {
            await this.updateLotName(line, args.lot_name);
        }
        this._updateLineQty(line, args);
        this._markLineAsDirty(line);
    }

   async validate() {
        /**
        * Asynchronously validates something.
        *
        * @return {Promise} The result of the validation.
        */

        if (this.validateMethod == 'action_validate') {
            const wizard = await this.orm.call("pin.message.wizard", "create", [{}]);
            this.dialogService.add(FormViewDialog, {
                title: 'Authentication Pin',
                resModel: 'pin.message.wizard',
                resId: wizard,
                context: {
                    form_view_ref: 'bista_inventory_enhancement.pin_message_wizard_barcode',
                    active_id: this.params.id,
                    active_model: this.params.model,
                    
                    },
                onRecordSaved: () => this.applyManagerPin(wizard)
                }, 
            )
        } else { 
            if (this.validateMethod == 'action_submit') {
                this.dialogService.add(ConfirmationDialog, {
                    body: _t("Are you sure you want to Submit?"),
                    confirm: async () => {
                        const action = await this.orm.call(
                            this.params.model,  
                            this.validateMethod,
                            [this.recordIds],
                            { context: { display_detailed_backorder: true } },
                        );
                        const options = {
                            on_close: ev => this._closeValidate(ev)
                        };
                        await this.save();
                        if (action && action.res_model) {
                            return this.trigger('do-action', { action, options });
                        }
                        return options.on_close();
                    },
                    cancel: () => {},
                });
            }
            
            
        }
    }

    async applyManagerPin(wizard) {
        var result = await this.orm.call(
            'pin.message.wizard',
            'apply_manager_pin',
            [wizard],
            { context: { active_id: this.params.id,
                active_model: this.params.model, from_barcode: true} },
        );
        if (result){
            this.notification.add(_t(result), { type: 'warning' });
        } else {
            this.notification.add(this.validateMessage, { type: 'success' });
            this.trigger('history-back');
            // window.location.reload();
        }
    }
}
