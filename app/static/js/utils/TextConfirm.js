// Simple, inline yes/no confirmation prompt.
import _ from './I18n';

function TextConfirm(the_element, yesfunc, question){
  var elem = the_element.parentNode;
  var bk = elem.innerHTML;
  var yes = document.createElement( "a" );
  var no =  document.createElement( "a" );
  yes.innerHTML = _("yes");
  no.innerHTML = _("no");
  var wrap = document.createElement('span');
  wrap.classList.add("red-confirm");
  if(!question){
    question = _('Are you sure?');
  }
  wrap.innerHTML = question + ' ';
  wrap.append(yes);
  wrap.append('/ ');
  wrap.append(no);
  var cNode = elem.cloneNode(false);
  cNode.appendChild(wrap)
  elem.parentNode.replaceChild(cNode,elem );
  yes.onclick = function(){
    if(yesfunc() == false){
      cNode.innerHTML = bk;
    }
  }
  no.onclick = function(){
    cNode.innerHTML = bk;
  };


}

export default TextConfirm;
