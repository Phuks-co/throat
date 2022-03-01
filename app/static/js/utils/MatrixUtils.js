import sanitizeHtml from "sanitize-html";
import u from "../Util";
import anchorme from "anchorme";
import _ from './I18n';

const sdk = require('matrix-js-sdk');


function escapeHtml(html) {
  const text = document.createTextNode(html);
  const p = document.createElement('p');
  p.appendChild(text);
  return p.innerHTML;
}

function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function loadHistory(client, room) {
  document.getElementById('chstatus').innerText = "Loading history......"
  try {
    client.scrollback(room, 30, (_, room) => {
      document.getElementById('chstatus').innerText = "";
      console.log(room.timeline)
      room.timeline.forEach((event) => {
        addMessage(event.event, event.sender, false)
      })
    })
  } catch (err) {
    document.getElementById('chstatus').innerText = "";
  }
}

function startWithToken(access_token, user_id) {
  document.getElementById('chstatus').innerText = "Connecting....."
  const defaultRoom = document.getElementById('matrix-roomId').getAttribute('data-value')
  const homeServerUrl = document.getElementById('matrix-homeserver').getAttribute('data-value')
  const client = sdk.createClient({
    baseUrl: homeServerUrl,
    accessToken: access_token,
    userId: user_id
  });
  window.isChatLoaded = true
  window.matrixClient = client
  window.currentlyTyping = new Set()
  client.startClient({lazyLoadMembers: true});
  client.once('sync', function (state) {
    if (state === 'PREPARED') {
      const rooms = client.getRooms()
      let foundRoom = false
      rooms.forEach((room) => {
        if (room.roomId != defaultRoom) return;
        foundRoom = room
      })
      if(!foundRoom) {
        document.getElementById('chstatus').innerText = "Making you join the chatroom >:("
        client.joinRoom(defaultRoom, {syncRoom: true}).then(() => {
          loadHistory(client, foundRoom)
        });
      } else {
        loadHistory(client, foundRoom)
      }
      client.on("Room.timeline", function (event, room, toStartOfTimeline) {
        if (room.roomId != defaultRoom) return;
        if (toStartOfTimeline) return; // Handled by scrollback func
        console.log('timeline', toStartOfTimeline, event);
        addMessage(event.event, event.sender, toStartOfTimeline)
      });

      client.on('RoomMember.typing', (_, member) => {
        if (member.roomId != defaultRoom) return;
        // Add or remove member from currently typing members
        let username = member.name;
        let typing = member.typing;

        // If event is in current room
        let currentlyTyping = window.currentlyTyping;
        if (typing) {
          // Add to list
          if (!currentlyTyping.has(username)) {
            currentlyTyping.add(username);
          }
        } else {
          // Remove from list
          currentlyTyping.delete(username)
        }
        const userArr = Array.from(currentlyTyping)
        if (userArr.length > 1) {
          const last = userArr.pop();
          document.getElementById('chstatus').innerText = userArr.join(', ') + ' and ' + last + ' are typing'
        } else if (userArr.length == 1) {
          document.getElementById('chstatus').innerText = userArr[0] + ' is typing'
        } else {
          document.getElementById('chstatus').innerText = ''
        }
      });

      u.sub('#chsend', 'keydown', function (e) {
        if (!document.getElementById('matrix-chat')) return
        if (!window.isChatLoaded) return;
        if (e.keyCode == 13) {
          const me = client.getUser(user_id)
          const content = {
              msgtype: 'm.text',
              body: this.value,
            };
          console.log(me)
          client.sendMessage(defaultRoom, content, undefined)
          this.value = '';
          //client.sendEvent(defaultRoom, 'm.room.message', this.value, "")
        }
      })
    }
  });
}

export function loadChat() {
  const homeServerUrl = document.getElementById('matrix-homeserver').getAttribute('data-value')

  window.matrixSdk = sdk
  const matrixClient = sdk.createClient({
    baseUrl: homeServerUrl
  });
  const accessToken = window.sessionStorage.getItem('matrixAccessToken')
  const userId = window.sessionStorage.getItem('matrixUserId')

  if (accessToken) {
    startWithToken(accessToken, userId)
    return;
  }

  document.getElementById('chstatus').innerText = "Fetching tokens..."

  u.post('/auth/matrix', {}, (data) => {
    const loginToken = data.token
    document.getElementById('chstatus').innerText = "Logging in...."
    matrixClient.loginWithToken(loginToken, (err, data) => {
      if (err) {
        document.getElementById('chstatus').innerText = "There was an error while logging you in :("
      } else {
        window.sessionStorage.setItem('matrixAccessToken', data.access_token)
        window.sessionStorage.setItem('matrixUserId', data.user_id)
        startWithToken(data.access_token, data.user_id)
      }
    })

  }, () => {
    document.getElementById('chstatus').innerText = "Could not fetch tokens :("
  })
}

function addMessage(message, sender, toStartOfTimeline, grayed) {

  const homeServerUrl = document.getElementById('matrix-homeserver').getAttribute('data-value')
  const cont = document.getElementById('chcont')

  const dMessage = document.createElement('div')
  dMessage.classList.add('msg')
  if (grayed) dMessage.classList.add('gray')
  dMessage.setAttribute('eventId', message.event_id)

  const messageSender = document.createElement('span')
  messageSender.classList.add('msguser')
  const messageContent = document.createElement('span')
  messageContent.classList.add('damsg')

  switch(message.type) {
    case 'm.room.message':
      messageSender.innerHTML = sender.name + '>'
      messageSender.title = sender.userId

      switch (message.content.msgtype) {
        case 'm.image':
          const imgLink = document.createElement('a');
          imgLink.href = homeServerUrl + '/_matrix/media/r0/download/' + message.content.url.replace('mxc://', '');
          imgLink.innerText = message.content.body
          imgLink.target = '_blank'
          const imgDesc = document.createElement('span');
          imgDesc.innerText = ` (${message.content.info.w}x${message.content.info.h}) ${formatBytes(message.content.info.size)}`
          messageContent.appendChild(imgLink);
          messageContent.appendChild(imgDesc);
          break;
        case 'm.emote':
          messageSender.innerHTML = ' * ' + sender.name + ' ';
          messageContent.innerText = message.content.body
          break;
        default:
          messageContent.innerHTML = anchorme(escapeHtml(message.content.body), {
            emails: false,
            files: false,
            attributes: [{name: "target", value: "blank"}]
          })
          if (message.content.format == 'org.matrix.custom.html') {
            messageContent.innerHTML = bodyToHtml(message.content, {})
          }
      }
      dMessage.appendChild(messageSender)
      dMessage.appendChild(messageContent)
      break;
    case 'm.room.member':
      messageSender.innerHTML = ' * ' + sender.name + ' ';
      messageSender.title = sender.userId
      switch (message.content.membership) {
        case 'leave':
          messageContent.innerText = _('left the room')
          break;
        case 'join':
          messageContent.innerText = _('joined the room')
          break;
      }
      dMessage.appendChild(messageSender)
      dMessage.appendChild(messageContent)
      break;
    case 'm.room.redaction':
      const deletedMessage = document.querySelector(`.msg[eventId="${message.redacts}"]`)
      if(deletedMessage) {
        deletedMessage.querySelector('.msguser').classList.add('gray')
        deletedMessage.querySelector('.damsg').classList.add('gray')
        deletedMessage.querySelector('.damsg').classList.add('irc-italic')
        deletedMessage.querySelector('.damsg').innerHTML = _('message deleted')
      }
      break;
    default:
      messageContent.innerText = '*Could not render this message*'
      messageContent.classList.add('gray')
      messageContent.classList.add('irc-italic')
      dMessage.appendChild(messageContent)
      console.warn("Could not render message:", message)
  }

  if (toStartOfTimeline) {
    cont.insertBefore(dMessage, cont.firstChild)
  } else {
    cont.appendChild(dMessage)
  }

  const k = document.getElementsByClassName('msg')
  if (k.length > 3) {
    if (u.isScrolledIntoView(k[k.length - 2])) {
      k[k.length - 2].scrollIntoView();
    }
  }
}


// Most of this was taken from the Matrix SDK.
// License: https://github.com/matrix-org/matrix-react-sdk/blob/430bceb91d2d79a4fac67b8e3a9650999ad2dc88/LICENSE

const SURROGATE_PAIR_PATTERN = /([\ud800-\udbff])([\udc00-\udfff])/;
const SYMBOL_PATTERN = /([\u2100-\u2bff])/;
const COLOR_REGEX = /^#[0-9a-fA-F]{6}$/;


function mightContainEmoji(str) {
  return SURROGATE_PAIR_PATTERN.test(str) || SYMBOL_PATTERN.test(str);
}

export const PERMITTED_URL_SCHEMES = ['http', 'https', 'ftp', 'mailto', 'magnet'];


const transformTags = { // custom to matrix
  // add blank targets to all hyperlinks except vector URLs
  'a': function (tagName, attribs) {
    if (attribs.href) {
      attribs.target = '_blank'; // by default
    }
    attribs.rel = 'noreferrer noopener'; // https://mathiasbynens.github.io/rel-noopener/
    return {tagName, attribs};
  },
  'img': function (tagName, attribs) {
    // Strip out imgs that aren't `mxc` here instead of using allowedSchemesByTag
    // because transformTags is used _before_ we filter by allowedSchemesByTag and
    // we don't want to allow images with `https?` `src`s.
    // We also drop inline images (as if they were not present at all) when the "show
    // images" preference is disabled. Future work might expose some UI to reveal them
    // like standalone image events have.
    if (!attribs.src || !attribs.src.startsWith('mxc://') || !SettingsStore.getValue("showImages")) {
      return {tagName, attribs: {}};
    }
    attribs.src = window.matrixClient.mxcUrlToHttp(
      attribs.src,
      attribs.width || 800,
      attribs.height || 600,
    );
    return {tagName, attribs};
  },
  '*': function (tagName, attribs) {
    // Delete any style previously assigned, style is an allowedTag for font and span
    // because attributes are stripped after transforming
    delete attribs.style;

    // Sanitise and transform data-mx-color and data-mx-bg-color to their CSS
    // equivalents
    const customCSSMapper = {
      'data-mx-color': 'color',
      'data-mx-bg-color': 'background-color',
      // $customAttributeKey: $cssAttributeKey
    };

    let style = "";
    Object.keys(customCSSMapper).forEach((customAttributeKey) => {
      const cssAttributeKey = customCSSMapper[customAttributeKey];
      const customAttributeValue = attribs[customAttributeKey];
      if (customAttributeValue &&
        typeof customAttributeValue === 'string' &&
        COLOR_REGEX.test(customAttributeValue)
      ) {
        style += cssAttributeKey + ":" + customAttributeValue + ";";
        delete attribs[customAttributeKey];
      }
    });

    if (style) {
      attribs.style = style;
    }

    return {tagName, attribs};
  },
};

const sanitizeHtmlParams = {
  allowedTags: [
    'font', // custom to matrix for IRC-style font coloring
    'del', // for markdown
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'p', 'a', 'ul', 'ol', 'sup', 'sub',
    'nl', 'li', 'b', 'i', 'u', 'strong', 'em', 'strike', 'code', 'hr', 'br', 'div',
    'table', 'thead', 'caption', 'tbody', 'tr', 'th', 'td', 'pre', 'span', 'img',
  ],
  allowedAttributes: {
    // custom ones first:
    font: ['color', 'data-mx-bg-color', 'data-mx-color', 'style'], // custom to matrix
    span: ['data-mx-maths', 'data-mx-bg-color', 'data-mx-color', 'data-mx-spoiler', 'style'], // custom to matrix
    div: ['data-mx-maths'],
    a: ['href', 'name', 'target', 'rel'], // remote target: custom to matrix
    img: ['src', 'width', 'height', 'alt', 'title'],
    ol: ['start'],
    code: ['class'], // We don't actually allow all classes, we filter them in transformTags
  },
  // Lots of these won't come up by default because we don't allow them
  selfClosing: ['img', 'br', 'hr', 'area', 'base', 'basefont', 'input', 'link', 'meta'],
  // URL schemes we permit
  allowedSchemes: PERMITTED_URL_SCHEMES,
  allowProtocolRelative: false,
  transformTags,
  // 50 levels deep "should be enough for anyone"
  nestingLimit: 50,
};

// Part of Replies fallback support
function stripPlainReply(body) {
  // Removes lines beginning with `> ` until you reach one that doesn't.
  const lines = body.split('\n');
  while (lines.length && lines[0].startsWith('> ')) lines.shift();
  // Reply fallback has a blank line after it, so remove it to prevent leading newline
  if (lines[0] === '') lines.shift();
  return lines.join('\n');
}

// Part of Replies fallback support
function stripHTMLReply(html) {
  // Sanitize the original HTML for inclusion in <mx-reply>.  We allow
  // any HTML, since the original sender could use special tags that we
  // don't recognize, but want to pass along to any recipients who do
  // recognize them -- recipients should be sanitizing before displaying
  // anyways.  However, we sanitize to 1) remove any mx-reply, so that we
  // don't generate a nested mx-reply, and 2) make sure that the HTML is
  // properly formatted (e.g. tags are closed where necessary)
  return sanitizeHtml(
    html,
    {
      allowedTags: false, // false means allow everything
      allowedAttributes: false,
      // we somehow can't allow all schemes, so we allow all that we
      // know of and mxc (for img tags)
      allowedSchemes: [...PERMITTED_URL_SCHEMES, 'mxc'],
      exclusiveFilter: (frame) => frame.tag === "mx-reply",
    },
  );
}


/* turn a matrix event body into htm
 * Ripped from the Matrix React SDK: https://github.com/matrix-org/matrix-react-sdk/blob/c4f726932149373e9c4b6d3ef29b62e4ccc2dd78/src/HtmlUtils.tsx#L381
 *
 * content: 'content' of the MatrixEvent
 *
 * highlights: optional list of words to highlight, ordered by longest word first
 *
 * opts.highlightLink: optional href to add to highlighted words
 * opts.disableBigEmoji: optional argument to disable the big emoji class.
 * opts.stripReplyFallback: optional argument specifying the event is a reply and so fallback needs removing
 * opts.returnString: return an HTML string rather than JSX elements
 * opts.forComposerQuote: optional param to lessen the url rewriting done by sanitization, for quoting into composer
 * opts.ref: React ref to attach to any React components returned (not compatible with opts.returnString)
 */
export function bodyToHtml(content, opts) {
  const isHtmlMessage = content.format === "org.matrix.custom.html" && content.formatted_body;
  let bodyHasEmoji = false;

  let sanitizeParams = sanitizeHtmlParams;

  let strippedBody;
  let safeBody;
  let isDisplayedWithHtml;
  // XXX: We sanitize the HTML whilst also highlighting its text nodes, to avoid accidentally trying
  // to highlight HTML tags themselves.  However, this does mean that we don't highlight textnodes which
  // are interrupted by HTML tags (not that we did before) - e.g. foo<span/>bar won't get highlighted
  // by an attempt to search for 'foobar'.  Then again, the search query probably wouldn't work either
  try {
    let formattedBody = typeof content.formatted_body === 'string' ? content.formatted_body : null;
    const plainBody = typeof content.body === 'string' ? content.body : "";

    if (opts.stripReplyFallback && formattedBody) formattedBody = stripHTMLReply(formattedBody);
    strippedBody = opts.stripReplyFallback ? stripPlainReply(plainBody) : plainBody;

    bodyHasEmoji = mightContainEmoji(isHtmlMessage ? formattedBody : plainBody);

    // Only generate safeBody if the message was sent as org.matrix.custom.html
    if (isHtmlMessage) {
      isDisplayedWithHtml = true;
      safeBody = sanitizeHtml(formattedBody, sanitizeParams);
    }
  } finally {
    delete sanitizeParams.textFilter;
  }

  return isDisplayedWithHtml ? safeBody : strippedBody;
}
