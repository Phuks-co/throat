// Collection of useful stuff
var u = {};

// same as $(document).ready()
u.ready = function (fn) {
  if (document.attachEvent ? document.readyState === "complete" : document.readyState !== "loading"){
    fn();
  } else {
    document.addEventListener('DOMContentLoaded', fn);
  }
};

// same as $.each
u.each = function(selector, fn){
  var elements = document.querySelectorAll(selector);
  Array.prototype.forEach.call(elements, fn);
};

u.addEventForChild = function(parent, eventName, childSelector, cb){
  parent.addEventListener(eventName, function(event){
    const clickedElement = event.target,
      matchingChild = clickedElement.closest(childSelector)
      if(matchingChild !== null){
      console.log(matchingChild)
      if(matchingChild.className == childSelector){
        console.log('woot')
        cb(event, matchingChild)
      }
    }
  })
};


module.exports = u;
