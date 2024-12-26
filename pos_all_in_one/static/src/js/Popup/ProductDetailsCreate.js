odoo.define('pos_all_in_one.ProductDetailsCreate', function(require) {
	'use strict';

	const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
	const Registries = require('point_of_sale.Registries');
	const { getDataURLFromFile } = require('web.utils');
	const rpc = require('web.rpc');
    const {Product} = require('point_of_sale.models');


	class ProductDetailsCreate extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.changes = {};
        }

        captureChange(event) {
            this.changes[event.target.name] = event.target.value;
        }
		get partnerImageUrl() {
            // We prioritize image_1920 in the `changes` field because we want
            // to show the uploaded image without fetching new data from the server.
            const partner = this.props.products;
            if (this.changes.image_1920) {
                return this.changes.image_1920;
            } else if (partner.id) {
                return `/web/image?model=product.product&id=${partner.id}&field=image_128&write_date=${partner.write_date}&unique=1`;
            } else {
                return false;
            }
        }

        async uploadImage(event) {
            let self = this;
            const file = event.target.files[0];
            if(file){
                if (!file.type.match(/image.*/)) {
                    await this.showPopup('ErrorPopup', {
                        title: self.env._t('Unsupported File Format'),
                        body: self.env._t(
                            'Only web-compatible Image formats such as .png or .jpeg are supported.'
                        ),
                    });
                } else {
                    const imageUrl = await getDataURLFromFile(file);
                    const loadedImage = await this._loadImage(imageUrl);
                    if (loadedImage) {
                        const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                        this.changes.image_1920 = resizedImage.toDataURL();
                        // Rerender to reflect the changes in the screen
                        this.render();
                    }
                }
            }
            
        }
        _resizeImage(img, maxwidth, maxheight) {
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            var ratio = 1;

            if (img.width > maxwidth) {
                ratio = maxwidth / img.width;
            }
            if (img.height * ratio > maxheight) {
                ratio = maxheight / img.height;
            }
            var width = Math.floor(img.width * ratio);
            var height = Math.floor(img.height * ratio);

            canvas.width = width;
            canvas.height = height;
            ctx.drawImage(img, 0, 0, width, height);
            return canvas;
        }
        /**
         * Loading image is converted to a Promise to allow await when
         * loading an image. It resolves to the loaded image if succesful,
         * else, resolves to false.
         *
         * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
         */
        _loadImage(url) {
            let self = this;
            return new Promise((resolve) => {
                const img = new Image();
                img.addEventListener('load', () => resolve(img));
                img.addEventListener('error', () => {
                    this.showPopup('ErrorPopup', {
                        title: self.env._t('Loading Image Error'),
                        body: self.env._t(
                            'Encountered error when loading image. Please try again.'
                        ),
                    });
                    resolve(false);
                });
                img.src = url;
            });
        }
		
		async create_product() {
			var self = this;
			var fields = {};
			$('.client-details-box .detail').each(function(idx,el){
				fields[el.name] = el.value;
			});

			if(fields.display_name == false){
				self.showPopup('ErrorPopup',{
					'title': self.env._t('Error: Could not Save Changes'),
					'body': self.env._t('please enter product details.'),
				});
			}else{
				fields.id = false;
				fields.image_1920 = this.changes.image_1920
				fields.pos_categ_id = fields.pos_categ_id || false;
				fields.list_price = fields.list_price || '';
				fields.standard_price = fields.standard_price || '';
				fields.barcode = fields.barcode || false;

                if (fields.cost_price == '') {
                    fields.cost_price = '0'
                }
                if (fields.list_price == '') {
                    fields.list_price = '0'
                }

                if (fields.standard_price == '') {
                    fields.standard_price = '0'
                }
               
				await self.rpc({
					model: 'product.product',
					method: 'create_from_ui',
					args: [fields],
				}).then(function(product){
                    var domain = [['id','=',product]];
                    rpc.query({
                            model: 'product.product',
                            method: 'search_read',
                            args: [domain,[]],
                    },{async: false,
                        timeout: 3000,
                        shadow: true,
                        }).then(function(out) {
                        out = out[0];
                        out.pos = self.env.pos;
                    });
                    self.env.pos.is_sync = true;
                    alert('Product Details Saved!!!!');
                    self.showScreen('ProductScreen', {});
                    self.cancel();
				},function(err, event){
                    self.showPopup('ErrorPopup',{
                        'title': self.env._t('Error: Could not Save Changes'),
                        'body': self.env._t('Added Product Details getting Error.'),
                    });
			    });
			}
		}

	}
	
	ProductDetailsCreate.template = 'ProductDetailsCreate';
	ProductDetailsCreate.defaultProps = {
		confirmText: 'Create',
		cancelText: 'Close',
		title: 'Create Product',
		body: '',
	};
	
	Registries.Component.add(ProductDetailsCreate);
	return ProductDetailsCreate;
});
