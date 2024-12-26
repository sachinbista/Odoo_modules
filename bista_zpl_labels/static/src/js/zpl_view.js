odoo.define("bista_zpl_labels.zpl_view", function (require) {
    "use strict";

    var AbstractController = require('web.AbstractController');

    var AbstractModel = require('web.AbstractModel');
    var AbstractRenderer = require('web.AbstractRenderer');
    var AbstractView = require('web.AbstractView');
    var core = require('web.core');
    var _lt = core._lt;

    var zplController = AbstractController.extend({
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.fields = params.controlPanel.props.fields || [];
            this.renderer = renderer
            this.params = params
            this.model = model
            this.parent = parent
            var fields = this._load_fields()
            renderer.fields = fields
            model.fields = fields
            console.log("Params ", this)

        },
        _load_fields: function () {
            var self = this;
            var field_list = []
            $.each(self.fields, function (index, field) {
                if (field.type === 'many2one') {
                    field['selection'] = self._rpc({
                        model: field.relation,
                        method: 'search_read',
                        fields: ['id', 'name'],
                    })
                }
                field_list[field.name] = field
            });
            return field_list


        }
    });


    var zplRenderer = AbstractRenderer.extend({
        // Initializer
        _render: function () {
            console.log("Rendered ", this)
            return $.when();
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            this.record = this.state.record[0]
            this._get_layout();
            this._set_field_value();
            this.controlPanel = $(".o_control_panel");
            this.control_btn = this.controlPanel.find(".o_cp_bottom_left .o_cp_buttons")
            this.control_btn.append(this._get_save_button())
            this._on_field_click_event();

        },

        _get_save_button: function () {
            var save_btn = $('<button type="button" class="btn btn-primary">Save</button>')
            var self = this;
            save_btn.on('click', function (e) {
                e.preventDefault();
                var content = self.zpl_blue.html()
                var res_id = self.record.id
                self._rpc({
                    model: 'zpl.label',
                    method: 'write',
                    args: [res_id, {
                        zpl_blue: content,
                    }],
                })
            })
            return save_btn
        },

        _get_fields: function () {
            var self = this;
            var label_type = self._get_field_selection('model', 'Label Type')
            this.field_draggable_container = $("<div class='field-draggable-container'>")
            this.field_container.append(label_type)
            this.field_container.append(this.field_draggable_container)
            label_type.change(function () {
                let model_id = $(this).find(":selected").attr("value")
                self._get_draggable_fields(model_id)
            })


        },

        _set_field_value: function () {
            var field_ids = Object.keys(this.fields);
            var self = this;
            var record = self.record
            this.zpl_blue.html(record['zpl_blue'])
            $.each(field_ids, function (key, value) {
                var field = self.fields[value]
                var field_ui = $("#" + field.name)
                if (field_ui.length) {
                    var val = record[field.name];
                    if (field.type === 'selection' || field.type === 'many2one') {
                        field_ui.val(val).change()

                    } else {
                        field_ui.val(val)
                    }
                }
            })

            this._preview_label();
        },

        _get_zpl_raw: function () {
            var raw = "^XA"
            var fields = this.zpl_blue.find(".zpl-field")
            var self = this;
            var field_added = []
            console.log("Fields length ", fields.length)
            $.each(fields, function (index, field) {
                var field = $(field)
                var field_value = field.find(".field-value")
                var field_id = field_value.attr('id')
                console.log("Field ID ", field_id)
                if (field_added.indexOf(field_id) === -1) {
                    field_added.push(field_id)
                    var label = field.find('.field-label')
                    var pos = self._get_field_position(label)
                    raw += "^FO" + pos[0] + "," + pos[1] + "^FD" + label.text() + "^FS"
                }

            })
            return raw + "^XZ"
        },
        _get_field_position: function (field) {
            var zpl = this.zpl_blue.offset()
            var offset = field.offset()
            return [parseInt(offset.left - zpl.left || 0.0), parseInt(offset.top - zpl.top || 0.0)]
        },
        _preview_label: function () {
            var raw = this._get_zpl_raw();
            const zplWidth = this._get_zpl_width();
            const zplHeight = this._get_zpl_height();
            var dpi = 12
            console.log("URL ", raw)
            var self = this;
            this._rpc({
                model: 'zpl.label',
                method: 'get_zpl',
                args: [raw, dpi, zplWidth, zplHeight]
            }).then(function (result) {
                self.zpl_white.attr("src", "data:image/png;base64," + result);

            })
        },


        // Layout
        _get_layout: function () {
            var layout = this.$el;
            layout.empty();
            this.left_layout = this._get_layout_left()
            this.right_layout = this._get_layout_right()
            this.center_layout = this._get_layout_center()
            layout.addClass("main_layout row")
            layout.append(this.left_layout)
            layout.append(this.center_layout)
            layout.append(this.right_layout)
            return layout
        },

        // Left Layout
        _get_layout_left: function () {
            var container = $("<div>").addClass("col-md-2 zpl-layout-left");
            var title = $("<div>")
            title.append($("<h3>").text("Drag and Drop Fields"))
            title.append($("<p>").text("Select model then drag and drop the available fields to the ZPL container"))
            var field_container = $("<div class='field-container'>")
            container.append(title)
            container.append(field_container)
            this.field_container = field_container
            this._get_fields()
            return container
        },

        // Drag and Drop
        _get_draggable_fields: async function (model_id) {
            var self = this;
            self.field_draggable_container.empty();

            var field_list = await this._rpc({
                model: 'ir.model.fields',
                method: 'search_read',
                fields: ['id', 'name', 'field_description', 'ttype'],
                domain: [['model_id.model', '=', model_id]],
            })

            $.each(field_list, function (index, field) {
                var field_group = $("<div class='field-value'>");
                field_group.append($("<span class='fa fa-bars'/>"))
                field_group.attr('id', field.name)
                field_group.attr("type", field.ttype)
                field_group.append($("<span>").text(field.field_description))
                var container = $("<div class='field-draggable'>")
                var label = $("<span class='field-label'>")
                container.append(label)
                container.append(field_group)
                self.field_draggable_container.append(container)
            });
            self._field_on_draggable();

        },

        _field_on_draggable: function () {
            var self = this;
            var zpl_id = "#" + self.zpl_blue.attr("id")
            $(".field-draggable").draggable({
                revert: 'invalid',
                helper: "clone",
                appendTo: zpl_id,
                scroll: false,
                grid: [5, 5]
                // containment: zpl_id,
            })
        },

        _zpl_droppable: function () {
            var self = this;
            self.zpl_blue.droppable({
                accept: ".field-draggable",
                drop: function (event, ui) {
                    var field = ui.draggable;
                    field.addClass('zpl-field')
                    console.log("Dragged field ", field, ui.helper)
                    $(this).append(field);
                    field.click();
                    self._field_movable(field, ui.helper);
                    self._preview_label();
                }
            })
        },

        // Center Layout
        _get_layout_center: function () {
            var container = $("<div>").addClass("col-md-8 p-0");
            var zpl_container = $("<div>").addClass("zpl-layout-center");
            container.append(this._get_tool_box())
            zpl_container.append(this._get_zpl_blue_print_layout());
            zpl_container.append(this._get_zpl_preview_layout());
            container.append(zpl_container)
            return container;
        },

        _get_tool_box: function () {
            var container = $("<div>").addClass("zpl-tools-container");
            var wrapper = $("<div class='wrapper'>")
            wrapper.append($("<h4 class='title'>").text("Tools"))
            container.append(wrapper)
            return container
        },

        _get_zpl_blue_print_layout: function () {
            var blue_print = $("<div>").addClass("zpl-container zpl-blue-print");
            var wrapper = $("<div class='wrapper'>")
            wrapper.append($("<h4 class='title'>").text("Blue Print"))
            this.zpl_blue = $("<div class='zpl zpl-blue' id='zpl_blue'>")
            wrapper.append(this.zpl_blue)
            blue_print.append(wrapper)
            this._zpl_droppable();
            return blue_print
        },

        _get_zpl_preview_layout: function () {
            var label_preview = $("<div>").addClass("zpl-container zpl-preview");
            var wrapper = $("<div class='wrapper'>")
            wrapper.append($("<h4 class='title'>").text("Label Preview"))
            var zpl_container = $("<div class='zpl zpl-white'>")
            this.zpl_white = $("<img src=''>")
            zpl_container.append(this.zpl_white)
            wrapper.append(zpl_container)
            label_preview.append(wrapper)
            return label_preview;
        },

        // Right Layout
        _get_layout_right: function () {
            var container = $("<div>").addClass("col-md-2 zpl-layout-right")
            var title = $("<div>")
            title.append($("<h3>").text("Label Configuration"))
            title.append($("<p>").text("Adjust the label Size and DPI."))
            this.settings_container = $("<div class='settings-container'>")
            container.append(title)
            container.append(this.settings_container)
            container.append(this._get_field_config())
            this._get_settings_fields();
            return container;
        },

        _get_settings_fields: function () {
            var self = this;
            var height_field = self._get_basic_field('height', 'Height (in)', 'float', "Enter Label height")
            var width_field = self._get_basic_field('width', 'Width (in)', 'float', "Enter Label Width")
            var dpi_field = self._get_field_selection('dpi', 'DPI')
            height_field.on("change", this._onchange_height.bind(this))
            width_field.on("change", this._onchange_width.bind(this))
            dpi_field.on("change", this._onchange_dpi.bind(this))
            this.settings_container.append(height_field)
            this.settings_container.append(width_field)
            this.settings_container.append(dpi_field)
        },

        _get_field_config: function () {
            var self = this;
            var container = $("<div>").addClass("field-config-container")
            var title = $("<div>")
            title.append($("<h3>").text("Field Configuration"))
            title.append($("<p>").text("Select the value source"))
            container.append($("<hr/>"))
            container.append(title)
            container.append(self._field_config_label())
            container.append(self._field_config_label_margin())
            this.field_config = container
            this.field_config.hide();
            return container
        },

        _field_config_label: function () {
            var field_label = this._get_basic_field('field_label', 'Label', 'char', "Enter field label")
            var self = this;
            field_label.on('input', function () {
                var label = $(this).find('input').val();
                if (label) {
                    var label_ui = self.field_selected.find('.field-label')
                    label_ui.text(label)
                    label_ui.show();
                }
            })
            return field_label
        },
        _field_config_label_margin: function () {
            var field_label = this._get_basic_field('field_label_margin', 'Label Margin', 'number')
            var self = this;
            field_label.on('input', function () {
                var label = $(this).find('input').val();
                if (label) {
                    self.field_selected.find('.field-label').css({
                        'padding-right': label + "px"
                    })
                }
            })
            return field_label
        },

        // Static Methods
        _update_label_size: function () {
            const zplWidth = this._get_zpl_width();
            const zplHeight = this._get_zpl_height();
            var dpi = this._get_zpl_dpi();

            var width = (zplWidth * dpi) + "px";
            var height = (zplHeight * dpi) + "px";
            var size = {
                "width": width,
                "max-width": width,
                "height": height,
                "max-height": height,
                "min-height": height,
                "min-width": width
            }
            this.zpl_blue.css(size);
            this.zpl_white.css(size)
        },

        _get_zpl_width: function () {
            return parseFloat($('#width').val() || '0.0');
        },

        _get_zpl_height: function () {
            return parseFloat($("#height").val() || '0.0');
        },
        _get_zpl_dpi: function () {
            return parseInt($("#dpi").val() || '0') * 25.4;
        },

        _field_config_hide: function () {
            this.field_config.hide();
        },

        _field_config_show: function (field) {
            this.field_selected = field
            this.field_config.show();
            this._set_field_config_value(field);
        },

        _set_field_config_value: function (field) {
            var field_label = field.find(".field-label")
            console.log("Field Label ", field_label, field)
            this.field_config.find("#field_label").val(field_label.text())
            this.field_config.find("#field_label_margin").val(field_label.css("padding-right").replace("px", ""))
        },

        _field_movable: function (field, helper) {
            var self = this;
            var zpl_id = "#" + self.zpl_blue.attr("id");
            field.draggable({
                'containment': zpl_id
            })
            var position = helper.position();
            var top = position.top;
            var left = position.left;
            field.css({
                'top': top + "px",
                'left': left + "px",
                'position': 'absolute'
            })
        },

        // onchange Methods
        _on_field_click_event: function () {
            var self = this;
            $('.zpl-layout-center').on('click', this._on_field_selected.bind(this));
        },

        _on_field_selected: function (event) {
            var field = $(event.target).closest('.zpl-field')
            if (!field.length) {
                console.log('Clicked outside of .item');
                this._field_config_hide();
            } else {
                console.log("Field is clieckdd ")
                console.log(field.attr('type'))
                this._field_config_show(field)
            }
        },

        _onchange_width() {
            this._update_label_size();

        },

        _onchange_height() {
            this._update_label_size();

        },

        _onchange_dpi() {
            this._update_label_size();
        },

        // Get Fields
        _get_field_many2one: async function async(name, string, ir_model, domain) {
            var model = $("<select>")
            model.attr('id', name)
            model.attr('type', 'many2one')
            model.append($("<option selected value>Select Option</option>"))
            var selection = {}
            if (ir_model) {
                selection = await this._rpc({
                    model: ir_model,
                    method: 'search_read',
                    fields: ['id', 'name'],
                    domain: domain || []
                })
            } else {
                selection = this.state.fields[name].selection
            }
            $.each(selection, function (index, record) {
                var option = $("<option>").text(record.name)
                option.attr("id", record.id)
                model.append(option)
            })

            var label = $("<label>").text(string)
            label.attr("for", name)

            var wrapper = $("<div class='form-group'>")
            wrapper.append(label)
            wrapper.append(model)
            return wrapper
        },

        _get_field_selection: function (name, string, options) {
            var model = $("<select>");
            model.attr('id', name)
            model.append($("<option selected value>Select Option</option>"))
            var wrapper = $("<div class='form-group'>")
            var selection = {};
            if (this.fields) {
                selection = this.fields[name].selection
            }
            if (options) {
                selection = options
            }
            $.each(selection, function (index, record) {
                var option = $("<option>").text(record[1])
                option.attr("value", record[0])
                model.append(option)
            })
            var label = $("<label>").text(string)
            label.attr("for", name)
            wrapper.append(label)
            wrapper.append(model)
            return wrapper

        },

        _get_basic_field: function (name, string, type, placeholder) {
            var wrapper = $("<div class='form-group'>")
            var label = $("<label>").text(string)
            label.attr("for", name)
            var input = $("<input>")
            input.attr("id", name)
            input.attr("name", name)
            input.attr("type", type)
            if (placeholder) {
                input.attr("placeholder", placeholder)
            }
            wrapper.append(label)
            wrapper.append(input)
            return wrapper

        },
    });

    var zplModel = AbstractModel.extend({
        get: function () {
            return {record: this.record};
        },
        load: function (params) {
            return this._load(params);
        },
        reload: function (id, params) {
            return this._load(params);
        },
        _load: async function (params) {
            var self = this;
            self.res_id = params.res_id
            if (!self.res_id) {
                return []
            }
            return await self._rpc({
                model: 'zpl.label',
                method: 'search_read',
                domain: [['id', '=', self.res_id]],
                fields: Object.keys(self.fields || []),
                limit: 1,
            }).then(function (result) {
                self.record = result;
            })
        },
    });

    var zplView = AbstractView.extend({
        config: _.extend({}, AbstractView.prototype.config, {
            Model: zplModel,
            Controller: zplController,
            Renderer: zplRenderer,
        }),
        icon: 'fa-th-large',
        viewType: "zpl_view",
        multi_record: false,
        withSearchBar: false,
        searchMenuTypes: [],
        display_name: _lt("ZPL"),
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);
        },
    });

    var viewRegistry = require('web.view_registry');

    viewRegistry.add('zpl_view', zplView);
    return zplView;
})