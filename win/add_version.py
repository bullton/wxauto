"""
向 exe 注入 Windows 版本信息
使用 ctypes + Windows API，操作前备份文件
"""
import sys
import os
import struct
import ctypes
from ctypes import wintypes
import shutil


HANDLE = wintypes.HANDLE
BOOL = wintypes.BOOL
DWORD = wintypes.DWORD
WORD = wintypes.WORD
LPWSTR = wintypes.LPCWSTR
LPBYTE = ctypes.POINTER(ctypes.c_byte)
LPDWORD = ctypes.POINTER(DWORD)

kernel32 = ctypes.windll.kernel32

BeginUpdateResourceW = kernel32.BeginUpdateResourceW
BeginUpdateResourceW.argtypes = [LPWSTR, BOOL]
BeginUpdateResourceW.restype = HANDLE

UpdateResourceW = kernel32.UpdateResourceW
UpdateResourceW.argtypes = [HANDLE, LPWSTR, LPWSTR, WORD, LPBYTE, DWORD]
UpdateResourceW.restype = BOOL

EndUpdateResourceW = kernel32.EndUpdateResourceW
EndUpdateResourceW.argtypes = [HANDLE, BOOL]
EndUpdateResourceW.restype = BOOL


def add_version_to_exe(exe_path: str):
    """使用 Windows API 向 exe 添加版本信息"""
    exe_path = os.path.abspath(exe_path)
    if not os.path.exists(exe_path):
        print(f"[错误] 文件不存在: {exe_path}")
        return False

    print(f"[1] 打开: {exe_path}")

    h_update = BeginUpdateResourceW(exe_path, False)
    if not h_update or h_update == HANDLE(-1):
        err = ctypes.get_last_error()
        print(f"[错误] BeginUpdateResourceW 失败, 错误码: {err}")
        return False

    strings = [
        ('CompanyName', 'bullton'),
        ('FileDescription', '微信聊天截图工具'),
        ('FileVersion', '1.3.0.0'),
        ('InternalName', 'wxauto'),
        ('OriginalFilename', '微信聊天截图工具.exe'),
        ('ProductName', '微信聊天截图工具'),
        ('ProductVersion', '1.3.0.0'),
        ('Author', 'bullton'),
        ('Email', 'bullton@163.com'),
    ]

    LANG, CP = 0x0804, 0x04B0

    fixed = struct.pack('<I', 0)
    fixed += struct.pack('<I', 1 << 16)
    fixed += struct.pack('<I', 1 << 16 | 3)
    fixed += struct.pack('<I', 0)
    fixed += struct.pack('<I', 1 << 16 | 3)
    fixed += struct.pack('<I', 0)
    fixed += struct.pack('<I', 0x3F << 16)
    fixed += struct.pack('<I', 0)
    fixed += struct.pack('<I', 0x40004)
    fixed += struct.pack('<I', 1)
    fixed += struct.pack('<I', 0)
    fixed += struct.pack('<I', 0)
    fixed += struct.pack('<I', 0)

    st_entries = b''
    for name, value in strings:
        s = value.encode('utf-16-le') + b'\x00\x00'
        st_entries += struct.pack('<H', len(name)) + name.encode('utf-16-le') + b'\x00\x00'
        st_entries += struct.pack('<H', len(s)) + s

    st_block = struct.pack('<H', len(st_entries) + 6)
    st_block += struct.pack('<I', LANG << 16 | CP)
    st_block += st_entries
    while len(st_block) % 4:
        st_block += b'\x00'

    sf_data = b'StringFileInfo\x00\x00'
    sf_data += st_block
    sf_block = struct.pack('<H', len(sf_data) + 6)
    sf_block += sf_data
    while len(sf_block) % 4:
        sf_block += b'\x00'

    var_entry = struct.pack('<HH', 0, 4) + struct.pack('<HH', 0, 0) + b'Translation\x00\x00' + struct.pack('<I', LANG << 16 | CP)
    var_block = struct.pack('<H', len(var_entry) + 6)
    var_block += b'VarFileInfo\x00\x00'
    var_block += var_entry
    while len(var_block) % 4:
        var_block += b'\x00'

    vi_data = fixed + sf_block + var_block
    vi_block = struct.pack('<H', 0)
    vi_block += struct.pack('<H', len(fixed))
    vi_block += struct.pack('<H', 0)
    vi_block += b'VS_VERSION_INFO\x00\x00'
    vi_block += vi_data
    while len(vi_block) % 4:
        vi_block += b'\x00'

    print(f"[2] 写入 VERSION_INFO ({len(vi_block)} bytes)...")

    RT_VERSION = ctypes.c_wchar_p(chr(16))
    VS_VER_NAME = ctypes.c_wchar_p(chr(1))

    data_bytes = bytes(vi_block)
    data_buf = (ctypes.c_byte * len(data_bytes)).from_buffer_copy(data_bytes)

    ok = UpdateResourceW(
        h_update,
        RT_VERSION,
        VS_VER_NAME,
        LANG,
        data_buf,
        len(data_bytes)
    )

    if not ok:
        err = ctypes.get_last_error()
        print(f"    [错误] UpdateResourceW 失败: {err}")
        EndUpdateResourceW(h_update, True)
        return False

    print(f"    [OK] 语言 0x{LANG:04X}")

    print(f"[3] 提交更改...")

    ok = EndUpdateResourceW(h_update, False)
    if not ok:
        err = ctypes.get_last_error()
        print(f"[错误] EndUpdateResourceW 失败: {err}")
        return False

    print(f"[完成] 版本信息已写入:")
    for name, value in strings:
        print(f"    {name}: {value}")

    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        dist_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist', '微信聊天截图工具.exe')
        if os.path.exists(dist_exe):
            exe_path = dist_exe
        else:
            print(f"用法: python {sys.argv[0]} <exe路径>")
            sys.exit(1)
    else:
        exe_path = sys.argv[1]

    add_version_to_exe(exe_path)
