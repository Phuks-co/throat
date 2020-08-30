/* Icon.js
Our own solution for svg icons :(
*/
import u from './Util';

function rendericons(){
  u.each('*[data-icon]', function(el,i){
    if(Icons[el.getAttribute('data-icon')]){
      el.innerHTML = Icons[el.getAttribute('data-icon')];
    }else{
      el.innerHTML = Icons.close;
    }
  })
}

// list of all the icons
var Icons = {
  mail: require('../svg/mail.svg'),
  cog: require('../svg/cog.svg'),
  sun: require('../svg/sun-fill.svg') ,
  moon: require('../svg/moon-fill.svg'),

  play: require('../svg/play_arrow.svg'),
  twitter: require('../svg/twitter.svg'),
  image: require('../svg/image.svg'),
  text: require('../svg/file-text.svg'),
  close: require('../svg/close.svg'),
  exclaim: require('../svg/exclaim.svg'),

  chat: require('../svg/chat.svg') ,
  link: require('../svg/link.svg') ,

  upvote: require('../svg/up.svg'),
  downvote: require('../svg/down.svg'),
  updown: require('../svg/updown.svg'),

  search: require('../svg/search.svg'),

  check: require('../svg/check.svg'),
  add: require('../svg/add.svg'),
  remove: require('../svg/remove.svg'),

  owner: require('../svg/star.svg'),

  comments: require('../svg/bubbles.svg'),

  bold: require('../svg/bold.svg'),
  italic: require('../svg/italic.svg'),
  underline: require('../svg/underline.svg'),
  strikethrough: require('../svg/strikethrough.svg'),
  title: require('../svg/title.svg'),
  bulletlist: require('../svg/bulletlist.svg'),
  numberlist: require('../svg/numberlist.svg'),
  code: require('../svg/code.svg'),
  quote: require('../svg/quote.svg'),

  coffee: require('../svg/coffee.svg'),
  donor: require('../svg/donor.svg'),
  copyright: require('../svg/copyright.svg'),

  edit: require('../svg/edit.svg'),

  down: require('../svg/caret-down.svg'),
  up: require('../svg/caret-up.svg'),

  resize: require('../svg/resize.svg'),
  resizeArrow: require('../svg/resize_arrow.svg'),

  rendericons: rendericons,
};

u.ready(function(){
  rendericons();
});

// here we apply em.

module.exports = Icons;
