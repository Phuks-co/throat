// Code for polls.

import u from './Util';
import _ from './utils/I18n';


u.sub('#poll-addoption', 'click', function(e){
    // Check if the number of available options is above the maximum.
    var opts = document.getElementById('poll-opts');
    if(opts.childElementCount >= 6){
        return;
    }

    // All is OK, add the option.
    var node = document.createElement('li');
    var tb = document.createElement('input');
    tb.name = 'options-' + opts.childElementCount;
    tb.classList.add('sbm-poll-opt');
    tb.classList.add('reqpoll');
    tb.type = 'text';
    tb.required = true;

    var tbdel = document.createElement('a');
    tbdel.innerHTML = _('remove');
    tbdel.style.marginLeft = '1em';
    tbdel.style.cursor = 'pointer';
    tbdel.classList.add('poll-del-opt');

    node.appendChild(tb);
    node.appendChild(tbdel);
    opts.appendChild(node);
});


u.addEventForChild(document, 'click', '.poll-del-opt', function(e, qelem){
    e.target.parentNode.parentNode.removeChild(e.target.parentNode);
});


u.sub('#closetime', 'click', function(e){
    if(this.checked){
        document.getElementById('closetime_date').removeAttribute('disabled');
        document.querySelector('.date-picker-future.input').removeAttribute('disabled');
        document.querySelector('.date-picker-future.flatpickr-mobile').removeAttribute('disabled');
    }else{
        document.getElementById('closetime_date').setAttribute('disabled', true);
        document.querySelector('.date-picker-future.input').setAttribute('disabled', true);
        document.querySelector('.date-picker-future.flatpickr-mobile').setAttribute('disabled', true);
        document.getElementById('closetime_date').value = '';
        document.querySelector('.date-picker-future.input').value = '';
    }
});

u.addEventForChild(document, 'click', '.poll-show-results', function(e, qelem){
    var pid=qelem.parentNode.parentNode.getAttribute('data-pid');
    u.each(".poll-space[data-pid='" + pid + "'] .poll-hid", function(e){
        e.style.display = 'inline-block';
    })
    qelem.parentNode.removeChild(qelem);
});

u.addEventForChild(document, 'click', '.poll-vote-btn', function(e, qelem){
    var pid=qelem.parentNode.parentNode.parentNode.parentNode.getAttribute('data-pid');
    var oid=qelem.getAttribute('data-oid'), tg=qelem;
    u.each(".poll-space[data-pid='" + pid + "'] .poll-vote-btn", function(k){
        k.setAttribute('disabled', true);
    })
    qelem.innerHTML = _("Voting...");

    u.post('/do/cast_vote/' + pid + '/' + oid, {},
    function(data){
      u.each(".poll-space[data-pid='" + pid + "'] .poll-vote-btn", function(k){
        k.removeAttribute('disabled');
      })
      tg.innerHTML = "Vote";
      if (data.status != "ok") {
        var errorbox = document.querySelector(".poll-space[data-pid='" + pid + "'] .error")
        errorbox.innerHTML = _("Error: %1", data.error);
        errorbox.style.display = "block";
      } else {
        // 1 - Remove all vote buttons.
        u.each(".poll-space[data-pid='" + pid + "'] .poll-vote-btn", function(k){
            k.style.display = 'none';
        })
        // 2 - Highlight voted option
        var pot = document.querySelector(".poll-option[data-oid='" + oid + "'] .poll-option-text");
        pot.innerHTML = pot.innerHTML + ' ' + _('(voted)')
        pot.style.fontWeight = 'bold';
        var pb = document.querySelector(".poll-option[data-oid='" + oid + "'] .poll-pbar");
        if(pb){
            pb.classList.add('poll-voted');
            // 3 - Update vote totals
            var totalVotes = parseInt(document.querySelector(".poll-space[data-pid='" + pid + "']").getAttribute('data-votes')) + 1;
            document.querySelector(".poll-space[data-pid='" + pid + "']").setAttribute('data-votes', totalVotes);
            u.each(".poll-space[data-pid='" + pid + "'] .poll-option", function(k){
                var locoid=k.getAttribute('data-oid'), locvotes=parseInt(k.getAttribute('data-votes'));
                if(locoid == oid){
                    locvotes++;
                    k.setAttribute('data-votes', locvotes);
                }
                var pbar = document.querySelector(".poll-option[data-oid='" + locoid + "'] .poll-pbar").children[0];
                if(locvotes != 0){
                    pbar.style.width = Math.round(locvotes/totalVotes*100) + '%';
                }
                var pvot = document.querySelector(".poll-option[data-oid='" + locoid + "'] .poll-votes");
                pvot.children[0].innerHTML = Math.round(locvotes/totalVotes*100);
                pvot.children[1].innerHTML = locvotes;
            })
        }
        // 4 - Add withdraw vote button.
        document.querySelector(".poll-space[data-pid='" + pid + "'] .poll-withdraw-form").style.display = 'block';
        // 5 - Show results.
        var m =document.querySelector(".poll-space[data-pid='" + pid + "'] .poll-show-results")
        if(m) m.click();

      }
    });
});

u.addEventForChild(document, 'click', '.poll-withdraw-btn', function(e, qelem){
    var pid=qelem.parentNode.parentNode.getAttribute('data-pid'), te=qelem;
    qelem.setAttribute('disabled', true);
    qelem.innerHTML = _('Working...');
    u.post('/do/remove_vote/' + pid, {},
    function(data){
        te.removeAttribute('disabled');
        te.innerHTML = _('Withdraw vote');
        if (data.status != "ok") {
            var errorbox = document.querySelector(".poll-space[data-pid='" + pid + "'] .error")
            errorbox.innerHTML = _("Error: %1", data.error);
            errorbox.style.display = "block";
        }else{
            // 1 - Display vote buttons again
            u.each(".poll-space[data-pid='" + pid + "'] .poll-vote-btn", function(k){
                k.style.display = 'inline-block';
            })
            // 2 - remove all highlighting
            u.each(".poll-space[data-pid='" + pid + "'] .poll-option .poll-option-text", function(k){
                k.innerHTML = k.innerHTML.replace(_('(voted)'), '');
                k.style.fontWeight = 'normal';
                if(k.children[0]){
                    k.children[0].style.fontWeight = 'normal';
                }
            });

            var ve = document.querySelector(".poll-space[data-pid='" + pid + "'] .poll-pbar.poll-voted")
            if(ve){
                var veoid = ve.parentNode.parentNode.getAttribute('data-oid');
                document.querySelector(".poll-space[data-pid='" + pid + "'] .poll-pbar.poll-voted").classList.remove('poll-voted');
                // 3 - Update vote counts
                var totalVotes = parseInt(document.querySelector(".poll-space[data-pid='" + pid + "']").getAttribute('data-votes')) - 1;
                document.querySelector(".poll-space[data-pid='" + pid + "']").setAttribute('data-votes', totalVotes);
                u.each(".poll-space[data-pid='" + pid + "'] .poll-option", function(k){
                    var locoid=k.getAttribute('data-oid'), locvotes=parseInt(k.getAttribute('data-votes'));
                    if(locoid == veoid){
                        locvotes--;
                        k.setAttribute('data-votes', locvotes)
                    }
                    var pbar = document.querySelector(".poll-option[data-oid='" + locoid + "'] .poll-pbar").children[0];
                    if(locvotes != 0){
                        var percent = Math.round(locvotes/totalVotes*100);
                    }else{
                        var percent = 0;
                    }
                    pbar.style.width = percent + "%";
                    var pvot = document.querySelector(".poll-option[data-oid='" + locoid + "'] .poll-votes");
                    pvot.children[0].innerHTML = percent;
                    pvot.children[1].innerHTML = locvotes;
                })
            }
            te.parentNode.style.display = 'none';
        }
    });
});
