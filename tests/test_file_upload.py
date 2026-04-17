"""tests/test_file_upload.py — unit tests for the FileUpload field and LocalFileBackend."""
import json
from pathlib import Path
import tempfile
import pytest

from nuru.forms.file_upload import FileUpload
from nuru.storage.local import LocalFileBackend


# ---------------------------------------------------------------------------
# FileUpload field – fluent API and getters
# ---------------------------------------------------------------------------

class TestFileUploadField:
    def test_defaults(self):
        f = FileUpload("avatar")
        assert f.get_key() == "avatar"
        assert f.get_field_type() == "file_upload"
        assert f.is_multiple() is False
        assert f.is_image_preview() is False
        assert f.get_accept_file_types() == []
        assert f.get_max_file_size() is None
        assert f.get_max_files() is None
        assert f.get_directory() == ""

    def test_fluent_chain(self):
        f = (
            FileUpload("doc")
            .label("Document")
            .required()
            .multiple()
            .max_files(5)
            .accept_file_types(["application/pdf"])
            .max_file_size(2 * 1024 * 1024)
            .directory("docs")
            .image()
            .image_crop_aspect_ratio("1:1")
            .image_resize(width=800, height=600, mode="contain")
            .can_download(True)
            .can_reorder(True)
        )
        assert f.get_label() == "Document"
        assert f.is_required() is True
        assert f.is_multiple() is True
        assert f.get_max_files() == 5
        assert f.get_accept_file_types() == ["application/pdf"]
        assert f.get_max_file_size() == 2 * 1024 * 1024
        assert f.get_directory() == "docs"
        assert f.is_image_preview() is True
        assert f.get_image_crop_aspect_ratio() == "1:1"
        assert f.get_image_resize_width() == 800
        assert f.get_image_resize_height() == 600
        assert f.get_image_resize_mode() == "contain"
        assert f.can_download_files() is True
        assert f.can_reorder_files() is True

    def test_parse_value_empty(self):
        f = FileUpload("x")
        assert f.parse_value(None) == []
        assert f.parse_value("") == []

    def test_parse_value_single_string(self):
        f = FileUpload("x")
        assert f.parse_value("avatars/abc.jpg") == ["avatars/abc.jpg"]

    def test_parse_value_json_list(self):
        f = FileUpload("x")
        raw = json.dumps(["a.pdf", "b.pdf"])
        assert f.parse_value(raw) == ["a.pdf", "b.pdf"]

    def test_serialize_value_single(self):
        f = FileUpload("x")
        assert f.serialize_value(["path/to/file.jpg"]) == "path/to/file.jpg"
        assert f.serialize_value([]) is None

    def test_serialize_value_multiple(self):
        f = FileUpload("x").multiple()
        result = f.serialize_value(["a.pdf", "b.pdf"])
        assert json.loads(result) == ["a.pdf", "b.pdf"]

    def test_filepond_config_keys(self):
        f = FileUpload("x").multiple().max_files(3).accept_file_types(["image/*"]).max_file_size(1024)
        cfg = f.filepond_config(upload_url="/admin/_upload")
        assert cfg["allowMultiple"] is True
        assert cfg["maxFiles"] == 3
        assert cfg["acceptedFileTypes"] == ["image/*"]
        assert cfg["maxFileSize"] == 1024
        assert "server" in cfg
        assert "process" in cfg["server"]
        assert "revert" in cfg["server"]


# ---------------------------------------------------------------------------
# LocalFileBackend
# ---------------------------------------------------------------------------

class TestLocalFileBackend:
    def setup_method(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.backend = LocalFileBackend(Path(self._tmpdir.name))

    def teardown_method(self):
        self._tmpdir.cleanup()

    def _make_file(self, content: bytes = b"hello"):
        class _Buf:
            def __init__(self, data):
                self._data = data
            def read(self):
                return self._data
        return _Buf(content)

    def test_save_returns_metadata(self):
        meta = self.backend.save(
            self._make_file(b"test data"),
            original_filename="test.txt",
        )
        assert "server_id" in meta
        assert meta["path"].exists()
        assert meta["size"] == 9
        assert meta["content_type"] == "text/plain"

    def test_save_with_directory(self):
        meta = self.backend.save(
            self._make_file(b"img"),
            original_filename="photo.jpg",
            directory="avatars",
        )
        assert meta["server_id"].startswith("avatars/")
        assert meta["path"].exists()

    def test_save_safe_name(self):
        meta = self.backend.save(
            self._make_file(b"x"),
            original_filename="../../etc/passwd",
        )
        # The filename must not be the original; it must be a uuid-based name
        assert ".." not in meta["filename"]
        assert meta["path"].exists()

    def test_delete_removes_file(self):
        meta = self.backend.save(self._make_file(b"x"), original_filename="a.txt")
        sid = meta["server_id"]
        assert self.backend.delete(sid) is True
        assert not meta["path"].exists()

    def test_delete_nonexistent_returns_false(self):
        assert self.backend.delete("nonexistent/file.txt") is False

    def test_delete_path_traversal_blocked(self):
        # Traversal attack: try to delete a file outside upload_dir
        assert self.backend.delete("../something.txt") is False

    def test_path_returns_absolute(self):
        meta = self.backend.save(self._make_file(b"x"), original_filename="b.txt")
        p = self.backend.path(meta["server_id"])
        assert p is not None
        assert p.is_absolute()

    def test_path_returns_none_for_missing(self):
        assert self.backend.path("no-such-file.txt") is None

    def test_path_traversal_blocked(self):
        assert self.backend.path("../secret.txt") is None

