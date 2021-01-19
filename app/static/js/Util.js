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
        if(matchingChild.matches(childSelector)){
          cb(event, matchingChild)
        }
      }
  })
};

u.get = function(url, success, error){ //
  const request = new XMLHttpRequest();
  request.open('GET', url, true);

  request.onload = function() {
    if (this.status >= 200 && this.status < 400) {
      try{
        const data = JSON.parse(this.response);
        success(data, this);
      }catch(e){
        success(this.response);
      }
    } else {
      success(this.response);
    }
  };

  request.onerror = function(err) {
    error(err)
  };

  request.send();
};

u.rawpost = function(url, data, success, error){
  var request = new XMLHttpRequest();
  request.open('POST', url, true);
  if(!(data instanceof FormData)){
    request.setRequestHeader("Content-Type", "application/json");
  }
  request.onload = function() {
    if (this.status >= 200 && this.status < 400) {
      try{
        var data = JSON.parse(this.response);
      }catch(e){
        return success(this.response);
      }
      success(data);
    } else {
      if(error){
        error(this.response, 'Status ' + this.status);
      }
    }
  };

  request.onerror = function(err) {
    error(_('Could not contact the server'), err);
  };
  request.send(data);
};

u.post = function(url, data, success, error){
  if(document.getElementById('csrf_token')){
    data['csrf_token'] = document.getElementById('csrf_token').value;
  }
  data = JSON.stringify(data);
  u.rawpost(url, data, success, error);
};

u.sub = function(query, event, fn){
  u.each(query, function(k){
    k.addEventListener(event, fn);
  })
}

export default u;
