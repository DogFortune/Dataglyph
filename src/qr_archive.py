import qrcode
from qrcode.constants import ERROR_CORRECT_M
import cv2
import numpy as np
import os
import base64
import argparse
from pathlib import Path
from pyzbar.pyzbar import decode
from PIL import Image
from tqdm import tqdm


def split_file(file_path, chunk_size=800):
    """ファイルを指定サイズのチャンクに分割"""
    with open(file_path, "rb") as f:
        data = f.read()

    # ファイル名とサイズの情報を追加
    file_name = os.path.basename(file_path)
    header = f"{file_name}:{len(data)}:".encode()

    # チャンクに分割
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunk = data[i : i + chunk_size]
        chunks.append(chunk)

    return header, chunks


def create_qr_codes(header, chunks, output_dir):
    """チャンクをQRコードに変換して保存"""
    os.makedirs(output_dir, exist_ok=True)
    total_chunks = len(chunks)

    # ヘッダー情報を含む最初のQRコード
    header_encoded = base64.b64encode(header)
    header_qr = qrcode.make(header_encoded)
    header_qr.save(f"{output_dir}/header.png")

    # 各チャンクのQRコード
    for i, chunk in enumerate(tqdm(chunks, desc="create chunk qr code")):
        # チャンク番号と総数を追加
        chunk_header = f"{i+1}/{total_chunks}:".encode()
        chunk_data = chunk_header + base64.b64encode(chunk)

        # QRコード生成（エラー訂正レベルをHに設定）
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(chunk_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(f"{output_dir}/chunk_{i+1:04d}.png")

    print(f"作成されたQRコード: {total_chunks+1}個 (ヘッダー含む)")


def read_qr_code(image_path):
    """QRコードを読み取る"""
    img = cv2.imread(image_path)
    decoded = decode(img)
    if decoded:
        return decoded[0].data
    return None


def restore_file(qr_dir, output_dir):
    """QRコードからファイルを復元"""
    os.makedirs(output_dir, exist_ok=True)

    # ヘッダー情報の取得
    header_data = read_qr_code(f"{qr_dir}/header.png")
    if not header_data:
        print("ヘッダーQRコードを読み取れませんでした")
        return False

    header_decoded = base64.b64decode(header_data)
    file_name, file_size_str, _ = header_decoded.decode().split(":", 2)
    file_size = int(file_size_str)

    # チャンクQRコードの読み取り
    chunk_files = sorted([f for f in os.listdir(qr_dir) if f.startswith("chunk_")])
    chunks = []

    for chunk_file in tqdm(chunk_files, desc="restore"):
        chunk_data = read_qr_code(f"{qr_dir}/{chunk_file}")
        if not chunk_data:
            print(f"QRコード {chunk_file} を読み取れませんでした")
            continue

        # チャンク情報を解析
        chunk_parts = chunk_data.split(b":", 1)
        if len(chunk_parts) != 2:
            print(f"不正なチャンク形式: {chunk_file}")
            continue

        chunk_header, chunk_payload = chunk_parts
        chunks.append(base64.b64decode(chunk_payload))

    # チャンクを結合してファイルを復元
    restored_data = b"".join(chunks)
    if len(restored_data) != file_size:
        print(
            f"警告: 復元サイズが一致しません（期待: {file_size}, 実際: {len(restored_data)}）"
        )

    output_path = f"{output_dir}/{file_name}"
    with open(output_path, "wb") as f:
        f.write(restored_data)

    print(f"ファイルを復元しました: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="バイナリファイルをQRコードに変換または復元します"
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # 変換コマンド
    encode_parser = subparsers.add_parser("encode", help="ファイルをQRコードに変換")
    encode_parser.add_argument("file", help="変換するファイルパス")
    encode_parser.add_argument(
        "--output", "-o", default="qrcodes", help="出力ディレクトリ"
    )
    encode_parser.add_argument(
        "--chunk-size", "-c", type=int, default=1000, help="チャンクサイズ (バイト)"
    )

    # 復元コマンド
    decode_parser = subparsers.add_parser("decode", help="QRコードからファイルを復元")
    decode_parser.add_argument("qrdir", help="QRコードが保存されているディレクトリ")
    decode_parser.add_argument(
        "--output", "-o", default="restored", help="出力ディレクトリ"
    )

    args = parser.parse_args()

    if args.command == "encode":
        header, chunks = split_file(args.file, args.chunk_size)
        create_qr_codes(header, chunks, args.output)
    elif args.command == "decode":
        restore_file(args.qrdir, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
