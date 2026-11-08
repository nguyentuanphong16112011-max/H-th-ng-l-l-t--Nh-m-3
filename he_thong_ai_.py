import time
import os
import requests
from google import genai
from google.genai import types

# --- CẤU HÌNH HỆ THỐNG RENDER ---
DIEN_TEN_TINH_MAC_DINH = "Tỉnh Thừa Thiên Huế"
BLYNK_AUTH_TOKEN = "THAY_BANG_TOKEN_BLYNK_CUA_CAU"
BLYNK_SERVER_URL = "https://blynk.cloud"

# Lấy mã bảo mật từ Environment Variables của Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ LỖI: Chưa cấu hình GEMINI_API_KEY trên Render!")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def get_coordinates(province_name):
    url = f"https://openstreetmap.org{province_name}&format=json&limit=1"
    headers = {"User-Agent": "FloodAI/2.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        if len(res) > 0: return res[0]['lat'], res[0]['lon']
    except: pass
    return "16.4637", "107.5908"

def get_water_level():
    url = f"{BLYNK_SERVER_URL}/external/api/get?token={BLYNK_AUTH_TOKEN}&V1"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200: return float(res.text)
    except: pass
    return 165.0

def get_weather(lat, lon):
    url = f"https://open-meteo.com{lat}&longitude={lon}&hourly=precipitation&forecast_days=3"
    try:
        res = requests.get(url, timeout=5).json()
        return f"Dự báo tổng lượng mưa tích lũy 3 ngày tới đạt {sum(res['hourly']['precipitation'])}mm."
    except: pass
    return "Không lấy được dữ liệu mưa."

def send_to_blynk(msg):
    url = f"{BLYNK_SERVER_URL}/external/api/update?token={BLYNK_AUTH_TOKEN}&V2={msg}"
    try: requests.get(url, timeout=5)
    except: pass

def ask_gemini(location, level, weather):
    sys_ins = "Bạn là chuyên gia thủy văn Việt Nam. Hãy đối chiếu mực nước và dự báo mưa để đưa ra kịch bản lũ lụt ngắn gọn dưới 35 từ bằng tiếng Việt hiển thị vừa màn hình Blynk."
    prompt = f"Trạm giám sát: {location}. Mực nước cảm biến: {level} cm. {weather}. Đưa ra dự báo ngay."
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=sys_ins)
        )
        return response.text.strip()
    except Exception as e:
        return f"Lỗi xử lý AI: {e}"

if __name__ == "__main__":
    print("🚀 Khởi động chu kỳ quét dữ liệu tự động...")
    current_location = DIEN_TEN_TINH_MAC_DINH
    url_location = f"{BLYNK_SERVER_URL}/external/api/get?token={BLYNK_AUTH_TOKEN}&V3"
    try:
        res = requests.get(url_location, timeout=5)
        if res.status_code == 200 and res.text.strip() != "":
            current_location = res.text.strip()
    except: pass
        
    lat, lon = get_coordinates(current_location)
    water_level = get_water_level()
    weather_info = get_weather(lat, lon)
    
    ai_prediction = ask_gemini(current_location, water_level, weather_info)
    print(f"📌 {current_location} | AI Dự báo: {ai_prediction}")
    
    send_to_blynk(ai_prediction)
    print("✅ Hoàn thành chu kỳ quét.")

