import u from './Util';

u.sub('.revoke-mod2inv', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/revoke_mod2inv/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('#accept-mod2-inv', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/accept_mod2inv/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('#refuse-mod2-inv', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/refuse_mod2inv/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('.revoke-mod2', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/remove_mod2/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('.revoke-ban', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/remove_sub_ban/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('#ptoggle', 'click', function(e){
  var oval = document.getElementById('ptypeval').value;
  document.getElementById('ptypeval').value = (document.getElementById('ptypeval').value == 'text') ? 'link' : 'text' ;
  var val = document.getElementById('ptypeval').value;
  this.innerHTML = 'Change to ' + oval + ' post';
  document.getElementById('ptype').innerHTML = val;
  if(val=='text'){
    document.getElementById('link').removeAttribute('required');
    u.each('.lncont', function(e){e.style.display='none';});
    u.each('.txcont', function(e){e.style.display='inline-block';});
  }else{
    document.getElementById('link').setAttribute('required', true);
    u.each('.lncont', function(e){e.style.display='inline-block';});
    u.each('.txcont', function(e){e.style.display='none';});
  }
});

u.sub('button.blk,button.unblk,button.sub,button.unsub', 'click', function(e){
  var sid=this.parentNode.getAttribute('data-sid');
  var act=this.getAttribute('data-ac')
  u.post('/do/' + act + '/' + sid, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});
