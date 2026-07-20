const initScrollAnimations = () => {
    console.log('Initializing scroll animations...');
    
    // Перевіряємо, чи завантажені бібліотеки GSAP та ScrollTrigger
    if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
        console.warn('GSAP or ScrollTrigger is not loaded.');
        return;
    }

    // Реєструємо плагін ScrollTrigger у GSAP
    gsap.registerPlugin(ScrollTrigger);

    // ── 1. АНІМАЦІЯ ПОЯВИ HERO-БЛОКУ (при завантаженні сторінки) ──
    const heroTl = gsap.timeline({ 
        defaults: { 
            ease: 'power2.out', 
            duration: 0.8 
        } 
    });

    // Поступова поява та плавний підйом контенту в Hero-блоці
    heroTl.from('.hero-badge', { opacity: 0, y: 15, delay: 0.1 })
          .from('.hero-title', { opacity: 0, y: 20 }, '-=0.6')
          .from('.hero-description', { opacity: 0, y: 15 }, '-=0.6')
          .from('.hero-search-card', { opacity: 0, y: 20 }, '-=0.6')
          .from('.hero-image-wrapper', { 
              opacity: 0, 
              scale: 0.96, 
              duration: 1.0, 
              ease: 'power1.out' 
          }, '-=0.8');

    // ── 2. АНІМАЦІЇ ДЛЯ СЕКЦІЇ "ЯК ЦЕ ПРАЦЮЄ" ──
    // Заголовок секції
    gsap.from('.section-works .section-header-centered', {
        opacity: 0,
        y: 20,
        duration: 0.8,
        ease: 'power2.out',
        scrollTrigger: {
            trigger: '.section-works',
            start: 'top 95%',
            toggleActions: 'play none none reverse'
        }
    });

    // Картки кроків інструкції
    gsap.from('.works-steps-grid .step-card', {
        opacity: 0,
        y: 25,
        duration: 0.7,
        stagger: 0.12,
        ease: 'power2.out',
        clearProps: 'opacity,transform',
        scrollTrigger: {
            trigger: '.works-steps-grid',
            start: 'top 92%',
            toggleActions: 'play none none reverse'
        }
    });

    // ── 3. АНІМАЦІЯ СЕКЦІЇ ЗАКЛИКУ ДО ДІЇ ДЛЯ БІЗНЕСУ ──
    gsap.from('.section-business .business-content-card', {
        opacity: 0,
        y: 30,
        scale: 0.98,
        duration: 0.9,
        ease: 'power2.out',
        clearProps: 'opacity,transform,scale',
        scrollTrigger: {
            trigger: '.section-business',
            start: 'top 95%',
            toggleActions: 'play none none reverse'
        }
    });

    // ── 4. АНІМАЦІЯ СЕКЦІЇ З ПРОФІЛЕМ АВТОРА ──
    gsap.from('.section-author .author-profile-card', {
        opacity: 0,
        y: 25,
        duration: 0.8,
        ease: 'power2.out',
        clearProps: 'opacity,transform',
        scrollTrigger: {
            trigger: '.section-author',
            start: 'top 95%',
            toggleActions: 'play none none reverse'
        }
    });
};

// Безпечний запуск анімації залежно від стану завантаження DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScrollAnimations);
} else {
    initScrollAnimations();
}
