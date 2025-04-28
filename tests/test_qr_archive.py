import os
import pytest
from pathlib import Path
from xxhash import xxh64
import qr_archive
from tempfile import TemporaryDirectory


def test_main():
    """全体テスト：画像→QRコード化→QRコードから復元し、ハッシュ値を比較して正常に復元できているかのテスト"""
    expected_xxh64_hash = "c5d8fc25b775ca32"
    target_file = Path(os.path.dirname(__file__), "001.jpg")
    x = xxh64()
    header, chunks = qr_archive.split_file(target_file)
    with TemporaryDirectory() as td:
        qr_dir = Path(td, "qr")
        qr_archive.create_qr_codes(header, chunks, qr_dir)
        output_dir = Path(td, "output")
        qr_archive.restore_file(qr_dir, output_dir)
        with open(Path(output_dir, "001.jpg"), "rb") as f:
            x.update(f.read())
        hash = x.hexdigest()
        assert expected_xxh64_hash == hash
