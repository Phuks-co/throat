import $ from 'jquery';
var icon = require('./Icon');
function get_hostname(url) {
  if(!url){return;}
  var matches = url.match(/^https?\:\/\/([^\/?#]+)(?:[\/?#]|$)/i);
  return matches[1];
}

function vimeoID(url) {
  var match = url.match(/https?:\/\/(?:www\.)?vimeo.com\/(?:channels\/(?:\w+\/)?|groups\/([^\/]*)\/videos\/|album\/(\d+)\/video\/|)(\d+)(?:$|\/|\?)/);
  if (match){
    return match[3];
	}
}
function vineID(url) {
  var match = url.match(/^http(?:s?):\/\/(?:www\.)?vine\.co\/v\/([a-zA-Z0-9]{1,13})$/);
  if (match){
    return match[1];
	}
}
function gfycatID(url) {
  var match = url.match(/^http(?:s?):\/\/gfycat\.com\/([a-zA-Z0-9]{1,60})$/);
  if (match){
    return match[1];
	}
}
function youtubeID(url) {
  var match =  url.match(/^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/);
  if (match && match[2].length == 11) {
    return match[2];
  }
}
function imgurID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?imgur\.com\/(.*?)(?:\/.gifv|$)/);
  if (match){
    return match[2].replace(/.gifv/,'');
	}
}

function close_expando( pid){
  $('div.expando-master[pid="'+pid+'"]').remove();
  $('div.expando-btn[data-pid="'+pid+'"]')[0].innerHTML = icon[$('div.expando-btn[data-pid="'+pid+'"]').data('icon')];
}

$(document).on('click', '.expando-btn', function(){
  var link = $(this).data('link');
  var pid = $(this).data('pid');
  var th = this;
  if($('div.expando-master[pid="'+pid+'"]').get(0)){
    return close_expando(pid);
  }
  var expando = $('<div pid="'+pid+'" class="expando-master pure-g"><div class="pure-u-1 pure-u-md-1-24"></div><div class="pure-u-1 pure-u-md-15-24 expandotxt"></div></div>');
  if(link == "None"){ // Found a Python here :(
    $.ajax({
      type: "GET",
      url: '/do/get_txtpost/' + pid, // XXX: Hardcoded URL
      dataType: 'json',
      success: function(data) {
        if (data.status == "ok") {
          expando.children('.expandotxt')[0].innerHTML = data.content;
        }
      }
    });
  }else{
    var domain = get_hostname(link);

    if((domain == 'youtube.com') || (domain == 'www.youtube.com') || (domain == 'youtu.be')){
      expando.children('.expandotxt')[0].innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://www.youtube.com/embed/' + youtubeID(link) +'"></iframe></div>';
    }else if(domain == 'gfycat.com'){
      expando.children('.expandotxt')[0].innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://gfycat.com/ifr/' + gfycatID(link) +'"></iframe></div>';
    }else if(domain == 'vimeo.com'){
      expando.children('.expandotxt')[0].innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://player.vimeo.com/video/' + vimeoID(link) +'"></iframe></div>';
    }else if(domain == 'vine.co'){
      expando.children('.expandotxt')[0].innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://vine.co/v/' + vineID(link) +'/embed/simple"></iframe></div>';
    }else if(/\.(png|jpg|gif|tiff|svg|bmp|jpeg)$/i.test(link)) {
      var img = document.createElement( "img" );
      img.src = link;
      img.onclick = function(){close_expando(pid);};
      expando.children('.expandotxt').append(img);
    }else if (/\.(mp4|webm)$/i.test(link)) {
      var vid = document.createElement( "video" );
      vid.src = link;
      vid.preload = 'auto';
      vid.autoplay = true;
      vid.loop = true;
      vid.controls = true;
      vid.innerHTML = document.createElement("source").src = link;
      expando.children('.expandotxt').append(vid);
    }else if(domain == 'i.imgur.com' && /\.gifv$/i.test(link)){
      var vidx = document.createElement( "video" );
      vidx.src = 'https://i.imgur.com/' + imgurID(link) + '.mp4';
      vidx.preload = 'auto';
      vidx.autoplay = true;
      vidx.loop = true;
      vidx.controls = true;
      vidx.innerHTML = document.createElement("source").src = 'https://i.imgur.com/' + imgurID(link) + '.mp4';
      expando.children('.expandotxt').append(vidx);
    }
  }
  this.innerHTML = icon.close;
  $('div.post[pid="'+pid+'"]').append(expando);
});
