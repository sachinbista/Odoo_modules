/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import {_t, _lt} from "web.core";
import { sprintf } from '@web/core/utils/strings';
import { patch } from 'web.utils';

patch(BarcodePickingModel.prototype, "customBarcodePickingModel", {
    constructor(params) {
        this._super(...arguments);
    },

    get barcodeInfo() {
        if (this.isCancelled || this.isDone) {
            return {
                class: this.isDone ? 'picking_already_done' : 'picking_already_cancelled',
                message: this.isDone ?
                    _t("This picking is already done") :
                    _t("This picking is cancelled"),
                warning: true,
            };
        }
        let barcodeInfo = this._super(...arguments);
        
        // Takes the parent line if the current line is part of a group.
        const line = this._getParentLine(this.selectedLine) || this.selectedLine;
        // Defines some messages who can appear in multiple cases.
        const infos = {
            scanScrLoc: {
                message: this.considerPackageLines && !this.config.restrict_scan_source_location ?
                    _lt("Scan the source location or a package") :
                    _lt("Scan the source location"),
                class: 'scan_src',
                icon: 'sign-out',
            },
            scanDestLoc: {
                message: _lt("Scan the destination location"),
                class: 'scan_dest',
                icon: 'sign-in',
            },
            scanProductOrDestLoc: {
                message: this.considerPackageLines ?
                    _lt("Scan a product, a package or the destination location.") :
                    _lt("Scan a product or the destination location."),
                class: 'scan_product_or_dest',
            },
            scanPackage: {
                message: this._getScanPackageMessage(line),
                class: "scan_package",
                icon: 'archive',
            },
            scanLot: {
                message: _lt("Scan a lot number"),
                class: "scan_lot",
                icon: "barcode",
            },
            scanSerial: {
                message: _lt("Scan a serial number"),
                class: "scan_serial",
                icon: "barcode",
            },
            // Changed message to add scan source location
            pressValidateBtn: {
                message: _lt("Press Validate or scan another product or source location"),
                class: 'scan_validate',
                icon: 'check-square',
            },
        };
        
        if (!line && this._moveEntirePackage()) { // About package lines.
            const packageLine = this.selectedPackageLine;
            if (packageLine) {
                if (this._lineIsComplete(packageLine)) {
                    if (this.config.restrict_scan_source_location && !this.lastScanned.sourceLocation) {
                        return infos.scanScrLoc;
                    } else if (this.config.restrict_scan_dest_location != 'no' && !this.lastScanned.destLocation) {
                        return this.config.restrict_scan_dest_location == 'mandatory' ?
                            infos.scanDestLoc :
                            infos.scanProductOrDestLoc;
                    } else if (this.pageIsDone) {
                        return infos.pressValidateBtn;
                    } else {
                        barcodeInfo.message = _lt("Scan a product or another package");
                        barcodeInfo.class = 'scan_product_or_package';
                    }
                } else {
                    barcodeInfo.message = sprintf(_t("Scan the package %s"), packageLine.result_package_id.name);
                    barcodeInfo.icon = 'archive';
                }
                return barcodeInfo;
            } else if (this.considerPackageLines && barcodeInfo.class == 'scan_product') {
                barcodeInfo.message = _lt("Scan a product or a package");
                barcodeInfo.class = 'scan_product_or_package';
            }
        }
        if (this.messageType === "scan_product" && !line &&
            this.config.restrict_scan_source_location && this.lastScanned.sourceLocation) {
            barcodeInfo.message = sprintf(
                _lt("Scan a product from %s"),
                this.lastScanned.sourceLocation.display_name);
            // Location was not showing after the first line was scanned therefore returned to scan source location
            return barcodeInfo
        }

        // About source location.
        if (this.displaySourceLocation) {
            if (!this.lastScanned.sourceLocation && !this.pageIsDone) {
                return infos.scanScrLoc;
            } else if (this.lastScanned.sourceLocation && this.lastScanned.destLocation == 'no' &&
                       line && this._lineIsComplete(line)) {
                if (this.config.restrict_put_in_pack === 'mandatory' && !line.result_package_id) {
                    return {
                        message: _lt("Scan a package"),
                        class: 'scan_package',
                        icon: 'archive',
                    };
                }
                return infos.scanScrLoc;
            }
        }

        if (!line) {
            if (this.pageIsDone) { // All is done, says to validate the transfer.
                return infos.pressValidateBtn;
            } else if (this.config.lines_need_to_be_packed) {
                const lines = new Array(...this.pageLines, ...this.packageLines);
                if (lines.every(line => !this._lineIsNotComplete(line)) &&
                    lines.some(line => this._lineNeedsToBePacked(line))) {
                        return infos.scanPackage;
                }
            }
            return barcodeInfo;
        }
        const product = line.product_id;

        // About tracking numbers.
        if (product.tracking !== 'none') {
            const isLot = product.tracking === "lot";
            if (this.getQtyDemand(line) && (line.lot_id || line.lot_name)) { // Reserved.
                if (this.getQtyDone(line) === 0) { // Lot/SN not scanned yet.
                    return isLot ? infos.scanLot : infos.scanSerial;
                } else if (this.getQtyDone(line) < this.getQtyDemand(line)) { // Lot/SN scanned but not enough.
                    barcodeInfo = isLot ? infos.scanLot : infos.scanSerial;
                    barcodeInfo.message = isLot ?
                        _t("Scan more lot numbers") :
                        _t("Scan another serial number");
                    return barcodeInfo;
                }
            } else if (!(line.lot_id || line.lot_name)) { // Not reserved.
                return isLot ? infos.scanLot : infos.scanSerial;
            }
        }

        // About package.
        if (this._lineNeedsToBePacked(line)) {
            if (this._lineIsComplete(line)) {
                return infos.scanPackage;
            }
            if (product.tracking == 'serial') {
                barcodeInfo.message = _t("Scan a serial number or a package");
            } else if (product.tracking == 'lot') {
                barcodeInfo.message = line.qty_done == 0 ?
                    _t("Scan a lot number") :
                    _t("Scan more lot numbers or a package");
                    barcodeInfo.class = "scan_lot";
            } else {
                barcodeInfo.message = _t("Scan more products or a package");
            }
            return barcodeInfo;
        }

        if (this.pageIsDone) {
            Object.assign(barcodeInfo, infos.pressValidateBtn);
        }

        // About destination location.
        const lineWaitingPackage = this.groups.group_tracking_lot && this.config.restrict_put_in_pack != "no" && !line.result_package_id;
        if (this.config.restrict_scan_dest_location != 'no' && line.qty_done) {
            if (this.pageIsDone) {
                if (this.lastScanned.destLocation) {
                    return infos.pressValidateBtn;
                } else {
                    return this.config.restrict_scan_dest_location == 'mandatory' && this._lineIsComplete(line) ?
                        infos.scanDestLoc :
                        infos.scanProductOrDestLoc;
                }
            } else if (this._lineIsComplete(line)) {
                if (lineWaitingPackage) {
                    barcodeInfo.message = this.config.restrict_scan_dest_location == 'mandatory' ?
                        _t("Scan a package or the destination location") :
                        _t("Scan a package, the destination location or another product");
                } else {
                    return this.config.restrict_scan_dest_location == 'mandatory' ?
                        infos.scanDestLoc :
                        infos.scanProductOrDestLoc;
                }
            } else {
                if (product.tracking == 'serial') {
                    barcodeInfo.message = lineWaitingPackage ?
                        _t("Scan a serial number or a package then the destination location") :
                        _t("Scan a serial number then the destination location");
                } else if (product.tracking == 'lot') {
                    barcodeInfo.message = lineWaitingPackage ?
                        _t("Scan a lot number or a packages then the destination location") :
                        _t("Scan a lot number then the destination location");
                } else {
                    barcodeInfo.message = lineWaitingPackage ?
                        _t("Scan a product, a package or the destination location") :
                        _t("Scan a product then the destination location");
                }
            }
        }

        return barcodeInfo;
    },

    _checkBarcode(barcodeData) {
        const check = { title: _lt("Not the expected scan") };
        const { location, lot, product, destLocation, packageType } = barcodeData;
        const resultPackage = barcodeData.package;
        const packageWithQuant = (barcodeData.package && barcodeData.package.quant_ids || []).length;

        if (this.config.restrict_scan_source_location && !barcodeData.location) {
            // Special case where the user can not scan a destination but a source was already scanned.
            // That means what is supposed to be a destination is in this case a source.
            if (this.lastScanned.sourceLocation && barcodeData.destLocation &&
                this.config.restrict_scan_dest_location == 'no') {
                barcodeData.location = barcodeData.destLocation;
                delete barcodeData.destLocation;
            }
            // Special case where the source is mandatory and the app's waiting for but none was
            // scanned, get the previous scanned one if possible.
            if (!this.lastScanned.sourceLocation && this._currentLocation) {
                this.lastScanned.sourceLocation = this._currentLocation;
            }
        }

        if (this.config.restrict_scan_source_location && !this._currentLocation && !this.selectedLine) { // Source Location.
            if (location) {
                this.location = location;
            } else {
                check.title = _t("Mandatory Source Location");
                check.message = sprintf(
                    _t("You are supposed to scan %s or another source location"),
                    this.location.display_name,
                );
            }
        } else if (this.config.restrict_scan_product && // Restriction on product.
            !(product || packageWithQuant || this.selectedLine) && // A product/package was scanned.
            !(this.config.restrict_scan_source_location && location && !this.selectedLine) // Maybe the user scanned the wrong location and trying to scan the right one
        ) {
            check.message = lot ?
                _t("Scan a product before scanning a tracking number") :
                _t("You must scan a product");
        } else if (this.config.restrict_put_in_pack == 'mandatory' && !(resultPackage || packageType) &&
                   this.selectedLine && !this.qty_done && !this.selectedLine.result_package_id &&
                   ((product && product.id != this.selectedLine.product_id.id) || location || destLocation)) { // Package.
            check.message = _t("You must scan a package or put in pack");
        // Avoid updating the destination location if it is the same as the source location 
        } else if (this.config.restrict_scan_dest_location == 'mandatory' && !this.lastScanned.destLocation) { // Destination Location.
            if (destLocation && this.lastScanned && this.lastScanned.sourceLocation.id !== destLocation.id) {
                this.lastScanned.destLocation = destLocation;
            } else if (product && this.selectedLine && this.selectedLine.product_id.id != product.id) {
                // Cannot scan another product before a destination was scanned.
                check.title = _t("Mandatory Destination Location");
                check.message = sprintf(
                    _t("Please scan destination location for %s before scanning other product"),
                    this.selectedLine.product_id.display_name
                );
            // Raise warning if destination location is same as source location
            } else if (destLocation && this.lastScanned && this.lastScanned.sourceLocation.id === destLocation.id) {
                check.title = _t("Same Destination Location");
                check.message = sprintf(_t("Source Location and Destination Location cannot be Same")
                );
            }
        }
        check.error = Boolean(check.message);
        return check;
    },

    _updateLineQty(line, args) {
        if (line.product_id.tracking === 'serial' && line.qty_done > 0 && (this.record.use_create_lots || this.record.use_existing_lots)) {
            return;
        }
        if (args.qty_done) {
            if (args.uom) {
                // An UoM was passed alongside the quantity, needs to check it's
                // compatible with the product's UoM.
                const lineUOM = line.product_uom_id;
                if (args.uom.category_id !== lineUOM.category_id) {
                    // Not the same UoM's category -> Can't be converted.
                    const message = sprintf(
                        _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the line's one (%s)."),
                        args.uom.name, lineUOM.name
                    );
                    return this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'danger' });
                } else if (args.uom.id !== lineUOM.id) {
                    // Compatible but not the same UoM => Need a conversion.
                    args.qty_done = (args.qty_done / args.uom.factor) * lineUOM.factor;
                    args.uom = lineUOM;
                }
            }
            
            
            line.qty_done += args.qty_done;
            this._checkAndUpdateLineQuantity(line, args);
            
            this._setUser();
        }
    },


    // Override this function to intialize count for the line to check the quantity exeeded once 
    _getNewLineDefaultValues(fieldsParams) {
        const defaultValues = this._super(...arguments);
        return Object.assign(defaultValues, {
            location_dest_id: this._defaultDestLocation(),
            reserved_uom_qty: false,
            qty_done: 0,
            picking_id: this.params.id,
            count: 0,
        });
    },

    // This funtion will check the quantity and if it is greater than the quantity
    // on the pallet it will raise warning if it is exeeded when scanned by product
    _checkAndUpdateLineQuantity(line, args) {
        let package_id = line.result_package_id || line.package_id;
        if (package_id && package_id.quant_ids.length > 0) {
            let quants = this.cache.getRecord('stock.quant', package_id.quant_ids);
            if (line.qty_done > quants.quantity) {
                if (line.result_package_id && line.count == 1) {
                    line.qty_done = 1;
                    line.result_package_id = false;
                } else {
                    line.qty_done -= args.qty_done;
                    const message = _t("Not allowed to scan a quantity greater than what is on the pallet.");
                    return this.notification.add(message, { type: 'danger' });
                }
            } else if (line.qty_done === quants.quantity) {
                line.result_package_id = package_id;
                line.count += 1
            }
        }
    }

});

patch(BarcodeModel.prototype, "customBarcodeModel", {

    async _processBarcode(barcode) {
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


            // Prefills `package_id` if possible.
            if (currentLine.location_id.id && currentLine.product_id.id && !currentLine.package_id) {
                const domain = [
                    ['location_id', '=', currentLine.location_id.id],
                    ['product_id', '=', currentLine.product_id.id],
                    ['package_id', '!=', false]
                ];
                const res = await this.orm.call(
                    'stock.quant',
                    'search_read',
                    [domain],
                    {}
                );
                this.cache.setCache(res.records);
                if (res && res.length == 1) {
                    currentLine.package_id = this.cache.getRecord('stock.quant.package', res[0].package_id[0]);
                }
            }



            this._selectLine(currentLine);
        }
        this.trigger('update');
    },
});