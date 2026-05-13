/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

export class SaleContractDashboard extends Component {
    static template = "rental_management.SaleContractDashboard";
    static props = { list: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ values: {} });

        onWillStart(async () => {
            await this.updateDashboardState();
        });
        onWillUpdateProps(async () => {
            await this.updateDashboardState();
        });
    }

    async updateDashboardState() {
        this.state.values = await this.orm.call(
            "property.vendor",
            "retrieve_sale_contract_list_dashboard_data",
            []
        );
    }

    async viewContract(ev) {
        ev.preventDefault();
        const field = ev.currentTarget.dataset.field;
        const value = ev.currentTarget.dataset.value;
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Contracts",
            res_model: "property.vendor",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            context: { create: false },
            domain: [[field, "=", value]],
        });
    }

    async onDashboardClick(ev) {
        const target = ev.target.closest(".o_sale_contract_action");
        if (target) {
            return this.viewContract({ preventDefault: () => {}, currentTarget: target });
        }
    }
}

export class SaleContractDashboardListRenderer extends ListRenderer {
    static template = "rental_management.SaleContractDashboardListRenderer";
    static components = {
        ...ListRenderer.components,
        SaleContractDashboard,
    };
}

export const SaleContractDashboardListView = {
    ...listView,
    Renderer: SaleContractDashboardListRenderer,
};

registry.category("views").add("sale_contract_dashboard_list", SaleContractDashboardListView);
