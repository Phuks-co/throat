import $ from 'jquery';

require('../css/miner.css');

// todo: move to util
function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) === 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

$('#mining-throttle-add').click(function() {
	var throttle = cminer.getThrottle()
	if (throttle != 0) {
		var step = 10;
		var stepb = 0.1;
		var newlvl = Math.round((throttle - stepb) * 10) / 10;
		var newperc = parseInt((throttle - stepb) * 100);
		document.getElementById("mining-throttle").innerHTML = Math.round(100 - newperc);
		cminer.setThrottle(newlvl)
		console.log("throttle up to " + Math.round(100 - newperc) + '%')
    localStorage.setItem('throttle', newlvl)
	}
});
$('#mining-throttle-subtract').click(function() {
	var throttle = cminer.getThrottle()
	if (throttle != 0.9) {
		var step = 10;
		var stepb = 0.1;
		var newlvl = Math.round((throttle + stepb) * 10) / 10;
		var newperc = parseInt((throttle + stepb) * 100);
		document.getElementById("mining-throttle").innerHTML = Math.round(100 - newperc);
		cminer.setThrottle(newlvl)
		console.log("throttle down to " + Math.round(100 - newperc) + '%')
    localStorage.setItem('throttle', newlvl)
	}
})


var MinerUI = function(miner, elements) {
  this.miner = miner;
  this.elements = elements;

  this.intervalUpdateStats = 0;
  this.intervalDrawGraph = 0;

  this.ctx = this.elements.canvas.getContext('2d');
  console.log(this.miner.getNumThreads())
  this.elements.threads.textContent = this.miner.getNumThreads();
  var newperc = parseInt((this.miner.getThrottle()) * 100);
  this.elements.throttle.textContent = Math.round(100 - newperc);

  this.elements.startButton.addEventListener('click', this.start.bind(this));
  this.elements.stopButton.addEventListener('click', this.stop.bind(this));

  this.elements.threadsAdd.addEventListener('click', this.addThread.bind(this));
  this.elements.threadsRemove.addEventListener('click', this.removeThread.bind(this));

  this.stats = [];
  /*for (var i = 0, x = 0; x < 300; i++, x += 5) {
    this.stats.push({hashes: 0, accepted: 0});
  }*/
  for (var i = 0, x = 0; x < (this.elements.canvas.offsetWidth/9)-10; i++, x += 1) {
    this.stats.push({hashes: 0, accepted: 0});
  }

  this.didAcceptHash = false;
  this.miner.on('accepted', function(){
    this.didAcceptHash = true;
  }.bind(this));
};

MinerUI.prototype.start = function(ev) {
  this.miner.start(CoinHive.FORCE_MULTI_TAB);
  this.elements.container.classList.add('running');
  this.elements.container.classList.remove('stopped');

  this.intervalUpdateStats = setInterval(this.updateStats.bind(this), 50);
  this.intervalDrawGraph = setInterval(this.drawGraph.bind(this), 500);

  this.elements.threads.textContent = this.miner.getNumThreads();

  ev.preventDefault();
  return false;
};

MinerUI.prototype.stop = function(ev) {
  this.miner.stop();
  this.elements.hashesPerSecond.textContent = 0;
  this.elements.container.classList.remove('running');
  this.elements.container.classList.add('stopped');

  clearInterval(this.intervalUpdateStats);
  clearInterval(this.intervalDrawGraph);

  ev.preventDefault();
  return false;
};

MinerUI.prototype.addThread = function(ev) {
  this.miner.setNumThreads(this.miner.getNumThreads() + 1);
  this.elements.threads.textContent = this.miner.getNumThreads();
  localStorage.setItem('threads', this.miner.getNumThreads());
  ev.preventDefault();
  return false;
};

MinerUI.prototype.removeThread = function(ev) {
  this.miner.setNumThreads(Math.max(0, this.miner.getNumThreads() - 1));
  this.elements.threads.textContent = this.miner.getNumThreads();
  localStorage.setItem('threads', this.miner.getNumThreads());

  ev.preventDefault();
  return false;
};

MinerUI.prototype.updateStats = function() {
  this.elements.hashesPerSecond.textContent = this.miner.getHashesPerSecond().toFixed(1);
  this.elements.hashesTotal.textContent = this.miner.getTotalHashes(true);
};

MinerUI.prototype.drawGraph = function() {

  // Resize canvas if necessary
  if (this.elements.canvas.offsetWidth !== this.elements.canvas.width) {
    this.elements.canvas.width = this.elements.canvas.offsetWidth;
    this.elements.canvas.height = this.elements.canvas.offsetHeight;
  }
  var w = this.elements.canvas.width;
  var h = this.elements.canvas.height;



  var current = this.stats.shift();
  var last = this.stats[this.stats.length-1];
  current.hashes = this.miner.getHashesPerSecond();
  current.accepted = this.didAcceptHash;
  this.didAcceptHash = false;
  this.stats.push(current);

  // Find max value
  var vmax = 0;
  for (var i = 0; i < this.stats.length; i++) {
    var v = this.stats[i].hashes;
    if (v > vmax) { vmax = v; }
  }
  // Draw all bars
  this.ctx.clearRect(0, 0, w, h);
  for (var i = this.stats.length, j = 1; i--; j++) {
    var s = this.stats[i];
    var mode = getCookie("dayNight");
    var vh = ((s.hashes/vmax) * (h - 16))|0;
    if (s.accepted) {
      if(mode == "dark"){
        this.ctx.fillStyle = '#555'
      }else{
        this.ctx.fillStyle = '#aaa'
      }
      this.ctx.fillRect(w - j*10, h - vh, 9, vh);
    }
    else {
      if(mode == "dark"){
        this.ctx.fillStyle = '#222'
      }else{
        this.ctx.fillStyle = '#ccc'
      }
      this.ctx.fillRect(w - j*10, h - vh, 9, vh);
    }
  }
};
var ui = new MinerUI(cminer, {
  container: document.getElementById('miner'),
  canvas: document.getElementById('mining-stats-canvas'),
  hashesPerSecond: document.getElementById('mining-hashes-per-second'),
  hashesPerSecond: document.getElementById('mining-hashes-per-second'),
  throttle: document.getElementById('mining-throttle'),
  threads: document.getElementById('mining-threads'),
  threadsAdd: document.getElementById('mining-threads-add'),
  threadsRemove: document.getElementById('mining-threads-remove'),
  hashesTotal: document.getElementById('mining-hashes-total'),
  startButton: document.getElementById('mining-start'),
  stopButton: document.getElementById('mining-stop')
});

window.setInterval(function(){
  $.ajax({
    url: '/miner/stats',
    dataType: 'json',
  }).done(function(d){
    $('#hps').text(d.hashesPerSecond);
    $('#ht').text(d.hashesTotal);
    $('#xpe').text(d.xmrPending);
    $('#xpa').text(d.xmrPaid);
  });
  $.ajax({
    url: '/miner/userstats',
    dataType: 'json',
  }).done(function(d){
    $('#nm').text(d.name);
    $('#bal').text(d.balance);
  });
  $.ajax({
    url: '/miner/leaderboard',
    dataType: 'json',
  }).done(function(d){
    var tabl = '';
    var tablb = '';
    for (var i = 0; i < d.users.length; i++) {
      tabl = tabl + '<tr><td class="center">'+ (i+1) + '</td><td><span>' + d.users[i].username + '</span></td>';
      tabl = tabl + '<td><b><span>' + d.users[i].score + '</span></b></td></tr>';
    }

    for (var i = 0; i < d.speed.length; i++) {
      tablb = tablb + '<tr><td class="center">'+ (i+1) + '</td><td><span>' + d.speed[i].username + '</span></td>';
      tablb = tablb + '<td><b><span>' + d.speed[i].hashes + '</span></b> H/s</td></tr>';
    }
    $('#miningleaderboard table').html(tabl);
    $('#speedleaderboard table').html(tabl);
  });
}, 120000);
