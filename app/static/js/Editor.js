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

    el.appendChild(makeThingy('bold', 'Bold', function(e){addTags(textarea, '**', '**');}));
    el.appendChild(makeThingy('italic', 'Italic', function(e){addTags(textarea, '*', '*');}));
    el.appendChild(makeThingy('strikethrough', 'Strikethrough', function(e){addTags(textarea, '~~', '~~');}));
    el.appendChild(makeThingy('title', 'Title', function(e){addTags(textarea, '# ', '');}));

    var x = document.createElement('span');
    x.className='separator';
    el.appendChild(x);

    el.appendChild(makeThingy('link', 'Insert link', function(e){
      var uri = prompt('Insert hyperlink');
      if(uri){
        if(getCursorSelection(textarea)[1] == ''){
          addTags(textarea, '[', 'Link Title', '](' + uri + ')');
        }else{
          addTags(textarea, '[', '](' + uri + ')');
        }
      }
    }));

    x = document.createElement('span');
    x.className='separator';
    el.appendChild(x);

    el.appendChild(makeThingy('bulletlist', 'Bullet list', function(e){addTags(textarea, '- ', '');}));
    el.appendChild(makeThingy('numberlist', 'Number list', function(e){addTags(textarea, '1. ', '');}));

    x = document.createElement('span');
    x.className='separator';
    el.appendChild(x);

    el.appendChild(makeThingy('code', 'Code', function(e){addTags(textarea, '`', '`');}));
    el.appendChild(makeThingy('quote', 'Quote', function(e){addTags(textarea, '> ', '');}));

    element.insertBefore(el, element.firstChild);
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
