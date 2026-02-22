/**
 * Theme Configuration API Helper
 * ─────────────────────────────────────────────────────────────────────────────
 * INTEGRATION NOTE:
 *   The FRONTEND_INTEGRATION_GUIDE.md currently defines:
 *     • POST /generate-paper
 *     • WS   /ws/{session_id}
 *
 *   There is NO dedicated backend endpoint for theme configuration yet.
 *   This module therefore persists theme settings in localStorage so the
 *   behaviour is fully functional today, while the API surface is structured
 *   to be a drop-in replacement the moment the backend ships, e.g.:
 *
 *     GET  /settings/theme  → ThemeConfig
 *     PUT  /settings/theme  → ThemeConfig
 *
 *   To wire a real backend, replace the two stub functions below with:
 *     export const getThemeConfig  = () => apiFetch<ThemeConfig>("/settings/theme");
 *     export const updateThemeConfig = (data) =>
 *         apiFetch<ThemeConfig>("/settings/theme", { method: "PUT", json: data });
 * ─────────────────────────────────────────────────────────────────────────────
 */

const LS_KEY = "qpilot_theme_config";

/** The two palette options available for selection. */
export type ThemeName = "ocean" | "royal";

/** The two mode options available for selection. */
export type ThemeMode = "light" | "dark";

/** Shape of the theme configuration object (shared with Zustand store). */
export interface ThemeConfig {
    theme: ThemeName;
    mode: ThemeMode;
}

/** Default theme applied on first load. */
const DEFAULT_CONFIG: ThemeConfig = {
    theme: "ocean",
    mode: "light",
};

/**
 * Simulates GET /settings/theme
 * Returns the persisted theme config, or the default if none exists yet.
 * Wraps in a Promise to match the signature a real HTTP call would have.
 */
export async function getThemeConfig(): Promise<ThemeConfig> {
    // Simulate a small network delay so loading skeleton is visible during dev.
    await new Promise((r) => setTimeout(r, 600));

    try {
        const stored = localStorage.getItem(LS_KEY);
        if (stored) {
            return JSON.parse(stored) as ThemeConfig;
        }
    } catch {
        // Corrupt storage – fall back to default.
    }
    return { ...DEFAULT_CONFIG };
}

/**
 * Simulates PUT /settings/theme
 * Persists the config to localStorage and returns the saved object.
 */
export async function updateThemeConfig(
    data: ThemeConfig
): Promise<ThemeConfig> {
    // Simulate a small network delay so the spinner is visible during dev.
    await new Promise((r) => setTimeout(r, 800));

    localStorage.setItem(LS_KEY, JSON.stringify(data));
    return { ...data };
}
