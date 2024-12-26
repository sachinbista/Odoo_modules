/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
const { whenReady } = owl;

var rpc = require('web.rpc');

var models = [];

(async function boot() {
    await whenReady();
    await rpc.query({
        model: "ir.model",
        method: "search_read",
        args:[
            [['disable_create_edit','=', true]],
            ['model'],
        ],
    }).then(function(result) {
        result.forEach(function(el){
            models.push(el.model);
        })            
    });

})();


patch(Many2OneField.prototype, 'disable_crate_edit', {
    setup() {
        let self = this;
        let crnt_model = this.props.relation;
        if (models.includes(crnt_model)){
             self.props.canCreate = false;
             self.props.canQuickCreate = false;
             self.props.canCreateEdit = false;
        }
        this._super(...arguments);
    },

    computeActiveActions(props) {
        let self = this;
        let crnt_model = this.props.relation;
        if (models.includes(crnt_model)){
            // self.props.canCreate = false;
            // self.props.canQuickCreate = false;
            // self.props.canCreateEdit = false;
            this.state.activeActions = {
                create: false,
                createEdit: false,
                write: false,
            };
        }else{
            this.state.activeActions = {
                create: props.canCreate,
                createEdit: props.canCreateEdit,
                write: props.canWrite,
            };
        }
        
    },

});
