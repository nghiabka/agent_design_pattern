"""
═══════════════════════════════════════════════════════════════════════
SMART HOME SIMULATOR — Mô phỏng hệ thống nhà thông minh
═══════════════════════════════════════════════════════════════════════

Simulator quản lý trạng thái của tất cả thiết bị IoT trong nhà.
Đóng vai trò như một "backend" mà agent gọi tới qua tools.

Thiết bị hỗ trợ:
  💡 Đèn (Light)         — on/off, brightness, color
  🌡️ Điều hòa (AC)       — on/off, temperature, mode
  📺 TV                  — on/off, channel, volume
  🔒 Khóa cửa (Lock)     — lock/unlock
  🎵 Loa (Speaker)       — on/off, volume, song
"""

from rich.console import Console
from rich.table import Table

console = Console()


class SmartHomeSimulator:
    """Mô phỏng trạng thái nhà thông minh."""

    def __init__(self):
        """Khởi tạo tất cả thiết bị với trạng thái mặc định."""
        self.devices = {
            # ── Đèn ──────────────────────────────────────────
            "living_room_light": {
                "type": "light",
                "name": "Đèn phòng khách",
                "room": "living_room",
                "state": "on",
                "brightness": 80,
                "color": "warm_white",
            },
            "bedroom_light": {
                "type": "light",
                "name": "Đèn phòng ngủ",
                "room": "bedroom",
                "state": "off",
                "brightness": 50,
                "color": "warm_white",
            },
            "kitchen_light": {
                "type": "light",
                "name": "Đèn nhà bếp",
                "room": "kitchen",
                "state": "on",
                "brightness": 100,
                "color": "cool_white",
            },
            # ── Điều hòa ─────────────────────────────────────
            "living_room_ac": {
                "type": "ac",
                "name": "Điều hòa phòng khách",
                "room": "living_room",
                "state": "on",
                "temperature": 25,
                "mode": "cool",
            },
            "bedroom_ac": {
                "type": "ac",
                "name": "Điều hòa phòng ngủ",
                "room": "bedroom",
                "state": "off",
                "temperature": 26,
                "mode": "cool",
            },
            # ── TV ────────────────────────────────────────────
            "living_room_tv": {
                "type": "tv",
                "name": "TV phòng khách",
                "room": "living_room",
                "state": "on",
                "channel": "VTV1",
                "volume": 30,
            },
            # ── Khóa cửa ─────────────────────────────────────
            "front_door_lock": {
                "type": "lock",
                "name": "Khóa cửa chính",
                "room": "entrance",
                "state": "locked",
            },
            "garage_door": {
                "type": "lock",
                "name": "Cửa garage",
                "room": "garage",
                "state": "locked",
            },
            # ── Loa ──────────────────────────────────────────
            "living_room_speaker": {
                "type": "speaker",
                "name": "Loa phòng khách",
                "room": "living_room",
                "state": "off",
                "volume": 50,
                "playing": None,
            },
        }

        # Log hành động
        self.action_log: list[str] = []

    def get_device(self, device_id: str) -> dict | None:
        """Lấy thông tin thiết bị theo ID."""
        return self.devices.get(device_id)

    def get_all_devices(self) -> dict:
        """Lấy tất cả thiết bị."""
        return self.devices

    def get_devices_by_room(self, room: str) -> dict:
        """Lấy thiết bị theo phòng."""
        return {
            k: v for k, v in self.devices.items()
            if v["room"] == room
        }

    def update_device(self, device_id: str, **kwargs) -> str:
        """Cập nhật trạng thái thiết bị.

        Returns:
            Thông báo kết quả.
        """
        device = self.devices.get(device_id)
        if not device:
            return f"❌ Không tìm thấy thiết bị: {device_id}"

        changes = []
        for key, value in kwargs.items():
            if key in device:
                old = device[key]
                device[key] = value
                changes.append(f"{key}: {old} → {value}")

        if changes:
            log_entry = f"[{device['name']}] {', '.join(changes)}"
            self.action_log.append(log_entry)
            return f"✅ {device['name']}: {', '.join(changes)}"
        else:
            return f"⚠️ Không có thay đổi cho {device['name']}"

    def print_status(self):
        """In trạng thái tất cả thiết bị."""
        table = Table(
            title="🏠 Smart Home Status",
            border_style="cyan",
            show_lines=True,
        )
        table.add_column("Thiết bị", style="bold", width=25)
        table.add_column("Phòng", style="dim", width=15)
        table.add_column("Trạng thái", width=12)
        table.add_column("Chi tiết", width=30)

        for dev_id, dev in self.devices.items():
            # Trạng thái với màu
            state = dev["state"]
            if state in ("on", "unlocked"):
                state_str = f"[green]{state}[/green]"
            elif state in ("off", "locked"):
                state_str = f"[red]{state}[/red]"
            else:
                state_str = state

            # Chi tiết tùy loại
            details = []
            if dev["type"] == "light":
                details.append(f"💡 {dev['brightness']}% {dev['color']}")
            elif dev["type"] == "ac":
                details.append(f"🌡️ {dev['temperature']}°C {dev['mode']}")
            elif dev["type"] == "tv":
                details.append(f"📺 {dev['channel']} vol:{dev['volume']}")
            elif dev["type"] == "lock":
                details.append(f"🔒 {state}")
            elif dev["type"] == "speaker":
                playing = dev.get("playing") or "—"
                details.append(f"🎵 vol:{dev['volume']} {playing}")

            room_names = {
                "living_room": "Phòng khách",
                "bedroom": "Phòng ngủ",
                "kitchen": "Nhà bếp",
                "entrance": "Cửa chính",
                "garage": "Garage",
            }

            table.add_row(
                dev["name"],
                room_names.get(dev["room"], dev["room"]),
                state_str,
                ", ".join(details),
            )

        console.print(table)


# Singleton — toàn bộ agent dùng chung 1 instance
smart_home = SmartHomeSimulator()
