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
  var match = url.match(/^https?:\/\/gfycat\.com\/(?:gifs\/detail\/?)?([a-zA-Z0-9]{1,60})$/);
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

function getParameterByName(name, url) {
  name = name.replace(/[\[\]]/g, "\\$&");
  var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
      results = regex.exec(url);
  if (!results) return null;
  if (!results[2]) return '';
  return decodeURIComponent(results[2].replace(/\+/g, " "));
}


function imgurID(url) {
  var match = url.match(/^http(?:s?):\/\/(i\.)?imgur\.com\/(.*?)(?:\/.gifv|$)/);
  if (match){
    return match[2].replace(/.gifv/,'');
	}
}

function instaudioID(url) {
    var match = url.match(/^http(?:s?):\/\/instaud\.io\/(\d+)/)
    if (match){
        return match[1];
    }
}

function close_expando( pid){
  var k = document.querySelector('div.expando-master[pid="'+pid+'"]')
  k.parentNode.removeChild(k);
  document.querySelector('div.expando[data-pid="'+pid+'"] .expando-btn').innerHTML = icon[document.querySelector('div.expando[data-pid="'+pid+'"] .expando-btn').getAttribute('data-icon')];
}

u.addEventForChild(document, 'click', '.expando', function(e, ematch){
    var th=ematch;

    var link=th.getAttribute('data-link');
    var pid=th.getAttribute('data-pid');
    if(document.querySelector('div.expando-master[pid="'+pid+'"]')){
      return close_expando(pid);
    }
    var expando = document.createElement('div');
    expando.setAttribute('pid', pid);
    expando.classList.add('expando-master');
    expando.innerHTML = '<div class="expandotxt"></div>';
    if(link == 'None'){
      u.get('/do/get_txtpost/' + pid, function(data){
        if(data.status == 'ok'){
          expando.querySelector('.expandotxt').innerHTML = data.content;
        }
      })
    }else{
      var domain = get_hostname(link);
      if((domain == 'youtube.com') || (domain == 'www.youtube.com') || (domain == 'youtu.be')){
        var extra = '?';
        if(getParameterByName('list', link)){
          extra += 'list=' + getParameterByName('list', link) + '&';
        }
        if(getParameterByName('t', link)){
          var time_regex = /(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?/;
          var start = getParameterByName('t', link);
          var m = null;
          if ((m = time_regex.exec(start)) !== null) {
            if (!m[1] && !m[2] && !m[3] && !m[4]) {
              start = start.replace(/\D/g,'');
              extra += 'start=' + start;
            }else{
              var i;
              for (i = 0; i < m.length; i++) {
                m[i] = (m[i] === undefined) ? 0 : m[i];
              }
              var time = parseInt(m[1]) * 86400 + parseInt(m[2]) * 3600 + parseInt(m[3]) * 60 + parseInt(m[4]);
              extra += 'start=' + time;
            }
          }else{ // not d h m s letters in t
            start = start.replace(/\D/g,'');
            extra += 'start=' + start;
          }
        }
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://www.youtube.com/embed/' + youtubeID(link) + extra +'" allowfullscreen=""></iframe></div>';
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
      }else if (domain == 'instaud.io') {
        var vid = document.createElement( "audio" );
        vid.src = 'https://instaud.io/_/' + instaudioID(link) + '.mp3';
        vid.preload = 'auto';
        vid.autoplay = true;
        vid.loop = false;
        vid.controls = true;
        vid.innerHTML = document.createElement("source").src = 'https://instaud.io/_/' + instaudioID(link);
        expando.querySelector('.expandotxt').appendChild(vid);
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
    th.querySelector('.expando-btn').innerHTML = icon.close;
    document.querySelector('div.post[pid="'+pid+'"]').appendChild(expando);
})
