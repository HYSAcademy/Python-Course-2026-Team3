import io
import zipfile
import tarfile
import pytest

from app.services.extractor import ExtractorFactory

def create_dummy_zip() -> io.BytesIO:
    """Creates an in-memory ZIP archive with 3 files (2 allowed, 1 disallowed)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('document.txt', b'Hello text')
        zf.writestr('data.json', b'{"key": "value"}')
        zf.writestr('image.png', b'fake image data')
    buf.seek(0)
    return buf

def create_dummy_tar() -> io.BytesIO:
    """Creates an in-memory TAR.GZ archive."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        files = [
            ('readme.html', b'<h1>Hello HTML</h1>'),
            ('virus.exe', b'malicious payload') 
        ]
        for name, content in files:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    buf.seek(0)
    return buf


def test_extractor_factory_returns_correct_instance():
    """Verify the factory returns the correct class for each extension."""
    zip_extractor = ExtractorFactory.get_extractor("test.zip")
    tar_extractor1 = ExtractorFactory.get_extractor("test.tar.gz")
    tar_extractor2 = ExtractorFactory.get_extractor("test.tgz")
    
    assert zip_extractor.__class__.__name__ == "ZipExtractor"
    assert tar_extractor1.__class__.__name__ == "TarExtractor"
    assert tar_extractor2.__class__.__name__ == "TarExtractor"

def test_extractor_factory_raises_error_for_invalid_extension():
    """Verify the factory fails on unknown format."""
    with pytest.raises(ValueError, match="Unsupported format for document.pdf"): 
        ExtractorFactory.get_extractor("document.pdf")



def test_zip_extractor_filters_and_reads_content():
    """Test ZIP extraction: ignores images, reads text."""
    dummy_zip = create_dummy_zip()
    extractor = ExtractorFactory.get_extractor("archive.zip")
    
    extracted_docs = list(extractor.extract(dummy_zip))
    
    assert len(extracted_docs) == 2
    filenames = [doc.original_filename for doc in extracted_docs]
    assert "document.txt" in filenames
    assert "data.json" in filenames
    assert "image.png" not in filenames
    txt_doc = next(doc for doc in extracted_docs if doc.original_filename == "document.txt")
    assert txt_doc.content == "Hello text"

def test_tar_extractor_filters_and_reads_content():
    """Test TAR.GZ extraction the same way."""
    dummy_tar = create_dummy_tar()
    extractor = ExtractorFactory.get_extractor("archive.tar.gz")
    
    extracted_docs = list(extractor.extract(dummy_tar))
    assert len(extracted_docs) == 1
    assert extracted_docs[0].original_filename == "readme.html"
    assert extracted_docs[0].content == "<h1>Hello HTML</h1>"