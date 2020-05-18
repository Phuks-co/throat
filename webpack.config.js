var path = require('path');

var webpack = require('webpack');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
var ManifestRevisionPlugin = require('manifest-revision-webpack-plugin');
//var BundleAnalyzerPlugin = 	require('webpack-bundle-analyzer').BundleAnalyzerPlugin;


module.exports = {
  mode: 'production',
  entry: {
    main: ['./app/static/js/main.js'],
  },
  output: {
    path: path.resolve(__dirname, 'app/static/gen'),
    filename: '[name].[chunkhash].js',
    chunkFilename: '[id].[chunkhash].js',
    publicPath: '/static/gen/'
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /(node_modules|bower_components|ext)/,
        use: {
          loader: 'babel-loader',
          options: {
            plugins: ['transform-es2015-modules-commonjs']
          }
        }
      },
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader'],
      },
      {
        test: [/\.pot?$/, /\.mo$/],
        loader: require.resolve('messageformat-po-loader'),
        options: {
          biDiSupport: false,
          defaultCharset: null,
          defaultLocale: 'en',
          forceContext: false,
          pluralFunction: null,
          verbose: false
        }
      },
      {
        test: /\.svg$/,
        exclude: [/sprite\.svg/],
        loader: 'svg-inline-loader'
      },
      { test: /\.(woff|woff2|eot|ttf)$/, loader: 'url-loader?limit=100000' }

    ],
  },
  plugins: [
//    new BundleAnalyzerPlugin(),
    new MiniCssExtractPlugin({
        filename: '[name].[chunkhash].css',
        chunkFilename: '[id].[chunkhash].css'
    }),
    new ManifestRevisionPlugin('./app/manifest.json', {
      rootAssetPath: './app/static/gen',
      ignorePaths: ['/static']
    })
  ],
  node: {
    fs: 'empty'
  }
};
