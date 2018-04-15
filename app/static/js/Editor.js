import u from './Util';
var icon = require('./Icon');

u.ready(function(){
  u.each('.markdown-editor', function(el,i){
    initializeEditor(el);
  })
});

function makeThingy(name, title, fn){
  var x = document.createElement( "div" );
  x.title=title,x.className=name;
  x.setAttribute('data-icon', name);
  x.innerHTML = icon[name];
  x.onclick = fn;
  return x;
}


function initializeEditor(element){
    var el =  document.createElement( "div" );
    var textarea = element.children[0];
    el.classList.add('editbtns');

    el.appendChild(makeThingy('bold', 'Bold (ctrl-b)', function(e){addTags(textarea, '**', '**');}));
    el.appendChild(makeThingy('italic', 'Italic (ctrl-i)', function(e){addTags(textarea, '*', '*');}));
    el.appendChild(makeThingy('strikethrough', 'Strikethrough (ctrl-shift-s)', function(e){addTags(textarea, '~~', '~~');}));
    el.appendChild(makeThingy('title', 'Title (ctrl-shift-h)', function(e){addTags(textarea, '# ', '');}));

    var x = document.createElement('span');
    x.className='separator';
    el.appendChild(x);

    var makeLink = function (e){
      var uri = prompt('Insert hyperlink');
      if(uri){
        if(getCursorSelection(textarea)[1] == ''){
          addTags(textarea, '[', 'Link Title', '](' + uri + ')');
        }else{
          addTags(textarea, '[', '](' + uri + ')');
        }
      }
    }

    el.appendChild(makeThingy('link', 'Insert link (ctrl-shift-k)', makeLink));

    x = document.createElement('span');
    x.className='separator';
    el.appendChild(x);

    el.appendChild(makeThingy('bulletlist', 'Bullet list', function(e){addTags(textarea, '- ', '');}));
    el.appendChild(makeThingy('numberlist', 'Number list', function(e){addTags(textarea, '1. ', '');}));

    x = document.createElement('span');
    x.className='separator';
    el.appendChild(x);

    el.appendChild(makeThingy('code', 'Code', function(e){addTags(textarea, '`', '`');}));
    el.appendChild(makeThingy('quote', 'Quote (ctrl-shift-.)', function(e){addTags(textarea, '> ', '');}));

    element.insertBefore(el, element.firstChild);

    textarea.onkeyup = function(e){
      if(e.ctrlKey == true && e.which == 66){
        addTags(textarea, '**', '**');
      }else if(e.ctrlKey == true  && e.which == 73){
        addTags(textarea, '*', '*');
      }else if(e.ctrlKey == true && e.shiftKey == true && e.which == 83){
        addTags(textarea, '~~', '~~');
      }else if(e.ctrlKey == true && e.shiftKey == true && e.which == 72){
        addTags(textarea, '# ', '');
      }else if(e.ctrlKey == true && e.shiftKey == true && e.which == 75){
        makeLink(e);
      }else if(e.ctrlKey == true && e.shiftKey == true && e.which == 190){
        addTags(textarea, '> ', '');
      }
    }
}


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

module.exports = initializeEditor;
