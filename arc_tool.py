#!/usr/bin/env python3
"""
Grim Dawn .arc 归档工具 — 纯 Python 实现，跨平台，无外部依赖。

用法:
    python arc_tool.py pack     <output.arc> <input_dir> [--level N] [--algo lz4|zlib]
    python arc_tool.py unpack   <input.arc>  <output_dir>
    python arc_tool.py database <input.arc>  <output_dir> [file]
    python arc_tool.py list     <input.arc>
    python arc_tool.py info     <input.arc>

默认使用 LZ4 压缩（与 ArchiveTool.exe 兼容）。
解压时自动检测压缩算法（LZ4/zlib），兼容所有 .arc 文件。
"""

from __future__ import annotations

import os
import struct
import sys
import time
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ARC_MAGIC = b"ARC\x00"
ARC_VERSION = 3
HEADER_SIZE = 28
RESERVED_SIZE = 0x800
RECORD_ENTRY_SIZE = 12
TOC_ENTRY_SIZE = 44
MAX_BLOCK_SIZE = 256 * 1024  # 256KB

EPOCH_DIFF = 116444736000000000

# 压缩算法标识
ALGO_LZ4 = "lz4"
ALGO_ZLIB = "zlib"

# ---------------------------------------------------------------------------
# 原生 LZ4 库（通过 ctypes 调用，速度快）
# ---------------------------------------------------------------------------

_lz4_lib = None

def _get_lz4_lib():
    """尝试加载原生 LZ4 库。"""
    global _lz4_lib
    if _lz4_lib is not None:
        return _lz4_lib

    import ctypes
    import ctypes.util

    # 尝试不同的库名
    for name in ['lz4', 'liblz4']:
        path = ctypes.util.find_library(name)
        if path:
            try:
                _lz4_lib = ctypes.CDLL(path)
                # 验证函数存在
                _lz4_lib.LZ4_compressBound
                _lz4_lib.LZ4_compress_default
                _lz4_lib.LZ4_decompress_safe
                return _lz4_lib
            except (OSError, AttributeError):
                continue

    # macOS Homebrew 路径
    for path in ['/opt/homebrew/lib/liblz4.dylib', '/usr/local/lib/liblz4.dylib']:
        try:
            _lz4_lib = ctypes.CDLL(path)
            _lz4_lib.LZ4_compressBound
            _lz4_lib.LZ4_compress_default
            _lz4_lib.LZ4_decompress_safe
            return _lz4_lib
        except OSError:
            continue

    return None


def lz4_compress_native(src: bytes) -> bytes:
    """使用原生 LZ4 库压缩。"""
    import ctypes

    lib = _get_lz4_lib()
    if lib is None:
        raise ImportError("LZ4 库不可用")

    src_len = len(src)
    max_size = lib.LZ4_compressBound(src_len)
    dst = ctypes.create_string_buffer(max_size)

    compressed_size = lib.LZ4_compress_default(
        src, dst, src_len, max_size
    )

    if compressed_size <= 0:
        raise RuntimeError("LZ4 压缩失败")

    return dst.raw[:compressed_size]


def lz4_decompress_native(src: bytes, uncompressed_size: int) -> bytes:
    """使用原生 LZ4 库解压。"""
    import ctypes

    lib = _get_lz4_lib()
    if lib is None:
        raise ImportError("LZ4 库不可用")

    dst = ctypes.create_string_buffer(uncompressed_size)

    result = lib.LZ4_decompress_safe(
        src, dst, len(src), uncompressed_size
    )

    if result <= 0:
        raise RuntimeError("LZ4 解压失败")

    return dst.raw[:result]


def has_native_lz4() -> bool:
    """检查是否有原生 LZ4 库。"""
    return _get_lz4_lib() is not None


# ---------------------------------------------------------------------------
# Pure Python LZ4 Block 解压实现
# ---------------------------------------------------------------------------

def lz4_decompress(src: bytes, uncompressed_size: int) -> bytes:
    """LZ4 block 格式解压（纯 Python 实现）。"""
    dst = bytearray(uncompressed_size)
    si = 0  # source index
    di = 0  # destination index
    src_len = len(src)

    while si < src_len:
        # 读取 token
        token = src[si]
        si += 1

        # 字面量长度
        literal_length = (token >> 4) & 0x0F
        if literal_length == 15:
            while si < src_len:
                extra = src[si]
                si += 1
                literal_length += extra
                if extra != 255:
                    break

        # 复制字面量
        dst[di:di + literal_length] = src[si:si + literal_length]
        si += literal_length
        di += literal_length

        if si >= src_len:
            break

        # 读取匹配偏移（2 字节小端）
        if si + 2 > src_len:
            break
        match_offset = src[si] | (src[si + 1] << 8)
        si += 2

        if match_offset == 0:
            break

        # 匹配长度
        match_length = (token & 0x0F) + 4  # minimum match is 4
        if (token & 0x0F) == 15:
            while si < src_len:
                extra = src[si]
                si += 1
                match_length += extra
                if extra != 255:
                    break

        # 复制匹配（可以重叠）
        match_pos = di - match_offset
        for _ in range(match_length):
            dst[di] = dst[match_pos]
            di += 1
            match_pos += 1

    return bytes(dst[:di])


# ---------------------------------------------------------------------------
# LZ4 压压实现（简化版，使用 zlib 作为后备）
# ---------------------------------------------------------------------------

def lz4_compress_bound(source_size: int) -> int:
    """计算 LZ4 压缩后最大可能大小。"""
    return source_size + (source_size // 255) + 16


def lz4_compress_block(src: bytes) -> bytes:
    """LZ4 block 格式压缩（纯 Python 实现）。

    正确实现 LZ4 压缩，兼容 ArchiveTool.exe。
    """
    src_len = len(src)
    dst = bytearray()
    si = 0
    anchor = 0  # 上一个序列的结束位置

    while si < src_len:
        # 在历史数据中查找匹配
        best_offset = 0
        best_length = 0

        # 搜索窗口（最大 64KB）
        search_start = max(0, si - 65535)
        for candidate in range(search_start, si):
            # 计算匹配长度
            length = 0
            while (si + length < src_len and
                   src[candidate + length] == src[si + length]):
                length += 1
                if si + length >= src_len:
                    break

            if length >= 4 and length > best_length:
                best_length = length
                best_offset = si - candidate

        if best_length >= 4:
            # 输出字面量 + 匹配
            literal_length = si - anchor

            # Token
            token_lit = min(literal_length, 15)
            token_mat = min(best_length - 4, 15)
            token = (token_lit << 4) | token_mat
            dst.append(token)

            # 字面量长度扩展
            if literal_length >= 15:
                remaining = literal_length - 15
                while remaining >= 255:
                    dst.append(255)
                    remaining -= 255
                dst.append(remaining)

            # 字面量数据
            dst.extend(src[anchor:anchor + literal_length])

            # 匹配偏移（2 字节小端）
            dst.extend(struct.pack("<H", best_offset))

            # 匹配长度扩展
            if best_length - 4 >= 15:
                remaining = best_length - 4 - 15
                while remaining >= 255:
                    dst.append(255)
                    remaining -= 255
                dst.append(remaining)

            si += best_length
            anchor = si
        else:
            si += 1

    # 输出最后的字面量
    if anchor < src_len:
        literal_length = src_len - anchor
        token = min(literal_length, 15) << 4
        dst.append(token)
        if literal_length >= 15:
            remaining = literal_length - 15
            while remaining >= 255:
                dst.append(255)
                remaining -= 255
            dst.append(remaining)
        dst.extend(src[anchor:src_len])

    return bytes(dst)


# ---------------------------------------------------------------------------
# 压缩/解压统一接口
# ---------------------------------------------------------------------------

def compress_data(data: bytes, algo: str = ALGO_LZ4, level: int = 6) -> tuple[bytes, str]:
    """压缩数据，返回 (compressed_data, algo_used)。"""
    if algo == ALGO_LZ4:
        # 优先使用原生 LZ4 库
        try:
            compressed = lz4_compress_native(data)
            # LZ4 模式下始终返回压缩数据（即使略大）
            return compressed, ALGO_LZ4
        except (ImportError, RuntimeError):
            pass

        # 尝试 lz4 Python 包
        try:
            import lz4.block
            compressed = lz4.block.compress(data, mode='default', store_size=False)
            return compressed, ALGO_LZ4
        except ImportError:
            pass

        # 使用纯 Python LZ4 实现
        compressed = lz4_compress_block(data)
        return compressed, ALGO_LZ4
    else:
        compressed = zlib.compress(data, level=level, wbits=-15)
        if len(compressed) < len(data):
            return compressed, ALGO_ZLIB
        return data, ALGO_ZLIB


def decompress_data(data: bytes, uncompressed_size: int, algo_hint: str = "auto") -> bytes:
    """解压数据，自动检测算法。"""
    if algo_hint == ALGO_LZ4 or algo_hint == "auto":
        # 优先使用原生 LZ4 库
        try:
            return lz4_decompress_native(data, uncompressed_size)
        except (ImportError, RuntimeError):
            pass

        # 尝试 lz4 Python 包
        try:
            import lz4.block
            return lz4.block.decompress(data, uncompressed_size=uncompressed_size)
        except (ImportError, Exception):
            pass

    if algo_hint == "auto":
        # 尝试纯 Python LZ4
        try:
            result = lz4_decompress(data, uncompressed_size)
            if len(result) == uncompressed_size:
                return result
        except Exception:
            pass

        # 尝试 zlib
        try:
            return zlib.decompress(data, wbits=-15)
        except zlib.error:
            pass

        # 尝试 zlib with header
        try:
            return zlib.decompress(data)
        except zlib.error:
            pass

    if algo_hint == ALGO_LZ4:
        return lz4_decompress(data, uncompressed_size)

    if algo_hint == ALGO_ZLIB:
        return zlib.decompress(data, wbits=-15)

    raise ValueError(f"无法解压数据（算法: {algo_hint}）")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def filetime_now() -> int:
    return int(time.time() * 10_000_000) + EPOCH_DIFF


def path_to_filetime(filepath: str) -> int:
    mtime = os.path.getmtime(filepath)
    return int(mtime * 10_000_000) + EPOCH_DIFF


def adler32(data: bytes) -> int:
    return zlib.adler32(data) & 0xFFFFFFFF


def detect_algo_from_data(data: bytes, expected_size: int) -> str:
    """尝试检测压缩算法。"""
    # 先尝试 LZ4
    try:
        import lz4.block
        result = lz4.block.decompress(data, uncompressed_size=expected_size)
        if len(result) == expected_size:
            return ALGO_LZ4
    except (ImportError, Exception):
        pass

    # 尝试纯 Python LZ4
    try:
        result = lz4_decompress(data, expected_size)
        if len(result) == expected_size:
            return ALGO_LZ4
    except Exception:
        pass

    # 尝试 zlib
    try:
        result = zlib.decompress(data, wbits=-15)
        if len(result) == expected_size:
            return ALGO_ZLIB
    except zlib.error:
        pass

    return ALGO_ZLIB  # default


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class ARCHeader:
    __slots__ = ("magic", "version", "num_file_entries", "num_data_records",
                 "record_table_size", "string_table_size", "record_table_offset")

    def __init__(self):
        self.magic = ARC_MAGIC
        self.version = ARC_VERSION
        self.num_file_entries = 0
        self.num_data_records = 0
        self.record_table_size = 0
        self.string_table_size = 0
        self.record_table_offset = 0

    def pack(self) -> bytes:
        return struct.pack(
            "<4s6I",
            self.magic, self.version, self.num_file_entries,
            self.num_data_records, self.record_table_size,
            self.string_table_size, self.record_table_offset,
        )

    @classmethod
    def unpack(cls, data: bytes) -> ARCHeader:
        h = cls()
        (h.magic, h.version, h.num_file_entries, h.num_data_records,
         h.record_table_size, h.string_table_size, h.record_table_offset
        ) = struct.unpack("<4s6I", data[:HEADER_SIZE])
        if h.magic != ARC_MAGIC:
            raise ValueError(f"无效的 ARC 文件头: magic={h.magic!r}")
        if h.version != ARC_VERSION:
            raise ValueError(f"不支持的 ARC 版本: {h.version}")
        return h


class ARCRecordEntry:
    __slots__ = ("part_offset", "compressed_size", "decompressed_size")

    def __init__(self, part_offset=0, compressed_size=0, decompressed_size=0):
        self.part_offset = part_offset
        self.compressed_size = compressed_size
        self.decompressed_size = decompressed_size

    def pack(self) -> bytes:
        return struct.pack("<3I", self.part_offset, self.compressed_size, self.decompressed_size)

    @classmethod
    def unpack(cls, data: bytes) -> ARCRecordEntry:
        e = cls()
        e.part_offset, e.compressed_size, e.decompressed_size = struct.unpack("<3I", data[:RECORD_ENTRY_SIZE])
        return e


class ARCTocEntry:
    __slots__ = ("entry_type", "file_offset", "compressed_size",
                 "decompressed_size", "decompressed_hash", "file_time",
                 "file_parts", "first_part_index", "string_entry_length",
                 "string_entry_offset")

    def __init__(self):
        self.entry_type = 3
        self.file_offset = 0
        self.compressed_size = 0
        self.decompressed_size = 0
        self.decompressed_hash = 0
        self.file_time = 0
        self.file_parts = 0
        self.first_part_index = 0
        self.string_entry_length = 0
        self.string_entry_offset = 0

    def pack(self) -> bytes:
        return struct.pack(
            "<5I Q 4I",
            self.entry_type, self.file_offset, self.compressed_size,
            self.decompressed_size, self.decompressed_hash, self.file_time,
            self.file_parts, self.first_part_index,
            self.string_entry_length, self.string_entry_offset,
        )

    @classmethod
    def unpack(cls, data: bytes) -> ARCTocEntry:
        e = cls()
        (e.entry_type, e.file_offset, e.compressed_size,
         e.decompressed_size, e.decompressed_hash, e.file_time,
         e.file_parts, e.first_part_index, e.string_entry_length,
         e.string_entry_offset
        ) = struct.unpack("<5I Q 4I", data[:TOC_ENTRY_SIZE])
        return e


# ---------------------------------------------------------------------------
# 文件名编码
# ---------------------------------------------------------------------------

def _get_encoding() -> str:
    try:
        "test".encode("gbk")
        return "gbk"
    except (LookupError, UnicodeEncodeError):
        return "utf-8"


def _decode_name(data: bytes) -> str:
    enc = _get_encoding()
    try:
        return data.decode(enc)
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 打包
# ---------------------------------------------------------------------------

def pack_arc(output_path: str, input_dir: str, algo: str = ALGO_ZLIB, level: int = 6) -> None:
    input_dir = os.path.abspath(input_dir)
    if not os.path.isdir(input_dir):
        print(f"[ERROR] 输入目录不存在: {input_dir}")
        sys.exit(1)

    # 收集文件
    files: list[tuple[str, str]] = []
    for root, _dirs, filenames in os.walk(input_dir):
        for fname in filenames:
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, input_dir).replace("\\", "/").lower()
            files.append((rel_path, abs_path))
    files.sort()

    num_files = len(files)
    if num_files == 0:
        print("[ERROR] 输入目录中没有文件")
        sys.exit(1)

    print(f"[INFO] 发现 {num_files} 个文件, 压缩算法: {algo}")

    # 构建字符串表
    enc = _get_encoding()
    string_entries: list[bytes] = []
    for rel_path, _ in files:
        string_entries.append(rel_path.encode(enc) + b"\x00")
    string_table = b"".join(string_entries)
    string_table_size = len(string_table)

    # 压缩数据
    records: list[ARCRecordEntry] = []
    toc_entries: list[ARCTocEntry] = []
    data_buffer = bytearray()
    current_record_index = 0

    for i, (rel_path, abs_path) in enumerate(files):
        with open(abs_path, "rb") as f:
            file_data = f.read()

        file_size = len(file_data)
        file_hash = adler32(file_data)
        file_time = path_to_filetime(abs_path)

        parts: list[ARCRecordEntry] = []
        offset = 0
        while offset < file_size:
            chunk = file_data[offset:offset + MAX_BLOCK_SIZE]
            compressed, _ = compress_data(chunk, algo, level)

            if len(compressed) < len(chunk):
                part = ARCRecordEntry(compressed_size=len(compressed), decompressed_size=len(chunk))
                data_buffer.extend(compressed)
            else:
                part = ARCRecordEntry(compressed_size=len(chunk), decompressed_size=len(chunk))
                data_buffer.extend(chunk)

            parts.append(part)
            offset += MAX_BLOCK_SIZE

        total_compressed = sum(p.compressed_size for p in parts)

        toc = ARCTocEntry()
        # LZ4 模式下始终使用 type 3（与 ArchiveTool.exe 兼容）
        if algo == ALGO_LZ4:
            toc.entry_type = 3
        else:
            toc.entry_type = 3 if any(p.compressed_size < p.decompressed_size for p in parts) else 1
        toc.compressed_size = total_compressed
        toc.decompressed_size = file_size
        toc.decompressed_hash = file_hash
        toc.file_time = file_time
        toc.file_parts = len(parts)
        toc.first_part_index = current_record_index

        str_offset = sum(len(string_entries[j]) for j in range(i))
        toc.string_entry_length = len(string_entries[i]) - 1
        toc.string_entry_offset = str_offset

        toc_entries.append(toc)
        records.extend(parts)
        current_record_index += len(parts)

        if (i + 1) % 100 == 0 or i + 1 == num_files:
            print(f"  [{i+1}/{num_files}] {rel_path}")

    # 计算偏移 - 与 ArchiveTool.exe 布局一致
    # 布局: Header + Reserved + DATA + Record Table + String Table + TOC
    data_offset = HEADER_SIZE + RESERVED_SIZE
    record_table_offset = data_offset + len(data_buffer)
    record_table_size = len(records) * RECORD_ENTRY_SIZE
    string_table_offset = record_table_offset + record_table_size
    toc_offset = string_table_offset + string_table_size

    # 设置数据块偏移
    current_data_offset = data_offset
    for rec in records:
        rec.part_offset = current_data_offset
        current_data_offset += rec.compressed_size

    header = ARCHeader()
    header.num_file_entries = num_files
    header.num_data_records = len(records)
    header.record_table_size = record_table_size
    header.string_table_size = string_table_size
    header.record_table_offset = record_table_offset

    with open(output_path, "wb") as f:
        f.write(header.pack())
        f.write(b"\x00" * RESERVED_SIZE)
        f.write(data_buffer)  # 数据在前
        for rec in records:
            f.write(rec.pack())
        f.write(string_table)
        for toc in toc_entries:
            f.write(toc.pack())

    output_size = os.path.getsize(output_path)
    print(f"[SUCCESS] 打包完成: {output_path} ({output_size} bytes)")


# ---------------------------------------------------------------------------
# 解包（核心）
# ---------------------------------------------------------------------------

def _read_arc_structure(arc_path: str):
    """读取 ARC 文件结构，返回 (header, record_table, string_table_data, toc_table, f)。"""
    f = open(arc_path, "rb")
    header = ARCHeader.unpack(f.read(HEADER_SIZE))

    # 跳转到记录表位置（由头部指定）
    f.seek(header.record_table_offset)

    record_table = [ARCRecordEntry.unpack(f.read(RECORD_ENTRY_SIZE))
                    for _ in range(header.num_data_records)]
    string_table_data = f.read(header.string_table_size)
    toc_table = [ARCTocEntry.unpack(f.read(TOC_ENTRY_SIZE))
                 for _ in range(header.num_file_entries)]

    return header, record_table, string_table_data, toc_table, f


def _decompress_file_data(f, toc: ARCTocEntry, record_table: list[ARCRecordEntry]) -> bytes:
    """解压单个文件的数据。"""
    file_data = bytearray()
    for part_idx in range(toc.first_part_index, toc.first_part_index + toc.file_parts):
        part = record_table[part_idx]
        f.seek(part.part_offset)
        compressed_data = f.read(part.compressed_size)

        if part.compressed_size < part.decompressed_size:
            decompressed = decompress_data(compressed_data, part.decompressed_size)
            file_data.extend(decompressed)
        else:
            file_data.extend(compressed_data)

    return bytes(file_data)


def unpack_arc(arc_path: str, output_dir: str) -> None:
    if not os.path.isfile(arc_path):
        print(f"[ERROR] 文件不存在: {arc_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    header, record_table, string_table_data, toc_table, f = _read_arc_structure(arc_path)

    print(f"[INFO] ARC v{header.version}, {header.num_file_entries} 个文件")

    for i, toc in enumerate(toc_table):
        name_bytes = string_table_data[toc.string_entry_offset:toc.string_entry_offset + toc.string_entry_length]
        rel_path = _decode_name(name_bytes)
        output_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        file_data = _decompress_file_data(f, toc, record_table)

        # 校验
        if len(file_data) != toc.decompressed_size:
            print(f"  [WARN] {rel_path}: 大小不匹配 ({len(file_data)} != {toc.decompressed_size})")

        with open(output_path, "wb") as out_f:
            out_f.write(file_data)

        try:
            unix_time = (toc.file_time - EPOCH_DIFF) / 10_000_000
            os.utime(output_path, (unix_time, unix_time))
        except (OSError, OverflowError):
            pass

        print(f"  [{i+1}/{header.num_file_entries}] {rel_path} ({len(file_data)} bytes)")

    f.close()
    print(f"[SUCCESS] 解包完成: {output_dir}")


# ---------------------------------------------------------------------------
# database 命令（提取数据库/文本文件）
# ---------------------------------------------------------------------------

def database_arc(arc_path: str, output_dir: str, target_file: str = None) -> None:
    """提取 .arc 中的数据库/文本文件。类似 ArchiveTool -database。"""
    if not os.path.isfile(arc_path):
        print(f"[ERROR] 文件不存在: {arc_path}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    header, record_table, string_table_data, toc_table, f = _read_arc_structure(arc_path)

    print(f"[INFO] ARC v{header.version}, {header.num_file_entries} 个文件")

    extracted = 0
    for i, toc in enumerate(toc_table):
        name_bytes = string_table_data[toc.string_entry_offset:toc.string_entry_offset + toc.string_entry_length]
        rel_path = _decode_name(name_bytes)

        # 如果指定了目标文件，只提取匹配的
        if target_file and target_file.lower() not in rel_path.lower():
            continue

        output_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        file_data = _decompress_file_data(f, toc, record_table)

        with open(output_path, "wb") as out_f:
            out_f.write(file_data)

        try:
            unix_time = (toc.file_time - EPOCH_DIFF) / 10_000_000
            os.utime(output_path, (unix_time, unix_time))
        except (OSError, OverflowError):
            pass

        extracted += 1
        print(f"  [{extracted}] {rel_path} ({len(file_data)} bytes)")

    f.close()
    if extracted == 0:
        print("[WARN] 未找到匹配的文件")
    else:
        print(f"[SUCCESS] 提取完成: {extracted} 个文件 -> {output_dir}")


# ---------------------------------------------------------------------------
# 列表
# ---------------------------------------------------------------------------

def list_arc(arc_path: str) -> None:
    if not os.path.isfile(arc_path):
        print(f"[ERROR] 文件不存在: {arc_path}")
        sys.exit(1)

    header, record_table, string_table_data, toc_table, f = _read_arc_structure(arc_path)

    print(f"ARC v{header.version}")
    print(f"文件数: {header.num_file_entries}")
    print(f"数据记录数: {header.num_data_records}")
    print(f"记录表大小: {header.record_table_size} bytes")
    print(f"字符串表大小: {header.string_table_size} bytes")
    print(f"记录表偏移: 0x{header.record_table_offset:X}")
    print()

    total_compressed = 0
    total_decompressed = 0

    for toc in toc_table:
        name_bytes = string_table_data[toc.string_entry_offset:toc.string_entry_offset + toc.string_entry_length]
        name = _decode_name(name_bytes)
        total_compressed += toc.compressed_size
        total_decompressed += toc.decompressed_size
        print(f"  {name}  ({toc.decompressed_size} bytes, "
              f"{toc.compressed_size} compressed, {toc.file_parts} parts, type={toc.entry_type})")

    print()
    print(f"总解压大小: {total_decompressed:,} bytes")
    print(f"总压缩大小: {total_compressed:,} bytes")
    if total_decompressed > 0:
        print(f"压缩率: {total_compressed / total_decompressed:.1%}")

    f.close()


# ---------------------------------------------------------------------------
# 信息
# ---------------------------------------------------------------------------

def info_arc(arc_path: str) -> None:
    """显示 ARC 文件详细信息。"""
    if not os.path.isfile(arc_path):
        print(f"[ERROR] 文件不存在: {arc_path}")
        sys.exit(1)

    file_size = os.path.getsize(arc_path)
    header, record_table, string_table_data, toc_table, f = _read_arc_structure(arc_path)

    print(f"文件: {arc_path}")
    print(f"大小: {file_size:,} bytes")
    print()
    print(f"=== 头部信息 ===")
    print(f"版本: {header.version}")
    print(f"文件条目数: {header.num_file_entries}")
    print(f"数据记录数: {header.num_data_records}")
    print(f"记录表大小: {header.record_table_size} bytes")
    print(f"字符串表大小: {header.string_table_size} bytes")
    print(f"记录表偏移: 0x{header.record_table_offset:X}")
    print()

    # 检测压缩算法
    algo_counts = {"lz4": 0, "zlib": 0, "raw": 0, "unknown": 0}
    for toc in toc_table[:10]:  # 采样前10个文件
        if toc.file_parts > 0:
            part = record_table[toc.first_part_index]
            f.seek(part.part_offset)
            data = f.read(min(part.compressed_size, 1024))
            if part.compressed_size < part.decompressed_size:
                algo = detect_algo_from_data(data, part.decompressed_size)
                algo_counts[algo] += 1
            else:
                algo_counts["raw"] += 1

    print(f"=== 压缩算法检测（采样） ===")
    for algo, count in algo_counts.items():
        if count > 0:
            print(f"  {algo}: {count} 个文件")

    # EntryType 统计
    type_counts = {}
    for toc in toc_table:
        t = toc.entry_type
        type_counts[t] = type_counts.get(t, 0) + 1
    print()
    print(f"=== EntryType 分布 ===")
    for t, count in sorted(type_counts.items()):
        print(f"  Type {t}: {count} 个文件")

    # 分块统计
    parts_counts = {}
    for toc in toc_table:
        p = toc.file_parts
        parts_counts[p] = parts_counts.get(p, 0) + 1
    print()
    print(f"=== 分块分布 ===")
    for p, count in sorted(parts_counts.items()):
        print(f"  {p} parts: {count} 个文件")

    f.close()


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "pack":
        if len(sys.argv) < 4:
            print("用法: arc_tool.py pack <output.arc> <input_dir> [--level N] [--algo lz4|zlib]")
            sys.exit(1)
        output_path = sys.argv[2]
        input_dir = sys.argv[3]
        algo = ALGO_LZ4
        level = 6
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--level" and i + 1 < len(sys.argv):
                level = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--algo" and i + 1 < len(sys.argv):
                algo = sys.argv[i + 1].lower()
                i += 2
            else:
                i += 1
        pack_arc(output_path, input_dir, algo, level)

    elif cmd == "unpack":
        if len(sys.argv) < 4:
            print("用法: arc_tool.py unpack <input.arc> <output_dir>")
            sys.exit(1)
        unpack_arc(sys.argv[2], sys.argv[3])

    elif cmd == "database":
        if len(sys.argv) < 4:
            print("用法: arc_tool.py database <input.arc> <output_dir> [file]")
            sys.exit(1)
        target_file = sys.argv[4] if len(sys.argv) > 4 else None
        database_arc(sys.argv[2], sys.argv[3], target_file)

    elif cmd == "list":
        list_arc(sys.argv[2])

    elif cmd == "info":
        info_arc(sys.argv[2])

    else:
        print(f"[ERROR] 未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
