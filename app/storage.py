""" Store and serve uploads and thumbnails. """
import os
import tempfile
import uuid
import magic
from mutagen.mp4 import MP4
import gi
gi.require_version('GExiv2', '0.10')  # noqa
from gi.repository import GExiv2
import hashlib
import jinja2

from flask import request, url_for
from flask_babel import _
from flask_login import current_user
from flask_cloudy import Storage
from .config import config

class SizeLimitExceededError(Exception):
    """Exception raised for files larger than permitted by configuration."""
    pass

FILE_NAMESPACE = uuid.UUID('acd2da84-91a2-4169-9fdb-054583b364c4')

storage = Storage()


def make_url(storage, cfg, name):
    if name is None or name is '':
        return url_for('static', filename='file-not-found.png')
    if config.storage.provider == 'LOCAL' and not config.storage.server:
        return cfg.url + name
    else:
        obj = storage.get(name)
        if obj is None:
            return url_for('static', filename='file-not-found.png')
        else:
            return obj.url


def file_url(name):
    return make_url(storage, config.storage.uploads, name)


def thumbnail_url(name):
    if config.storage.thumbnails.path == config.storage.uploads.path:
        return make_url(storage, config.storage.thumbnails, name)
    else:
        with storage.use(config.storage.thumbnails.path) as thumbnail_storage:
            return make_url(thumbnail_storage, config.storage.thumbnails, name)


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


def upload_file():
    if not current_user.canupload:
        return False, False

    if 'files' not in request.files:
        return False, False

    ufile = request.files.getlist('files')[0]
    if ufile.filename == '':
        return False, False

    mtype = mtype_from_file(ufile, allow_video_formats=config.site.allow_video_uploads)
    if mtype is None:
        return _("File type not allowed"), False

    try:
        hash = calculate_file_md5(ufile, size_limit=config.site.upload_max_size)
    except SizeLimitExceededError:
        return _("File size exceeds the maximum allowed size (%(size)s)",
                 size=human_readable(config.site.upload_max_size)), False

    basename = str(uuid.uuid5(FILE_NAMESPACE, hash))

    return store_file(ufile, basename, mtype, remove_metadata=True), True


EXTENSIONS = {'image/jpeg': '.jpg',
              'image/png': '.png',
              'image/gif': '.gif',
              'video/mp4': '.mp4',
              'video/webm': '.webm'}
allowed_extensions = [ext[1:] for ext in EXTENSIONS.values()]


def store_file(ufile, basename, mtype, remove_metadata=False):
    """Store a file. Setting remove_metadata will remove image format
    metadata before storing.
    """
    filename = basename + EXTENSIONS[mtype]
    if storage.get(filename) is None:
        ufile.seek(0)
        with tempfile.TemporaryDirectory() as tempdir:
            fullpath = os.path.join(tempdir, filename)
            ufile.save(fullpath)
            clear_metadata(fullpath, mtype)

            # TODO probably there are errors that need handling
            return storage.upload(fullpath, name=filename, acl=config.storage.acl).name
    return filename


def get_stored_file_size(filename):
    obj = storage.get(filename)
    if obj is not None:
        return obj.size
    else:
        # Missing objects don't take up space.
        return 0


def remove_file(filename):
    storage.delete(filename)


def store_thumbnail(im, basename):
    """Store a thumbnail image."""
    def find_existing_or_store_new(storage, im, filename):
        obj = storage.get(filename)
        if obj is not None:
            return obj.name
        else:
            with tempfile.TemporaryDirectory() as tempdir:
                fullpath = os.path.join(tempdir, filename)
                im.save(fullpath, "JPEG", optimize=True, quality=85)
                return storage.upload(fullpath, name=filename,
                                      acl=config.storage.acl).name

    filename = basename + '.jpg'
    if config.storage.thumbnails.path == config.storage.uploads.path:
        return find_existing_or_store_new(storage, im, filename)
    else:
        with storage.use(config.storage.thumbnails.path) as thumbnail_storage:
            return find_existing_or_store_new(thumbnail_storage, im, filename)


def mtype_from_file(ufile, allow_video_formats=True):
    """ Determine the file type from a file storage object and return the
    MIME type, or None if the file type is not recognized.
    """
    ufile.seek(0)
    mtype = magic.from_buffer(ufile.read(1024), mime=True)
    if mtype in EXTENSIONS:
        return mtype
    return None


def calculate_file_md5(ufile, size_limit=None):
    """Read all data from a file and calculate the MD5 hash of the result.
    If a size limit is given, stop reading and raise an error if it is
    exceeded.
    """
    ufile.seek(0)
    size = 0
    md5 = hashlib.md5()
    while True:
        data = ufile.read(65536)
        if not data:
            break
        size += len(data)
        if size_limit is not None and size > size_limit:
            raise SizeLimitExceededError
        md5.update(data)
    return md5.hexdigest()


def human_readable(bytes):
    return jinja2.Template('{{ bytes|filesizeformat }}').render(bytes=bytes)
