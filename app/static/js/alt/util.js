/* Misc functions go here */

/* Little hack so we can operate various modules with one route */
m.routes = function mRoutes( defaultRoute, routesMap ){
	var routes = {};

	for( var route in routesMap ){
		routes[ route ] = {
			controller : subRouter( routesMap[ route ] ),
			view       : noop
		};
	}

	return m.route( document.body, defaultRoute, routes );

	function subRouter( modules ){
		return function routeChange(){
			m.redraw.strategy( 'none' );

			for( var key in modules ){
				m.module( document.querySelector( key ), modules[ key ] );
			}
		};
	}

	function noop(){}
};

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}


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
function xkcdID(url) {
  var match = url.match(/^http(?:s?):\/\/xkcd\.com\/([a-zA-Z0-9/]{1,10})$/);
  if (match){
    return match[1].replace(/\//,'');
	}
}
function streamableID(url) {
  var match = url.match(/^http(?:s?):\/\/streamable\.com\/([a-zA-Z0-9]{1,10})$/);
  if (match){
    return match[1];
	}
}
