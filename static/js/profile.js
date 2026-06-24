function showSection(name, btn) {
    document.querySelectorAll('.section-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById('section-' + name);
    if (panel) panel.classList.add('active');
    if (btn) btn.classList.add('active');
}

// Language syncing logic
function switchLang(lang) {
    // Locate global select if exists or set directly
    const globalSelect = document.getElementById('lang-select');
    if (globalSelect) {
        globalSelect.value = lang;
        globalSelect.dispatchEvent(new Event('change'));
    } else {
        localStorage.setItem('lang', lang);
        location.reload();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const tab = params.get('tab');
    if (tab) {
        const btn = document.querySelector(`button[onclick*="'${tab}'"]`);
        if (btn) {
            showSection(tab, btn);
        }
    } else if (params.has('edit_station') || params.get('action') === 'new_station') {
        const btn = document.querySelector(`button[onclick*="'station'"]`);
        if (btn) {
            showSection('station', btn);
        }
    }

    // Set matching value on lang select if active
    const savedLang = localStorage.getItem('lang') || 'uk';
    const profLangSelect = document.getElementById('profile-lang-select');
    if (profLangSelect) {
        profLangSelect.value = savedLang;
    }
});