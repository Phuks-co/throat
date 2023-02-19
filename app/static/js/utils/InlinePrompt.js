
// We are looking for an object that looks like the following
// {
//  text: string,
//  options: [
//    [option: string, onclick: function]
//  ],
//  elem: Element,
// }
function InlinePrompt({
  text,
  options,
  elem
}) {
  if(text == null) {
    console.error("Need a text body to put in here.");
    return;
  }
  if(options.length < 1) {
    console.error("Need at least one option for a user to click on");
    return;
  }
  if(elem == null) {
    console.error("Need to be able to attach the UI to something");
    return;
  }

  // Get holder var
  const parent = elem.parentNode;
  // Pull out current content
  const current_content = parent.innerHTML;
  // Clone the node with nothing in it.
  const cNode = parent.cloneNode(false);

  const wrap = document.createElement("span");

  //Swap in new cloned node with empty span.
  cNode.appendChild(wrap)
  parent.parentNode.replaceChild(cNode,parent);

  const opt_elems = options.map(
    ([str, oc]) => {
      const a = document.createElement("a");
      a.innerHTML = str;
      a.onclick = (ev) => {
        if(oc != null) {
          oc(ev);
        }
        cNode.innerHTML = current_content;
        ev.preventDefault();
        return false;
      };
      return a;
    }
  );

  wrap.classList.add("red-confirm");
  wrap.innerText = `${text} `;

  opt_elems.forEach((elem, i) => {
    wrap.append(elem);
    if(i < opt_elems.length - 1){
      wrap.append("/ ");
    }
  });
}

export default InlinePrompt;
