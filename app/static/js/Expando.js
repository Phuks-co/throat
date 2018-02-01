import u from './Util'
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
  var match = url.match(/^http(?:s?):\/\/gfycat\.com\/(?:gifs\/detail\/?)([a-zA-Z0-9]{1,60})$/);
  if (match){
    return match[1];
	}
}
function youtubeID(url) {
  var match =  url.match(/^.*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=|hooktube.com\/(watch\?v=)?)([^#\&\?]*).*/);
  if (match && match[3].length == 11) {
    return match[3];
  }
}
function imgurID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?imgur\.com\/(.*?)(?:\/.gifv|$)/);
  if (match){
    return match[2].replace(/.gifv/,'');
	}
}

function close_expando( pid){
  var k = document.querySelector('div.expando-master[pid="'+pid+'"]')
  k.parentNode.removeChild(k);
  document.querySelector('div.expando-btn[data-pid="'+pid+'"]').innerHTML = icon[document.querySelector('div.expando-btn[data-pid="'+pid+'"]').getAttribute('data-icon')];
}

u.addEventForChild(document, 'click', '.expando-btn', function(e, ematch){
    var th=ematch;

    var link=th.getAttribute('data-link');
    var pid=th.getAttribute('data-pid');
    if(document.querySelector('div.expando-master[pid="'+pid+'"]')){
      return close_expando(pid);
    }
    var expando = document.createElement('div');
    expando.setAttribute('pid', pid);
    expando.classList.add('expando-master');
    expando.classList.add('pure-g');
    expando.innerHTML = '<div class="pure-u-1 pure-u-md-1-24"></div><div class="pure-u-1 pure-u-md-22-24 expandotxt"></div>';
    if(link == 'None'){
      u.get('/do/get_txtpost/' + pid, function(data){
        if(data.status == 'ok'){
          expando.querySelector('.expandotxt').innerHTML = data.content;
        }
      })
    }else{
      var domain = get_hostname(link);
      if((domain == 'youtube.com') || (domain == 'www.youtube.com') || (domain == 'youtu.be')){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://www.youtube.com/embed/' + youtubeID(link) +'" allowfullscreen=""></iframe></div>';
      }else if((domain == 'hooktube.com') || (domain == 'www.hooktube.com')){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://hooktube.com/embed/' + youtubeID(link) +'" allowfullscreen=""></iframe></div>';
      }else if(domain == 'gfycat.com'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://gfycat.com/ifr/' + gfycatID(link) +'"></iframe></div>';
      }else if(domain == 'vimeo.com'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://player.vimeo.com/video/' + vimeoID(link) +'"></iframe></div>';
      }else if(domain == 'vine.co'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://vine.co/v/' + vineID(link) +'/embed/simple"></iframe></div>';
      }else if(/\.(png|jpg|gif|tiff|svg|bmp|jpeg)$/i.test(link)) {
        var img = document.createElement( "img" );
        img.src = link;
        img.onclick = function(){close_expando(pid);};
        expando.querySelector('.expandotxt').appendChild(img);
      }else if (/\.(mp4|webm)$/i.test(link)) {
        var vid = document.createElement( "video" );
        vid.src = link;
        vid.preload = 'auto';
        vid.autoplay = true;
        vid.loop = true;
        vid.controls = true;
        vid.innerHTML = document.createElement("source").src = link;
        expando.querySelector('.expandotxt').appendChild(vid);
      }else if(domain == 'i.imgur.com' && /\.gifv$/i.test(link)){
        var vidx = document.createElement( "video" );
        vidx.src = 'https://i.imgur.com/' + imgurID(link) + '.mp4';
        vidx.preload = 'auto';
        vidx.autoplay = true;
        vidx.loop = true;
        vidx.controls = true;
        vidx.innerHTML = document.createElement("source").src = 'https://i.imgur.com/' + imgurID(link) + '.mp4';
        expando.querySelector('.expandotxt').appendChild(vidx);
      }

    }
    th.innerHTML = icon.close;
    document.querySelector('div.post[pid="'+pid+'"]').appendChild(expando);
})
