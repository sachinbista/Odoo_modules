/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { listView } from "@web/views/list/list_view";
import { patch } from "@web/core/utils/patch";

import { ListRenderer } from "@web/views/list/list_renderer";
const { onMounted } = owl;


patch(ListRenderer.prototype, '/bista_go_flow/static/src/js/sign_document.js', {
    async onCellClicked(record, column, ev) {
        this._super(...arguments);
        var timer = setInterval(function () {
            if($('button[name="go_to_document"]').length){
                $('button[name="go_to_document"]').trigger('click');
            }
            if($('button.o_sign_sign_directly').length){
                $('button.o_sign_sign_directly').trigger('click');
            }
            var iframe = $('.o_sign_pdf_iframe').length && $('.o_sign_pdf_iframe')[0];
            if (iframe.contentDocument){
                var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                // Check if loading is complete
                if (iframeDoc.readyState == 'complete' || iframeDoc.readyState == 'interactive') {
                    if(iframeDoc.getElementsByClassName('o_sign_sign_item_navigator')[0]){
                        iframeDoc.getElementsByClassName('o_sign_sign_item_navigator')[0].click();
                        clearInterval(timer);
                        return;
                    }
                }
            }else{
                // clearInterval(timer);
            }

        }, 500);
        console.log(this);
    }
});

// export const signNotifyService = {
//     dependencies: ["bus_service", "notification"],

//     start(env, { bus_service, notification }) {
//         let isNotificationDisplayed = false;
//         let bundleNotifTimerID = null;
//         bus_service.addEventListener('notification', onNotification.bind(this));       
//         bus_service.start();
//         function onNotification({ detail: notifications }) {
//             for (const { payload, type } of notifications) {
//                 if (type === 'web.notify') {
//                     var timer = setInterval(function () {
//                         var iframe = $('.o_sign_pdf_iframe')[0];
//                         var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
//                         // Check if loading is complete
//                         if (iframeDoc.readyState == 'complete' || iframeDoc.readyState == 'interactive') {
//                             iframeDoc.getElementsByClassName('o_sign_sign_item_navigator')[0].click();
//                             clearInterval(timer);
//                             return;
//                         }
//                     }, 2500);
//                  }
//             }
//        }
//      },
//  };

// registry.category("services").add("signNotifyService", signNotifyService);