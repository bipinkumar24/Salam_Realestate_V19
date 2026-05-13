/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

export class PropertyListDashboard extends Component {
    static template = "rental_management.RentalPropertyDashboard";
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
            "property.details",
            "retrieve_list_dashboard_data",
            []
        );
    }

    async openProperties(domain) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Properties",
            res_model: "property.details",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            target: "current",
            context: { create: true },
            domain,
        });
    }

    async viewAllProperties(ev) {
        ev.preventDefault();
        const status = ev.currentTarget.dataset.status;
        const domain = status === "all" ? [] : [["stage", "=", status]];
        await this.openProperties(domain);
    }

    async viewForRentProperties(ev) {
        ev.preventDefault();
        const type = ev.currentTarget.dataset.status;
        const domain = [
            ["stage", "=", "available"],
            ["sale_lease", "=", "for_tenancy"],
        ];
        if (type !== "all") {
            domain.push(["type", "=", type]);
        }
        await this.openProperties(domain);
    }

    async viewProperties(ev) {
        ev.preventDefault();
        const status = ev.currentTarget.dataset.status;
        const type = ev.currentTarget.dataset.type;
        const domain = status === "all" ? [["stage", "!=", "draft"]] : [["stage", "=", status]];
        domain.push(["type", "=", type]);
        await this.openProperties(domain);
    }

    async onDashboardClick(ev) {
        const rentTarget = ev.target.closest(".o_property_for_rent_action");
        if (rentTarget) {
            return this.viewForRentProperties({ preventDefault: () => {}, currentTarget: rentTarget });
        }
        const typeTarget = ev.target.closest(".o_property_type_status_action");
        if (typeTarget) {
            return this.viewProperties({ preventDefault: () => {}, currentTarget: typeTarget });
        }
        const statusTarget = ev.target.closest(".o_property_status_action");
        if (statusTarget) {
            return this.viewAllProperties({ preventDefault: () => {}, currentTarget: statusTarget });
        }
    }
}

export class PropertyDashboardListRenderer extends ListRenderer {
    static template = "rental_management.PropertyDashboardListRenderer";
    static components = {
        ...ListRenderer.components,
        PropertyListDashboard,
    };
}

export const PropertyDashboardListView = {
    ...listView,
    Renderer: PropertyDashboardListRenderer,
};

registry.category("views").add("rental_property_dashboard_list", PropertyDashboardListView);
