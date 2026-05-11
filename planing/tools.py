"""
═══════════════════════════════════════════════════════════════════════
TOOLS — Simulated APIs cho Travel Planner Agent
═══════════════════════════════════════════════════════════════════════

Các tools mô phỏng API tra cứu thông tin du lịch:
  • search_flights     — Tìm chuyến bay
  • search_hotels      — Tìm khách sạn
  • get_weather        — Tra cứu thời tiết
  • get_attractions    — Điểm tham quan
  • estimate_budget    — Ước tính ngân sách
"""

from langchain_core.tools import tool


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Tìm chuyến bay từ điểm đi đến điểm đến.

    Args:
        origin: Thành phố xuất phát.
        destination: Thành phố đến.
        date: Ngày bay (YYYY-MM-DD).

    Returns:
        Danh sách chuyến bay tìm được.
    """
    flights = {
        "default": [
            {"airline": "Vietnam Airlines", "time": "06:00 - 08:30", "price": 2500000},
            {"airline": "VietJet Air", "time": "09:15 - 11:45", "price": 1800000},
            {"airline": "Bamboo Airways", "time": "14:00 - 16:30", "price": 2200000},
        ]
    }

    result = f"✈️ CHUYẾN BAY: {origin} → {destination} | Ngày: {date}\n"
    result += "━" * 50 + "\n"
    for f in flights["default"]:
        result += f"  • {f['airline']} | {f['time']} | {f['price']:,} VND\n"
    return result


@tool
def search_hotels(destination: str, checkin: str, nights: int) -> str:
    """Tìm khách sạn tại điểm đến.

    Args:
        destination: Thành phố.
        checkin: Ngày check-in (YYYY-MM-DD).
        nights: Số đêm ở.

    Returns:
        Danh sách khách sạn tìm được.
    """
    hotels = [
        {"name": f"Grand {destination} Hotel", "stars": 5, "price": 2800000, "rating": 4.8},
        {"name": f"{destination} Boutique Inn", "stars": 4, "price": 1500000, "rating": 4.5},
        {"name": f"Budget Stay {destination}", "stars": 3, "price": 650000, "rating": 4.1},
    ]

    result = f"🏨 KHÁCH SẠN: {destination} | Check-in: {checkin} | {nights} đêm\n"
    result += "━" * 50 + "\n"
    for h in hotels:
        total = h["price"] * nights
        result += f"  • {h['name']} ({'⭐' * h['stars']}) | {h['price']:,}/đêm | Tổng: {total:,} VND | ⭐ {h['rating']}\n"
    return result


@tool
def get_weather(destination: str, date: str) -> str:
    """Tra cứu dự báo thời tiết.

    Args:
        destination: Thành phố.
        date: Ngày cần tra cứu.

    Returns:
        Thông tin thời tiết.
    """
    return (
        f"🌤️ THỜI TIẾT: {destination} | {date}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Nhiệt độ: 27°C - 33°C\n"
        f"  Độ ẩm: 70%\n"
        f"  Dự báo: Nắng buổi sáng, chiều mưa rào\n"
        f"  Gợi ý: Mang áo mưa, kem chống nắng"
    )


@tool
def get_attractions(destination: str) -> str:
    """Tra cứu điểm tham quan nổi bật.

    Args:
        destination: Thành phố.

    Returns:
        Danh sách điểm tham quan.
    """
    return (
        f"🗺️ ĐIỂM THAM QUAN: {destination}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  1. Khu phố cổ — Miễn phí\n"
        f"  2. Bảo tàng lịch sử — 50,000 VND\n"
        f"  3. Công viên quốc gia — 100,000 VND\n"
        f"  4. Bãi biển hoàng hôn — Miễn phí\n"
        f"  5. Chợ đêm truyền thống — Miễn phí\n"
        f"  💡 Nên dành ít nhất 2-3 ngày để tham quan"
    )


@tool
def estimate_budget(
    flight_cost: int,
    hotel_cost: int,
    days: int,
    travelers: int,
) -> str:
    """Ước tính tổng ngân sách chuyến đi.

    Args:
        flight_cost: Chi phí vé máy bay (VND/người).
        hotel_cost: Chi phí khách sạn (VND tổng).
        days: Số ngày đi.
        travelers: Số người đi.

    Returns:
        Bảng ước tính ngân sách.
    """
    meals = 300000 * days * travelers
    transport = 200000 * days
    activities = 150000 * days * travelers
    total = (flight_cost * travelers) + hotel_cost + meals + transport + activities

    return (
        f"💰 ƯỚC TÍNH NGÂN SÁCH\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ✈️ Vé máy bay:  {flight_cost * travelers:>12,} VND ({travelers} người)\n"
        f"  🏨 Khách sạn:   {hotel_cost:>12,} VND\n"
        f"  🍜 Ăn uống:     {meals:>12,} VND ({days} ngày × {travelers} người)\n"
        f"  🚕 Di chuyển:   {transport:>12,} VND\n"
        f"  🎫 Hoạt động:   {activities:>12,} VND\n"
        f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  💵 TỔNG CỘNG:   {total:>12,} VND\n"
        f"  📊 Trung bình:  {total // travelers:>12,} VND/người"
    )


ALL_TOOLS = [search_flights, search_hotels, get_weather, get_attractions, estimate_budget]
