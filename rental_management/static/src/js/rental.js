/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Component, onMounted, onWillStart, useEffect, useState } from "@odoo/owl";

export class RentalDashboard extends Component {
    static template = "rental_management.RentalDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ stats: null });
        this.display = { controlPanel: false };

        onWillStart(async () => {
            this.state.stats = await this.orm.call("property.details", "get_property_stats", []);
        });

        onMounted(() => {
            this.renderDashboard();
        });

        useEffect(
            () => {
                this.renderDashboard();
            },
            () => [this.state.stats]
        );
    }

    renderDashboard() {
        if (!this.state.stats || !this.el) {
            return;
        }
        const stats = this.state.stats;
        this.topBrokers(stats.tenancy_top_broker);
        this.topBrokersSold(stats.tenancy_top_broker);
        this.tenancyDuePaid(stats.due_paid_amount);
        this.soldDuePaid(stats.due_paid_amount);
    }

    getPropertyTypeBars() {
        const data = this.state.stats?.property_type;
        if (!Array.isArray(data) || data.length < 2) {
            return [];
        }
        const labels = Array.isArray(data[0]) ? data[0] : [];
        const values = Array.isArray(data[1]) ? data[1] : [];
        const maxValue = Math.max(...values, 0);
        const colors = ["#87F4B5", "#F6D5BB", "#6CE778", "#94DCDE"];
        return labels.map((label, index) => {
            const value = Number(values[index] || 0);
            return {
                key: `${label}-${index}`,
                label,
                value,
                color: colors[index % colors.length],
                height: maxValue ? `${Math.max((value / maxValue) * 100, value > 0 ? 12 : 2)}%` : "2%",
            };
        });
    }

    renderGraph(selector, options) {
        const target = this.el.querySelector(selector);
        const ApexCharts = globalThis.ApexCharts || window.ApexCharts;
        if (!target || !ApexCharts) {
            return;
        }
        target.innerHTML = "";
        const graph = new ApexCharts(target, options);
        graph.render();
    }

    topBrokers(data) {
        if (!Array.isArray(data) || data.length < 2) {
            return;
        }
        this.renderGraph("#top_brokers", {
            series: [{ name: "Rent Contracts", data: data[1] }],
            chart: { height: 200, type: "bar" },
            colors: ["#EF745C", "#D06257", "#B15052", "#923E4D", "#722B47"],
            plotOptions: { bar: { columnWidth: "40%", distributed: true } },
            dataLabels: { enabled: true },
            legend: { show: true },
            xaxis: {
                categories: data[0],
                labels: {
                    style: {
                        colors: ["#EF745C", "#D06257", "#B15052", "#923E4D", "#722B47"],
                        fontSize: "12px",
                    },
                },
            },
        });
    }

    topBrokersSold(data) {
        if (!Array.isArray(data) || data.length < 4) {
            return;
        }
        this.renderGraph("#top_brokers_sale", {
            series: [{ name: "Sale Contracts", data: data[3] }],
            chart: { height: 200, type: "bar" },
            colors: ["#11D3F3", "#38DEDF", "#5FE8CB", "#86F3B6", "#ADFDA2"],
            plotOptions: { bar: { columnWidth: "40%", distributed: true } },
            dataLabels: { enabled: true },
            legend: { show: true },
            xaxis: {
                categories: data[2],
                labels: {
                    style: {
                        colors: ["#11D3F3", "#38DEDF", "#5FE8CB", "#86F3B6", "#ADFDA2"],
                        fontSize: "12px",
                    },
                },
            },
        });
    }

    tenancyDuePaid(data) {
        if (!Array.isArray(data) || data.length < 4) {
            return;
        }
        this.renderGraph("#tenancy_due_paid", {
            series: data[3],
            chart: { type: "pie", height: 300 },
            colors: ["#FF884B", "#64E291"],
            dataLabels: { enabled: false },
            labels: data[2],
            legend: { position: "bottom" },
        });
    }

    soldDuePaid(data) {
        if (!Array.isArray(data) || data.length < 2) {
            return;
        }
        this.renderGraph("#sold_due_paid", {
            series: data[1],
            chart: { type: "pie", height: 225 },
            colors: ["#FF884B", "#64E291"],
            dataLabels: { enabled: false },
            labels: data[0],
            legend: { position: "bottom" },
        });
    }

    async doWindowAction(name, resModel, domain = [], views = [[false, "list"], [false, "form"]], context = { create: false }) {
        await this.actionService.doAction({
            name: _t(name),
            type: "ir.actions.act_window",
            res_model: resModel,
            domain,
            views,
            context,
            target: "current",
        });
    }

    async onDashboardClick(ev) {
        if (ev.target.closest(".avail-property")) {
            return this.doWindowAction("Available Property", "property.details", [["stage", "=", "available"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".total-property")) {
            return this.doWindowAction("Total Property", "property.details", [], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".booked-property")) {
            return this.doWindowAction("Booked Property", "property.details", [["stage", "=", "booked"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".lease-property")) {
            return this.doWindowAction("Property On Lease", "property.details", [["stage", "=", "on_lease"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".sale-property")) {
            return this.doWindowAction("Property On Sale", "property.details", [["stage", "=", "sale"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".sold-property")) {
            return this.doWindowAction("Sold Property", "property.details", [["stage", "=", "sold"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".sold-total")) {
            return this.doWindowAction("Property Sold", "property.vendor", [["stage", "=", "sold"]], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".rent-total")) {
            return this.doWindowAction("Property Rent", "rent.invoice", ["|", ["type", "=", "rent"], ["type", "=", "full_rent"]], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".draft-contract")) {
            return this.doWindowAction("Draft Contract", "tenancy.details", [["contract_type", "=", "new_contract"]], [[false, "kanban"], [false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".running-contract")) {
            return this.doWindowAction("Running Contract", "tenancy.details", [["contract_type", "=", "running_contract"]], [[false, "kanban"], [false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".expire-contract")) {
            return this.doWindowAction("Expire Contract", "tenancy.details", [["contract_type", "=", "expire_contract"]], [[false, "kanban"], [false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".extend-contract")) {
            return this.doWindowAction("Extended Contract", "tenancy.details", [["is_extended", "=", true]], [[false, "kanban"], [false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".close-contract")) {
            return this.doWindowAction("Close Contracts", "tenancy.details", [["contract_type", "=", "close_contract"]], [[false, "kanban"], [false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".pending-invoice")) {
            return this.doWindowAction("Pending Invoice", "rent.invoice", [["payment_state", "=", "not_paid"]], [[false, "list"], [false, "form"]], { search_default_landlord: 1, create: false });
        }
        if (ev.target.closest(".booked-property-sale")) {
            return this.doWindowAction("Booked Property", "property.vendor", [["stage", "=", "booked"]], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".sale-sold")) {
            return this.doWindowAction("Sold Property", "property.vendor", [["stage", "=", "sold"]], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".refund-sold")) {
            return this.doWindowAction("Refund", "property.vendor", [["stage", "=", "refund"]], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".pending-invoice-sale")) {
            return this.doWindowAction("Sale Pending Invoices", "account.move", [["payment_state", "=", "not_paid"], ["sold_id", "!=", false]], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".view-region")) {
            return this.doWindowAction("Regions", "property.region", [], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".view-project")) {
            return this.doWindowAction("Projects", "property.project", [], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".view-subproject")) {
            return this.doWindowAction("Sub Projects", "property.sub.project", [], [[false, "list"], [false, "form"]]);
        }
        if (ev.target.closest(".view-customer")) {
            return this.doWindowAction("Customers", "res.partner", [["user_type", "=", "customer"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
        if (ev.target.closest(".view-landlord")) {
            return this.doWindowAction("Landlords", "res.partner", [["user_type", "=", "landlord"]], [[false, "list"], [false, "kanban"], [false, "form"]]);
        }
    }
}

registry.category("actions").add("property_dashboard", RentalDashboard);
