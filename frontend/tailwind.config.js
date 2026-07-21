/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Disable Preflight — the project ships its own reset in index.css
  corePlugins: { preflight: false },
  theme: {
    extend: {
      // Mirror existing CSS custom property tokens so Tailwind utilities stay coherent
      colors: {
        bg:         '#f1f5f9',
        surface:    '#ffffff',
        'surface-2':'#f8fafc',
        'surface-3':'#f1f5f9',
        border:     '#e2e8f0',
        'border-mid':'#cbd5e1',
        text1:      '#0f172a',
        text2:      '#475569',
        text3:      '#94a3b8',
        blue: {
          DEFAULT: '#2563eb',
          dark:    '#1d4ed8',
          light:   '#eff6ff',
          mid:     '#dbeafe',
        },
        success:    '#059669',
        warning:    '#d97706',
        danger:     '#dc2626',
      },
      borderRadius: {
        xs:  '6px',
        sm:  '10px',
        DEFAULT: '14px',
        lg:  '20px',
        xl:  '28px',
      },
      boxShadow: {
        xs:   '0 1px 2px rgba(15,23,42,0.05)',
        sm:   '0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04)',
        DEFAULT: '0 4px 6px -1px rgba(15,23,42,0.07), 0 2px 4px -1px rgba(15,23,42,0.04)',
        md:   '0 8px 20px -4px rgba(15,23,42,0.10), 0 4px 8px -2px rgba(15,23,42,0.05)',
        lg:   '0 20px 40px -8px rgba(15,23,42,0.12), 0 8px 16px -4px rgba(15,23,42,0.06)',
        blue: '0 0 0 3px rgba(37,99,235,0.15)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.34,1.56,0.64,1)',
        smooth: 'cubic-bezier(0.22,1,0.36,1)',
      },
    },
  },
  plugins: [],
}
