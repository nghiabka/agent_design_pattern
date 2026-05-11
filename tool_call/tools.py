"""
═══════════════════════════════════════════════════════════════════════
TOOLS — Smart Home API tools cho LLM agent
═══════════════════════════════════════════════════════════════════════

Mỗi tool wrap một API call tới Smart Home Simulator.
LLM agent sẽ QUYẾT ĐỊNH gọi tool nào dựa trên yêu cầu user.

Đây là core của Tool Call pattern:
  User nói ngôn ngữ tự nhiên → LLM hiểu ý → gọi đúng tool với đúng params.

Tools:
  • control_light     — Bật/tắt, chỉnh độ sáng, đổi màu đèn
  • control_ac        — Bật/tắt, chỉnh nhiệt độ, đổi chế độ điều hòa
  • control_tv        — Bật/tắt, chuyển kênh, chỉnh âm lượng TV
  • control_lock      — Khóa/mở khóa cửa
  • control_speaker   — Bật/tắt, phát nhạc, chỉnh âm lượng loa
  • get_device_status — Xem trạng thái thiết bị / tất cả thiết bị
"""

from langchain_core.tools import tool
from smart_home import smart_home


# ═══════════════════════════════════════════════════════════════
# ROOM & DEVICE ID MAPPING
# ═══════════════════════════════════════════════════════════════
# Agent gọi tool với tên phòng / thiết bị bằng ngôn ngữ tự nhiên.
# Mapping giúp chuyển đổi sang device_id chính xác.

ROOM_MAP = {
    "phòng khách": "living_room",
    "living room": "living_room",
    "phòng ngủ": "bedroom",
    "bedroom": "bedroom",
    "nhà bếp": "kitchen",
    "bếp": "kitchen",
    "kitchen": "kitchen",
    "cửa chính": "entrance",
    "entrance": "entrance",
    "garage": "garage",
    "nhà xe": "garage",
}


def resolve_device_id(room: str, device_type: str) -> str | None:
    """Chuyển đổi room name + device type → device_id.

    Args:
        room: Tên phòng (tiếng Việt hoặc tiếng Anh).
        device_type: Loại thiết bị (light, ac, tv, lock, speaker).

    Returns:
        device_id hoặc None nếu không tìm thấy.
    """
    room_key = ROOM_MAP.get(room.lower().strip(), room.lower().strip())
    device_id = f"{room_key}_{device_type}"
    if smart_home.get_device(device_id):
        return device_id
    # Thử tìm theo room
    devices = smart_home.get_devices_by_room(room_key)
    for dev_id, dev in devices.items():
        if dev["type"] == device_type:
            return dev_id
    return None


# ═══════════════════════════════════════════════════════════════
# TOOL: Control Light
# ═══════════════════════════════════════════════════════════════

@tool
def control_light(
    room: str,
    action: str,
    brightness: int = -1,
    color: str = "",
) -> str:
    """Điều khiển đèn trong nhà.

    Args:
        room: Tên phòng (ví dụ: "phòng khách", "phòng ngủ", "nhà bếp").
        action: Hành động — "on" (bật), "off" (tắt).
        brightness: Độ sáng 0-100 (tùy chọn, -1 = không thay đổi).
        color: Màu đèn (tùy chọn, ví dụ: "warm_white", "cool_white", "red", "blue").

    Returns:
        Kết quả thực thi.
    """
    device_id = resolve_device_id(room, "light")
    if not device_id:
        return f"❌ Không tìm thấy đèn ở {room}. Các phòng có đèn: phòng khách, phòng ngủ, nhà bếp."

    updates = {"state": action}
    if brightness >= 0:
        updates["brightness"] = max(0, min(100, brightness))
    if color:
        updates["color"] = color

    return smart_home.update_device(device_id, **updates)


# ═══════════════════════════════════════════════════════════════
# TOOL: Control AC
# ═══════════════════════════════════════════════════════════════

@tool
def control_ac(
    room: str,
    action: str,
    temperature: int = -1,
    mode: str = "",
) -> str:
    """Điều khiển điều hòa không khí.

    Args:
        room: Tên phòng (ví dụ: "phòng khách", "phòng ngủ").
        action: Hành động — "on" (bật), "off" (tắt).
        temperature: Nhiệt độ 16-30 độ C (tùy chọn, -1 = không thay đổi).
        mode: Chế độ — "cool" (làm mát), "heat" (sưởi), "fan" (quạt), "auto".

    Returns:
        Kết quả thực thi.
    """
    device_id = resolve_device_id(room, "ac")
    if not device_id:
        return f"❌ Không tìm thấy điều hòa ở {room}. Các phòng có điều hòa: phòng khách, phòng ngủ."

    updates = {"state": action}
    if temperature >= 0:
        updates["temperature"] = max(16, min(30, temperature))
    if mode:
        updates["mode"] = mode

    return smart_home.update_device(device_id, **updates)


# ═══════════════════════════════════════════════════════════════
# TOOL: Control TV
# ═══════════════════════════════════════════════════════════════

@tool
def control_tv(
    room: str,
    action: str,
    channel: str = "",
    volume: int = -1,
) -> str:
    """Điều khiển TV.

    Args:
        room: Tên phòng (ví dụ: "phòng khách").
        action: Hành động — "on" (bật), "off" (tắt).
        channel: Kênh TV (tùy chọn, ví dụ: "VTV1", "VTV3", "HBO", "Netflix").
        volume: Âm lượng 0-100 (tùy chọn, -1 = không thay đổi).

    Returns:
        Kết quả thực thi.
    """
    device_id = resolve_device_id(room, "tv")
    if not device_id:
        return f"❌ Không tìm thấy TV ở {room}. TV có ở: phòng khách."

    updates = {"state": action}
    if channel:
        updates["channel"] = channel
    if volume >= 0:
        updates["volume"] = max(0, min(100, volume))

    return smart_home.update_device(device_id, **updates)


# ═══════════════════════════════════════════════════════════════
# TOOL: Control Lock
# ═══════════════════════════════════════════════════════════════

@tool
def control_lock(
    location: str,
    action: str,
) -> str:
    """Điều khiển khóa cửa.

    Args:
        location: Vị trí — "cửa chính" (front_door), "garage".
        action: Hành động — "lock" (khóa), "unlock" (mở khóa).

    Returns:
        Kết quả thực thi.
    """
    loc_map = {
        "cửa chính": "front_door_lock",
        "front door": "front_door_lock",
        "cửa trước": "front_door_lock",
        "garage": "garage_door",
        "nhà xe": "garage_door",
        "cửa garage": "garage_door",
    }

    device_id = loc_map.get(location.lower().strip())
    if not device_id:
        return f"❌ Không tìm thấy khóa ở {location}. Có: cửa chính, garage."

    state = "locked" if action == "lock" else "unlocked"
    return smart_home.update_device(device_id, state=state)


# ═══════════════════════════════════════════════════════════════
# TOOL: Control Speaker
# ═══════════════════════════════════════════════════════════════

@tool
def control_speaker(
    room: str,
    action: str,
    volume: int = -1,
    song: str = "",
) -> str:
    """Điều khiển loa / hệ thống âm thanh.

    Args:
        room: Tên phòng (ví dụ: "phòng khách").
        action: Hành động — "on" (bật), "off" (tắt), "play" (phát nhạc).
        volume: Âm lượng 0-100 (tùy chọn, -1 = không thay đổi).
        song: Tên bài hát / playlist (tùy chọn).

    Returns:
        Kết quả thực thi.
    """
    device_id = resolve_device_id(room, "speaker")
    if not device_id:
        return f"❌ Không tìm thấy loa ở {room}. Loa có ở: phòng khách."

    updates = {}
    if action in ("on", "play"):
        updates["state"] = "on"
    elif action == "off":
        updates["state"] = "off"

    if volume >= 0:
        updates["volume"] = max(0, min(100, volume))
    if song:
        updates["playing"] = song

    return smart_home.update_device(device_id, **updates)


# ═══════════════════════════════════════════════════════════════
# TOOL: Get Device Status
# ═══════════════════════════════════════════════════════════════

@tool
def get_device_status(
    room: str = "",
    device_type: str = "",
) -> str:
    """Xem trạng thái thiết bị trong nhà.

    Args:
        room: Tên phòng (để trống = tất cả phòng).
        device_type: Loại thiết bị — "light", "ac", "tv", "lock", "speaker" (để trống = tất cả).

    Returns:
        Trạng thái thiết bị.
    """
    if room:
        room_key = ROOM_MAP.get(room.lower().strip(), room.lower().strip())
        devices = smart_home.get_devices_by_room(room_key)
    else:
        devices = smart_home.get_all_devices()

    if device_type:
        devices = {k: v for k, v in devices.items() if v["type"] == device_type}

    if not devices:
        return f"Không tìm thấy thiết bị phù hợp (room={room}, type={device_type})."

    lines = ["🏠 TRẠNG THÁI THIẾT BỊ:\n"]
    for dev_id, dev in devices.items():
        status = f"  • {dev['name']} [{dev['state']}]"
        if dev["type"] == "light":
            status += f" | 💡 {dev['brightness']}% {dev['color']}"
        elif dev["type"] == "ac":
            status += f" | 🌡️ {dev['temperature']}°C {dev['mode']}"
        elif dev["type"] == "tv":
            status += f" | 📺 {dev['channel']} vol:{dev['volume']}"
        elif dev["type"] == "speaker":
            playing = dev.get("playing") or "—"
            status += f" | 🎵 vol:{dev['volume']} {playing}"
        lines.append(status)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Danh sách tools để agent sử dụng
# ═══════════════════════════════════════════════════════════════

ALL_TOOLS = [
    control_light,
    control_ac,
    control_tv,
    control_lock,
    control_speaker,
    get_device_status,
]
