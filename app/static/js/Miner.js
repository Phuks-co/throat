import u from './Util'

require('../css/miner.css');

function escapeHtml(html)
{
    var text = document.createTextNode(html);
    var div = document.createElement('div');
    div.appendChild(text);
    return div.innerHTML;
}

window.setInterval(function(){
  u.get('/miner/stats', function(d){
    document.getElementById('nm').innerHTML = d.name;
    document.getElementById('bal').innerHTML = d.balance;
    document.getElementById('hps').innerHTML = d.hash;
    document.getElementById('ht').innerHTML = d.totalHashes;
    document.getElementById('xpe').innerHTML = d.amtDue;
    document.getElementById('xpa').innerHTML = d.amtPaid;
    var tabl = '';
    var tablb = '';
    for (var i = 0; i < d.users.length; i++) {
      tabl = tabl + '<tr><td class="center">'+ (i+1) + '</td><td>' + escapeHtml(d.users[i].username) + '</td>';
      tabl = tabl + '<td><b><span>' + d.users[i].score + '</span></b></td></tr>';
    }

    for (var i = 0; i < d.speed.length; i++) {
      tablb = tablb + '<tr><td class="center">'+ (i+1) + '</td><td><span>' + escapeHtml(d.speed[i].username) + '</span></td>';
      tablb = tablb + '<td><b><span>' + d.speed[i].hashes + '</span></b> H/s</td></tr>';
    }
    document.querySelector('#miningleaderboard table').innerHTML = tabl;
    document.querySelector('#speedleaderboard table').innerHTML = tablb;
  })
}, 120000);
