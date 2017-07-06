import './ext/CustomElements.min.js';
import 'purecss/build/base.css';
import 'purecss/build/forms.css';
import 'purecss/build/buttons.css';
import 'purecss/build/grids.css';
import 'purecss/build/grids-responsive.css';
import 'purecss/build/menus.css';
import 'time-elements/time-elements.js';
import $ from 'jquery';

require('../css/main.css');
require('../css/dark.css');

require('./Icon');
require('./Expando');


function vote(obj, how){
  $.ajax({
    type: "POST",
    url: '/do/vote/'+ obj.data('pid') + '/' + how,
    success: function(data) {
      if(data.status == "ok"){
        obj.addClass((how == 'up') ? 'upvoted' : 'downvoted');
        obj.parent().children((how == 'up') ? '.downvote' : '.upvote').removeClass((how == 'up') ? 'downvoted' : 'upvoted');
        var count = obj.parent().children('.score');
        count.text((how == 'up') ? (parseInt(count.text())+1) : (parseInt(count.text())-1));
      }
    }
  }).catch(function(e){
    if(e.status == 403){
      // TODO: Show error if user is not authenticated
    }
  });
}

// up/downvote buttons.
$(document).on('click', '.upvote', function(){
  var obj = $(this);
  vote(obj, 'up');
});

$(document).on('click', '.downvote', function(){
  var obj = $(this);
  vote(obj, 'down');
});
