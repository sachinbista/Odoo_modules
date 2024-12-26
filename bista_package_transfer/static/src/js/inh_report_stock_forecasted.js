odoo.define('bista_red_lab.ReplenishReport', function (require) {
    "use strict";

    const core = require('web.core');
    const dom = require('web.dom');
    const GraphView = require('web.GraphView');

    const qweb = core.qweb;
    const _t = core._t;

    require('stock.ReplenishReport');

    const ReplenishReport = core.action_registry.get('replenish_report');

    ReplenishReport.include({
        /**
         * @override
         * @private
         */
        _createGraphView: async function () {
            let viewController;
            const appendGraph = () => {
                promController.then(() => {
                    this.iframe.removeEventListener('load', appendGraph);
                    const $reportGraphDiv = $(this.iframe).contents().find('.o_report_graph');
                    if (!$reportGraphDiv) {
                        return;
                    }
                    dom.append(this.$el, viewController.$el, {
                        in_DOM: true,
                        callbacks: [{widget: viewController}],
                    });
                    const renderer = viewController.renderer;
                    // Remove the graph control panel.
                    $('.o_control_panel:last').remove();
                    const $graphPanel = $('.o_graph_controller');
                    $graphPanel.appendTo($reportGraphDiv);

                    if (!renderer.state.dataPoints.length) {
                        // Changes the "No Data" helper message.
                        // debugger;
                        const graphHelper = renderer.$('.o_view_nocontent');
                        const newMessage = $(qweb.render("bista_warehouse_inventory.NoContentHelper", {
                            description: _t("Try to add some incoming or outgoing transfers."),
                        }));
                        graphHelper.replaceWith(newMessage);
                        $reportGraphDiv.replaceWith(newMessage);
                    } else {
                        this.chart = renderer.chart;
                        // Lame hack to fix the size of the graph.
                        setTimeout(() => {
                            this.chart.canvas.height = 300;
                            this.chart.canvas.style.height = "300px";
                            this.chart.resize();
                        }, 1);
                    }
                });
            };
            // Wait the iframe fo append the graph chart and move it into the iframe.
            this.iframe.addEventListener('load', appendGraph);

            const model = 'report.stock.quantity';
            const promController = this._rpc({
                model: model,
                method: 'fields_view_get',
                kwargs: {
                    view_type: 'graph',
                }
            }).then(viewInfo => {
                const params = {
                    modelName: model,
                    domain: this._getReportDomain(),
                    hasActionMenus: false,
                };
                const graphView = new GraphView(viewInfo, params);
                return graphView.getController(this);
            }).then(res => {
                viewController = res;

                // Hack to put the res_model on the url. This way, the report always know on with res_model it refers.
                if (location.href.indexOf('active_model') === -1) {
                    const url = window.location.href + `&active_model=${this.resModel}`;
                    window.history.pushState({}, "", url);
                }
                const fragment = document.createDocumentFragment();
                return viewController.appendTo(fragment);
            });
        },
    })
});