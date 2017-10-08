import $ from 'jquery';
var icon = require('./Icon');

$(document).ready(function(){
  $('.markdown-editor').each(function(){
    initializeEditor($(this));
  })
});

function initializeEditor(element){
    // we are manually aplying the icons here, because we can.
    var txps = '<div class="editbtns"><div class="bold" data-icon="bold" title="Bold">' + icon.bold + '</div>' +
                '<div class="italic" data-icon="italic" title="Italic">' + icon.italic + '</div>' +
                '<div class="strikethrough" data-icon="strikethrough" title="Strikethrough">' + icon.strikethrough + '</div>' +
                '<div class="title" data-icon="title" title="Title">' + icon.title + '</div>' +
                '<span class="separator"></span>' +
                '<div class="link" data-icon="link" title="Hyperlink">' + icon.link + '</div>' +
                '<span class="separator"></span>' +
                '<div class="bulletlist" data-icon="link" title="Bullet list">' + icon.bulletlist + '</div>' +
                '<div class="numberlist" data-icon="link" title="Number list">' + icon.numberlist + '</div>' +
                '<span class="separator"></span>' +
                '<div class="quote" data-icon="quote" title="Quote block">' + icon.quote + '</div>' +
                '<div class="code" data-icon="code" title="Code block">' + icon.code + '</div>' +
               '</div>';
    element.prepend(txps);
}

$(document).on('click', '.editbtns .link', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  var uri = prompt('Insert hyperlink');
  if(uri){
    if(getCursorSelection(textarea)[1] == ''){
      addTags(textarea, '[', 'Link Title', '](' + uri + ')');
    }else{
      addTags(textarea, '[', '](' + uri + ')');
    }
  }
});

$(document).on('click', '.editbtns .title', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '## ', '');
});

$(document).on('click', '.editbtns .bold', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '**', '**');
});

$(document).on('click', '.editbtns .italic', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '*', '*');
});

$(document).on('click', '.editbtns .bulletlist', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '* ', '');
});

$(document).on('click', '.editbtns .numberlist', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '1. ', '');
});

$(document).on('click', '.editbtns .quote', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '> ', '');
});

$(document).on('click', '.editbtns .code', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '`', '`');
});

$(document).on('click', '.editbtns .strikethrough', function(){
  var textarea = $(this).parent().parent().children('textarea')[0];
  addTags(textarea, '~~', '~~');
});


function addTags(textarea, begin, end, bm){
  var sel = getCursorSelection(textarea);
  if(bm){
    var rbm = begin;
    begin = begin + end;
    end = bm;
  }
  textarea.value = sel[0] + begin + sel[1] + end + sel[2];
  var u = sel[0].length + begin.length + sel[1].length;
  if(bm){
    setSelection(textarea, rbm.length + sel[0].length, u);
  }else{
    setSelection(textarea, u, u);
  }
}

function getCursorSelection(textarea){
  var i = textarea.selectionStart;
  var n = textarea.selectionEnd;
  return [textarea.value.substring(0,i),
          textarea.value.substring(i,n),
          textarea.value.substring(n, textarea.value.length)];
}

function setSelection(textarea, begin, end){
  if(textarea.setSelectionRange){
    textarea.focus();
    textarea.setSelectionRange(begin, end);
  }else if(textarea.createTextRange){
    var tra = textarea.createTextRange();
    tra.collapse(0);
    tra.moveEnd('character', end);
    tra.moveStart('character', begin);
    tra.select();
  }
}
