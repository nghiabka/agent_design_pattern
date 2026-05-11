"""
═══════════════════════════════════════════════════════════════════════
TOOLS — Các handler functions cho sub-agents
═══════════════════════════════════════════════════════════════════════

Mỗi specialized agent được trang bị một FunctionTool wrap một Python function.
Các function này simulate các hành động thực tế:

  • booking_handler: Xử lý đặt vé máy bay và khách sạn
  • info_handler:    Truy xuất thông tin chung (thời tiết, visa, giá cả...)
  • unclear_handler: Fallback cho yêu cầu không rõ ràng
"""

from langchain_core.tools import tool


# ═══════════════════════════════════════════════════════════════
# BOOKING HANDLER — Xử lý đặt chỗ
# ═══════════════════════════════════════════════════════════════

@tool
def booking_handler(
    booking_type: str,
    destination: str,
    date: str,
    passengers: int = 1,
) -> str:
    """Xử lý đặt vé máy bay hoặc khách sạn.

    Args:
        booking_type: Loại đặt chỗ — "flight" hoặc "hotel".
        destination: Điểm đến (thành phố/quốc gia).
        date: Ngày đặt (format: YYYY-MM-DD).
        passengers: Số hành khách / phòng (mặc định 1).

    Returns:
        Thông tin xác nhận đặt chỗ (simulated).
    """
    # ── Simulate booking logic ────────────────────────────────
    if booking_type.lower() == "flight":
        return (
            f"✈️ ĐẶT VÉ MÁY BAY THÀNH CÔNG!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Mã booking:  FL-{hash(destination + date) % 100000:05d}\n"
            f"  Điểm đến:    {destination}\n"
            f"  Ngày bay:    {date}\n"
            f"  Hành khách:  {passengers}\n"
            f"  Hạng ghế:    Economy\n"
            f"  Giá:         ${passengers * 450}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Trạng thái:  CONFIRMED ✓"
        )
    elif booking_type.lower() == "hotel":
        return (
            f"🏨 ĐẶT PHÒNG KHÁCH SẠN THÀNH CÔNG!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Mã booking:  HT-{hash(destination + date) % 100000:05d}\n"
            f"  Khách sạn:   Grand {destination} Hotel\n"
            f"  Check-in:    {date}\n"
            f"  Số phòng:    {passengers}\n"
            f"  Loại phòng:  Deluxe Double\n"
            f"  Giá/đêm:     ${passengers * 120}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Trạng thái:  CONFIRMED ✓"
        )
    else:
        return f"❌ Loại booking không hợp lệ: {booking_type}. Chỉ hỗ trợ 'flight' hoặc 'hotel'."


# ═══════════════════════════════════════════════════════════════
# INFO HANDLER — Truy xuất thông tin chung
# ═══════════════════════════════════════════════════════════════

@tool
def info_handler(
    query_type: str,
    location: str,
) -> str:
    """Truy xuất thông tin chung về du lịch, thời tiết, visa, giá cả.

    Args:
        query_type: Loại thông tin cần truy xuất — "weather", "visa", "attractions", "currency".
        location: Địa điểm cần tra cứu.

    Returns:
        Thông tin tra cứu (simulated).
    """
    # ── Simulate info retrieval ───────────────────────────────
    info_db = {
        "weather": (
            f"🌤️ THỜI TIẾT TẠI {location.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Nhiệt độ:    28°C — 33°C\n"
            f"  Độ ẩm:       65%\n"
            f"  Dự báo:      Nắng xen kẽ mây, chiều có mưa rào\n"
            f"  Gió:         Đông Nam 15 km/h\n"
            f"  UV Index:    7 (Cao)"
        ),
        "visa": (
            f"📋 THÔNG TIN VISA — {location.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  Loại visa:      Tourist Visa\n"
            f"  Thời hạn:       30 ngày\n"
            f"  Phí:            $50\n"
            f"  Xử lý:         3-5 ngày làm việc\n"
            f"  Yêu cầu:       Passport còn hạn ≥ 6 tháng\n"
            f"  E-Visa:         Có hỗ trợ ✓"
        ),
        "attractions": (
            f"🗺️ ĐIỂM THAM QUAN NỔI BẬT — {location.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  1. Trung tâm lịch sử cổ đại\n"
            f"  2. Bãi biển hoàng hôn\n"
            f"  3. Chợ đêm truyền thống\n"
            f"  4. Công viên quốc gia\n"
            f"  5. Bảo tàng nghệ thuật đương đại\n"
            f"  ⭐ Đánh giá trung bình: 4.5/5"
        ),
        "currency": (
            f"💱 TỶ GIÁ NGOẠI TỆ — {location.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  1 USD = 25,000 VND (tham khảo)\n"
            f"  Phương thức thanh toán phổ biến:\n"
            f"    • Tiền mặt nội tệ\n"
            f"    • Visa/Mastercard (nhà hàng, khách sạn)\n"
            f"    • ATM quốc tế có sẵn ✓"
        ),
    }

    result = info_db.get(query_type.lower())
    if result:
        return result
    else:
        return (
            f"ℹ️ THÔNG TIN VỀ {location.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  {location} là một điểm đến du lịch hấp dẫn.\n"
            f"  Liên hệ tổng đài 1900-xxxx để biết thêm chi tiết.\n"
            f"  (Loại truy vấn '{query_type}' chưa được hỗ trợ)"
        )


# ═══════════════════════════════════════════════════════════════
# UNCLEAR HANDLER — Fallback xử lý yêu cầu không rõ ràng
# ═══════════════════════════════════════════════════════════════

@tool
def unclear_handler(
    user_message: str,
) -> str:
    """Xử lý các yêu cầu không rõ ràng, không thuộc booking hay info.

    Args:
        user_message: Tin nhắn gốc của người dùng.

    Returns:
        Thông báo yêu cầu làm rõ.
    """
    return (
        f"🤔 YÊU CẦU CHƯA RÕ RÀNG\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Tin nhắn: \"{user_message}\"\n\n"
        f"  Tôi có thể hỗ trợ bạn với:\n"
        f"  ✈️  Đặt vé máy bay\n"
        f"  🏨 Đặt phòng khách sạn\n"
        f"  🌤️  Tra cứu thời tiết\n"
        f"  📋 Thông tin visa\n"
        f"  🗺️  Điểm tham quan\n"
        f"  💱 Tỷ giá ngoại tệ\n\n"
        f"  Vui lòng mô tả rõ hơn yêu cầu của bạn!"
    )
