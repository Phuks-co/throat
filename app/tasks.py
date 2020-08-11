import cgi
import hashlib
from io import BytesIO
import math
import re
import time
from urllib.parse import urljoin
import uuid

from bs4 import BeautifulSoup
from flask import current_app
import gevent
from PIL import Image
import requests

from .config import config
from .misc import WHITESPACE, logger
from .storage import store_thumbnail


def create_thumbnail(link, store):
    """Try to create a thumbnail for an external link.  So as not to delay
    the response in the event the external server is slow, fetch from
    that server in a new gevent thread. Store should be a list of
    tuples consisting of database models, primary key names and
    primary key values.  When the thumbnail is successfully created,
    update the thumbnail fields of those records in the database, and emit
    socket server messages to anyone who might be waiting for that thumbnail.
    """
    if config.app.testing:
        create_thumbnail_async(current_app, link, store)
    else:
        gevent.spawn(create_thumbnail_async, current_app._get_current_object(),
                     link, store)


def create_thumbnail_async(app, link, store):
    with app.app_context():
        result = ''
        typ, dat = fetch_image_data(link)
        current_app.logger.info("Fetched %s for thumbnail, %s bytes", typ, len(dat))
        if dat is not None:
            start = time.time()
            if typ == 'image':
                img = Image.open(BytesIO(dat)).convert('RGB')
            else: # favicon
                im = Image.open(BytesIO(dat))
                n_im = Image.new("RGBA", im.size, "WHITE")
                n_im.paste(im, (0, 0), im)
                img = n_im.convert("RGB")
            logger.info("Opening image")
            result = thumbnail_from_img(img)
        for model, field, value in store:
            model.update(thumbnail=result).where(getattr(model, field) == value).execute()
        # socket server messages based on model, id



def fetch_image_data(link):
    """ Try to fetch image data from a URL , and return it, or None. """
    # 1 - Check if it's an image
    try:
        req = safeRequest(link)
    except (requests.exceptions.RequestException, ValueError):
        return None, None
    ctype = req[0].headers.get('content-type', '').split(";")[0].lower()
    if ctype in ['image/gif', 'image/jpeg', 'image/png']:
        # yay, it's an image!!1
        return 'image', req[1]
    elif ctype == 'text/html':
        # Not an image!! Let's try with OpenGraph
        try:
            og = BeautifulSoup(req[1], 'lxml')
        except:
            # If it errors here it's probably because lxml is not installed.
            logger.warning('Thumbnail fetch failed. Is lxml installed?')
            return None, None
        try:
            img = urljoin(link, og('meta', {'property': 'og:image'})[0].get('content'))
            req = safeRequest(img)
            return 'image', req[1]
        except (OSError, ValueError, IndexError):
            # no image, try fetching just the favicon then
            try:
                img = urljoin(link, og('link', {'rel': 'icon'})[0].get('href'))
                req = safeRequest(img)
                return 'favicon', req[1]
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

    im.thumbnail((70, 70), Image.ANTIALIAS)
    return im


def _image_entropy(img):
    """calculate the entropy of an image"""
    hist = img.histogram()
    hist_size = sum(hist)
    hist = [float(h) / hist_size for h in hist]

    return -sum(p * math.log(p, 2) for p in hist if p != 0)


def safeRequest(url, receive_timeout=10, max_size=25000000, mimetypes=None,
                partial_read=False):
    """Gets stuff from the internet, with timeouts, content type and size
    restrictions.  If partial_read is True it will return approximately
    the first max_size bytes, otherwise it will raise an error if
    max_size is exceeded. """
    # Returns (Response, File)
    try:
        r = requests.get(url, stream=True, timeout=receive_timeout,
                         headers={'User-Agent': 'Throat/1 (Phuks)'})
    except:
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
