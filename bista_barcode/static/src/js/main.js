/** @odoo-module **/

import {patch} from 'web.utils';
import MainComponent from '@stock_barcode/components/main';

patch(MainComponent.prototype, 'bista_barcode/static/src/js/main.js', {

    goToMainMenu() {
        this.env.model._goToMainMenu()
    }

});
