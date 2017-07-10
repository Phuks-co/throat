// Simple, inline yes/no confirmation prompt.
import $ from 'jquery';

function TextConfirm(the_element, yesfunc, question){
  var elem = $(the_element).parent();
  var bk = elem.html();
  var yes = document.createElement( "a" );
  var no =  document.createElement( "a" );
  yes.innerHTML = "yes";
  yes.onclick = yesfunc;
  no.innerHTML = "no";
  no.onclick = function(){
    elem.html(bk);
  };
  var wrap = document.createElement('span');
  wrap.classList.add("red-confirm");
  if(!question){
    question = 'Are you sure?';
  }
  wrap.innerHTML = question + ' ';
  wrap.append(yes);
  wrap.append('/ ');
  wrap.append(no);
  elem.html(wrap);
}

export default TextConfirm;
