"""Small, read-only MMD diagnostics core. No network, third-party modules, or writes."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path, PureWindowsPath
import os
import struct
from typing import BinaryIO

MAX_BYTES = 256 * 1024 * 1024
MAX_VERTICES = 1_000_000
MAX_FACES_INDICES = 5_000_000
MAX_TEXTURES = 100_000
MAX_VMD_KEYS = 2_000_000


class InvalidFormat(ValueError):
    pass


@dataclass
class Finding:
    severity: str
    code: str
    message: str


@dataclass
class Report:
    tool: str
    filename: str
    status: str = 'PASS'
    summary: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str) -> None:
        self.findings.append(Finding(severity, code, message))
        if severity == 'ERROR':
            self.status = 'FAIL'
        elif severity == 'WARN' and self.status == 'PASS':
            self.status = 'WARN'

    def as_dict(self) -> dict:
        return asdict(self)


class Reader:
    def __init__(self, file: BinaryIO, size: int):
        self.file = file
        self.size = size

    @property
    def remaining(self) -> int:
        return self.size - self.file.tell()

    def read(self, n: int) -> bytes:
        if n < 0 or n > self.remaining:
            raise InvalidFormat(f'Truncated or malformed binary field ({n} bytes requested; {self.remaining} remain)')
        out = self.file.read(n)
        if len(out) != n:
            raise InvalidFormat('Unexpected end of file')
        return out

    def skip(self, n: int) -> None:
        if n < 0 or n > self.remaining:
            raise InvalidFormat(f'Truncated section ({n} bytes requested; {self.remaining} remain)')
        self.file.seek(n, os.SEEK_CUR)

    def unpack(self, fmt: str):
        return struct.unpack('<' + fmt, self.read(struct.calcsize('<' + fmt)))

    def integer(self, size: int, signed: bool = False) -> int:
        if size not in (1, 2, 4):
            raise InvalidFormat('Invalid PMX index size')
        return int.from_bytes(self.read(size), 'little', signed=signed)

    def count(self, limit: int, label: str) -> int:
        value, = self.unpack('i')
        if value < 0 or value > limit:
            raise InvalidFormat(f'{label}: impossible count {value} (limit {limit})')
        return value

    def pmx_text(self, encoding: str) -> str:
        n = self.count(2 * 1024 * 1024, 'Text length')
        data = self.read(n)
        try:
            return data.decode(encoding, errors='strict')
        except UnicodeError as ex:
            raise InvalidFormat(f'Invalid {encoding} text') from ex


def _texture_check(model_path: Path, raw: str, report: Report, seen: set[str]) -> None:
    if not raw.strip():
        return
    key = raw.replace('\\', '/').casefold()
    if key in seen:
        report.add('WARN', 'DUPLICATE_TEXTURE_PATH', f'Duplicate texture declaration: {raw}')
    seen.add(key)
    win = PureWindowsPath(raw)
    normalized = raw.replace('\\', '/')
    if win.is_absolute() or bool(win.drive) or normalized.startswith('/') or '://' in normalized:
        report.add('WARN', 'EXTERNAL_TEXTURE_PATH', f'Absolute or external texture reference (not opened): {raw}')
        return
    try:
        base = model_path.parent.resolve()
        target = (base / normalized).resolve()
        if not target.is_relative_to(base):
            report.add('WARN', 'ESCAPING_TEXTURE_PATH', f'Texture escapes model folder (not opened): {raw}')
            return
        if not target.is_file():
            report.add('WARN', 'MISSING_TEXTURE', f'Texture not found: {raw}')
    except (OSError, ValueError):
        report.add('WARN', 'INVALID_TEXTURE_PATH', f'Unsafe or invalid texture name: {raw}')


def inspect_pmx(path: Path) -> Report:
    """Inspect PMX metadata, vertex/index validity and texture names; never modify files.

    This is NOT a full PMX model validator: bone/morph/physics/material sections are
    not parsed in R0. Scanning only texture declarations may include unused names.
    """
    report = Report('model_doctor', path.name)
    try:
        size = path.stat().st_size
        if size > MAX_BYTES:
            raise InvalidFormat(f'File exceeds {MAX_BYTES} byte safety limit')
        with path.open('rb') as f:
            r = Reader(f, size)
            if r.read(4) != b'PMX ':
                raise InvalidFormat('PMX signature does not match')
            version, = r.unpack('f')
            if not (abs(version - 2.0) < 0.001 or abs(version - 2.1) < 0.001):
                raise InvalidFormat(f'Unsupported PMX version: {version}')
            global_count, = r.unpack('B')
            if global_count < 8 or global_count > 64:
                raise InvalidFormat(f'Invalid PMX globals length: {global_count}')
            flags = r.read(global_count)
            enc, add_uv, vertex_size, tex_size, mat_size, bone_size, morph_size, rigid_size = flags[:8]
            if enc not in (0, 1):
                raise InvalidFormat('Invalid PMX text encoding')
            if add_uv > 4 or any(n not in (1, 2, 4) for n in (vertex_size, tex_size, mat_size, bone_size, morph_size, rigid_size)):
                raise InvalidFormat('Invalid PMX globals / index widths')
            encoding = 'utf-16-le' if enc == 0 else 'utf-8'
            name_jp = r.pmx_text(encoding)
            name_en = r.pmx_text(encoding)
            r.pmx_text(encoding)  # comments jp
            r.pmx_text(encoding)  # comments en
            vertices = r.count(MAX_VERTICES, 'Vertex count')
            for _ in range(vertices):
                r.skip(32 + (16 * add_uv))  # xyz normal uv additional UV
                weight, = r.unpack('B')
                if weight == 0:  # BDEF1
                    r.skip(bone_size)
                elif weight == 1:  # BDEF2
                    r.skip(bone_size * 2 + 4)
                elif weight in (2, 4):  # BDEF4 and QDEF (PMX 2.1)
                    r.skip(bone_size * 4 + 16)
                elif weight == 3:  # SDEF
                    r.skip(bone_size * 2 + 4 + 36)
                else:
                    raise InvalidFormat(f'Unknown PMX weight type {weight}')
                r.skip(4)  # edge scale
            index_count = r.count(MAX_FACES_INDICES, 'Face index count')
            if index_count % 3:
                report.add('WARN', 'NON_TRIANGULATED_INDICES', f'Face index count {index_count} is not a multiple of three')
            invalid_indices = 0
            for _ in range(index_count):
                idx = r.integer(vertex_size)
                if idx >= vertices:
                    invalid_indices += 1
            if invalid_indices:
                report.add('ERROR', 'INVALID_VERTEX_REFERENCE', f'{invalid_indices} face indices refer outside the {vertices} available vertices')
            texture_count = r.count(MAX_TEXTURES, 'Texture count')
            texture_names = [r.pmx_text(encoding) for _ in range(texture_count)]
            seen: set[str] = set()
            for raw in texture_names:
                _texture_check(path, raw, report, seen)
            report.summary = {
                'pmx_version': round(version, 1), 'model_jp': name_jp,
                'model_en': name_en, 'vertices': vertices,
                'triangles_by_indices': index_count // 3,
                'face_indices': index_count, 'invalid_indices': invalid_indices,
                'texture_declarations': texture_count,
                'scope': 'header, vertices, face indices, texture declarations ONLY',
            }
            report.add('INFO', 'LIMITED_SCOPE', 'R0 does not yet inspect materials, bones, morphs, rigid bodies, joints or soft bodies')
    except (OSError, InvalidFormat) as ex:
        report.add('ERROR', 'FORMAT_OR_IO_ERROR', str(ex))
    return report


def _decode_vmd_name(b: bytes) -> str:
    return b.split(b'\x00', 1)[0].decode('shift_jis', errors='replace')


def inspect_vmd(path: Path) -> Report:
    """Read VMD 0002 bone and morph keyframe counts/frame ranges; other sections ignored."""
    report = Report('motion_peek', path.name)
    try:
        size = path.stat().st_size
        if size > MAX_BYTES:
            raise InvalidFormat(f'File exceeds {MAX_BYTES} byte safety limit')
        with path.open('rb') as f:
            r = Reader(f, size)
            header = r.read(30).split(b'\x00', 1)[0]
            if header != b'Vocaloid Motion Data 0002':
                raise InvalidFormat('Only VMD 0002 files are supported in R0')
            model = _decode_vmd_name(r.read(20))
            bone_count = r.count(MAX_VMD_KEYS, 'Bone keyframe count')
            if bone_count * 111 > r.remaining:
                raise InvalidFormat('Truncated VMD bone keyframes')
            bone_names: set[str] = set()
            max_frame = 0
            for _ in range(bone_count):
                bone_names.add(_decode_vmd_name(r.read(15)))
                frame, = r.unpack('I')
                max_frame = max(frame, max_frame)
                r.skip(92)  # position (12), quaternion (16), interpolation (64)
            morph_count = r.count(MAX_VMD_KEYS, 'Morph keyframe count')
            if morph_count * 23 > r.remaining:
                raise InvalidFormat('Truncated VMD morph keyframes')
            morph_names: set[str] = set()
            for _ in range(morph_count):
                morph_names.add(_decode_vmd_name(r.read(15)))
                frame, = r.unpack('I')
                max_frame = max(frame, max_frame)
                r.skip(4)  # morph weight
            report.summary = {
                'model': model, 'bone_keyframes': bone_count,
                'unique_bones': len(bone_names), 'morph_keyframes': morph_count,
                'unique_morphs': len(morph_names), 'max_bone_or_morph_frame': max_frame,
                'scope': 'VMD 0002 bone/morph track overview ONLY',
            }
            report.add('INFO', 'LIMITED_SCOPE', 'Camera, lights, IK visibility and shadow tracks are not parsed in R0')
    except (OSError, InvalidFormat) as ex:
        report.add('ERROR', 'FORMAT_OR_IO_ERROR', str(ex))
    return report
