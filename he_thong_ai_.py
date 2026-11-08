import time
import requests
from google import genai
from google.genai import types

# =====================================================================
# PHẦN 1: CẤU HÌNH HỆ THỐNG (CẬU CHỈ CẦN THAY ĐỔI THÔNG TIN TẠI ĐÂY)
# =====================================================================
# 📍 1. Nhập tên Tỉnh/Thành phố cậu muốn giám sát (Viết đúng tiếng Việt có dấu)
DIEN_TEN_TINH_TAI_DAY = "Tỉnh Thừa Thiên Huế" 

# 🔑 2. Điền các mã Token bảo mật của cậu vào đây
BLYNK_AUTH_TOKEN = "THAY_BẰNG_TOKEN_BLYNK_CỦA_CẬU"
GEMINI_API_KEY = "AQ.Ab8RN6ILOGfm-89bxVTwX-UQChTeWjHqZqoq4ty2A8RCBOfIxQ"

# 🌐 URL Server Blynk (Mặc định cho khu vực Châu Á)
BLYNK_SERVER_URL = "https://blynk.cloud"

# Khởi tạo kết nối với Gemini API
client = genai.Client(api_key=GEMINI_API_KEY)

# =====================================================================
# PHẦN 2: CÁC HÀM TỰ ĐỘNG THU THẬP DỮ LIỆU
# =====================================================================
def get_coordinates_from_province(province_name):
    """Tự động tra cứu Kinh độ/Vĩ độ dựa trên tên Tỉnh để đồng bộ trạm khí tượng"""
    url = f"https://openstreetmap.org{province_name}&format=json&limit=1"
    headers = {"User-Agent": "FloodWarningSystemAI/2.0 (contact@example.com)"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200 and len(response.json()) > 0:
            data = response.json()
            print(f"📌 Định vị thành công [{province_name}]: Vĩ độ {data[0]['lat']}, Kinh độ {data[0]['lon']}")
            return data[0]['lat'], data[0]['lon']
    except Exception as e:
        print(f"❌ Lỗi tự động tra cứu tọa độ: {e}")
    # Trả về tọa độ mặc định của Huế nếu gặp sự cố mạng
    print("⚠️ Không tra được tọa độ, sử dụng tọa độ mặc định (Thừa Thiên Huế).")
    return "16.4637", "107.5908"

def get_current_water_level_from_blynk():
    """Lấy số đo mực nước thực tế hiện tại từ cảm biến Blynk (Chân ảo V1)"""
    url = f"{BLYNK_SERVER_URL}/external/api/get?token={BLYNK_AUTH_TOKEN}&V1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return float(response.text)
    except Exception as e:
        print(f"⚠️ Lỗi kết nối Blynk Cloud: {e}")
    # Số giả lập (cm) để code không bị lỗi nếu cậu chưa bật phần cứng ESP32
    return 165.0 

def get_weather_forecast_from_satellite(lat, lon):
    """Tự động quét dự báo tổng lượng mưa tích lũy 3 ngày tới từ vệ tinh Open-Meteo"""
    url = f"https://open-meteo.com{lat}&longitude={lon}&hourly=precipitation&forecast_days=3"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            total_rain = sum(data["hourly"]["precipitation"])
            return f"Dự báo tổng lượng mưa tích lũy 3 ngày tới đạt {total_rain:.1f}mm."
    except Exception as e:
        print(f"⚠️ Lỗi kết nối trạm khí tượng vệ tinh: {e}")
    return "Không thu thập được dữ liệu lượng mưa tương lai."

def send_prediction_to_blynk_app(message):
    """Đẩy dòng chữ nhận định của AI Gemini về Chân ảo V2 hiển thị trên App Blynk"""
    url = f"{BLYNK_SERVER_URL}/external/api/update?token={BLYNK_AUTH_TOKEN}&V2={message}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("🚀 Đã đẩy kết quả dự báo của AI lên App Blynk thành công!")
    except Exception as e:
        print(f"❌ Không thể gửi dữ liệu lên Blynk: {e}")

# =====================================================================
# PHẦN 3: KÍCH HOẠT TRÍ TUỆ NHÂN TẠO GEMINI PHÂN TÍCH
# =====================================================================
def ask_gemini_to_predict_flood(location, level, weather):
    """Gửi toàn bộ gói dữ liệu (Vị trí + Mực nước + Khí tượng) cho Gemini"""
    
    system_instruction = """
    Bạn là một chuyên gia thủy văn cao cấp am hiểu sâu sắc về địa hình và lịch sử thiên tai tại Việt Nam.
    Khi nhận được tên một địa phương, bạn hãy tự động truy xuất kiến thức sẵn có của mình về đặc điểm địa lý 
    (sông ngòi, đập thủy điện, vùng trũng) và lịch sử bão lũ của chính địa phương đó để làm cơ sở phân tích.
    
    Nhiệm vụ: Đối chiếu mực nước hiện tại và dự báo mưa để đưa ra kịch bản lũ lụt thực tế nhất.
    YÊU CẦU BẮT BUỘC: Câu trả lời phải viết bằng tiếng Việt, cực kỳ ngắn gọn, cô đọng dưới 35 từ để hiển thị trọn vẹn trên widget Blynk Mobile.
    """
    
    prompt = f"""
    Hệ thống đang thực hiện giám sát thiên tai tại: {location}
    - Chỉ số cảm biến mực nước hiện tại: {level} cm.
    - Tình hình khí tượng: {weather}

    Dựa trên đặc thù địa hình và kinh nghiệm lịch sử bão lũ của {location}, hãy đưa ra dự báo nguy cơ ngập lụt ngay.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction)
        )
        return response.text.strip()
    except Exception as e:
        return f"Lỗi xử lý AI: {e}"

# =====================================================================
# PHẦN 4: VÒNG LẶP HỆ THỐNG TỰ ĐỘNG CHẠY 24/7 (MAIN LOOP)
# =====================================================================
if __name__ == "__main__":
    print("==========================================================")
    print(" HỆ THỐNG AI DỰ BÁO LŨ LỤT THỜI GIAN THỰC ĐANG KHỞI ĐỘNG... ")
    print("==========================================================")
    
    # Bước 1: Tra cứu tọa độ một lần duy nhất khi bật file
    latitude, longitude = get_coordinates_from_province(DIEN_TEN_TINH_TAI_DAY)
    
    while True:
        print(f"\n⏰ [{time.strftime('%H:%M:%S')}] Bắt đầu chu kỳ quét dữ liệu mới...")
        
        # Bước 2: Thu thập toàn bộ dữ liệu từ các nguồn
        water_level = get_current_water_level_from_blynk()
        weather_info = get_weather_forecast_from_satellite(latitude, longitude)
        
        print(f"📊 Dữ liệu Blynk (Mực nước): {water_level} cm")
        print(f"🌦️ Dữ liệu Khí tượng (Mưa): {weather_info}")
        
        # Bước 3: Đưa gói dữ liệu vào bộ não AI Gemini để phân tích ngữ cảnh
        ai_prediction = ask_gemini_to_predict_flood(DIEN_TEN_TINH_TAI_DAY, water_level, weather_info)
        print(f"🧠 AI Gemini dự báo: \"{ai_prediction}\"")
        
        # Bước 4: Xuất ngược kết quả cảnh báo ra màn hình điện thoại qua Blynk
        send_prediction_to_blynk_app(ai_prediction)
        
        # Bước 5: Treo máy chờ 15 phút (900 giây) trước khi bắt đầu chu kỳ tiếp theo
        print("😴 Hệ thống tạm nghỉ. Sẽ quét lại sau 15 phút...")
        time.sleep(900)
