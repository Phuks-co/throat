import $ from 'jquery';

$(document).on('click', '.revoke-mod2inv', function(){
  var user=$(this).data('user');
  var nsub=$(this).data('sub');
  $.ajax({
    type: "POST",
    url: '/do/revoke_mod2inv/' + nsub + '/' + user,
    data: {'csrf_token': $('#csrf_token')[0].value},
    dataType: 'json',
    success: function(data) {
        if (data.status == "ok") {
          document.location.reload();
        }
    }
  });
});

$('#accept-mod2-inv').click(function(){
  var user=$(this).data('user');
  var nsub=$(this).data('sub');
  $.ajax({
    type: "POST",
    url: '/do/accept_mod2inv/' + nsub + '/' + user,
    data: {'csrf_token': $('#csrf_token')[0].value},
    dataType: 'json',
    success: function(data) {
        if (data.status == "ok") {
          document.location.reload();
        }
    }
  });
});

$('#refuse-mod2-inv').click(function(){
  var user=$(this).data('user');
  var nsub=$(this).data('sub');
  $.ajax({
    type: "POST",
    url: '/do/refuse_mod2inv/' + nsub + '/' + user,
    data: {'csrf_token': $('#csrf_token')[0].value},
    dataType: 'json',
    success: function(data) {
        if (data.status == "ok") {
          document.location.reload();
        }
    }
  });
});

$('.revoke-mod2').click(function(){
  var user=$(this).data('user');
  var nsub=$(this).data('sub');
  $.ajax({
    type: "POST",
    url: '/do/remove_mod2/' + nsub + '/' + user,
    data: {'csrf_token': $('#csrf_token')[0].value},
    dataType: 'json',
    success: function(data) {
        if (data.status == "ok") {
          document.location.reload();
        }
    }
  });
});
