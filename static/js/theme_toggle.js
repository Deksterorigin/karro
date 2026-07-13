document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('theme-toggle');
    if (toggleBtn) {
        const sunIcon = toggleBtn.querySelector('.sun-icon');
        const moonIcon = toggleBtn.querySelector('.moon-icon');
        
        function updateIcons(theme) {
            if (theme === 'dark') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        }
        
        let currentTheme = localStorage.getItem('karro_theme') || 'light';
        updateIcons(currentTheme);
        
        toggleBtn.addEventListener('click', () => {
            currentTheme = localStorage.getItem('karro_theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            localStorage.setItem('karro_theme', newTheme);
            if (newTheme === 'dark') {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            updateIcons(newTheme);
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: newTheme }));
        });
    }
});
