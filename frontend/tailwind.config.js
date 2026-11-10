export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#D7191F', deep: '#B32E26', tint: '#F7D4D5', soft: '#FBF1F1', line: '#EBD9DA' },
        ink: '#1F1A1A', ok: '#1E8E3E', warn: '#E8A317',
      },
      fontFamily: { sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
