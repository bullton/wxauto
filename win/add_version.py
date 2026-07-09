"""
向 exe 注入 Windows 版本信息（作者、版本等）
使用纯 ctypes + Windows API，无需 pywin32
"""
import sys
import os
import struct
import ctypes
from ctypes import wintypes


# Windows API types
HANDLE = wintypes.HANDLE
BOOL = wintypes.BOOL
DWORD = wintypes.DWORD
WORD = wintypes.WORD
LPWSTR = wintypes.LPCWSTR
LPBYTE = ctypes.POINTER(ctypes.c_byte)
LPDWORD = ctypes.POINTER(DWORD)


# Windows API functions
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

    # ===== 构建 VERSION_INFO 二进制数据 =====

    def le16(v):
        return struct.pack('<H', v & 0xFFFF)

    def le32(v):
        return struct.pack('<I', v & 0xFFFFFFFF)

    def wstr(s):
        return s.encode('utf-16-le') + b'\x00\x00'

    def align4(data):
        while len(data) % 4:
            data += b'\x00'
        return data

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

    LANG, CP = 0x0804, 0x04B0  # 中文简体

    # VS_FIXEDFILEINFO (52 bytes)
    fixed = b''
    fixed += le32(0)            # dwSignature
    fixed += le32(1 << 16)     # dwStrucVersion = 1.0
    fixed += le32(1 << 16 | 3)  # dwFileVersionMS = 1.3
    fixed += le32(0)            # dwFileVersionLS = 0.0
    fixed += le32(1 << 16 | 3)  # dwProductVersionMS = 1.3
    fixed += le32(0)            # dwProductVersionLS = 0.0
    fixed += le32(0x3F << 16)  # dwFileFlagsMask
    fixed += le32(0)           # dwFileFlags
    fixed += le32(0x40004)     # dwFileOS = VOS__WINDOWS32
    fixed += le32(1)           # dwFileType = VFT_APP
    fixed += le32(0)           # dwFileSubtype
    fixed += le32(0)           # dwFileDateMS
    fixed += le32(0)           # dwFileDateLS

    # StringTable entries
    st_entries = b''
    for name, value in strings:
        st_entries += wstr(name) + wstr(value)

    # StringTable: header(6) + key(4) + entries(padded)
    st_data = st_entries
    st_block = bytearray(align4(b'\x00\x00\x00\x01' + le32(LANG << 16 | CP) + st_data))
    struct.pack_into('<H', st_block, 0, len(st_block))

    # StringFileInfo: header(6) + key(14 padded) + StringTable
    sf_block = bytearray(align4(
        b'\x00\x00\x00\x01' + b'StringFileInfo\x00\x00' + bytes(st_block)
    ))
    struct.pack_into('<H', sf_block, 0, len(sf_block))

    # VarFileInfo: header(6) + key(12 padded) + var_entry(16)
    var_entry = le16(0) + le16(4) + le16(0) + b'Translation\x00\x00' + le32(LANG << 16 | CP)
    var_block = bytearray(align4(b'\x00\x00\x00\x01' + b'VarFileInfo\x00\x00' + var_entry))
    struct.pack_into('<H', var_block, 0, len(var_block))

    # VS_VERSION_INFO root
    vi_data = fixed + bytes(sf_block) + bytes(var_block)
    vi_block = bytearray(align4(
        le16(0) + le16(len(fixed)) + le16(0) + b'VS_VERSION_INFO\x00\x00' + vi_data
    ))
    struct.pack_into('<H', vi_block, 0, len(vi_block))

    print(f"[2] 写入 VERSION_INFO ({len(vi_block)} bytes)...")

    # UpdateResource: type=RT_VERSION(16)=MAKEINTRESOURCE(16), name=1=VS_VERSION_INFO
    RT_VERSION = ctypes.c_wchar_p(chr(16))      # MAKEINTRESOURCE(16)
    VS_VER_NAME = ctypes.c_wchar_p(chr(1))       # MAKEINTRESOURCE(1)

    data_bytes = bytes(vi_block)
    data_buf = (ctypes.c_byte * len(data_bytes)).from_buffer_copy(data_bytes)

    ok = UpdateResourceW(
        h_update,
        RT_VERSION,       # type: RT_VERSION
        VS_VER_NAME,     # name: VS_VERSION_INFO
        LANG,            # language
        data_buf,        # data
        len(data_bytes)  # size
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
