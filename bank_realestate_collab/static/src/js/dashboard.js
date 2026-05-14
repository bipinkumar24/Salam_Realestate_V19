/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useState } = owl;

/**
 * BRE Dashboard Widget
 * Renders quick-stat KPI cards on the main dashboard board.
 */
class BREDashboardWidget extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            stats: {
                total_applications: 0,
                pending_review: 0,
                approved: 0,
                rejected: 0,
                total_properties: 0,
                available_properties: 0,
                total_financing: 0,
            },
            loading: true,
        });
        onWillStart(async () => {
            await this._loadStats();
        });
    }

    async _loadStats() {
        try {
            // Application stats
            const apps = await this.rpc("/web/dataset/call_kw", {
                model: "bre.customer.application",
                method: "search_read",
                args: [[]],
                kwargs: {
                    fields: ["bank_status", "financing_amount"],
                    limit: 0,
                },
            });

            const stats = {
                total_applications: apps.length,
                pending_review: apps.filter(a => a.bank_status === "pending").length,
                under_review: apps.filter(a => a.bank_status === "under_review").length,
                approved: apps.filter(a => a.bank_status === "approved").length,
                rejected: apps.filter(a => a.bank_status === "rejected").length,
                total_financing: apps.reduce((s, a) => s + (a.financing_amount || 0), 0),
            };

            // Property stats
            const props = await this.rpc("/web/dataset/call_kw", {
                model: "bre.property.listing",
                method: "search_read",
                args: [[]],
                kwargs: { fields: ["status"], limit: 0 },
            });

            stats.total_properties = props.length;
            stats.available_properties = props.filter(p => p.status === "available").length;

            this.state.stats = stats;
            this.state.loading = false;
        } catch (e) {
            console.warn("BRE Dashboard stats failed to load", e);
            this.state.loading = false;
        }
    }

    formatCurrency(value) {
        if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + "M";
        if (value >= 1_000) return (value / 1_000).toFixed(0) + "K";
        return value.toLocaleString();
    }
}

BREDashboardWidget.template = "bank_realestate_collab.DashboardWidget";

// Register as a systray item (lightweight – no DOM conflicts)
// Full board integration is via the native Odoo 'board' module.
registry.category("actions").add("bre_dashboard_action", BREDashboardWidget);
