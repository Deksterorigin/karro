document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const mainNav = document.getElementById('main-nav');
    const menuBackdrop = document.getElementById('menu-backdrop');
    const body = document.body;

    if (menuToggle && mainNav && menuBackdrop) {
        function toggleMenu() {
            const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
            menuToggle.setAttribute('aria-expanded', !isExpanded);
            menuToggle.classList.toggle('active');
            mainNav.classList.toggle('active');
            menuBackdrop.classList.toggle('active');
            body.classList.toggle('menu-open');
        }

        function closeMenu() {
            menuToggle.setAttribute('aria-expanded', 'false');
            menuToggle.classList.remove('active');
            mainNav.classList.remove('active');
            menuBackdrop.classList.remove('active');
            body.classList.remove('menu-open');
        }

        menuToggle.addEventListener('click', toggleMenu);
        menuBackdrop.addEventListener('click', closeMenu);

        // Закриваємо меню при кліку на посилання навігації (важливо для якірних посилань)
        const navLinks = mainNav.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', closeMenu);
        });
    }

    // Синхронізація мобільного та десктопного перемикача мов
    const langSelectDesktop = document.getElementById('lang-select');
    const langSelectMobile = document.getElementById('lang-select-mobile');

    if (langSelectDesktop && langSelectMobile) {
        langSelectMobile.value = langSelectDesktop.value;

        langSelectDesktop.addEventListener('change', () => {
            langSelectMobile.value = langSelectDesktop.value;
        });

        langSelectMobile.addEventListener('change', (e) => {
            langSelectDesktop.value = e.target.value;
            langSelectDesktop.dispatchEvent(new Event('change'));
        });
    }
});
