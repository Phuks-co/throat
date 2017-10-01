import $ from 'jquery';
var icon = require('./Icon');

$(document).ready(function(){
  $('.markdown-editor').each(function(i){
    // we are manually aplying the icons here, because we can.
    var txps = '<div class="editbtns"><div class="bold" data-icon="bold">' + icon.bold + '</div>' +
                '<div class="italic" data-icon="italic">' + icon.italic + '</div>' +
                '<div class="strikethrough" data-icon="strikethrough">' + icon.strikethrough + '</div>' +
                '<span class="separator"></span>' +
                '<div class="link" data-icon="link">' + icon.link + '</div>'
               '</div>';
    $(this).prepend(txps);
  });
});
