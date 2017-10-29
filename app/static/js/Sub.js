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

$('.revoke-ban').click(function(){
  var user=$(this).data('user');
  var nsub=$(this).data('sub');
  $.ajax({
    type: "POST",
    url: '/do/remove_sub_ban/' + nsub + '/' + user,
    data: {'csrf_token': $('#csrf_token')[0].value},
    dataType: 'json',
    success: function(data) {
        if (data.status == "ok") {
          document.location.reload();
        }
    }
  });
});


$('#ptoggle').click(function(){
  var oval = $('#ptypeval').val();
  $('#ptypeval').val(($('#ptypeval').val() == 'text') ? 'link' : 'text' );
  var val = $('#ptypeval').val();
  $(this).html('Change to ' + oval + ' post');
  $('#ptype').html(val);
  if(val=='text'){
    $('#txcont').show();
    $('#lncont').hide();
    $('#link').prop('required', false);
    $('#content').prop('required', true);
  }else{
    $('#txcont').hide();
    $('#lncont').show();
    $('#link').prop('required', true);
    $('#content').prop('required', false);
  }
});
