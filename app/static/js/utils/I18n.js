// When adding new languages, add them here.
let languages = {
    'es': require('../../../translations/es/LC_MESSAGES/messages.po'),
    'ru': require('../../../translations/ru/LC_MESSAGES/messages.po'),
    'sk': require('../../../translations/sk/LC_MESSAGES/messages.po'),
};

// Taken from gettext.js
const strfmt = function (fmt) {
    const args = arguments;

    return fmt
        // put space after double % to prevent placeholder replacement of such matches
        .replace(/%%/g, '%% ')
        // replace placeholders
        .replace(/%(\d+)/g, function (str, p1) {
            return args[p1];
        })
        // replace double % and space with single %
        .replace(/%% /g, '%');
};

function _(){
    let string = arguments[0];
    let args = Array.from(arguments);
    args.shift();
    let lang = document.getElementsByTagName('html')[0].getAttribute('lang');
    
    if(!languages[lang] || !languages[lang][string]){
        return strfmt.apply(strfmt, [string, ...args]);
    }
    return languages[lang][string](args);
}

export default _;
