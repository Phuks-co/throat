// Code for polls.

import u from './Util';
import Icons from './Icon';


u.sub('#poll-addoption', 'click', function(e){
    // Check if the number of available options is above the maximum.
    var opts = document.getElementById('poll-opts');
    if(opts.childElementCount >= 6){
        return;
    }
    
    // All is OK, add the option.
    var node = document.createElement('li');
    var tb = document.createElement('input');
    tb.name = 'op[]';
    tb.classList.add('sbm-poll-opt');
    tb.type = 'text';
    tb.required = true;

    var tbdel = document.createElement('a');
    tbdel.innerHTML = 'remove';
    tbdel.style.marginLeft = '1em';
    tbdel.style.cursor = 'pointer';
    tbdel.onclick = function(ev){
        this.parentNode.parentNode.removeChild(this.parentNode);
    }

    node.appendChild(tb);
    node.appendChild(tbdel);
    opts.appendChild(node);
});
