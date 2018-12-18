var path = require('path');

var webpack = require('webpack');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var ManifestRevisionPlugin = require('manifest-revision-webpack-plugin');
//var BundleAnalyzerPlugin = 	require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const externalCSS = new ExtractTextPlugin('[name].[contenthash].css');

module.exports = {
  entry: {
    main: ['./app/static/js/main.js'],
    miner: './app/static/js/Miner.js',
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
        loader: externalCSS.extract({ fallback: 'style-loader', use: 'css-loader' })
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
    new webpack.optimize.CommonsChunkPlugin("main"),
    externalCSS,
    new ManifestRevisionPlugin('./app/manifest.json', {
      rootAssetPath: './app/static/gen',
      ignorePaths: ['/static']
    })
  ],
  node: {
    fs: 'empty'
  }
};
