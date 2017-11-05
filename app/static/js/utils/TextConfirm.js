// Simple, inline yes/no confirmation prompt.

function TextConfirm(the_element, yesfunc, question){
  var elem = the_element.parentNode;
  var bk = elem.innerHTML;
  var yes = document.createElement( "a" );
  var no =  document.createElement( "a" );
  yes.innerHTML = "yes";
  yes.onclick = yesfunc;
  no.innerHTML = "no";
  no.onclick = function(){
    elem.innerHTML = bk;
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
  var cNode = elem.cloneNode(false);
  cNode.appendChild(wrap)
  elem.parentNode.replaceChild(cNode,elem );
}

export default TextConfirm;
