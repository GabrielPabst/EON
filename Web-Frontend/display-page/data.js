// Configuration Example - Copy this to create your own data.js
// This file shows how to easily customize your website

const websiteData = {
    // BASIC SETTINGS - Change these first
    meta: {
        title: "EON",
        description: "The Eyes of Automation",
    },

    // TOP BAR - The promotional banner at the top
    topBar: {
        text: "🎉 New Desktop App - Try it now!",
        link: "#features"
    },

    // NAVIGATION - Main menu items
    navigation: {
        logo: "EON", // Your brand name
        links: [
            { text: "Features", href: "#features" },
            { text: "Marketplace", href: "#pricing" },
            { text: "Download", href: "#about" },
            { text: "Contact", href: "#contact" }
        ]
    },

    // HERO SECTION - Main landing area
    hero: {
        title: "EON",
        subtitle: "The Eyes of Automation",
        description: "Revolutionize your workflow with cutting-edge vision automation tools designed for efficiency and productivity.",
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
           // { icon: "fas fa-star", position: { top: "20%", left: "10%" }, delay: 0 },
           // { icon: "fas fa-heart", position: { top: "30%", right: "15%" }, delay: 1 },
           // { icon: "fas fa-bolt", position: { bottom: "30%", left: "20%" }, delay: 2 },
           // { icon: "fas fa-gem", position: { bottom: "40%", right: "10%" }, delay: 3 }
        ]
    },

    // FEATURES - Your app's key features
    features: {
        title: "Why Choose Us",
        items: [
            {
                icon: "fas fa-eye",
                title: "Inovative Vision Technology",
                description: "Give your automation the power of sight with our advanced computer vision features."
            },
            {
                icon: "fas fa-rocket",
                title: "Fast & Reliable",
                description: "Download and deploy makros in seconds using our optimized platform."
            },
            {
                icon: "fas fa-shield-alt",
                title: "Secure",
                description: "Full overview over all tasks executed on your machine."
            },
            {
                icon: "fas fa-users",
                title: "Collaborative",
                description: "Share makros and workflows with our growing community."
            },
            {
                icon: "fas fa-chart-line",
                title: "Analytics",
                description: "Detailed insights and reporting on makros in our dashboard."
            },
            {
                icon: "fas fa-headset",
                title: "Support",
                description: "Write us on Discord, via email or github and we will help you out."
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
                description: "Download our app and configure preferences."
            },
            {
                number: 3,
                title: "Launch",
                description: "Start using all the powerful features immediately."
            },
            ,
            {
                number: 5,
                title: "Build",
                description: "Record and create your own makros using our visual editor."
            },
            {
                number: 6,
                title: "Grow",
                description: "Scale up your automation using community makros."
            },
            {
                number: 7,
                title: "Publish",
                description: "Upload your own makros to share with the community and use everywhere."
            }
        ]
    },

    // STATISTICS - Show your app's performance/metrics
    stats: {
        title: "Our Impact",
        cards: [
            /*{
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
            },*/
            {
                title: "System Uptime",
                icon: "fas fa-server",
                type: "chart",
                chartType: "wave",
                value: "90.9%",
                change: "Last 2 days",
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
                    { label: "Makros Uploaded: 10", value: 90 },
                    { label: "Automations Executed: 200", value: 80 },
                    { label: "Account Signups: 15", value: 70 },
                    { label: "Images Recogniced: 600", value: 90 }
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

