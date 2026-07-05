/** @odoo-module **/
// Albirru Backend Theme - Theme Service
// Compatible with Odoo 19

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { EventBus } from "@odoo/owl";

/**
 * Theme Service - Manages theme settings and preferences
 */
export const albirruThemeService = {
    dependencies: [],

    start() {
        const bus = new EventBus();
        let themeSettings = session.albirru_theme_settings || {};
        let bookmarks = session.albirru_bookmarks || [];
        const branding = session.albirru_branding || {};

        // Apply initial theme settings with error handling
        try {
            applyThemeSettings(themeSettings);
            // Apply menu background from theme settings
            applyMenuBackgrounds(themeSettings);
        } catch (e) {
            console.warn('Failed to apply initial theme settings:', e);
        }

        return {
            bus,

            /**
             * Get current theme settings
             */
            getSettings() {
                return { ...themeSettings };
            },

            /**
             * Get bookmarks
             */
            getBookmarks() {
                return [...bookmarks];
            },

            /**
             * Get branding info
             */
            getBranding() {
                return { ...branding };
            },

            /**
             * Check if dark mode is active
             */
            isDarkMode() {
                return themeSettings.dark_mode || false;
            },

            /**
             * Toggle dark mode
             */
            async toggleDarkMode() {
                const newValue = !themeSettings.dark_mode;
                themeSettings.dark_mode = newValue;

                // Apply immediately
                applyDarkMode(newValue);

                // Save to albirru.theme.config
                await this.saveThemeSetting('dark_mode', newValue);

                bus.trigger('THEME_CHANGED', { setting: 'dark_mode', value: newValue });
                return newValue;
            },

            /**
             * Check if sidebar is pinned
             */
            isSidebarPinned() {
                return themeSettings.sidebar_pinned !== false;
            },

            /**
             * Toggle sidebar pinned state
             */
            async toggleSidebarPinned() {
                const newValue = !themeSettings.sidebar_pinned;
                themeSettings.sidebar_pinned = newValue;

                // Apply immediately
                applySidebarPinned(newValue);

                // Save to albirru.theme.config
                await this.saveThemeSetting('sidebar_pinned', newValue);

                bus.trigger('THEME_CHANGED', { setting: 'sidebar_pinned', value: newValue });
                return newValue;
            },

            /**
             * Save setting to albirru.theme.config via controller
             */
            async saveThemeSetting(field, value) {
                try {
                    await rpc('/albirru_backend_theme/save_setting', {
                        field: field,
                        value: value,
                    });
                } catch (error) {
                    console.error('Failed to save theme setting:', error);
                }
            },

            /**
             * Add a bookmark
             */
            async addBookmark(name, url, icon = 'fa-bookmark') {
                try {
                    const result = await rpc('/albirru_backend_theme/add_bookmark', {
                        name,
                        url,
                        icon,
                    });

                    if (result.success) {
                        bookmarks.push(result.bookmark);
                        bus.trigger('BOOKMARKS_CHANGED', { bookmarks: [...bookmarks] });
                        return result.bookmark;
                    }
                } catch (error) {
                    console.error('Failed to add bookmark:', error);
                    throw error;
                }
            },

            /**
             * Remove a bookmark
             */
            async removeBookmark(bookmarkId) {
                try {
                    const result = await rpc('/albirru_backend_theme/remove_bookmark', {
                        bookmark_id: bookmarkId,
                    });

                    if (result.success) {
                        bookmarks = bookmarks.filter(b => b.id !== bookmarkId);
                        bus.trigger('BOOKMARKS_CHANGED', { bookmarks: [...bookmarks] });
                    }
                } catch (error) {
                    console.error('Failed to remove bookmark:', error);
                    throw error;
                }
            },

            /**
             * Update theme setting locally and in database
             */
            async updateSetting(key, value) {
                themeSettings[key] = value;

                // Automatically update has_menu_background flag
                if (key === 'menu_background') {
                    themeSettings.has_menu_background = !!value;
                    applyMenuBackgrounds(themeSettings);
                }

                applyThemeSettings(themeSettings);
                await this.saveThemeSetting(key, value);
                bus.trigger('THEME_CHANGED', { setting: key, value });
            },

            /**
             * Open the App Drawer
             */
            openAppDrawer() {
                bus.trigger('APP_DRAWER_OPEN');
            },

            /**
             * Close the App Drawer
             */
            closeAppDrawer() {
                bus.trigger('APP_DRAWER_CLOSE');
            },

            /**
             * Toggle the App Drawer
             */
            toggleAppDrawer() {
                bus.trigger('APP_DRAWER_TOGGLE');
            },
        };
    },
};

/**
 * Apply all theme settings to DOM
 */
function applyThemeSettings(settings) {
    const html = document.documentElement;

    // Theme style (rounded, standard, square)
    if (settings.theme_style) {
        html.setAttribute('data-albirru-style', settings.theme_style);
    }

    // Color scheme
    if (settings.color_scheme) {
        html.setAttribute('data-albirru-scheme', settings.color_scheme);
    }

    // Custom colors
    if (settings.use_custom_colors) {
        if (settings.primary_color) {
            html.style.setProperty('--albirru-primary', settings.primary_color);
            const rgb = hexToRgb(settings.primary_color);
            if (rgb) {
                html.style.setProperty('--albirru-primary-rgb', `${rgb.r}, ${rgb.g}, ${rgb.b}`);
            }
        }
        if (settings.secondary_color) {
            html.style.setProperty('--albirru-secondary', settings.secondary_color);
        }
        if (settings.accent_color) {
            html.style.setProperty('--albirru-accent', settings.accent_color);
        }
        html.setAttribute('data-albirru-custom-colors', 'true');
    } else {
        html.style.removeProperty('--albirru-primary');
        html.style.removeProperty('--albirru-primary-rgb');
        html.style.removeProperty('--albirru-secondary');
        html.style.removeProperty('--albirru-accent');
        html.setAttribute('data-albirru-custom-colors', 'false');
    }

    // Dark mode
    applyDarkMode(settings.dark_mode);

    // Sidebar position and pinned state
    applySidebarPosition(settings.sidebar_position);
    applySidebarPinned(settings.sidebar_pinned !== false);

    // Sidebar style


    // Font family
    if (settings.font_family) {
        html.setAttribute('data-albirru-font', settings.font_family);
        loadGoogleFont(settings.font_family);
    }

    // Font size
    if (settings.font_size) {
        html.setAttribute('data-albirru-font-size', settings.font_size);
    }

    // Input style
    if (settings.input_style) {
        html.setAttribute('data-albirru-input', settings.input_style);
    }

    // Button style
    if (settings.button_style) {
        html.setAttribute('data-albirru-button', settings.button_style);
    }

    // List view settings
    if (settings.list_row_height) {
        html.setAttribute('data-albirru-list', settings.list_row_height);
    }

    if (settings.list_sticky_header) {
        html.setAttribute('data-albirru-sticky', 'true');
    }

    // Chatter position
    if (settings.chatter_position) {
        html.setAttribute('data-albirru-chatter', settings.chatter_position);
    }

    // Loader style
    if (settings.loader_style) {
        html.setAttribute('data-albirru-loader', settings.loader_style);
    }
}

/**
 * Apply dark mode
 */
function applyDarkMode(isDark) {
    const html = document.documentElement;

    if (isDark) {
        html.classList.add('albirru-dark-mode');
        html.setAttribute('data-albirru-dark', 'true');
    } else {
        html.classList.remove('albirru-dark-mode');
        html.setAttribute('data-albirru-dark', 'false');
    }
}

/**
 * Apply sidebar position (left or top)
 */
function applySidebarPosition(position) {
    // Wait for o_web_client to be available
    const applyPosition = () => {
        const webClient = document.querySelector('.o_web_client');
        if (webClient) {
            // Remove all position classes
            webClient.classList.remove('albirru-sidebar-left', 'albirru-sidebar-top');

            // Add the appropriate class
            if (position === 'left') {
                webClient.classList.add('albirru-sidebar-left');
            } else if (position === 'top') {
                webClient.classList.add('albirru-sidebar-top');
            }
        } else {
            // Retry after a short delay if element not found yet
            setTimeout(applyPosition, 100);
        }
    };

    applyPosition();
}

/**
 * Apply sidebar pinned state
 */
function applySidebarPinned(isPinned) {
    const applyPinned = () => {
        const webClient = document.querySelector('.o_web_client');
        if (webClient) {
            if (isPinned) {
                webClient.classList.remove('albirru-sidebar-collapsed');
            } else {
                webClient.classList.add('albirru-sidebar-collapsed');
            }
        } else {
            // Retry after a short delay if element not found yet
            setTimeout(applyPinned, 100);
        }
    };

    applyPinned();
}



/**
 * Load Google Font dynamically
 */
function loadGoogleFont(fontFamily) {
    const fontMap = {
        inter: "Inter:wght@300;400;500;600;700",
        roboto: "Roboto:wght@300;400;500;700",
        poppins: "Poppins:wght@300;400;500;600;700",
        open_sans: "Open+Sans:wght@300;400;500;600;700",
        lato: "Lato:wght@300;400;700",
        nunito: "Nunito+Sans:wght@300;400;600;700",
    };

    const font = fontMap[fontFamily];
    if (!font) return;

    // Check if already loaded
    const existingLink = document.querySelector(`link[data-albirru-font="${fontFamily}"]`);
    if (existingLink) return;

    const fontUrl = `https://fonts.googleapis.com/css2?family=${font}&display=swap`;

    // Add preload hint for faster font loading
    const preload = document.createElement("link");
    preload.rel = "preload";
    preload.as = "style";
    preload.href = fontUrl;
    document.head.appendChild(preload);

    // Then load the actual stylesheet
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = fontUrl;
    link.setAttribute("data-albirru-font", fontFamily);
    document.head.appendChild(link);
}

/**
 * Utility: Convert HEX color to RGB
 */
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

/**
 * Apply menu background image and opacity from theme settings
 */
function applyMenuBackgrounds(settings) {
    const html = document.documentElement;

    // Apply menu background if available
    if (settings.has_menu_background) {
        // Use cache key if available, otherwise fallback to timestamp or nothing
        const cacheKey = settings.menu_bg_cache_key || new Date().getTime();
        html.style.setProperty('--albirru-menu-bg-image',
            `url('/albirru_backend_theme/menu_background?v=${cacheKey}')`);
        html.setAttribute('data-albirru-menu-bg', 'true');

        // Apply opacity from settings (convert % to decimal)
        const opacity = (settings.menu_bg_opacity || 15) / 100;
        html.style.setProperty('--albirru-menu-bg-opacity', opacity);
    } else {
        html.style.removeProperty('--albirru-menu-bg-image');
        html.style.removeProperty('--albirru-menu-bg-opacity');
        html.removeAttribute('data-albirru-menu-bg');
    }
}

// Register the service
registry.category("services").add("albirruTheme", albirruThemeService);

