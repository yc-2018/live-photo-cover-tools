#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a single-file Android/Google/Xiaomi style Live Photo / 实况照片 from a
cover image and an MP4 video.

The output is a JPEG file with Live Photo / 实况照片 XMP metadata. The JPEG still
image is stored first, and the original MP4 bytes are appended at the end.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None


XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


def fail(message: str) -> None:
    raise SystemExit(f"错误：{message}")


def read_file(path: Path, label: str) -> bytes:
    if not path.exists():
        fail(f"{label}不存在：{path}")
    return path.read_bytes()


def check_mp4(video_data: bytes) -> None:
    if len(video_data) < 16:
        fail("视频文件太小，不像有效 MP4。")
    if b"ftyp" not in video_data[:64]:
        fail("视频文件开头没有找到 MP4 ftyp 标记，请确认输入是 mp4/m4v 文件。")


def probe_duration_us(video_path: Path) -> str:
    """Return duration in microseconds if ffprobe exists, otherwise 0."""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return "0"

    if proc.returncode != 0:
        return "0"

    try:
        seconds = float(proc.stdout.strip())
    except ValueError:
        return "0"

    if seconds <= 0:
        return "0"

    return str(int(seconds * 1_000_000 / 2))


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
        fail("XMP 元数据太大，无法写进 JPEG APP1 段。")
    return b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload


def parse_size(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    normalized = value.lower().replace("×", "x")
    if "x" not in normalized:
        fail("--size 格式应为 宽x高，例如 3072x4096")
    left, right = normalized.split("x", 1)
    try:
        width = int(left.strip())
        height = int(right.strip())
    except ValueError:
        fail("--size 格式应为数字，例如 3072x4096")
    if width <= 0 or height <= 0:
        fail("--size 的宽高必须大于 0")
    return width, height


def make_cover_jpeg(
    cover_path: Path,
    *,
    size: tuple[int, int] | None,
    fit: str,
    quality: int,
) -> bytes:
    if Image is None or ImageOps is None:
        fail("缺少 Pillow。请先运行：python -m pip install pillow")

    with Image.open(cover_path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        target_size = size or img.size

        if target_size != img.size:
            if fit == "crop":
                img = ImageOps.fit(
                    img,
                    target_size,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
            elif fit == "contain":
                contained = ImageOps.contain(img, target_size, method=Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", target_size, (0, 0, 0))
                offset = ((target_size[0] - contained.width) // 2, (target_size[1] - contained.height) // 2)
                canvas.paste(contained, offset)
                img = canvas
            elif fit == "stretch":
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            else:
                fail(f"未知 fit 模式：{fit}")

        buf = BytesIO()
        img.save(buf, "JPEG", quality=max(1, min(quality, 100)), optimize=True)
        return buf.getvalue()


def create_live_photo(
    cover_path: Path,
    video_path: Path,
    output_path: Path,
    *,
    size: tuple[int, int] | None,
    fit: str,
    quality: int,
    presentation_timestamp_us: str | None,
) -> None:
    video_data = read_file(video_path, "视频")
    check_mp4(video_data)

    cover_jpeg = make_cover_jpeg(cover_path, size=size, fit=fit, quality=quality)
    if not cover_jpeg.startswith(b"\xff\xd8"):
        fail("生成的新封面不是 JPEG。")

    timestamp = presentation_timestamp_us
    if timestamp is None:
        timestamp = probe_duration_us(video_path)

    xmp_segment = build_xmp(len(video_data), timestamp)
    output_data = cover_jpeg[:2] + xmp_segment + cover_jpeg[2:] + video_data

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output_data)

    print("完成。")
    print(f"封面图：{cover_path}")
    print(f"视频：{video_path}")
    print(f"输出：{output_path}")
    print(f"封面 JPEG 长度：{len(cover_jpeg)} bytes")
    print(f"视频长度：{len(video_data)} bytes")
    print(f"视频起点：{len(output_data) - len(video_data)}")
    print(f"输出大小：{len(output_data)} bytes")
    print(f"PresentationTimestampUs：{timestamp}")


def default_output_path(cover_path: Path) -> Path:
    return cover_path.with_name(f"{cover_path.stem}-实况图.jpg")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把一张封面图和一个 MP4 合成为单文件 Live Photo / 实况照片 JPG。"
    )
    parser.add_argument("--cover", required=True, type=Path, help="封面图片，支持 jpg/png/webp 等 Pillow 可读格式")
    parser.add_argument("--video", required=True, type=Path, help="MP4 视频文件")
    parser.add_argument(
        "--output",
        type=Path,
        help="输出 Live Photo / 实况照片 JPG；不填则使用 封面名-实况图.jpg",
    )
    parser.add_argument("--size", help="输出封面尺寸，例如 3072x4096；不填则使用封面原尺寸")
    parser.add_argument(
        "--fit",
        choices=("crop", "contain", "stretch"),
        default="crop",
        help="指定 --size 后的适配方式：crop 裁切填满；contain 黑边完整显示；stretch 拉伸",
    )
    parser.add_argument("--quality", type=int, default=95, help="输出 JPEG 质量，1-100，默认 95")
    parser.add_argument(
        "--presentation-us",
        help="Live Photo / 实况照片展示时间戳，单位微秒；不填则尝试用 ffprobe 取视频中点，失败则写 0",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cover_path = args.cover.resolve()
    output_path = args.output.resolve() if args.output else default_output_path(cover_path)
    create_live_photo(
        cover_path,
        args.video.resolve(),
        output_path,
        size=parse_size(args.size),
        fit=args.fit,
        quality=args.quality,
        presentation_timestamp_us=args.presentation_us,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
