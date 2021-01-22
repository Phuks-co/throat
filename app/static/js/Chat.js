import u from "./Util";

function loadChat() {
  document.getElementById('chstatus').innerText = "Loading.."
  console.info('Loading Chat bundle')
  import(/* webpackChunkName: "chat" */ './utils/MatrixUtils')
    .then((chat) => {
      console.info('Chat bundle Loaded.')
      chat.loadChat()
    })
}


u.sub('#chtitle', 'click', function(){
  const hid = this.getAttribute('hid') === 'true';
  const matrixEnabled = document.getElementById('matrix-chat')
  if (hid && !window.isChatLoaded && matrixEnabled) {
    console.log('Load')
    loadChat()
  }
  if(!hid){ // hid
    this.parentNode.style.height = '1.65em';
    this.parentNode.style.width = '25%';
    document.getElementById('chbott').style.display='none';
    this.setAttribute('hid', true);
  }else{
    this.parentNode.style.height = '50%';
    this.parentNode.style.width = '50%';
    document.getElementById('chbott').style.display='block';
    this.removeAttribute('hid');
    const x = document.getElementById('chcont');
    x.scrollTop = x.scrollHeight
  }
})

