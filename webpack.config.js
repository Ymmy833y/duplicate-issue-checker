const path = require('path');

module.exports = {
    entry: './app/static/js/markdown.js',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, './app/static/dist'),
    },
    mode: 'development',
};
