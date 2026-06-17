#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replace the still cover of a single-file Android/Xiaomi/Google Live Photo / 实况照片.

This script is for files like MVIMG_*.jpg where the primary JPEG is followed by
an embedded MP4 video segment. It creates a new JPEG cover, writes Live Photo / 实况照片
XMP metadata, and appends the original MP4 segment unchanged.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


@dataclass(frozen=True)
class MotionInfo:
    video_start: int
    video_length: int
    presentation_timestamp_us: str
    original_size: tuple[int, int]
    exif_segment: bytes


def fail(message: str) -> None:
    raise SystemExit(f"错误：{message}")


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        fail(f"文件不存在：{path}")


def jpeg_size(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\xff\xd8"):
        fail("输入文件不是 JPEG，缺少 SOI 标记。")

    pos = 2
    while pos < len(data) - 8:
        if data[pos] != 0xFF:
            pos += 1
            continue

        while pos < len(data) and data[pos] == 0xFF:
            pos += 1

        marker = data[pos]
        pos += 1

        if marker == 0xDA:
            break
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue

        seg_len = int.from_bytes(data[pos : pos + 2], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            height = int.from_bytes(data[pos + 3 : pos + 5], "big")
            width = int.from_bytes(data[pos + 5 : pos + 7], "big")
            return width, height

        pos += seg_len

    fail("没有从 JPEG 头部读到图片尺寸。")


def extract_app1_exif(data: bytes) -> bytes:
    pos = 2
    while pos < len(data) - 4:
        if data[pos] != 0xFF:
            break

        while pos < len(data) and data[pos] == 0xFF:
            pos += 1

        marker_pos = pos - 1
        marker = data[pos]
        pos += 1

        if marker == 0xDA:
            break
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue

        seg_len = int.from_bytes(data[pos : pos + 2], "big")
        segment = data[marker_pos : pos + seg_len]
        payload = data[pos + 2 : pos + seg_len]

        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            return segment

        pos += seg_len

    return b""


def find_motion_info(data: bytes) -> MotionInfo:
    head = data[:200_000].decode("utf-8", "replace")

    # Modern Live Photo / 实况照片 files usually store the MP4 length in the XMP
    # Container directory. The video itself is the last N bytes of the file.
    length_match = re.search(
        r'Item:Semantic="MotionPhoto"\s+Item:Length="(\d+)"', head
    )
    if not length_match:
        length_match = re.search(r'Item:Length="(\d+)"\s+Item:Padding="0"', head)
    if not length_match:
        fail("没有找到 Live Photo / 实况照片的视频长度元数据 Item:Length，无法安全定位内嵌视频。")

    video_length = int(length_match.group(1))
    if video_length <= 0 or video_length >= len(data):
        fail(f"读取到的视频长度异常：{video_length}")

    video_start = len(data) - video_length
    video_head = data[video_start : video_start + 64]
    if b"ftyp" not in video_head:
        fail(
            "按 XMP 长度定位到的尾部数据不像 MP4。"
            f" video_start={video_start}, video_length={video_length}"
        )

    timestamp_match = re.search(
        r'GCamera:MotionPhotoPresentationTimestampUs="([0-9-]+)"', head
    )
    timestamp = timestamp_match.group(1) if timestamp_match else "0"

    return MotionInfo(
        video_start=video_start,
        video_length=video_length,
        presentation_timestamp_us=timestamp,
        original_size=jpeg_size(data),
        exif_segment=extract_app1_exif(data),
    )


def build_xmp(video_length: int, presentation_timestamp_us: str) -> bytes:
    xmp = f'''<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
      xmlns:GCamera="http://ns.google.com/photos/1.0/camera/"
      xmlns:Container="http://ns.google.com/photos/1.0/container/"
      xmlns:Item="http://ns.google.com/photos/1.0/container/item/"
      GCamera:MotionPhoto="1"
      GCamera:MotionPhotoVersion="1"
      GCamera:MotionPhotoPresentationTimestampUs="{presentation_timestamp_us}">
      <Container:Directory>
        <rdf:Seq>
          <rdf:li rdf:parseType="Resource">
            <Container:Item Item:Mime="image/jpeg" Item:Semantic="Primary"/>
          </rdf:li>
          <rdf:li rdf:parseType="Resource">
            <Container:Item Item:Mime="video/mp4" Item:Semantic="MotionPhoto" Item:Length="{video_length}" Item:Padding="0"/>
          </rdf:li>
        </rdf:Seq>
      </Container:Directory>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''.encode("utf-8")

    payload = XMP_HEADER + xmp
    if len(payload) + 2 > 65535:
        fail("XMP 元数据太大，不能写入单个 JPEG APP1 段。")

    return b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload


def make_cover_jpeg(cover: Path, size: tuple[int, int], fit: str, quality: int) -> bytes:
    if Image is None or ImageOps is None:
        fail("缺少 Pillow。请先运行：python -m pip install pillow")

    with Image.open(cover) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")

        if fit == "crop":
            img = ImageOps.fit(
                img,
                size,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        elif fit == "contain":
            contained = ImageOps.contain(img, size, method=Image.Resampling.LANCZOS)
            img = Image.new("RGB", size, (0, 0, 0))
            offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
            img.paste(contained, offset)
        elif fit == "stretch":
            img = img.resize(size, Image.Resampling.LANCZOS)
        else:
            fail(f"未知 fit 模式：{fit}")

        from io import BytesIO

        buf = BytesIO()
        img.save(buf, "JPEG", quality=max(1, min(quality, 100)), optimize=True)
        return buf.getvalue()


def combine_live_photo(
    original_data: bytes,
    cover_jpeg: bytes,
    info: MotionInfo,
) -> bytes:
    if not cover_jpeg.startswith(b"\xff\xd8"):
        fail("生成的新封面不是 JPEG。")

    xmp_segment = build_xmp(info.video_length, info.presentation_timestamp_us)
    video = original_data[info.video_start :]
    return cover_jpeg[:2] + info.exif_segment + xmp_segment + cover_jpeg[2:] + video


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_cover_replaced{input_path.suffix}")


def backup_path(input_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return input_path.with_name(f"{input_path.stem}.backup_{stamp}{input_path.suffix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="替换 Android/小米/Google 单文件 Live Photo / 实况照片 MVIMG JPG 的静态封面。"
    )
    parser.add_argument("--input", required=True, type=Path, help="原 Live Photo / 实况照片 JPG，例如 MVIMG_*.jpg")
    parser.add_argument("--cover", required=True, type=Path, help="要换进去的新封面图片")
    parser.add_argument("--output", type=Path, help="输出文件路径；不填则生成 *_cover_replaced.jpg")
    parser.add_argument(
        "--fit",
        choices=("crop", "contain", "stretch"),
        default="crop",
        help="封面适配方式：crop 裁切填满；contain 黑边完整显示；stretch 拉伸",
    )
    parser.add_argument("--quality", type=int, default=95, help="输出 JPEG 质量，1-100，默认 95")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="直接替换原文件。会先在同目录创建 backup_时间戳 备份。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.resolve()
    cover_path = args.cover.resolve()

    original_data = read_bytes(input_path)
    if not cover_path.exists():
        fail(f"新封面不存在：{cover_path}")

    info = find_motion_info(original_data)
    cover_jpeg = make_cover_jpeg(cover_path, info.original_size, args.fit, args.quality)
    combined = combine_live_photo(original_data, cover_jpeg, info)

    if args.replace:
        backup = backup_path(input_path)
        shutil.copy2(input_path, backup)
        output_path = input_path
    else:
        output_path = args.output.resolve() if args.output else default_output_path(input_path)
        backup = None

    output_path.write_bytes(combined)

    print("完成。")
    print(f"输入文件：{input_path}")
    print(f"新封面：{cover_path}")
    print(f"输出文件：{output_path}")
    if backup:
        print(f"原图备份：{backup}")
    print(f"原图尺寸：{info.original_size[0]}x{info.original_size[1]}")
    print(f"视频段长度：{info.video_length} bytes")
    print(f"视频段新位置：{len(combined) - info.video_length}")
    print(f"输出大小：{len(combined)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
