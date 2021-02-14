import cgi
import hashlib
from io import BytesIO
import math
import re
import time
from urllib.parse import urljoin
import uuid

from bs4 import BeautifulSoup
from flask import current_app, jsonify
import gevent
from PIL import Image
import requests

from .config import config
from .misc import WHITESPACE, logger
from .storage import store_thumbnail, thumbnail_url
from .socketio import send_deferred_event


def create_thumbnail(fileid, store):
    from .storage import file_url
    create_thumbnail_external(file_url(fileid), store)


def create_thumbnail_external(link, store):
    """Try to create a thumbnail for an external link.  So as not to delay
    the response in the event the external server is slow, fetch from
    that server in a new gevent thread. Store should be a list of
    tuples consisting of database models, primary key names and
    primary key values.  When the thumbnail is successfully created,
    update the thumbnail fields of those records in the database, and emit
    socket server messages to anyone who might be waiting for that thumbnail.
    """
    if config.app.testing:
        create_thumbnail_async(link, store)
    else:
        gevent.spawn(create_thumbnail_async_appctx, current_app._get_current_object(),
                     link, store)


def create_thumbnail_async_appctx(app, link, store):
    with app.app_context():
        create_thumbnail_async(link, store)


def create_thumbnail_async(link, store):
    result = ''
    typ, dat = fetch_image_data(link)
    if dat is not None:
        if typ == 'image':
            img = Image.open(BytesIO(dat)).convert('RGB')
        else:  # favicon
            im = Image.open(BytesIO(dat))
            n_im = Image.new("RGBA", im.size, "WHITE")
            n_im.paste(im, (0, 0), im)
            img = n_im.convert("RGB")
        result = thumbnail_from_img(img)
    for model, field, value in store:
        model.update(thumbnail=result).where(getattr(model, field) == value).execute()
        token = '-'.join([model.__name__, str(value)])
        result_dict = {'target': token,
                       'thumbnail': thumbnail_url(result) if result else ''}
        send_deferred_event('thumbnail', token, result_dict)


def fetch_image_data(link):
    """ Try to fetch image data from a URL , and return it, or None. """
    # 1 - Check if it's an image
    try:
        resp, data = safe_request(link)
    except (requests.exceptions.RequestException, ValueError):
        return None, None
    ctype = resp.headers.get('content-type', '').split(";")[0].lower()
    if ctype in ['image/gif', 'image/jpeg', 'image/png']:
        # yay, it's an image!!1
        return 'image', data
    elif ctype == 'text/html':
        # Not an image!! Let's try with OpenGraph
        try:
            # Trim the HTML to the end of the last meta tag
            end_meta_tag = data.rfind(b'<meta')
            if end_meta_tag == -1:
                return None, None
            end_meta_tag = data.find(b'>', end_meta_tag)
            if end_meta_tag == -1:
                end_meta_tag = len(data)
            else:
                end_meta_tag += 1
            data = data[:end_meta_tag]
            logger.debug('Fetched header of %s: %s bytes', link, len(data))
            _, options = cgi.parse_header(resp.headers.get('Content-Type', ''))
            charset = options.get('charset', 'utf-8')
            start = time.time()
            og = BeautifulSoup(data, 'lxml', from_encoding=charset)
            logger.debug('Parsed HTML from %s in %s ms', link, int((time.time() - start) * 1000))
        except Exception as e:
            # If it errors here it's probably because lxml is not installed.
            logger.warning('Thumbnail fetch failed. Is lxml installed? Error: %s', e)
            return None, None
        try:
            img = urljoin(link, og('meta', {'property': 'og:image'})[0].get('content'))
            _, image = safe_request(img)
            return 'image', image
        except (OSError, ValueError, IndexError):
            # no image, try fetching just the favicon then
            try:
                img = urljoin(link, og('link', {'rel': 'icon'})[0].get('href'))
                _, icon = safe_request(img)
                return 'favicon', icon
            except (OSError, ValueError, IndexError):
                return None, None
    return None, None


THUMB_NAMESPACE = uuid.UUID('f674f09a-4dcf-4e4e-a0b2-79153e27e387')


def thumbnail_from_img(im):
    """Generate a thumbnail from an image in memory and write it to
    storage.  Return the filename."""
    thash = hashlib.blake2b(im.tobytes())
    im = generate_thumb(im)
    filename = store_thumbnail(im, str(uuid.uuid5(THUMB_NAMESPACE, thash.hexdigest())))
    im.close()
    return filename


def generate_thumb(im: Image) -> Image:
    x, y = im.size
    while y > x:
        slice_height = min(y - x, 10)
        bottom = im.crop((0, y - slice_height, x, y))
        top = im.crop((0, 0, x, slice_height))

        if _image_entropy(bottom) < _image_entropy(top):
            im = im.crop((0, 0, x, y - slice_height))
        else:
            im = im.crop((0, slice_height, x, y))

        x, y = im.size
        gevent.sleep(0)

    im.thumbnail((70, 70), Image.ANTIALIAS)
    return im


def _image_entropy(img):
    """calculate the entropy of an image"""
    hist = img.histogram()
    hist_size = sum(hist)
    hist = [float(h) / hist_size for h in hist]

    return -sum(p * math.log(p, 2) for p in hist if p != 0)


def grab_title(url):
    """Start the grab title process.  Returns a response with a token
    which can be used to get the actual title via socketio, once it has
    been fetched. """
    if config.app.testing:
        return jsonify(grab_title_async(current_app, url))
    else:
        token = 'title-' + str(uuid.uuid4())
        gevent.spawn(send_title_grab_async, current_app._get_current_object(),
                     url, token)
        return jsonify(status='deferred', token=token)


def send_title_grab_async(app, url, token):
    """Grab the title from the url and send it to whoever might be waiting
    via socketio. """
    result = grab_title_async(app, url)
    result.update(target=token)
    with app.app_context():
        send_deferred_event('grab_title', token, result)


def grab_title_async(app, url):
    with app.app_context():
        try:
            resp, data = safe_request(url, max_size=500000, mimetypes={'text/html'},
                                      partial_read=True)

            # Truncate the HTML so less parsing work will be required.
            end_title_pos = data.find(b'</title>')
            if end_title_pos == -1:
                raise ValueError
            data = data[:end_title_pos] + b'</title></head><body></body>'

            _, options = cgi.parse_header(resp.headers.get('Content-Type', ''))
            charset = options.get('charset', 'utf-8')
            og = BeautifulSoup(data, 'lxml', from_encoding=charset)
            title = og('title')[0].text
            title = title.strip(WHITESPACE)
            title = re.sub(' - YouTube$', '', title)
            return {'status': 'ok', 'title': title}
        except (requests.exceptions.RequestException, ValueError,
                OSError, IndexError, KeyError):
            return {'status': 'error'}


def safe_request(url, receive_timeout=10, max_size=25000000, mimetypes=None,
                 partial_read=False):
    """Gets stuff from the internet, with timeouts, content type and size
    restrictions.  If partial_read is True it will return approximately
    the first max_size bytes, otherwise it will raise an error if
    max_size is exceeded. """
    # Returns (Response, File)
    try:
        r = requests.get(url, stream=True, timeout=receive_timeout,
                         headers={'User-Agent': 'Throat/1 (Phuks)'})
    except:  # noqa
        raise ValueError('error fetching')
    r.raise_for_status()

    if int(r.headers.get('Content-Length', 1)) > max_size and not partial_read:
        raise ValueError('response too large')

    if mimetypes is not None:
        mtype, _ = cgi.parse_header(r.headers.get('Content-Type', ''))
        if mtype not in mimetypes:
            raise ValueError('wrong content type')

    size = 0
    start = time.time()
    f = b''
    for chunk in r.iter_content(1024):
        if time.time() - start > receive_timeout:
            raise ValueError('timeout reached')
        gevent.sleep(0)  # Otherwise this loop can block other greenlets for > 0.5s

        size += len(chunk)
        f += chunk
        if size > max_size:
            if partial_read:
                return r, f
            else:
                raise ValueError('response too large')
    return r, f
