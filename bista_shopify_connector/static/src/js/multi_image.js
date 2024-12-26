odoo.define('bista_shopify_connector.MultiImage', function (require) {
    "use strict";

    var core = require('web.core');
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    var fieldRegistry = require('web.field_registry');
    var Pager = require('web.Pager');
    var dataset = require('web.data');
    var Dialog = require('web.Dialog');
    var qweb = core.qweb;
    var _t = core._t;

    FieldOne2Many.include( {

        events: {
            'click .oe-image-preview': 'image_preview',
            'click .oe_image_list': 'image_list_view',
        },

        start: async function () {
            const _super = this._super.bind(this);
            return _super(...arguments);
        },
        _render: function () {
            this._super.apply(this, arguments);
            if (this.attrs.widget != 'image_multi') {
                this.$el.find(".oe-image-preview").remove();
                this.$el.find(".oe_image_list").remove();
            }
        },

        image_preview : function () {
            if (this.view.type === "list" && this.attrs.widget ===
                'image_multi') {
                var self = this;
                var saved_images = [];
                var url_list = [];
                var model = self.field.relation;
                var res_ids = self.value.res_ids;
                self.mydataset = new dataset.DataSetSearch(self, model, {}, []);
                if (res_ids.length > 0) {
                    if (_.every(res_ids, function (i) {
                        return _.isString(i);
                    })) {
                        Dialog.alert(self,
                            _t("Please Save the record when you are adding an image for the first time !!"));
                        return;
                    } else {
                        _.each(res_ids, function (i) {
                            if (_.isNumber(i)) {
                                saved_images.push(i);
                            }
                        });
                        self.mydataset.read_slice([], {
                            'domain': [['id', 'in', saved_images]],
                        }).then(function (records) {
                            if (records && !_.isEmpty(records)) {
                                _.each(records, function (img) {
                                    if (img) {
                                        var src = window.location.origin +
                                        "/web/binary/image?model=" + model +
                                        "&field=image&id=" + img.id;
                                        if (img.image) {
                                            src = "data:image/jpeg;base64," + img.image;
                                        }
                                        var title = img.title
                                            ? img.title
                                            : '';
                                        var description = img.description
                                            ? img.description
                                            : '';
                                        url_list.push( {
                                            "url": src,
                                            "title": 'Title:-' + title +
                                                '<br/>Description:-' +
                                                description,
                                        });
                                    }
                                });
                            } else {
                                self.do_warn("Image", "Image not available !");
                                return;
                            }
                            self.$el.find('.oe-image-preview').lightbox( {
                                fitToScreen: true,
                                jsonData: url_list,
                                loopImages: true,
                                imageClickClose: false,
                                disableNavbarLinks: true,
                            });
                        });
                    }
                } else {
                    Dialog.alert(self,
                        _t("There are no image for showing in preview !!"));
                    return;
                }
            }
        },
        image_list_view : function () {
            if (this.view.type === "list" && this.attrs.widget === 'image_multi') {
                var self = this;
                var saved_images = [];
                var model = self.field.relation;
                var res_ids = self.value.res_ids;
                self.mydataset = new dataset.DataSetSearch(self, model, {}, []);
                if (res_ids.length > 0) {
                    if (_.every(res_ids, function (i) {
                        return _.isString(i);
                    })) {
                        Dialog.alert(self,
                            _t("Please Save the record when you are adding an image for the first time !!"));
                        return;
                    } else {
                        _.each(res_ids, function (i) {
                            if (_.isNumber(i)) {
                                saved_images.push(i);
                            }
                        });
                        self.mydataset.read_slice([], {
                            'domain': [['id', 'in', saved_images]],
                        }).then(function (records) {
                            self.images_list = records;
                            if (self.images_list.length === 0) {
                                self.do_warn(_t("Image"),
                                    _t("Image not available !"));
                                return;
                            }

                            self.image_list_dialog = new Dialog(self, {
                                title: _t("Image List"),
                                width: '840px',
                                height: '70%',
                                min_width: '600px',
                                min_height: '500px',
                                buttons: [{
                                    text: _t("Close"),
                                    click: function () {
                                        self.image_list_dialog.close();
                                        self.trigger_up('reload');
                                    },
                                    close: true,
                                }],
                            });
                            self.image_list_dialog.opened().then(function () {
                                self.on_render_dialog();
                            });
                            self.image_list_dialog.open();

                        });
                    }
                } else {
                    Dialog.alert(self,
                        _t("There are no image for showing in preview !!"));
                    return;
                }
            }
        },
        on_render_dialog: function () {
            var self = this;
            var images_list = [];
            images_list = self.images_list;
            var model = self.field.relation;
            var url_list = [];
            var images = [];
            var start = 0;
            if (images_list) {
                _.each(images_list, function (img) {
                    var src = window.location.origin +
                    "/web/binary/image?model=" + model + "&field=image&id=" +
                    img.id;
                    if (img.image) {
                        src = "data:image/jpeg;base64," + img.image;
                    }
                    if (img) {
                        if (img.title) {
                            url_list.push({
                                'name': img.title,
                                'path': src,
                                'id': img.id,
                            });
                        } else {
                            url_list.push({
                                'name': 'Image',
                                'path': src,
                                'id': img.id,
                            });
                        }
                    }
                });
            } else {
                return false;
            }

            for (var i = 1; i <= Math.ceil(url_list.length / 4); i++) {
                images.push(url_list.slice(start, start + 4));
                start = i * 4;
            }
            self.image_list_dialog.$el.html(qweb.render('DialogImageList', {
                'widget': self,
                'image_list': images,
                'readonly': self.isReadonly,
            }));
            self.image_list_dialog.$el.find(".oe-remove-image").click(
                function () {
                    self.do_remove_image(this);
                });
        },

        do_remove_image: function (curr_id) {
            var self = this;
            var model = self.field.relation;
            self._rpc( {
                model: model,
                method: 'unlink',
                args: [parseInt($(curr_id)[0].id, 10)],
            });
            $(curr_id).closest('table.hoverbox').parent().remove();
        },
    });
});
