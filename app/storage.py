""" Store and serve uploads and thumbnails. """
import uuid
import pathlib

import gevent
import libcloud.storage.types
import magic
from PIL.Image import Exif
from mutagen.mp4 import MP4
from PIL import Image, TiffImagePlugin
from contextlib import ExitStack
import hashlib
import jinja2
from werkzeug.datastructures import FileStorage

from flask import current_app, request, url_for
from flask_babel import _
from flask_login import current_user
from flask_cloudy import Storage
from .config import config


class SizeLimitExceededError(Exception):
    """Exception raised for files larger than permitted by configuration."""

    pass


FILE_NAMESPACE = uuid.UUID("acd2da84-91a2-4169-9fdb-054583b364c4")

ISO8601 = "%Y-%m-%dT%H:%M:%SZ"


class Objectview(object):
    def __init__(self, d):
        self.__dict__ = d


class S3Storage:
    def __init__(self):
        self.s3 = None
        self.app = None
        self.container = None

    def init_app(self, app):
        self.app = app
        config = app.config["THROAT_CONFIG"]
        self.container = config.storage.container
        import boto3

        if "key" in config.storage.keys():
            # Region? For the moment I'm just going to assume that a key has been set that will get the region right,
            # the libcloud region set is going to be a pain to deal with, and eventually incomplete.
            session = boto3.Session(
                aws_access_key_id=config.storage.key,
                aws_secret_access_key=config.storage.secret,
            )
            self.s3 = session.client("s3", endpoint_url=config.storage.endpoint_url)
        else:
            self.s3 = boto3.client("s3")

    def get(self, filename):
        # Using head here because we never use the object directly
        try:
            head = self.s3.head_object(Bucket=self.container, Key=filename)
            return Objectview({"size": head["ContentLength"], "name": filename})
            # FIXME: broad except
        except:  # noqa
            return None

    def delete(self, filename):
        self.s3.delete_object(Bucket=self.container, Key=filename)

    def upload(self, fileobj, name=None, prefix=None, **kwargs):
        if "acl" in kwargs:
            kwargs["ACL"] = kwargs["acl"]
            del kwargs["acl"]
        if "content_type" in kwargs:
            kwargs["ContentType"] = kwargs["content_type"]
            del kwargs["content_type"]
        file_key = name
        if prefix:
            file_key = prefix.lstrip("/") + name
        self.s3.upload_fileobj(
            fileobj, Bucket=self.container, Key=file_key, ExtraArgs=kwargs
        )
        return Objectview({"name": name})


storage = None  # type: Storage


def storage_init_app(app):
    global storage
    if "S3" in app.config["THROAT_CONFIG"].storage.provider:
        storage = S3Storage()
    else:
        storage = Storage()
    # XXX: flask-cloudy has a tendency to mercilessly delete the container when it doesn't have anything inside of it
    # so, to prevent errors we attempt to re-create it at startup and when uploading files.
    # We don't do this in the thumbnails container because we never delete anything from there (for now)
    if app.config["THROAT_CONFIG"].storage.provider == "LOCAL":
        pathlib.Path(app.config["THROAT_CONFIG"].storage.uploads.path).mkdir(
            exist_ok=True
        )
    storage.init_app(app)


def make_url(storage, cfg, name):
    if name is None or name == "":
        return url_for("static", filename="img/1x1.gif")
    if config.storage.provider == "LOCAL" and config.storage.server:
        obj = storage.get(name)
        if obj is None:
            return url_for("static", filename="img/1x1.gif")
        elif "server_name" in config.site and config.storage.server:
            return f"http://{config.site.server_name}{config.storage.server_url}/{name}"
        else:
            return obj.url
    else:
        return cfg.url + name


def file_url(name):
    return make_url(storage, config.storage.uploads, name)


def thumbnail_url(name):
    with ExitStack() as stack:
        stg = storage
        if (
            config.storage.provider == "LOCAL"
            and config.storage.thumbnails.path != config.storage.uploads.path
        ):
            stg = stack.enter_context(storage.use(config.storage.thumbnails.path))
        return make_url(stg, config.storage.thumbnails, name)


def clear_metadata(fileobj: FileStorage, mime_type: str):
    resultIO = FileStorage()
    fileobj.seek(0)
    if mime_type in ("image/jpeg", "image/png"):
        image = Image.open(fileobj)
        if not image.info.get("exif"):
            return fileobj
        exifdata = Exif()
        exifdata.load(image.info["exif"])
        # XXX: We want to remove all EXIF data except orientation (tag 274) or people will start seeing
        # rotated images...
        # Also, Pillow can't encode EXIF data, so we have to do it manually
        if exifdata.endian == "<":
            head = b"II\x2A\x00\x08\x00\x00\x00"
        else:
            head = b"MM\x00\x2A\x00\x00\x00\x08"
        ifd = TiffImagePlugin.ImageFileDirectory_v2(ifh=head)
        for tag, value in exifdata.items():
            if tag == 274:
                ifd[tag] = value
        newExif = b"Exif\x00\x00" + head + ifd.tobytes(8)
        image.save(
            resultIO, format=Image.EXTENSION[EXTENSIONS[mime_type]], exif=newExif
        )
        return resultIO
    elif mime_type == "video/mp4":
        video = MP4(fileobj)
        video.clear()
        video.save(resultIO)
        return resultIO
    elif mime_type == "video/webm":
        # XXX: Mutagen doesn't seem to support webm files
        return fileobj
    else:
        # In the case that we don't know how to clean up the file, just return it.
        return fileobj


def upload_file():
    if not current_user.canupload:
        return False, False

    if "files" not in request.files:
        return False, False

    ufile = request.files.getlist("files")[0]
    if ufile.filename == "":
        return False, False

    mtype = mtype_from_file(ufile, allow_video_formats=config.site.allow_video_uploads)
    if mtype is None:
        return _("File type not allowed"), False

    try:
        fhash = calculate_file_hash(ufile, size_limit=config.site.upload_max_size)
    except SizeLimitExceededError:
        return (
            _(
                "File size exceeds the maximum allowed size (%(size)s)",
                size=human_readable(config.site.upload_max_size),
            ),
            False,
        )

    basename = str(uuid.uuid5(FILE_NAMESPACE, fhash))

    return store_file(ufile, basename, mtype, remove_metadata=True), True


EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/svg": ".svg",
}

VIDEO_EXTENSIONS = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}
allowed_extensions = [ext[1:] for ext in EXTENSIONS.values()]
allowed_extensions += [ext[1:] for ext in VIDEO_EXTENSIONS.values()]


def store_file(ufile, basename, mtype, remove_metadata=False):
    """Store a file. Setting remove_metadata will remove image format
    metadata before storing.
    """
    _extensions = dict(EXTENSIONS)
    _extensions.update(VIDEO_EXTENSIONS)
    filename = basename + _extensions[mtype]
    try:
        if storage.get(filename) is not None:
            current_app.logger.debug("Found in stored files: %s", filename)
            return filename
    except libcloud.storage.types.ContainerDoesNotExistError:
        pathlib.Path(config.storage.uploads.path).mkdir(exist_ok=True)

    if remove_metadata:
        ufile = clear_metadata(ufile, mtype)
    ufile.seek(0)
    ufile.filename = filename
    current_app.logger.debug("Adding %s to stored files", filename)
    return storage.upload(
        ufile,
        prefix=config.storage.uploads.filename_prefix,
        name=filename,
        acl=config.storage.acl,
        content_type=mtype,
    ).name


def get_stored_file_size(filename):
    obj = storage.get(filename)

    if obj is not None:
        return obj.size
    else:
        # Missing objects don't take up space.
        return 0


def remove_file(filename):
    current_app.logger.debug("Removing %s from stored files", filename)
    if isinstance(storage, S3Storage):
        storage.delete(filename)
    else:
        obj = storage.get(filename)
        obj.delete()


def store_thumbnail(im, basename):
    """Store a thumbnail image."""

    def find_existing_or_store_new(storage, im, filename):
        obj = storage.get(filename)
        if obj is not None:
            current_app.logger.debug("Found in stored thumbnails: %s", filename)
            return obj.name
        else:
            tempIO = FileStorage(filename=filename)
            im.save(tempIO, "JPEG", optimize=True, quality=85)
            tempIO.seek(0)
            current_app.logger.debug("Adding %s to stored thumbnails", filename)
            return storage.upload(
                tempIO,
                name=filename,
                prefix=config.storage.thumbnails.filename_prefix,
                acl=config.storage.acl,
                content_type="image/jpeg",
            ).name

    filename = basename + ".jpg"
    with ExitStack() as stack:
        stg = storage
        if (
            config.storage.provider == "LOCAL"
            and config.storage.thumbnails.path != config.storage.uploads.path
        ):
            stg = stack.enter_context(storage.use(config.storage.thumbnails.path))
        return find_existing_or_store_new(stg, im, filename)


def mtype_from_file(ufile, allow_video_formats=True):
    """Determine the file type from a file storage object and return the
    MIME type, or None if the file type is not recognized.
    """
    ufile.seek(0)
    mtype = magic.from_buffer(ufile.read(1024), mime=True)
    if mtype in EXTENSIONS or (allow_video_formats and mtype in VIDEO_EXTENSIONS):
        return mtype
    return None


def calculate_file_hash(ufile, size_limit=None):
    """Read all data from a file and calculate the MD5 hash of the result.
    If a size limit is given, stop reading and raise an error if it is
    exceeded.
    """
    ufile.seek(0)
    size = 0
    fhash = hashlib.blake2b()
    while True:
        data = ufile.read(65536)
        if not data:
            break
        size += len(data)
        if size_limit is not None and size > size_limit:
            raise SizeLimitExceededError
        fhash.update(data)
        gevent.sleep(0)
    return fhash.hexdigest()


def human_readable(fbytes):
    return jinja2.Template("{{ bytes|filesizeformat }}").render(bytes=fbytes)
