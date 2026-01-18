/** @type {import('tailwindcss').Config} */
const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  darkMode: ["class"],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', ...defaultTheme.fontFamily.sans],
        display: ['var(--font-display)', 'sans-serif'],
        mono: ['var(--font-mono)', ...defaultTheme.fontFamily.mono],
      },
      colors: {
        border: "hsl(var(--border))",
        "border-hover": "hsl(var(--border-hover))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: {
          DEFAULT: "hsl(var(--background))",
          deep: "hsl(var(--background-deep))",
          elevated: "hsl(var(--background-elevated))",
          surface: "hsl(var(--background-surface))",
        },
        foreground: {
          DEFAULT: "hsl(var(--foreground))",
          muted: "hsl(var(--foreground-muted))",
          dim: "hsl(var(--foreground-dim))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          dark: "hsl(var(--destructive-dark))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Vermillion accent colors
        vermillion: {
          DEFAULT: "hsl(var(--vermillion))",
          light: "hsl(var(--vermillion-light))",
          dark: "hsl(var(--vermillion-dark))",
        },
        // Semantic colors
        success: {
          DEFAULT: "hsl(var(--success))",
          vibrant: "hsl(var(--success-vibrant))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        // Glass colors
        glass: {
          bg: "hsl(var(--glass-bg) / <alpha-value>)",
          border: "hsl(var(--glass-border) / <alpha-value>)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      backdropBlur: {
        xs: '2px',
        sm: 'var(--blur-sm)',
        md: 'var(--blur-md)',
        lg: 'var(--blur-lg)',
        xl: 'var(--blur-xl)',
      },
      boxShadow: {
        'glow-vermillion': '0 0 20px hsl(var(--vermillion) / 0.3)',
        'glow-vermillion-sm': '0 0 10px hsl(var(--vermillion) / 0.2)',
        'glow-vermillion-lg': '0 0 30px hsl(var(--vermillion) / 0.4)',
        'glow-success': '0 0 15px hsl(var(--success) / 0.3)',
        'glow-destructive': '0 0 15px hsl(var(--destructive) / 0.3)',
        'glass': '0 4px 30px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        'glass-elevated': '0 8px 40px rgba(0, 0, 0, 0.4), 0 0 80px hsl(var(--vermillion) / 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "fade-in": {
          from: { opacity: 0, transform: "translateY(10px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        "fade-in-up": {
          from: { opacity: 0, transform: "translateY(20px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        "slide-in-right": {
          from: { opacity: 0, transform: "translateX(20px)" },
          to: { opacity: 1, transform: "translateX(0)" },
        },
        "slide-in-left": {
          from: { opacity: 0, transform: "translateX(-20px)" },
          to: { opacity: 1, transform: "translateX(0)" },
        },
        "vermillion-pulse": {
          "0%, 100%": {
            boxShadow: "0 4px 30px rgba(0, 0, 0, 0.3), 0 0 20px hsl(var(--vermillion) / 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.05)"
          },
          "50%": {
            boxShadow: "0 4px 30px rgba(0, 0, 0, 0.3), 0 0 40px hsl(var(--vermillion) / 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)"
          },
        },
        "glass-shimmer": {
          from: { backgroundPosition: "-200% 0" },
          to: { backgroundPosition: "200% 0" },
        },
        "scale-in": {
          from: { opacity: 0, transform: "scale(0.95)" },
          to: { opacity: 1, transform: "scale(1)" },
        },
        "number-tick": {
          from: { opacity: 0, transform: "translateY(-8px)" },
          to: { opacity: 1, transform: "translateY(0)" },
        },
        "glass-fade-in": {
          from: { opacity: 0, backdropFilter: "blur(0px)", transform: "translateY(10px)" },
          to: { opacity: 1, backdropFilter: "blur(var(--blur-md))", transform: "translateY(0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.5s ease-out forwards",
        "fade-in-up": "fade-in-up 0.5s ease-out forwards",
        "slide-in-right": "slide-in-right 0.4s ease-out forwards",
        "slide-in-left": "slide-in-left 0.4s ease-out forwards",
        "vermillion-pulse": "vermillion-pulse 3s ease-in-out infinite",
        "glass-shimmer": "glass-shimmer 1.5s infinite",
        "scale-in": "scale-in 0.3s ease-out forwards",
        "number-tick": "number-tick 0.3s ease-out forwards",
        "glass-in": "glass-fade-in 0.5s ease-out forwards",
      },
      transitionDuration: {
        '400': '400ms',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-vermillion': 'linear-gradient(135deg, hsl(var(--vermillion-light)), hsl(var(--vermillion)))',
        'gradient-dark': 'linear-gradient(180deg, hsl(var(--background-elevated)), hsl(var(--background)))',
        'gradient-mesh': 'radial-gradient(ellipse at 20% 30%, hsl(var(--vermillion) / 0.08) 0%, transparent 50%), radial-gradient(ellipse at 80% 70%, hsl(210 100% 50% / 0.05) 0%, transparent 50%), radial-gradient(ellipse at 50% 50%, hsl(240 8% 8%) 0%, hsl(240 10% 4%) 100%)',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
