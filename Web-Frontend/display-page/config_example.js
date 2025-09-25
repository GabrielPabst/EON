// Configuration Example - Copy this to create your own data.js
// This file shows how to easily customize your website

const websiteData = {
    // BASIC SETTINGS - Change these first
    meta: {
        title: "Your App Name - Description",
        description: "Your app description here"
    },

    // TOP BAR - The promotional banner at the top
    topBar: {
        text: "🎉 New Feature Launch - Try it now!",
        link: "#features"
    },

    // NAVIGATION - Main menu items
    navigation: {
        logo: "YourApp", // Your brand name
        links: [
            { text: "Features", href: "#features" },
            { text: "Pricing", href: "#pricing" },
            { text: "About", href: "#about" },
            { text: "Contact", href: "#contact" }
        ]
    },

    // HERO SECTION - Main landing area
    hero: {
        title: "Your App Name",
        subtitle: "Your Catchy Tagline",
        description: "A compelling description of what your app does and why people should care. Keep it concise but impactful.",
        buttons: [
            {
                text: "Get Started",
                icon: "fas fa-rocket",
                href: "#signup",
                type: "primary"
            },
            {
                text: "Learn More",
                icon: "fas fa-info-circle",
                href: "#about",
                type: "secondary"
            }
        ],
        // Floating background icons - customize these
        floatingIcons: [
            { icon: "fas fa-star", position: { top: "20%", left: "10%" }, delay: 0 },
            { icon: "fas fa-heart", position: { top: "30%", right: "15%" }, delay: 1 },
            { icon: "fas fa-bolt", position: { bottom: "30%", left: "20%" }, delay: 2 },
            { icon: "fas fa-gem", position: { bottom: "40%", right: "10%" }, delay: 3 }
        ]
    },

    // FEATURES - Your app's key features
    features: {
        title: "Why Choose Us",
        items: [
            {
                icon: "fas fa-rocket",
                title: "Fast & Reliable",
                description: "Lightning-fast performance with 99.9% uptime guarantee."
            },
            {
                icon: "fas fa-shield-alt",
                title: "Secure",
                description: "Enterprise-grade security to protect your data."
            },
            {
                icon: "fas fa-users",
                title: "Collaborative",
                description: "Work together with your team in real-time."
            },
            {
                icon: "fas fa-mobile-alt",
                title: "Mobile Ready",
                description: "Access from anywhere on any device."
            },
            {
                icon: "fas fa-chart-line",
                title: "Analytics",
                description: "Detailed insights and reporting dashboard."
            },
            {
                icon: "fas fa-headset",
                title: "24/7 Support",
                description: "Round-the-clock customer support when you need it."
            }
        ]
    },

    // USER GUIDE - Step-by-step instructions
    guide: {
        title: "Getting Started",
        description: "Follow these simple steps to get up and running quickly.",
        steps: [
            {
                number: 1,
                title: "Sign Up",
                description: "Create your free account in less than 60 seconds."
            },
            {
                number: 2,
                title: "Setup",
                description: "Configure your preferences and connect your tools."
            },
            {
                number: 3,
                title: "Launch",
                description: "Start using all the powerful features immediately."
            },
            {
                number: 4,
                title: "Grow",
                description: "Scale up as your needs grow with our flexible plans."
            }
        ]
    },

    // STATISTICS - Show your app's performance/metrics
    stats: {
        title: "Our Impact",
        cards: [
            {
                title: "Happy Users",
                icon: "fas fa-users",
                type: "chart",
                chartType: "line",
                value: "50,000+",
                change: "+150% this year",
                changeType: "positive",
                chartData: {
                    labels: Array.from({length: 12}, (_, i) => `Month ${i + 1}`),
                    values: [
                        1000, 1500, 2200, 3100, 4200, 5800, 7500, 9200, 11800, 
                        15200, 18900, 23400, 28100, 33800, 40200, 47500
                    ]
                }
            },
            {
                title: "System Uptime",
                icon: "fas fa-server",
                type: "chart",
                chartType: "wave",
                value: "99.9%",
                change: "Last 30 days",
                changeType: "neutral"
            },
            {
                title: "Customer Satisfaction",
                icon: "fas fa-smile",
                type: "progress",
                value: "95%",
                description: "Based on user reviews",
                progressValue: 95
            },
            {
                title: "Growth Metrics",
                icon: "fas fa-chart-bar",
                type: "bars",
                bars: [
                    { label: "New Signups: 12K", value: 80 },
                    { label: "Active Users: 45K", value: 90 },
                    { label: "Retention Rate: 85%", value: 85 },
                    { label: "Referrals: 3.2K", value: 65 }
                ]
            }
        ]
    },

    // FOOTER - Links and company info
    footer: {
        sections: [
            {
                title: "Product",
                links: [
                    { text: "Features", href: "#features" },
                    { text: "Pricing", href: "#pricing" },
                    { text: "Updates", href: "#updates" },
                    { text: "Beta", href: "#beta" }
                ]
            },
            {
                title: "Company",
                links: [
                    { text: "About", href: "#about" },
                    { text: "Blog", href: "#blog" },
                    { text: "Careers", href: "#careers" },
                    { text: "Press", href: "#press" }
                ]
            },
            {
                title: "Support",
                links: [
                    { text: "Help Center", href: "#help" },
                    { text: "Contact", href: "#contact" },
                    { text: "Status", href: "#status" },
                    { text: "Community", href: "#community" }
                ]
            },
            {
                title: "Legal",
                links: [
                    { text: "Privacy", href: "#privacy" },
                    { text: "Terms", href: "#terms" },
                    { text: "Security", href: "#security" },
                    { text: "Cookies", href: "#cookies" }
                ]
            }
        ],
        copyright: "&copy; 2024 Your Company. All rights reserved."
    }
};

// CUSTOMIZATION TIPS:
// 1. Change the color scheme by updating CSS variables in styles.css
// 2. Add more chart types in the stats section
// 3. Modify icons using Font Awesome classes
// 4. Update chart data arrays to reflect your real metrics
// 5. Add more steps to the user guide as needed
// 6. Customize floating icons and their positions