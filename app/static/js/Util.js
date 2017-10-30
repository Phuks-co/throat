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
        if(matchingChild.matches(childSelector)){
          cb(event, matchingChild)
        }
      }
  })
};

u.get = function(url, success, error){ //
  var request = new XMLHttpRequest();
  request.open('GET', url, true);

  request.onload = function() {
    if (this.status >= 200 && this.status < 400) {
      var data = JSON.parse(this.response);
      success(data);
    } else {
      success(data);
    }
  };

  request.onerror = function(err) {
    error(err)
  };

  request.send();
}

module.exports = u;
