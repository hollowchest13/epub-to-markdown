import pytest

from core.utils import is_supported


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("f1.txt", False),
        ("f2.epub", True),
        ("f3.pdf", True),
        ("f4.md", True),
    ],
)
def test_is_supported(tmp_path, filename, expected):
    file_path = tmp_path / filename
    assert is_supported(file_path) == expected
