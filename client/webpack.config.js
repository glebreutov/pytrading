var path = require('path')

module.exports = {
  entry: './client/index_py.js',
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
  },
  module: {
    loaders: [
      {
        test: /\.js$/,
        exclude: /(node_modules)/,
        loader: 'babel-loader?presets[]=es2015,presets[]=stage-0,presets[]=react',
      },
    ],
  },
  devtool: 'source-map',
}
