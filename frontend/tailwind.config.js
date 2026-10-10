/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#FFFFFF',   // page background — pure white
        ink:   '#111317',   // near-black text + buttons (cool)
        sand:  '#F4F6F8',   // card / panel / chip fill on white
        line:  '#E4E7EC',   // hairlines
        muted: '#5E6672',   // secondary text
        brand: '#0A66F0',   // logo blue — the single accent
      },
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans:  ['"Schibsted Grotesk"', 'system-ui', 'sans-serif'],
      },
      maxWidth: { page: '1180px' },
      borderRadius: { pill: '999px' },
    },
  },
  plugins: [],
};
