/** @odoo-module **/
// Albirru Backend Theme - Global Search Modal
// Compatible with Odoo 19

import { Component, useState, useRef, onMounted, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { fuzzyLookup } from "@web/core/utils/search";

/**
 * Global Search Modal Component
 */
export class AlbirruSearchModal extends Component {
    static template = "albirru_backend_theme.SearchModal";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");

        this.inputRef = useRef("searchInput");

        this.state = useState({
            isOpen: false,
            query: "",
            searchType: "menu", // "menu" or "records"
            results: [],
            selectedIndex: 0,
            isLoading: false,
            selectedModel: "all",
            availableModels: [],
        });

        // Build searchable menus
        this._searchableMenus = this._buildSearchableMenus();

        // Register hotkey (Ctrl+K) - Note: meta key is not supported in Odoo 19
        useHotkey("control+k", () => this.open(), { global: true });

        // Listen for custom event from systray button
        useExternalListener(window, "albirru-open-search-modal", () => this.open());

        // Load available models for record search
        this._loadAvailableModels();
    }

    /**
     * Build searchable menus from menu service
     */
    _buildSearchableMenus() {
        const menus = {};

        for (const app of this.menuService.getApps()) {
            const tree = this.menuService.getMenuAsTree(app.id);
            this._flattenMenuTree(tree, "", menus);
        }

        return menus;
    }

    /**
     * Flatten menu tree for searching
     */
    _flattenMenuTree(menu, prefix, result) {
        if (!menu) return;

        const fullName = prefix ? `${prefix} / ${menu.name}` : menu.name;

        if (menu.actionID) {
            result[fullName] = {
                id: menu.id,
                name: fullName,
                actionID: menu.actionID,
                actionPath: menu.actionPath,
            };
        }

        if (menu.childrenTree) {
            for (const child of menu.childrenTree) {
                this._flattenMenuTree(child, fullName, result);
            }
        }
    }

    /**
     * Load available models for record search
     */
    async _loadAvailableModels() {
        try {
            // Use standard RPC call for Odoo 19
            const models = await rpc("/web/dataset/call_kw", {
                model: "ir.model",
                method: "search_read",
                args: [
                    [["transient", "=", false]],
                    ["id", "name", "model"]
                ],
                kwargs: {
                    limit: 100,
                    order: "name",
                },
            });
            this.state.availableModels = models || [];
        } catch (error) {
            // Silently fail - record search is optional feature
            this.state.availableModels = [];
        }
    }

    /**
     * Open search modal
     */
    open() {
        this.state.isOpen = true;
        this.state.query = "";
        this.state.results = [];
        this.state.selectedIndex = 0;

        // Focus input after modal opens
        setTimeout(() => {
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        }, 100);
    }

    /**
     * Close search modal
     */
    close() {
        this.state.isOpen = false;
        this.state.query = "";
        this.state.results = [];
    }

    /**
     * Handle input change
     */
    onInputChange(ev) {
        this.state.query = ev.target.value;
        this.state.selectedIndex = 0;
        this._performSearch();
    }

    /**
     * Perform search based on type
     */
    async _performSearch() {
        const query = this.state.query.trim();

        if (!query) {
            this.state.results = [];
            return;
        }

        if (this.state.searchType === "menu") {
            this._searchMenus(query);
        } else {
            await this._searchRecords(query);
        }
    }

    /**
     * Search menus
     */
    _searchMenus(query) {
        const menuNames = Object.keys(this._searchableMenus);
        const matches = fuzzyLookup(query, menuNames, (name) => name);

        this.state.results = matches.slice(0, 10).map((name) => ({
            type: "menu",
            ...this._searchableMenus[name],
        }));
    }

    /**
     * Search records
     */
    async _searchRecords(query) {
        this.state.isLoading = true;

        try {
            const model = this.state.selectedModel;
            const domain = [["name", "ilike", query]];
            const fields = ["id", "name", "display_name"];

            if (model === "all") {
                // Search in priority models (common across most Odoo installations)
                const priorityModels = [
                    "res.partner",
                    "hr.employee",
                    "sale.order",
                    "purchase.order",
                    "crm.lead",
                    "project.task",
                    "project.project",
                    "account.move",
                    "product.product",
                    "product.template",
                    "stock.picking",
                    "hr.department",
                    "res.users",
                ];

                // Use Promise.all for parallel requests
                const searchPromises = priorityModels.map(async (m) => {
                    try {
                        const records = await rpc("/web/dataset/call_kw", {
                            model: m,
                            method: "search_read",
                            args: [domain, fields],
                            kwargs: { limit: 3 },
                        });
                        return (records || []).map((record) => ({
                            type: "record",
                            id: record.id,
                            name: record.display_name || record.name,
                            model: m,
                            modelName: m.replace(/\./g, " ").replace(/\b\w/g, l => l.toUpperCase()),
                        }));
                    } catch (e) {
                        // Model might not exist or no access - skip silently
                        return [];
                    }
                });

                const allResults = await Promise.all(searchPromises);
                const results = allResults.flat();
                this.state.results = results.slice(0, 15);
            } else {
                const records = await rpc("/web/dataset/call_kw", {
                    model: model,
                    method: "search_read",
                    args: [domain, fields],
                    kwargs: { limit: 10 },
                });

                this.state.results = (records || []).map((record) => ({
                    type: "record",
                    id: record.id,
                    name: record.display_name || record.name,
                    model: model,
                    modelName: model,
                }));
            }
        } catch (error) {
            // Silently fail - show empty results
            this.state.results = [];
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Handle keyboard navigation
     */
    onKeyDown(ev) {
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.state.selectedIndex = Math.min(
                    this.state.selectedIndex + 1,
                    this.state.results.length - 1
                );
                break;
            case "ArrowUp":
                ev.preventDefault();
                this.state.selectedIndex = Math.max(this.state.selectedIndex - 1, 0);
                break;
            case "Enter":
                ev.preventDefault();
                this.selectResult(this.state.results[this.state.selectedIndex]);
                break;
            case "Escape":
                this.close();
                break;
        }
    }

    /**
     * Select a search result
     */
    async selectResult(result) {
        if (!result) return;

        this.close();

        if (result.type === "menu") {
            // Navigate to menu
            const url = result.actionPath
                ? `/odoo/${result.actionPath}`
                : `/odoo/action-${result.actionID}`;
            window.location.href = url;
        } else if (result.type === "record") {
            // Navigate to record
            window.location.href = `/odoo/${result.model}/${result.id}`;
        }
    }

    /**
     * Change search type
     */
    onSearchTypeChange(type) {
        this.state.searchType = type;
        this.state.results = [];
        this.state.selectedIndex = 0;
        this._performSearch();
    }

    /**
     * Change selected model
     */
    onModelChange(ev) {
        this.state.selectedModel = ev.target.value;
        this._performSearch();
    }

    /**
     * Handle backdrop click
     */
    onBackdropClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.close();
        }
    }
}

/**
 * Systray Search Item Component
 */
export class AlbirruSearchSystray extends Component {
    static template = "albirru_backend_theme.SearchSystrayItem";
    static props = {};

    onClick() {
        const event = new CustomEvent("albirru-open-search-modal");
        window.dispatchEvent(event);
    }
}

// Register components
if (session.albirru_theme_installed) {
    registry.category("main_components").add("AlbirruSearchModal", {
        Component: AlbirruSearchModal,
        props: {},
    }, { sequence: 100 });

    registry.category("systray").add("AlbirruSearchSystray", {
        Component: AlbirruSearchSystray,
    }, { sequence: 5 }); // Low sequence to appear on the left side of systray
}
