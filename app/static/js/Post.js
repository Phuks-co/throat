// Post page-related code.
import TextConfirm from  './utils/TextConfirm';
import $ from 'jquery';
import Icons from './Icon';
import initializeEditor from './Editor';

// Saving/unsaving posts.
$('.savepost').click(function(e){
  var pid = $(e.currentTarget).data().pid;
  $.ajax({
    type: "POST",
    url: '/do/save_post/' + pid,
    dataType: 'json',
    success: function(data) {
      $(e.currentTarget).text('saved');
    }
  });
});

$('.removesavedpost').click(function(e){
  var pid = $(e.currentTarget).data().pid;
  $.ajax({
    type: "POST",
    url: '/do/remove_saved_post/' + pid,
    dataType: 'json',
    success: function(data) {
      if(data.status == "ok"){
        $(e.currentTarget).text('removed');
      } else {
        $(e.currentTarget).text('oops');
      }
    }
  });
});

// Delete post
$(document).on('click', '.delete-post', function(){
  // confirmation
  TextConfirm(this, function(){
    $.ajax({
      type: "POST",
      url: '/do/delete_post',
      data: $("#delete-post-form").serialize(),
      dataType: 'json',
      success: function(data) {
          if (data.status != "ok") {
            $(this).parent().html('There was an error while deleting your post.');
          } else {
            $(this).parent().html('Post removed');
            document.location.reload();
          }
      },
      error: function(data, err) {
          $(this).parent().html('could not contact server');
      }
    });
  });
});

// Stick post
$(document).on('click', '.stick-post', function(){
  // confirmation
  var pid = $(this).parent().parent().data('pid');
  TextConfirm(this, function(){
    $.ajax({
      type: "POST",
      url: '/do/stick/' + pid,
      data: $("#delete-post-form").serialize(),
      dataType: 'json',
      success: function(data) {
          if (data.status != "ok") {
            $(this).parent().html('Error.');
          } else {
            $(this).parent().html('Done!');
            document.location.reload();
          }
      },
      error: function(data, err) {
          $(this).parent().html('could not contact server');
      }
    });
  });
});

// post source
$(document).on('click', '.post-source', function(){
  var elem = document.getElementById('postcontent');
  var oc = elem.innerHTML;
  var back =  document.createElement( "a" );
  back.innerHTML = "<s>source</s>";
  back.onclick = function(){
    elem.innerHTML = oc;
    $(this).parent().html('<a class="post-source">source</a>');
  };
  var h = elem.clientHeight-6;
  elem.innerHTML = '<textarea style="height: ' + h + 'px">' + document.getElementById('post-source').innerHTML + '</textarea>';
  $(this).parent().html(back);
});


// edit post
$(document).on('click', '.edit-post', function(){
  var elem = document.getElementById('postcontent');
  var oc = elem.innerHTML;
  var back =  document.createElement( "a" );
  back.innerHTML = "<s>edit</s>";
  back.onclick = function(){
    elem.innerHTML = oc;
    $(this).parent().html('<a class="edit-post">edit</a>');
  };
  var h = elem.clientHeight-6;
  elem.innerHTML = '<div id="editpost" class="cwrap markdown-editor"><textarea style="height: ' + h + 'px">' + document.getElementById('post-source').innerHTML + '</textarea></div><div style="display:none" class="error"></div><button class="pure-button pure-button-primary button-xsmall btn-editpost" data-pid="' + $(this).data('pid') +'">Save changes</button> <button class="pure-button button-xsmall btn-preview" data-pvid="editpost" >Preview</button><div class="cmpreview canclose" style="display:none;"><h4>Comment preview</h4><span class="closemsg">×</span><div class="cpreview-content"></div></div>';
  $(this).parent().html(back);
  initializeEditor($('#editpost'));
});


// comment source
$(document).on('click', '.comment-source', function(){
  var cid = $(this).data('cid');
  var elem = document.getElementById('content-' + cid);
  var oc = elem.innerHTML;
  var back =  document.createElement( "s" );
  back.innerHTML = "source";
  back.onclick = function(){
    elem.innerHTML = oc;
    $(this).parent().html('source');
  };
  var h = elem.clientHeight + 28;
  elem.innerHTML = '<div class="cwrap"><textarea style="height: ' + h + 'px">' + document.getElementById('sauce-' + cid).innerHTML + '</textarea></div>';
  $(this).html(back);
});

// edit comment
$(document).on('click', '.edit-comment', function(){
  var cid = $(this).data('cid');
  var elem = document.getElementById('content-' + cid);
  var oc = elem.innerHTML;
  var back =  document.createElement( "s" );
  back.innerHTML = "edit";
  back.onclick = function(){
    elem.innerHTML = oc;
    $(this).parent().html('edit');
  };
  var h = elem.clientHeight + 28;
  elem.innerHTML = '<div class="cwrap markdown-editor" id="ecomm-'+cid+'"><textarea style="height: ' + h + 'px">' + document.getElementById('sauce-' + cid).innerHTML + '</textarea></div><div style="display:none" class="error"></div><button class="pure-button pure-button-primary button-xsmall btn-editcomment" data-cid="'+cid+'">Save changes</button> <button class="pure-button button-xsmall btn-preview" data-pvid="ecomm-'+cid+'">Preview</button><div class="cmpreview canclose" style="display:none;"><h4>Comment preview</h4><span class="closemsg">×</span><div class="cpreview-content"></div></div>';
  $(this).html(back);
  initializeEditor($('#ecomm-' + cid));
});

$(document).on('click', '.btn-editpost', function(){
  var obj=$(this);
  var content=$('#editpost textarea')[0].value;
  obj.prop('disabled', true);
  $.ajax({
    type: "POST",
    url: '/do/edit_txtpost/' + obj.data('pid'),
    data: {'csrf_token': $('#csrf_token')[0].value, content: content},
    dataType: 'json',
    success: function(data) {
        if (data.status != "ok") {
          obj.parent().children('.error').show();
          obj.parent().children('.error').html('There was an error while editing: ' + data.error);
          obj.prop('disabled', false);
        } else {
          obj.html('Saved.');
          document.location.reload();
        }
    },
    error: function(data, err) {
      obj.parent().children('.error').show();
      obj.parent().children('.error').html('could not contact server');
      obj.prop('disabled', false);
    }
  })
});


$(document).on('click', '.btn-editcomment', function(){
  var obj = $(this);
  var cid = obj.data('cid');
  var content = $('#ecomm-' + cid + ' textarea')[0].value;
  obj.prop('disabled', true);
  $.ajax({
    type: "POST",
    url: '/do/edit_comment',
    data: {'csrf_token': $('#csrf_token')[0].value, cid: cid, text: content},
    dataType: 'json',
    success: function(data) {
        if (data.status != "ok") {
          obj.parent().children('.error').show();
          obj.parent().children('.error').html('There was an error while editing: ' + data.error);
          obj.prop('disabled', false);
        } else {
          obj.html('Saved.');
          document.location.reload();
        }
    },
    error: function(data, err) {
      obj.parent().children('.error').show();
      obj.parent().children('.error').html('could not contact server');
      obj.prop('disabled', false);
    }
  });
});

$(document).on('click', '.btn-preview', function(e){
  e.preventDefault();
  var obj = $(this);
  var content = $('#' + $(this).data('pvid') + ' textarea')[0].value;
  obj.prop('disabled', true);
  obj.text('Loading...');
  $.ajax({
    type: "POST",
    url: '/do/preview',
    data: {'csrf_token': $('#csrf_token')[0].value, text: content},
    dataType: 'json',
    success: function(data) {
      if (data.status == "ok") {
        obj.parent().children('.cmpreview').children('.cpreview-content').html(data.text);
        obj.parent().children('.cmpreview').show()
      }else{
        obj.parent().children('.error').show();
        obj.parent().children('.error').html('could not contact server');
      }
      obj.prop('disabled', false);
      obj.text('Preview');
    },
    error: function(data, err) {
      obj.parent().children('.error').show();
      obj.parent().children('.error').html('could not contact server');
      obj.prop('disabled', false);
      obj.text('Preview');
    }
  });
});

// Delete comment
$(document).on('click', '.delete-comment', function(){
  // confirmation
  var cid = $(this).data('cid');
  $("#dcf-cid").val(cid);
  TextConfirm(this, function(){
    $.ajax({
      type: "POST",
      url: '/do/delete_comment',
      data: $("#delete-comment-form").serialize(),
      dataType: 'json',
      success: function(data) {
          if (data.status != "ok") {
            $(this).parent().html('There was an error while deleting the comment.');
          } else {
            $(this).parent().html('Comment removed');
            document.location.reload();
          }
      },
      error: function(data, err) {
          $(this).parent().html('could not contact server');
      }
    });
  });
});

// Grab post title from url
$(document).on('click', '#graburl', function(){
  $(this).prop('disabled', true);
  $(this).html('Grabbing...');
  $.ajax({
    type: "GET",
    dataType: 'json',
    url: '/do/grabtitle',
    data: {'u': $('#link').prop('value')},
    success: function(data) {
      if(data.status == 'error'){
        $('#title').prop('value', 'Error fetching title');
        $('#graburl').prop('disabled', false);
        $('#graburl').html('Grab title');
      }else{
        $('#title').prop('value', data.title);
        $('#graburl').prop('disabled', false);
        $('#graburl').html('Done!');
      }
    }
  });
});

// Load children
$(document).on('click', '.loadchildren', function(e){
  e.preventDefault();
  var ob = $(this)
  $.ajax({
    type: "POST",
    dataType: 'json',
    url: '/do/get_children/' + $(this).data('pid') + '/' + $(this).data('cid'),
    dataType: 'html',
    success: function(data){
      ob.parent().html(data);
      $('div[data-icon],span[data-icon]').each(function(i){
        this.innerHTML = Icons[$(this).data('icon')];
      });
    }
  });
});

$(document).on('click', '.loadsibling', function(e){
  e.preventDefault();
  var ob = $(this)
  var page = (ob.data('page') !== '') ? ob.data('page') : 1;
  var parent = (ob.data('cid') !== '') ? ob.data('cid') : 1;
  $.ajax({
    type: "POST",
    dataType: 'json',
    url: '/do/get_sibling/' + $(this).data('pid') + '/' + parent + '/' + page,
    dataType: 'html',
    success: function(data){
      ob.replaceWith(data);
      $('div[data-icon],span[data-icon]').each(function(i){
        this.innerHTML = Icons[$(this).data('icon')];
      });
    }
  });
});

// collapse/expand comment
$(document).on('click', '.togglecomment.collapse', function(e){
  e.preventDefault();
  var cid = $(this).data('cid');
  $(this).text('[+]')
  $('#comment-'+cid+' .votecomment').hide();
  $('#comment-'+cid+' .bottombar').hide();
  $('#comment-'+cid+' .commblock .content').hide();
  $('#'+cid+' .pchild').hide();
  $(this).removeClass('collapse');
  $(this).addClass('expand');
  $(this).parent().parent().css('margin-left', '1.6em');
  $(this).text = '[+]';
})

$(document).on('click', '.togglecomment.expand', function(e){
  e.preventDefault();
  var cid = $(this).data('cid');
  $(this).text('[–]')
  $('#comment-'+cid+' .votecomment').show();
  $('#comment-'+cid+' .bottombar').show();
  $('#comment-'+cid+' .commblock .content').show();
  $('#'+cid+' .pchild').show();
  $(this).removeClass('expand');
  $(this).addClass('collapse');
  $(this).text = '[-]';
  $(this).parent().parent().css('margin-left', '0');
})
