// Main JavaScript file for EON website
document.addEventListener('DOMContentLoaded', function() {
    initializeWebsite();
    initializeAnimations();
    initializeCharts();
    initializeEvents();
});

// Initialize website with data
function initializeWebsite() {
    populateMetadata();
    populateTopBar();
    populateNavigation();
    populateHero();
    populateFeatures();
    populateGuide();
    populateStats();
    populateFooter();
}

// Populate metadata
function populateMetadata() {
    document.getElementById('page-title').textContent = websiteData.meta.title;
}

// Populate top bar
function populateTopBar() {
    const topBarLink = document.getElementById('top-bar-link');
    topBarLink.textContent = websiteData.topBar.text;
    topBarLink.href = websiteData.topBar.link;
}

// Populate navigation
function populateNavigation() {
    const logo = document.getElementById('nav-logo');
    const navLinks = document.getElementById('nav-links');
    
    logo.textContent = websiteData.navigation.logo;
    
    websiteData.navigation.links.forEach(link => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = link.href;
        a.textContent = link.text;
        li.appendChild(a);
        navLinks.appendChild(li);
    });
}

// Populate hero section
function populateHero() {
    const title = document.getElementById('hero-title');
    const subtitle = document.getElementById('hero-subtitle');
    const description = document.getElementById('hero-description');
    const ctaButtons = document.getElementById('cta-buttons');
    const floatingElements = document.getElementById('floating-elements');
    
    title.textContent = websiteData.hero.title;
    subtitle.textContent = websiteData.hero.subtitle;
    description.textContent = websiteData.hero.description;
    
    // Add CTA buttons
    websiteData.hero.buttons.forEach(button => {
        const a = document.createElement('a');
        a.href = button.href;
        a.className = `btn btn-${button.type}`;
        a.innerHTML = `<i class="${button.icon}"></i> ${button.text}`;
        ctaButtons.appendChild(a);
    });
    
    // Add floating icons
    websiteData.hero.floatingIcons.forEach(icon => {
        const i = document.createElement('i');
        i.className = `${icon.icon} floating-icon`;
        
        // Set position
        Object.keys(icon.position).forEach(prop => {
            i.style[prop] = icon.position[prop];
        });
        
        i.style.animationDelay = `${icon.delay}s`;
        floatingElements.appendChild(i);
    });
}

// Populate features section
function populateFeatures() {
    const featuresTitle = document.getElementById('features-title');
    const featureGrid = document.getElementById('feature-grid');
    
    featuresTitle.textContent = websiteData.features.title;
    
    websiteData.features.items.forEach(feature => {
        const card = document.createElement('div');
        card.className = 'feature-card fade-in';
        card.innerHTML = `
            <div class="feature-icon">
                <i class="${feature.icon}"></i>
            </div>
            <h3>${feature.title}</h3>
            <p>${feature.description}</p>
        `;
        featureGrid.appendChild(card);
    });
}

// Populate guide section
function populateGuide() {
    const guideTitle = document.getElementById('guide-title');
    const guideDescription = document.getElementById('guide-description');
    const guideSteps = document.getElementById('guide-steps');
    
    guideTitle.textContent = websiteData.guide.title;
    guideDescription.textContent = websiteData.guide.description;
    
    websiteData.guide.steps.forEach(step => {
        const stepCard = document.createElement('div');
        stepCard.className = 'step-card fade-in';
        stepCard.innerHTML = `
            <div class="step-header">
                <div class="step-number">${step.number}</div>
                <h3>${step.title}</h3>
            </div>
            <p>${step.description}</p>
        `;
        guideSteps.appendChild(stepCard);
    });
}

// Populate stats section
function populateStats() {
    const statsTitle = document.getElementById('stats-title');
    const statsGrid = document.getElementById('stats-grid');
    
    statsTitle.textContent = websiteData.stats.title;
    
    websiteData.stats.cards.forEach((card, index) => {
        const statCard = document.createElement('div');
        statCard.className = 'stat-card fade-in';
        
        let cardContent = `
            <h3>
                <i class="${card.icon}"></i>
                ${card.title}
            </h3>
        `;
        
        if (card.type === 'chart') {
            cardContent += `
                <div class="chart-container">
                    <canvas id="${card.chartType}Chart${index}"></canvas>
                </div>
                <div class="stat-value">
                    <div class="stat-number">${card.value}</div>
                    <div class="stat-change ${card.changeType}">${card.change}</div>
                </div>
            `;
        } else if (card.type === 'progress') {
            cardContent += `
                <div class="progress-ring-container">
                    <div class="progress-ring-wrapper">
                        <svg width="150" height="150" class="progress-ring">
                            <circle cx="75" cy="75" r="65" fill="none" stroke="rgba(255, 119, 0, 0.2)" stroke-width="8"/>
                            <circle cx="75" cy="75" r="65" fill="none" stroke="#ff7700" stroke-width="8" 
                                    stroke-dasharray="408" stroke-dashoffset="408" stroke-linecap="round" 
                                    class="progress-ring-bar" data-value="${card.progressValue}"/>
                        </svg>
                        <div class="progress-value">
                            <div class="progress-value-number">${card.value}</div>
                            <div class="progress-value-label">Satisfaction</div>
                        </div>
                    </div>
                </div>
                <div class="stat-value">
                    <div class="stat-change neutral">${card.description}</div>
                </div>
            `;
        } else if (card.type === 'bars') {
            cardContent += `
                <div class="data-bars">
                    ${card.bars.map(bar => `
                        <div class="data-bar">
                            <div class="data-bar-fill" data-width="${bar.value}%" style="width: 0%;">
                                ${bar.label}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        statCard.innerHTML = cardContent;
        statsGrid.appendChild(statCard);
    });
}

// Populate footer
function populateFooter() {
    const footerContent = document.getElementById('footer-content');
    const footerText = document.getElementById('footer-text');
    
    websiteData.footer.sections.forEach(section => {
        const footerSection = document.createElement('div');
        footerSection.className = 'footer-section';
        
        let sectionHTML = `<h3>${section.title}</h3>`;
        section.links.forEach(link => {
            sectionHTML += `<a href="${link.href}">${link.text}</a>`;
        });
        
        footerSection.innerHTML = sectionHTML;
        footerContent.appendChild(footerSection);
    });
    
    footerText.innerHTML = websiteData.footer.copyright;
}

// Initialize animations
function initializeAnimations() {
    createParticleSystem();
    initializeScrollAnimations();
    initializeHeroAnimations();
    initializeFloatingIconAnimations();
}

// Particle system
function createParticleSystem() {
    function createParticle() {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * window.innerWidth + 'px';
        particle.style.top = window.innerHeight + 'px';
        particle.style.width = Math.random() * 4 + 1 + 'px';
        particle.style.height = particle.style.width;
        particle.style.opacity = Math.random() * 0.5 + 0.1;
        document.body.appendChild(particle);

        anime({
            targets: particle,
            translateY: -window.innerHeight - 100,
            translateX: (Math.random() - 0.5) * 200,
            opacity: [particle.style.opacity, 0],
            duration: Math.random() * 3000 + 5000,
            easing: 'linear',
            complete: () => {
                if (particle.parentNode) {
                    particle.parentNode.removeChild(particle);
                }
            }
        });
    }

    setInterval(createParticle, 200);
}

// Scroll animations
function initializeScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.classList.contains('animated')) {
                // Mark as animated to prevent re-triggering
                entry.target.classList.add('animated');
                
                anime({
                    targets: entry.target,
                    opacity: [0, 1],
                    translateY: [30, 0],
                    duration: 800,
                    easing: 'easeOutQuart',
                    delay: Math.random() * 200,
                    complete: () => {
                        // Unobserve after animation completes to prevent re-triggering
                        observer.unobserve(entry.target);
                    }
                });
            }
        });
    }, observerOptions);

    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });
}

// Hero animations
function initializeHeroAnimations() {
    anime.timeline({
        loop: false
    })
    .add({
        targets: '.hero-title',
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 1000,
        easing: 'easeOutElastic(1, .6)',
        delay: 500
    })
    .add({
        targets: '.hero-subtitle',
        translateY: [30, 0],
        opacity: [0, 1],
        duration: 800,
        easing: 'easeOutQuart',
    }, '-=600')
    .add({
        targets: '.hero-description',
        translateY: [30, 0],
        opacity: [0, 1],
        duration: 800,
        easing: 'easeOutQuart',
    }, '-=600')
    .add({
        targets: '.cta-buttons .btn',
        scale: [0.8, 1],
        opacity: [0, 1],
        duration: 600,
        easing: 'easeOutBack',
        delay: anime.stagger(100)
    }, '-=400');
}

// Floating icons animation
function initializeFloatingIconAnimations() {
    anime({
        targets: '.floating-icon',
        rotateZ: 360,
        duration: 20000,
        loop: true,
        easing: 'linear'
    });
}

// Initialize charts
function initializeCharts() {
    setTimeout(() => {
        createLineCharts();
        createWaveCharts();
        initializeProgressRings();
        initializeDataBars();
    }, 1000);
}

// Create line charts
function createLineCharts() {
    const lineChartCanvases = document.querySelectorAll('canvas[id*="lineChart"]');
    
    lineChartCanvases.forEach((canvas, index) => {
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.offsetWidth * 2;
        const height = canvas.height = canvas.offsetHeight * 2;
        ctx.scale(2, 2);
        
        const chartData = websiteData.stats.cards.find(card => card.chartType === 'line');
        if (!chartData || !chartData.chartData) return;
        
        const data = chartData.chartData.values;
        
        function drawChart() {
            ctx.clearRect(0, 0, width/2, height/2);
            
            // Draw grid
            ctx.strokeStyle = 'rgba(255, 119, 0, 0.1)';
            ctx.lineWidth = 1;
            for (let i = 0; i < 5; i++) {
                const y = (height/2) * (i / 4) * 0.8 + 20;
                ctx.beginPath();
                ctx.moveTo(20, y);
                ctx.lineTo(width/2 - 20, y);
                ctx.stroke();
            }
            
            // Draw line chart
            ctx.strokeStyle = '#ff7700';
            ctx.lineWidth = 3;
            ctx.beginPath();
            
            const maxValue = Math.max(...data);
            const minValue = Math.min(...data);
            
            for (let i = 0; i < data.length; i++) {
                const x = 20 + (width/2 - 40) * (i / (data.length - 1));
                const normalizedValue = (data[i] - minValue) / (maxValue - minValue);
                const y = height/2 - 20 - normalizedValue * (height/2 - 40);
                
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            
            // Add glow effect
            ctx.shadowColor = '#ff7700';
            ctx.shadowBlur = 10;
            ctx.stroke();
            ctx.shadowBlur = 0;
        }
        
        drawChart();
    });
}

// Create wave charts
function createWaveCharts() {
    const waveChartCanvases = document.querySelectorAll('canvas[id*="waveChart"]');
    
    waveChartCanvases.forEach(canvas => {
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.offsetWidth * 2;
        const height = canvas.height = canvas.offsetHeight * 2;
        ctx.scale(2, 2);
        
        let angle = 0;
        
        function drawWaveChart() {
            ctx.clearRect(0, 0, width/2, height/2);
            
            // Draw performance waves
            ctx.strokeStyle = '#ff7700';
            ctx.lineWidth = 2;
            ctx.beginPath();
            
            for (let x = 0; x < width/2; x += 2) {
                const baseY = height/4 + Math.sin((x + angle) * 0.02) * 20;
                const y = baseY + Math.sin((x + angle) * 0.05) * 10;
                
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            
            // Second wave
            ctx.strokeStyle = 'rgba(255, 119, 0, 0.6)';
            ctx.beginPath();
            for (let x = 0; x < width/2; x += 2) {
                const baseY = height/2 + Math.sin((x + angle + 100) * 0.015) * 15;
                const y = baseY + Math.sin((x + angle + 100) * 0.04) * 8;
                
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            
            // Third wave
            ctx.strokeStyle = 'rgba(255, 119, 0, 0.3)';
            ctx.beginPath();
            for (let x = 0; x < width/2; x += 2) {
                const baseY = 3*height/4 + Math.sin((x + angle + 200) * 0.01) * 12;
                const y = baseY + Math.sin((x + angle + 200) * 0.03) * 6;
                
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            
            angle += 2;
            requestAnimationFrame(drawWaveChart);
        }
        
        drawWaveChart();
    });
}

// Initialize progress rings
function initializeProgressRings() {
    const progressRings = document.querySelectorAll('.progress-ring-bar');
    
    progressRings.forEach(ring => {
        const value = parseInt(ring.dataset.value);
        const circumference = 2 * Math.PI * 65; // radius = 65
        const offset = circumference - (value / 100) * circumference;
        
        anime({
            targets: ring,
            strokeDashoffset: [circumference, offset],
            duration: 2000,
            easing: 'easeOutQuart',
            delay: 800
        });
    });
}

// Initialize data bars
function initializeDataBars() {
    const dataBars = document.querySelectorAll('.data-bar-fill');
    
    dataBars.forEach((bar, index) => {
        const targetWidth = bar.dataset.width;
        
        anime({
            targets: bar,
            width: targetWidth,
            duration: 1500,
            easing: 'easeOutQuart',
            delay: 1000 + index * 200
        });
    });
}

// Initialize events
function initializeEvents() {
    initializeSmoothScrolling();
    initializeFeatureCardHovers();
    initializeDynamicBackground();
}

// Smooth scrolling
function initializeSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Feature card hover effects
function initializeFeatureCardHovers() {
    document.querySelectorAll('.feature-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            anime({
                targets: card.querySelector('.feature-icon'),
                scale: 1.1,
                rotateY: 360,
                duration: 600,
                easing: 'easeOutBack'
            });
        });

        card.addEventListener('mouseleave', () => {
            anime({
                targets: card.querySelector('.feature-icon'),
                scale: 1,
                rotateY: 0,
                duration: 400,
                easing: 'easeOutQuart'
            });
        });
    });
}

// Dynamic background gradient
function initializeDynamicBackground() {
    let gradientAngle = 0;
    setInterval(() => {
        gradientAngle += 0.5;
        const hero = document.querySelector('.hero');
        if (hero) {
            hero.style.background = `radial-gradient(ellipse at center, rgba(255, 119, 0, ${0.1 + Math.sin(gradientAngle * 0.01) * 0.05}) 0%, rgba(0, 0, 0, 1) 70%)`;
        }
    }, 50);
}