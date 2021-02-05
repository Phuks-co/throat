import u from './Util'
import icon from './Icon';

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
function streamableID(url) {
  var match = url.match(/^http(?:s?):\/\/(?:www\.)?streamable\.com\/([a-zA-Z0-9]{1,13})$/);
  if (match){
    return match[1];
	}
}
function gfycatID(url) {
  var match = url.match(/^https?:\/\/gfycat\.com\/(?:gifs\/detail\/?)?([a-zA-Z0-9/-]{1,60})$/);
  if (match){
    var gfy = match[1].split("-", 1);
    return gfy;
	}
}
function streamjaID(url) {
  var match = url.match(/^https?:\/\/streamja\.com\/([a-zA-Z0-9]{1,20})$/);
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

function close_expando( pid){
  var k = document.querySelector('div.expando-master[pid="'+pid+'"]')
  k.parentNode.removeChild(k);
  document.querySelector('div.expando[data-pid="'+pid+'"] .expando-btn').innerHTML = icon[document.querySelector('div.expando[data-pid="'+pid+'"] .expando-btn').getAttribute('data-icon')];
}

function video_expando(link, expando) {
  const vid = document.createElement( "video" );
  vid.src = link;
  vid.preload = 'auto';
  vid.autoplay = true;
  vid.loop = false;
  vid.controls = true;
  vid.innerHTML = document.createElement("source").src = link;
  vid.style.width = "640px";
  vid.style.height = "360px";

  const handle = document.createElement('div');
  handle.className = 'resize-handle';
  handle.innerHTML = '<div class="i-icon" data-icon="resizeArrow"</div>';

  const wrapper = document.createElement('div');
  wrapper.className = 'expando-wrapper';
  wrapper.appendChild(vid)
  wrapper.appendChild(handle)
  //wrapper.innerHTML = vid.outerHTML + handle.outerHTML;
  expando.querySelector('.expandotxt').appendChild(wrapper);

  resizer(expando.querySelector('.expandotxt video'), expando.querySelector('.expandotxt .resize-handle'), expando.querySelector('.expandotxt'))
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
        expando.querySelector('.expandotxt').innerHTML = '<div class="expando-wrapper" style="height: 386px; will-change: height;"><iframe style="height: 360px; width: 640px;" src="https://www.youtube.com/embed/' + youtubeID(link) + extra +'" allowfullscreen=""></iframe><div class="resize-handle"><div class="i-icon" data-icon="resizeArrow"</div></div>';
        resizer(expando.querySelector('.expandotxt iframe'), expando.querySelector('.expandotxt .resize-handle'), expando.querySelector('.expandotxt'))
      }else if(domain == 'gfycat.com'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://gfycat.com/ifr/' + gfycatID(link) +'"></iframe></div>';
      }else if(domain == 'vimeo.com'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://player.vimeo.com/video/' + vimeoID(link) +'"></iframe></div>';
      }else if(domain == 'streamja.com'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://streamja.com/embed/' + streamjaID(link) +'"></iframe></div>';
      }else if(domain == 'streamable.com'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://streamable.com/o/' + streamableID(link) +'"></iframe></div>';
      }else if(domain == 'vine.co'){
        expando.querySelector('.expandotxt').innerHTML = '<div class="iframewrapper"><iframe width="100%" src="https://vine.co/v/' + vineID(link) +'/embed/simple"></iframe></div>';
      }else if(/\.(png|jpg|gif|tiff|svg|bmp|jpeg)$/i.test(link)) {
        const img = document.createElement("img");
        img.src = link;
        img.draggable = false;
        //img.onclick = function(){close_expando(pid);};
        confResizer(img, expando.querySelector('.expandotxt'));
        expando.querySelector('.expandotxt').appendChild(img);
      }else if (/\.(mp4|webm)$/i.test(link)) {
        video_expando(link, expando)
      }else if(domain == 'i.imgur.com' && /\.gifv$/i.test(link)){
        video_expando('https://i.imgur.com/' + imgurID(link) + '.mp4', expando)
      }
    }
    th.querySelector('.expando-btn').innerHTML = icon.close;
    document.querySelector('div.post[pid="'+pid+'"]').appendChild(expando);
    icon.rendericons();
})

function resizer(element, handle, boundary) {
  if(!handle) element = handle;

  let lastX, lastY, left, top, startWidth, startHeight, startDiag;
  let active = false;

  handle.addEventListener('mousedown', initResize);

  function resize(e) {
    const deltaX = e.clientX - lastX;
    const deltaY = e.clientY - lastY;

    if(1 & ~e.buttons) return stop();
    if(!deltaX || !deltaY) return;
    if(!active) activate();

    // It has decided to move!
    const ratio = 1;

    const diag = Math.round(Math.hypot(Math.max(1, e.clientX - left), Math.max(1, e.clientY - top)))

    const nWidth = diag / startDiag * startWidth;

    if(nWidth * ratio < 100) return;

    const width = element.getBoundingClientRect().width;
    const height = element.getBoundingClientRect().height;

    if(nWidth * ratio >= boundary.clientWidth * 0.95 && (nWidth * ratio) > width) return;

    element.style.height = ((height / width) * (nWidth * ratio)).toFixed(2) + 'px';
    element.style.width = nWidth * ratio + 'px';

    lastX = e.clientX;
    lastY = e.clientY;
    //resize(element, nWidth * ratio);

  }

  function activate() {
    active = true;
    left = element.getBoundingClientRect().left;
    top = element.getBoundingClientRect().top;
    startWidth = element.getBoundingClientRect().width;
    startHeight = element.getBoundingClientRect().height;

    startDiag = Math.round(Math.hypot(Math.max(1, lastX - left), Math.max(1, lastY - top)))
  }

  function stop() {
    document.removeEventListener('mouseup', stop);
    document.removeEventListener('mousemove', resize);
    element.style.pointerEvents = 'all';
  }

  function initResize(e) {
    if (e.button !== 0) return;
    lastX = e.clientX;
    lastY = e.clientY;
    active = false;

    document.addEventListener('mouseup', stop);
    document.addEventListener('mousemove', resize);
    element.style.pointerEvents = 'none';
    
    e.preventDefault();
  }

}


function confResizer(el, pnode, corner) {
  if(corner) {
    const resizer = document.createElement('div');
    resizer.style.width = '10px';
    resizer.style.height = '10px';
    resizer.style.background = 'red';
    resizer.style.position = 'absolute';
    resizer.style.right = 0;
    resizer.style.bottom = 0;
    resizer.style.cursor = 'se-resize';
    //Append Child to Element
    element.appendChild(resizer);
    //box function onmousemove
    resizer.addEventListener('mousedown', initResize, false);
  }else{
    el.addEventListener('mousedown', initResize, false);
  }

  //element.appendChild(resizer);
  //box function onmousemove
  let startx = 0, starty = 0;
  //Window funtion mousemove & mouseup
  function initResize(e) {
    startx = e.clientX;
    starty = e.clientY;
    window.addEventListener('mousemove', resize, false);
    window.addEventListener('mouseup', stopResize, false);
  }

  function resize(e) {
    // Average x and y mvmt
    let emvt = (e.clientX - startx) + (e.clientY - starty);
    emvt = emvt / 2
    startx = e.clientX
    starty = e.clientY

    // Get ratio of resize so we can keep the aspect ratio
    const resizeRatio = (el.width + emvt) / el.width

    // Check if we're going out of bounds (so far the only limit is width)
    if(el.width * resizeRatio >= pnode.clientWidth * 0.95 && resizeRatio > 1) return;

    //el.style.width = (el.width * resizeRatio) + 'px';
    el.style.height = (el.height * resizeRatio) + 'px';
  }

  function stopResize(e) {
    window.removeEventListener('mousemove', resize, false);
    window.removeEventListener('mouseup', stopResize, false);
  }
}
