import ctypes
from ctypes import wintypes
from enum import IntEnum
from core.logger import logger


class FocusAssistState(IntEnum):
    OFF = 0
    PRIORITY = 1  # Priority Only
    ALARMS = 2  # Alarms Only


def query_focus_assist():
    query_state = ctypes.windll.ntdll.ZwQueryWnfStateData
    state_name = ctypes.c_ulonglong(0x0D83063EA3BF1C75)
    buffer = ctypes.c_uint32()
    size = ctypes.c_ulong(4)
    status = query_state(
        ctypes.byref(state_name),
        None,
        None,
        ctypes.byref(ctypes.c_ulong()),
        ctypes.byref(buffer),
        ctypes.byref(size),
    )
    logger.info(f"Status: 0x{ctypes.c_ulong(status).value:08X}")
    return buffer.value


def set_focus_assist(mode: int):
    update_state = ctypes.windll.ntdll.ZwUpdateWnfStateData
    if mode not in (0, 1, 2):
        raise ValueError("Mode must be 0, 1, or 2.")

    data = bytes([mode, 0, 0, 0])

    state_name = ctypes.c_longlong(0xD83063EA3BF5075)

    status = update_state(
        ctypes.byref(state_name), ctypes.c_char_p(data), len(data), 0, 0, 0, 0
    )

    logger.info(f"Status: 0x{ctypes.c_ulong(status).value:08X}")
