import u from "./Util";

function toggleChat() {
    if (!hid) {
        // Hide chat
        this.parentNode.style.height = '1.65em';
        this.parentNode.style.width = '25%';
        document.getElementById('chbott').style.display='none';
        this.setAttribute('hid', true);
    } else {
        // Show chat
        this.parentNode.style.height = '50%';
        this.parentNode.style.width = '50%';
        document.getElementById('chbott').style.display='block';
        this.removeAttribute('hid');
        const x = document.getElementById('chcont');
        x.scrollTop = x.scrollHeight
    }
}

async function loadSdk() {
    console.log('Loading Matrix SDK...')
    import(/* webpackChunkName: "matrix-js-sdk" */ 'matrix-js-sdk').then(() => {
        console.log('Okey dokey')
    })
}


u.sub('#chtitle', 'click', function(e){
    const hid = this.getAttribute('hid');

    if(hid && !window.isChatInitialized) {
        loadSdk()
    } else {
        toggleChat()
    }
})

