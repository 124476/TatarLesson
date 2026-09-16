(function() {
    const THEME_KEY = 'site-theme';
    const DEFAULT_THEME = 'light';

    function getPreferredTheme() {
        const stored = localStorage.getItem(THEME_KEY);
        if (stored) return stored;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return DEFAULT_THEME;
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateButtonIcon(theme);
    }

    window.toggleTheme = function() {
        const current = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
        const next = current === 'light' ? 'dark' : 'light';
        setTheme(next);
    };

    function updateButtonIcon(theme) {
        const btn = document.getElementById('themeToggleBtn');
        if (!btn) return;
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = theme === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        const initialTheme = getPreferredTheme();
        setTheme(initialTheme);
    });
})();