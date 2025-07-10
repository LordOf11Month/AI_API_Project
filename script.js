document.addEventListener('DOMContentLoaded', () => {
    const disabledLink = document.querySelector('.btn.disabled');

    if (disabledLink) {
        disabledLink.addEventListener('click', (e) => {
            e.preventDefault();
            alert('Bu özellik henüz aktif değil. Lütfen daha sonra tekrar kontrol edin.');
        });
    }

    const sections = document.querySelectorAll('section');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = 1;
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    sections.forEach(section => {
        section.style.opacity = 0;
        section.style.transform = 'translateY(20px)';
        section.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
        observer.observe(section);
    });
}); 