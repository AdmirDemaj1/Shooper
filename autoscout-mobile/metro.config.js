const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

config.resolver.blockList = [
  /node_modules\/.*\/node_modules/,
  /\..*\/(node_modules|__rn_placeholder__|\.gradle|build|\.git|\.next|dist|coverage)/,
  /node_modules\/@.*\/node_modules/,
];

config.watchFolders = [];
config.transformer.minifierPath = 'metro-minify-terser';
config.maxWorkers = 2;

module.exports = config;
