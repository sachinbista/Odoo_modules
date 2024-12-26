/** @odoo-module **/

const { onWillStart, useState } = owl;
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { useModel } from "@web/views/model";

import { FormStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";


patch(FormStatusIndicator, "show_edit_save_form_view_props", {
    props: { ...FormStatusIndicator.props,
            fieldIsDirty: { type: Boolean, optional: true },
            edit: Function,
            readonly: Function,
            mode: { type: String, optional: true },
           },
    defaultProps : {
        fieldIsDirty: false,
    },
});

patch(FormStatusIndicator.prototype, "show_edit_save_form_view_prototype", {
    async edit() {
        await this.props.edit();
    },

    async readonly() {
        await this.props.readonly();
    },

    async discard() {
        await this.props.discard();
        await this.props.readonly();
    },
    async save() {
        var result = await this.props.save();
        if (result && this.props.model.root.isValid) {
            await this.props.readonly();
        }
    },

    get isNew() {
        if (this.props.model.root.isNew) {
            return true;
        }
        else {
            return false;
        }
    },
});

patch(FormController.prototype, 'show_edit_save_form_view', {
    setup() {
        this.readonlyFirst = false;
        this.archInfo = this.props.archInfo;
        const { create, edit } = this.archInfo.activeActions;
        this.canCreate = create && !this.props.preventCreate;
        this.canEdit = edit && !this.props.preventEdit;

        if (this.canEdit){
            if (this.props.mode !== 'edit') {
                this.props.preventEdit = true;
            }
            this.readonlyFirst = true;
        }
        this._super();
        var mode = this.props.mode || "readonly";
        this.state = useState({
            mode: mode,
            isDisabled: false,
        });
        if (this.readonlyFirst) {
            this.props.preventEdit = false;
        }
    },

    async edit() {
        await this._super(...arguments);
        this.state.mode = 'edit';
    },

    async readonly() {
        await this.model.root.switchMode("readonly");
        this.state.mode = 'readonly';
    },

});
