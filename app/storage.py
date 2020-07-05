""" Store and serve uploads and thumbnails. """
import tempfile
import uuid
import magic
from mutagen.mp4 import MP4
import gi
gi.require_version('GExiv2', '0.10')  # noqa
from gi.repository import GExiv2
import hashlib

from flask import request, url_for
from flask_babel import _
from flask_login import current_user
from flask_cloudy import Storage
from .config import config

FILE_NAMESPACE = uuid.UUID('acd2da84-91a2-4169-9fdb-054583b364c4')

storage = Storage()


def make_url(local_url, name):
    if config.storage.provider == 'LOCAL' and not config.storage.server:
        return local_url + name
    else:
        obj = storage.get(name)
        if obj is None:
            return url_for('static', filename='file-not-found.png')
        else:
            return obj.url


def file_url(name):
    return make_url(config.storage.uploads.url, name)


def thumbnail_url(name):
    return make_url(config.storage.thumbnails.url, name)


def clear_metadata(path: str, mime_type: str):
    if mime_type in ('image/jpeg', 'image/png'):
        exif = GExiv2.Metadata()
        exif.open_path(path)
        exif.clear()
        exif.save_file(path)
    elif mime_type == 'video/mp4':
        video = MP4(path)
        video.clear()
        video.save()
    elif mime_type == 'video/webm':
        # XXX: Mutagen doesn't seem to support webm files
        pass


def upload_file(max_size=16777216):
    if not current_user.canupload:
        return False, False

    if 'files' not in request.files:
        return False, False

    ufile = request.files.getlist('files')[0]
    if ufile.filename == '':
        return False, False

    mtype = magic.from_buffer(ufile.read(1024), mime=True)

    if mtype == 'image/jpeg':
        extension = '.jpg'
    elif mtype == 'image/png':
        extension = '.png'
    elif mtype == 'image/gif':
        extension = '.gif'
    elif mtype == 'video/mp4':
        extension = '.mp4'
    elif mtype == 'video/webm':
        extension = '.webm'
    else:
        return _("File type not allowed"), False
    ufile.seek(0)
    md5 = hashlib.md5()
    while True:
        data = ufile.read(65536)
        if not data:
            break
        md5.update(data)

    f_name = str(uuid.uuid5(FILE_NAMESPACE, md5.hexdigest())) + extension
    ufile.seek(0)
    fpath = os.path.join(config.storage.uploads.path, f_name)
    if not os.path.isfile(fpath):
        ufile.save(fpath)
        fsize = os.stat(fpath).st_size
        if fsize > max_size:  # Max file size exceeded
            os.remove(fpath)
            return _("File size exceeds the maximum allowed size (%(size)i MB)", size=max_size / 1024 / 1024), False
        # remove metadata
        clear_metadata(fpath, mtype)
    return f_name, True
