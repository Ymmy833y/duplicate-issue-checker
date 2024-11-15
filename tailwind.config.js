/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: 'jit',
  content: [
    './app/templates/**/*.html',
    './app/static/**/*.js',
  ],
  safelist: [
    {
      pattern: /bg-(green|yellow|red|blue|purple|gray)-\d{2,3}/,
    },
    {
      pattern: /text-(green|yellow|red|blue|purple|gray)-\d{2,3}/,
    },
    {
      pattern: /border-(green|yellow|red|blue|purple|gray)-\d{2,3}/,
    },
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

