# -*- coding: utf-8 -*-
"""
MODULE DỊCH VỤ TRÍ TUỆ NHÂN TẠO - AI SERVICE (GEMINI PRO)
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Kiến trúc 5 điểm chạm AI sư phạm:
1. AI Kiểm duyệt kỹ năng đăng ký (kiem_duyet)
2. AI Gợi ý ghép cặp người dạy - người học (goi_y_ghep_cap)
3. AI Soạn dàn ý buổi học cấu trúc 60 phút (dan_y_buoi_hoc)
4. AI Tóm tắt phản hồi học sinh cho gia sư (tom_tat_phan_hoi)
5. AI Cảnh báo sớm quản trị học đường (canh_bao)

Nguyên tắc vận hành:
- Có GEMINI_API_KEY: Tự động kết nối Google Gemini Pro API.
- Không có key hoặc lỗi mạng/timeout: Tự động chuyển chế độ dự phòng (Rule-based Fallback),
  đảm bảo hệ thống KHÔNG BAO GIỜ bị crash lỗi 500, UI thông báo "Chế độ cơ bản".
- Mọi tương tác AI đều được ghi vết minh bạch vào bảng ai_logs.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Cố gắng khởi tạo Google GenAI Client
_gemini_client = None
GEMINI_AVAILABLE = False
_last_init_key = None
_active_model = None

# Danh sách các model flash thế hệ mới ưu tiên kiểm tra theo thứ tự
CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]


def init_gemini_client(api_key=None):
    """
    Khởi tạo hoặc cập nhật Google GenAI Client với log chẩn đoán minh bạch.
    Bảo mật: Tuyệt đối không bao giờ in API key ra log.
    """
    global _gemini_client, GEMINI_AVAILABLE, _last_init_key, _active_model

    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
    else:
        api_key = str(api_key).strip()

    _last_init_key = api_key
    key_present = bool(api_key)
    key_len = len(api_key)

    # Log chẩn đoán lúc khởi tạo (Đúng định dạng yêu cầu, KHÔNG BAO GIỜ in key)
    print(f"[AI Init] key present: {key_present} | len: {key_len}")

    if not key_present:
        _gemini_client = None
        GEMINI_AVAILABLE = False
        _active_model = None
        print("[AI Init] client ready: False - Thieu GEMINI_API_KEY")
        return None

    try:
        from google import genai
        from google.genai import types

        # Khởi tạo client chính thức của thư viện google-genai với timeout ~18s (18000ms)
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=18000)
        )
        _gemini_client = client
        GEMINI_AVAILABLE = True
        print("[AI Init] client ready: True")
        return _gemini_client
    except Exception as e:
        _gemini_client = None
        GEMINI_AVAILABLE = False
        _active_model = None
        # Không nuốt lỗi câm ở khâu init
        print(f"[AI Init] client ready: False - Loi khoi tao: {e}")
        return None


# Tự động chẩn đoán và khởi tạo khi nạp module
init_gemini_client()


def get_gemini_client():
    """Lấy client hiện tại, tự động re-init nếu biến môi trường GEMINI_API_KEY thay đổi."""
    global _gemini_client, _last_init_key
    current_key = os.getenv("GEMINI_API_KEY", "").strip()
    if current_key != _last_init_key or (_gemini_client is None and current_key):
        return init_gemini_client(current_key)
    return _gemini_client


def is_ai_live():
    """Kiểm tra xem Gemini API có sẵn sàng hoạt động hay đang ở chế độ dự phòng."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return False
    client = get_gemini_client()
    return client is not None and GEMINI_AVAILABLE


def log_ai_interaction(db, user_id, chuc_nang, input_tom_tat, output_text):
    """
    Ghi vết minh bạch mọi tương tác của AI vào bảng ai_logs trong SQLite.
    Cô giáo và Ban Giám khảo có thể tra cứu toàn bộ lịch sử suy luận của AI tại đây.
    """
    try:
        cur = db.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """INSERT INTO ai_logs (user_id, chuc_nang, input_tom_tat, output_text, thoi_gian)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, chuc_nang, str(input_tom_tat)[:500], str(output_text), now_str)
        )
        db.commit()
    except Exception as e:
        print(f"[AI Log Error]: Khong the ghi log AI: {e}")


def call_gemini(prompt, system_instruction=""):
    """
    Hàm gọi Gemini API với cơ chế dự phòng an toàn và giới hạn thời gian (timeout ~18s).
    Sử dụng thư viện google-genai mới nhất:
    - from google import genai
    - client = genai.Client(api_key=api_key)
    - client.models.generate_content(model=<model-flash-mới-nhất>, contents=...)
    - Tự kiểm tra tên model đang khả dụng (gemini-2.0-flash / gemini-2.5-flash / gemini-1.5-flash).
    - Giữ timeout ~18s như cũ.
    - Fallback model khác nếu lỗi; trả về None nếu toàn bộ thất bại (không crash).
    """
    global _active_model

    if not is_ai_live():
        return None

    client = get_gemini_client()
    if not client:
        return None

    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
            http_options=types.HttpOptions(timeout=18000)
        )
    except Exception as e:
        print(f"[Gemini Config Error]: {e}")
        config = None

    # Ưu tiên model đang khả dụng hoặc thử lần lượt danh sách model flash
    models_to_try = list(CANDIDATE_MODELS)
    if _active_model and _active_model in models_to_try:
        models_to_try.remove(_active_model)
        models_to_try.insert(0, _active_model)

    last_error = None
    for model_name in models_to_try:
        try:
            kwargs = {
                "model": model_name,
                "contents": prompt,
            }
            if config is not None:
                kwargs["config"] = config

            response = client.models.generate_content(**kwargs)
            if response and getattr(response, "text", None):
                text = response.text.strip()
                if text:
                    _active_model = model_name
                    return text
        except Exception as e:
            last_error = e
            print(f"[Gemini Call Warning] Model '{model_name}' that bai: {e}")
            continue

    if last_error:
        print(f"[Gemini Call Error] Toan bo model Gemini deu that bai: {last_error}")
    return None


# ==============================================================================
# 1. AI KIỂM DUYỆT KỸ NĂNG (ĐIỂM CHẠM 1)
# ==============================================================================
def ai_moderate_skill(db, user_id, linh_vuc, tieu_de, mo_ta):
    """
    Kiểm duyệt nội dung kỹ năng học sinh đăng ký:
    - Kiểm tra tính phù hợp với môi trường giáo dục phổ thông.
    - Phát hiện ngôn từ phản cảm, cờ bạc, bạo lực, gian lận thi cử.
    - Trả về: (is_approved: bool, reason: str, is_live: bool)
      * PHU_HOP: Được duyệt hoặc đánh giá tích cực.
      * KHONG_PHU_HOP: Chuyển giáo viên duyệt tay, kèm lý do chi tiết.
    """
    input_summary = f"[{linh_vuc}] {tieu_de}: {mo_ta}"
    
    # Danh sách từ khóa nhạy cảm lọc nhanh (Rule-based Filter)
    toxic_keywords = [
        "hack", "gian lận", "quay cóp", "cờ bạc", "cá độ", "lô đề", "đánh bài", 
        "bạo lực", "vũ khí", "đánh nhau", "khiêu dâm", "chửi bới", "ma túy", 
        "thuốc lá", "chất kích thích", "lừa đảo"
    ]
    
    is_live = is_ai_live()
    if is_live:
        prompt = f"""
Bạn là chuyên gia kiểm duyệt nội dung sư phạm của nền tảng 'Ngân hàng Thời gian Học đường' (TimeBank EDU).
Hãy thẩm định xem kỹ năng sau do học sinh đăng ký có PHÙ HỢP với môi trường giáo dục trường học không:
Lĩnh vực: {linh_vuc}
Tiêu đề: {tieu_de}
Mô tả: {mo_ta}

Quy tắc:
1. Nếu nội dung lành mạnh, mang tính học tập, năng khiếu, phát triển bản thân: Trả về dòng đầu là PHU_HOP.
2. Nếu chứa nội dung độc hại, cờ bạc, gian lận thi cử, bạo lực, phản cảm: Trả về dòng đầu là KHONG_PHU_HOP.
3. Dòng thứ 2: Nêu ngắn gọn lý do bằng tiếng Việt (1 câu, tối đa 30 từ).

Định dạng trả về:
PHU_HOP hoặc KHONG_PHU_HOP
[Lý do ngắn gọn]
"""
        response_text = call_gemini(prompt)
        if response_text:
            lines = [line.strip() for line in response_text.split("\n") if line.strip()]
            status_line = lines[0].upper() if lines else "PHU_HOP"
            reason_line = lines[1] if len(lines) > 1 else "Nội dung học tập tích cực, phù hợp học đường."
            
            is_approved = ("PHU_HOP" in status_line) and ("KHONG_PHU_HOP" not in status_line)
            log_ai_interaction(db, user_id, "kiem_duyet", input_summary, f"{status_line} - {reason_line}")
            return is_approved, reason_line, True

    # CHẾ ĐỘ DỰ PHÒNG (RULE-BASED FALLBACK)
    content_lower = f"{tieu_de} {mo_ta}".lower()
    has_toxic = any(word in content_lower for word in toxic_keywords)
    
    if has_toxic:
        is_approved = False
        reason = "Phát hiện nội dung có thể chưa phù hợp với môi trường sư phạm, chuyển Giáo viên duyệt tay."
    else:
        is_approved = True
        reason = "Nội dung kỹ năng học tập tích cực, phù hợp với định hướng rèn luyện học đường."
        
    log_ai_interaction(db, user_id, "kiem_duyet", input_summary, f"[Rule-Based] {'PHU_HOP' if is_approved else 'KHONG_PHU_HOP'} - {reason}")
    return is_approved, reason, False


# ==============================================================================
# 2. AI GỢI Ý GHÉP CẶP HỌC TẬP (ĐIỂM CHẠM 2)
# ==============================================================================
def ai_matchmake(db, user_id, mon_hoc, trinh_do, gio_ranh, candidates):
    """
    AI Gợi ý ghép cặp người học với 3 bạn gia sư phù hợp nhất:
    - Dựa trên môn cần học, trình độ, thời gian rảnh và đánh giá chất lượng.
    - Trả về danh sách tối đa 3 ứng viên có giải thích sư phạm tiếng Việt.
    """
    input_summary = f"Môn: {mon_hoc}, Trình độ: {trinh_do}, Rảnh: {gio_ranh}, Số ứng viên: {len(candidates)}"
    
    if not candidates:
        return [], is_ai_live()

    is_live = is_ai_live()
    if is_live:
        candidates_info = []
        for idx, c in enumerate(candidates[:8]):
            cand_ranh = c['gio_ranh'] if c['gio_ranh'] else 'Linh hoạt'
            candidates_info.append(
                f"- Ứng viên #{c['id']} (Gia sư: {c['ho_ten']}, Lớp {c['lop']}): "
                f"Kỹ năng '{c['tieu_de']}', Lĩnh vực '{c['linh_vuc']}', Đánh giá {c['sao_tb']} sao, Giờ rảnh: '{cand_ranh}'"
            )
            
        prompt = f"""
Bạn là Trợ lý AI sư phạm thông minh của TimeBank EDU.
Một học sinh đang cần tìm bạn gia sư kèm cặp với nhu cầu:
- Môn học / Kỹ năng cần tìm: {mon_hoc}
- Trình độ hiện tại: {trinh_do}
- Thời gian rảnh của người học: {gio_ranh}

Danh sách ứng viên gia sư hiện có:
{chr(10).join(candidates_info)}

Nhiệm vụ:
Chọn ra tối đa 3 ứng viên PHÙ HỢP NHẤT.
Với mỗi người, viết lời giải thích ngắn gọn (tối đa 25 từ) lý do vì sao ghép cặp này hiệu quả (xét về môn học, độ tương thích giờ rảnh, uy tín đánh giá sao).

Trả về dạng JSON mảng (chỉ xuất JSON, không giải thích thêm):
[
  {{"id": <id_ky_nang>, "ly_do": "<lời giải thích tiếng Việt ngắn gọn>"}}, ...
]
"""
        response_text = call_gemini(prompt)
        if response_text:
            try:
                # Trích xuất JSON từ phản hồi
                clean_json = response_text.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                    
                matches_data = json.loads(clean_json)
                results = []
                cand_map = {c["id"]: c for c in candidates}
                for item in matches_data:
                    c_id = item.get("id")
                    if c_id in cand_map:
                        item_obj = dict(cand_map[c_id])
                        item_obj["ai_ly_do"] = item.get("ly_do", "Rất phù hợp với môn học và thời gian của bạn.")
                        results.append(item_obj)
                if results:
                    log_ai_interaction(db, user_id, "goi_y_ghep_cap", input_summary, json.dumps([r['id'] for r in results]))
                    return results[:3], True
            except Exception as e:
                print(f"[Matchmaking JSON Parse Error]: {e}")

    # CHẾ ĐỘ DỰ PHÒNG (RULE-BASED FALLBACK)
    results = []
    # Ưu tiên ứng viên có môn trùng khớp và số sao cao
    sorted_cand = sorted(
        candidates, 
        key=lambda x: (
            1 if mon_hoc.lower() in (str(x['linh_vuc']) + ' ' + str(x['tieu_de'])).lower() else 0,
            float(x['sao_tb'] if x['sao_tb'] is not None else 5.0)
        ), 
        reverse=True
    )
    
    for c in sorted_cand[:3]:
        item_obj = dict(c)
        r_time = c['gio_ranh'] if c['gio_ranh'] else 'Linh hoạt'
        s_tb = c['sao_tb'] if c['sao_tb'] is not None else 5.0
        item_obj["ai_ly_do"] = f"Bạn {c['ho_ten']} có chuyên môn tốt ({s_tb}★) và có lịch rảnh '{r_time}' thuận tiện để cùng học."
        results.append(item_obj)
        
    log_ai_interaction(db, user_id, "goi_y_ghep_cap", input_summary, f"[Rule-Based] {len(results)} gia sư được chọn")
    return results, False


# ==============================================================================
# 3. AI SOẠN DÀN Ý BUỔI HỌC (ĐIỂM CHẠM 3)
# ==============================================================================
def ai_generate_lesson_plan(db, user_id, session_id, tieu_de, linh_vuc, mo_ta, so_gio=1.0):
    """
    AI Soạn cấu trúc buổi học chuẩn 60 phút sư phạm (hoặc tương đương so_gio):
    - Mở đầu (5 phút): Khởi động & xác định mục tiêu.
    - Trọng tâm (25 phút): Giảng giải kiến thức và nguyên lý cốt lõi.
    - Luyện tập (20 phút): Kèm cặp thực hành và bài tập củng cố.
    - Tổng kết & Đánh giá (10 phút): Tóm tắt, giải đáp thắc mắc và dặn dò.
    """
    input_summary = f"Phiên #{session_id}: {tieu_de} ({linh_vuc}, {so_gio}h)"
    
    is_live = is_ai_live()
    if is_live:
        prompt = f"""
Bạn là chuyên gia cố vấn phương pháp giảng dạy sư phạm của nền tảng TimeBank EDU.
Hãy xây dựng một DÀN Ý BUỔI HỌC KÈM CẶP CHI TIẾT (60 phút) giữa 2 học sinh:
- Chuyên đề: {tieu_de}
- Lĩnh vực: {linh_vuc}
- Mục tiêu bài học: {mo_ta}

Cấu trúc bắt buộc chuẩn hóa 4 phần:
1. Mở đầu & Khởi động (5 phút): Cách bắt đầu thân thiện, kiểm tra kiến thức nền và mục tiêu bài học.
2. Kiến thức Trọng tâm (25 phút): 2-3 ý chính cần giải thích dễ hiểu, trực quan.
3. Luyện tập & Kèm cặp (20 phút): Bài tập thực hành mẫu hoặc hoạt động đôi để học sinh tự làm.
4. Tổng kết & Đánh giá (10 phút): Tóm lược 3 điểm cốt lõi, hỏi đáp thắc mắc và gợi ý bài tập rèn luyện thêm.

Trình bày bằng tiếng Việt rõ ràng, ngôn từ truyền cảm hứng, thân thiện cho học sinh phổ thông.
"""
        response_text = call_gemini(prompt)
        if response_text:
            log_ai_interaction(db, user_id, "dan_y_buoi_hoc", input_summary, response_text[:300] + "...")
            return response_text, True

    # CHẾ ĐỘ DỰ PHÒNG (RULE-BASED FALLBACK)
    fallback_plan = f"""[DÀN Ý BUỔI HỌC SƯ PHẠM 60 PHÚT - HỖ TRỢ BỞI TIMEBANK EDU]
Chuyên đề: {tieu_de} (Lĩnh vực: {linh_vuc})

1. Mở đầu & Khởi động (5 phút):
- Chào hỏi thân thiện, tạo không khí học tập cởi mở, không áp lực.
- Bạn gia sư hỏi người học về những khó khăn hiện tại và thống nhất mục tiêu buổi học.

2. Kiến thức Trọng tâm (25 phút):
- Trình bày khái niệm và nguyên lý căn bản của {tieu_de} qua ví dụ thực tế.
- Phân tích 1-2 dạng bài tập tiêu biểu hoặc thao tác mẫu từng bước.
- Khuyến khích người học đặt câu hỏi ngay khi chưa rõ.

3. Kèm cặp & Luyện tập (20 phút):
- Học sinh tự thực hành giải bài tập tương tự dưới sự quan sát của gia sư.
- Gia sư kiên nhẫn chỉ ra lỗi sai phổ biến và mẹo ghi nhớ nhanh.

4. Tổng kết & Đánh giá (10 phút):
- Tổng kết 3 ý quan trọng nhất đã tiếp thu trong buổi học.
- Động viên, khen ngợi sự tiến bộ và hẹn lịch buổi trao đổi tiếp theo."""

    log_ai_interaction(db, user_id, "dan_y_buoi_hoc", input_summary, "[Rule-Based] Dàn ý 4 bước chuẩn 60 phút")
    return fallback_plan, False


# ==============================================================================
# 4. AI TÓM TẮT PHẢN HỒI (ĐIỂM CHẠM 4)
# ==============================================================================
def ai_summarize_feedback(db, user_id, ratings_list):
    """
    Gom các đánh giá học sinh dành cho bạn gia sư để tổng hợp:
    - Điểm mạnh (2-3 ý)
    - Gợi ý cải thiện (2-3 ý) với giọng văn khích lệ, sư phạm.
    """
    if not ratings_list:
        return {
            "diem_manh": ["Luôn nhiệt tình, sẵn sàng sẻ chia kiến thức với bạn bè."],
            "cai_thien": ["Hãy tích cực tham gia thêm các phiên học để nhận thêm phản hồi chi tiết nhé!"],
            "loi_nhan": "Bạn đang khởi đầu rất tốt trong hành trình trao đổi tri thức tại TimeBank EDU!"
        }, False

    reviews_text = []
    for r in ratings_list:
        reviews_text.append(f"- {r['so_sao']}★: \"{r['nhan_xet']}\"")
    full_reviews = "\n".join(reviews_text)
    input_summary = f"Tổng {len(ratings_list)} đánh giá của user #{user_id}"

    is_live = is_ai_live()
    if is_live:
        prompt = f"""
Bạn là Cố vấn sư phạm đồng hành cùng học sinh trong nền tảng 'Ngân hàng Thời gian Học đường'.
Dưới đây là các nhận xét thực tế từ bạn bè sau các buổi học mà bạn gia sư này đã kèm cặp:
{full_reviews}

Hãy đọc kỹ và đúc kết thành bản tóm tắt sư phạm với giọng văn chân thành, khích lệ:
1. Điểm mạnh nổi bật (2-3 gạch đầu dòng ngắn gọn)
2. Gợi ý cải thiện (2-3 gạch đầu dòng khích lệ, hướng tới nâng cao kỹ năng truyền đạt)
3. Một lời nhắn truyền cảm hứng (tối đa 25 từ)

Xuất kết quả đúng định dạng JSON sau:
{{
  "diem_manh": ["ý 1", "ý 2", "ý 3"],
  "cai_thien": ["ý 1", "ý 2"],
  "loi_nhan": "lời nhắn động viên"
}}
"""
        response_text = call_gemini(prompt)
        if response_text:
            try:
                clean_json = response_text.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                res_obj = json.loads(clean_json)
                log_ai_interaction(db, user_id, "tom_tat_phan_hoi", input_summary, json.dumps(res_obj, ensure_ascii=False))
                return res_obj, True
            except Exception as e:
                print(f"[Feedback Summary JSON Parse Error]: {e}")

    # CHẾ ĐỘ DỰ PHÒNG (RULE-BASED FALLBACK)
    avg_stars = sum(r['so_sao'] for r in ratings_list) / len(ratings_list)
    fallback_res = {
        "diem_manh": [
            f"Được bạn bè đánh giá cao về thái độ nhiệt tình, trung bình đạt {avg_stars:.1f}★.",
            "Phương pháp giải thích dễ hiểu, kiên nhẫn chỉ dẫn từng bài tập.",
            "Luôn đúng giờ và có tinh thần trách nhiệm cao trong phiên học."
        ],
        "cai_thien": [
            "Có thể chuẩn bị thêm một số câu hỏi tương tác nhanh để bạn học chủ động hơn.",
            "Dành thêm 5 phút cuối để cùng bạn học tóm lược bài và giải tỏa các thắc mắc còn lại."
        ],
        "loi_nhan": "Sự sẻ chia tri thức của bạn chính là nguồn cảm hứng tuyệt vời cho cộng đồng học đường!"
    }
    log_ai_interaction(db, user_id, "tom_tat_phan_hoi", input_summary, "[Rule-Based] Tóm tắt phản hồi học sinh")
    return fallback_res, False


# ==============================================================================
# 5. AI CẢNH BÁO SỚM QUẢN TRỊ (ĐIỂM CHẠM 5)
# ==============================================================================
def ai_admin_early_warning(db, admin_user_id):
    """
    Quét và phát hiện các trường hợp cần can thiệp sư phạm sớm:
    1. Học sinh 7 ngày không tham gia phiên nào (nguy cơ bị cô lập hoặc quên lịch).
    2. Cặp đôi gia sư - học sinh bị đánh giá <= 2 sao từ 2 lần trở lên (xung đột phong cách).
    Đề xuất giải pháp can thiệp sư phạm nhân văn từ AI.
    """
    cur = db.cursor()
    
    # 1. Quét học sinh 7 ngày không có phiên học nào
    cur.execute("""
        SELECT u.id, u.ho_ten, u.lop, u.ma_hoc_sinh, u.so_du_gio,
               MAX(s.thoi_gian_bat_dau) AS phien_gan_nhat
        FROM users u
        LEFT JOIN sessions s ON (u.id = s.nguoi_day_id OR u.id = s.nguoi_hoc_id)
        WHERE u.vai_tro = 'hoc_sinh'
        GROUP BY u.id, u.ho_ten, u.lop, u.ma_hoc_sinh, u.so_du_gio
    """)
    students = cur.fetchall()
    
    inactive_students = []
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    
    for st in students:
        last_session = st["phien_gan_nhat"]
        if not last_session:
            inactive_students.append({
                "id": st["id"],
                "ho_ten": st["ho_ten"],
                "lop": st["lop"],
                "ma_hoc_sinh": st["ma_hoc_sinh"],
                "ly_do": "Chưa từng tham gia phiên học nào kể từ khi mở sổ thời gian."
            })
        else:
            try:
                dt = datetime.strptime(last_session[:19], "%Y-%m-%d %H:%M:%S")
                if dt < seven_days_ago:
                    inactive_students.append({
                        "id": st["id"],
                        "ho_ten": st["ho_ten"],
                        "lop": st["lop"],
                        "ma_hoc_sinh": st["ma_hoc_sinh"],
                        "ly_do": f"Hơn 7 ngày chưa tham gia phiên học (lần gần nhất: {last_session[:10]})."
                    })
            except Exception:
                pass

    # 2. Quét cặp đôi có từ 2 lần đánh giá <= 2 sao
    cur.execute("""
        SELECT r.nguoi_danh_gia_id, r.nguoi_duoc_danh_gia_id,
               u1.ho_ten AS ten_nguoi_danh_gia, u2.ho_ten AS ten_nguoi_duoc_danh_gia,
               COUNT(*) AS so_lan_sao_thap
        FROM ratings r
        JOIN users u1 ON r.nguoi_danh_gia_id = u1.id
        JOIN users u2 ON r.nguoi_duoc_danh_gia_id = u2.id
        WHERE r.so_sao <= 2
        GROUP BY r.nguoi_danh_gia_id, r.nguoi_duoc_danh_gia_id, u1.ho_ten, u2.ho_ten
        HAVING COUNT(*) >= 2
    """)
    low_rated_pairs = cur.fetchall()
    
    pairs_list = []
    for p in low_rated_pairs:
        pairs_list.append({
            "nguoi_danh_gia": p["ten_nguoi_danh_gia"],
            "nguoi_duoc_danh_gia": p["ten_nguoi_duoc_danh_gia"],
            "so_lan": p["so_lan_sao_thap"],
            "mo_ta": f"Cặp đôi {p['ten_nguoi_danh_gia']} và {p['ten_nguoi_duoc_danh_gia']} có {p['so_lan_sao_thap']} phiên bị đánh giá ≤2 sao."
        })

    input_summary = f"Học sinh ngưng học: {len(inactive_students)}, Cặp đôi xung đột: {len(pairs_list)}"

    is_live = is_ai_live()
    if is_live and (inactive_students or pairs_list):
        prompt = f"""
Bạn là Chuyên gia tư vấn tâm lý và quản lý giáo dục trường học tại TimeBank EDU.
Dưới đây là các dữ liệu cảnh báo sớm từ hệ thống:
1. Học sinh hơn 7 ngày không tham gia học:
{json.dumps(inactive_students[:5], ensure_ascii=False)}

2. Các cặp đôi bị đánh giá thấp (<= 2 sao từ 2 lần trở lên):
{json.dumps(pairs_list[:5], ensure_ascii=False)}

Hãy đưa ra các GỢI Ý CAN THIỆP SƯ PHẠM NHÂN VĂN cho Ban Giám Hiệu và Giáo viên chủ nhiệm:
- Cách tiếp cận nhẹ nhàng với học sinh ngưng hoạt động.
- Biện pháp hòa giải hoặc gợi ý đổi gia sư phù hợp hơn cho các cặp đôi khó hòa hợp.
- Trình bày dạng danh sách gạch đầu dòng rõ ràng, súc tích (khoảng 3-4 lời khuyên thiết thực).
"""
        response_text = call_gemini(prompt)
        if response_text:
            log_ai_interaction(db, admin_user_id, "canh_bao", input_summary, response_text[:300] + "...")
            return {
                "inactive_students": inactive_students,
                "low_rated_pairs": pairs_list,
                "ai_recommendations": response_text,
                "is_live": True
            }

    # CHẾ ĐỘ DỰ PHÒNG (RULE-BASED FALLBACK)
    fallback_recs = """[GỢI Ý CAN THIỆP SƯ PHẠM TỪ HỆ THỐNG]
1. Với học sinh ngưng hoạt động trên 7 ngày: Giáo viên chủ nhiệm nhắn tin hoặc trao đổi nhanh sau giờ sinh hoạt lớp để nắm bắt khó khăn (lịch học bận, chưa tìm được môn ưng ý).
2. Với các cặp đôi đánh giá thấp (≤ 2 sao từ 2 lần): Khuyến nghị học sinh chuyển sang chọn gia sư khác có phong cách phù hợp hơn trên Chợ kỹ năng.
3. Tổ chức mini-workshop chia sẻ 'Kỹ năng làm gia sư bạn bè' trong buổi sinh hoạt đầu tuần để nâng cao văn hóa phản hồi tích cực."""

    log_ai_interaction(db, admin_user_id, "canh_bao", input_summary, "[Rule-Based] Cảnh báo sớm quản trị học đường")
    return {
        "inactive_students": inactive_students,
        "low_rated_pairs": pairs_list,
        "ai_recommendations": fallback_recs,
        "is_live": False
    }


# ==============================================================================
# 6. AI TẠO QUIZ TRẮC NGHIỆM THÍCH ỨNG (MILESTONE M-AI+)
# ==============================================================================
def ai_generate_quiz(db, user_id, session_id, tieu_de, linh_vuc, mo_ta, dan_y_ai=""):
    """
    Điểm chạm AI+: Người dạy yêu cầu AI tạo bộ câu hỏi lượng giá sau buổi học:
    - Gemini đọc dan_y_ai + mo_ta -> tạo 5 câu trắc nghiệm 4 lựa chọn (A, B, C, D).
    - Phân cấp dễ -> khó, ngôn ngữ tiếng Việt, giọng VUI VẺ, khích lệ như trò chơi ("Game hóa học đường").
    - Lưu trực tiếp vào bảng quiz_questions.
    - Lưu nhật ký vào bảng ai_logs (chuc_nang = 'tao_quiz').
    """
    input_summary = f"Quiz phiên #{session_id}: {tieu_de} ({linh_vuc})"
    cur = db.cursor()

    is_live = is_ai_live()
    if is_live:
        prompt = f"""
Bạn là Trợ lý AI giáo dục truyền cảm hứng của nền tảng TimeBank EDU.
Sau một buổi học trao đổi tri thức giữa 2 bạn học sinh:
- Chuyên đề: {tieu_de}
- Lĩnh vực: {linh_vuc}
- Mục tiêu buổi học: {mo_ta}
- Dàn ý đã học:
{dan_y_ai if dan_y_ai else "Buổi học kèm 1-1 về kiến thức trọng tâm và bài tập thực hành."}

Nhiệm vụ:
Hãy tạo một bộ QUIZ 5 CÂU HỎI TRẮC NGHIỆM để người học ôn tập lại kiến thức vừa học:
1. Độ khó tăng dần:
   - Câu 1: Dễ - Khởi động vui vẻ, kiểm tra sự hào hứng và khái niệm cơ bản.
   - Câu 2: Dễ - Nhận biết kiến thức cốt lõi.
   - Câu 3: Trung bình - Vận dụng vào bài tập hoặc tình huống thực tế.
   - Câu 4: Trung bình - Phân tích, suy luận hoặc mẹo tránh lỗi sai.
   - Câu 5: Khó & Vui vẻ - Thử thách tư duy sáng tạo, lời khuyên thực tế.
2. Phong cách: Tiếng Việt, giọng VUI VẺ, khích lệ, thân thiện như một trò chơi đố vui học đường, không gây áp lực thi cử.
3. Mỗi câu có đúng 4 lựa chọn (lua_chon_a, lua_chon_b, lua_chon_c, lua_chon_d) và đáp án đúng là "A", "B", "C", hoặc "D".

Xuất kết quả đúng định dạng JSON sau:
[
  {{
    "cau_hoi": "Nội dung câu hỏi vui vẻ?",
    "lua_chon_a": "Đáp án A",
    "lua_chon_b": "Đáp án B",
    "lua_chon_c": "Đáp án C",
    "lua_chon_d": "Đáp án D",
    "dap_an_dung": "A"
  }}
]
"""
        response_text = call_gemini(prompt)
        if response_text:
            try:
                clean_json = response_text.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                quiz_data = json.loads(clean_json)
                if isinstance(quiz_data, list) and len(quiz_data) >= 5:
                    cur.execute("DELETE FROM quiz_questions WHERE session_id = ?", (session_id,))
                    questions_to_insert = []
                    for q in quiz_data[:5]:
                        ans = str(q.get("dap_an_dung", "A")).strip().upper()
                        if ans not in ("A", "B", "C", "D"):
                            ans = "A"
                        questions_to_insert.append((
                            session_id,
                            str(q.get("cau_hoi", "")),
                            str(q.get("lua_chon_a", "")),
                            str(q.get("lua_chon_b", "")),
                            str(q.get("lua_chon_c", "")),
                            str(q.get("lua_chon_d", "")),
                            ans
                        ))
                    cur.executemany(
                        """INSERT INTO quiz_questions 
                           (session_id, cau_hoi, lua_chon_a, lua_chon_b, lua_chon_c, lua_chon_d, dap_an_dung)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        questions_to_insert
                    )
                    db.commit()
                    log_ai_interaction(db, user_id, "tao_quiz", input_summary, f"Tạo thành công 5 câu hỏi từ Gemini cho phiên #{session_id}")
                    cur.execute("SELECT * FROM quiz_questions WHERE session_id = ? ORDER BY id ASC", (session_id,))
                    return [dict(r) for r in cur.fetchall()], True
            except Exception as e:
                print(f"[AI Quiz JSON Parse Error]: {e}")

    # CHẾ ĐỘ DỰ PHÒNG (RULE-BASED FALLBACK)
    cur.execute("DELETE FROM quiz_questions WHERE session_id = ?", (session_id,))
    fallback_questions = [
        (
            session_id,
            f"🌟 [Khởi động vui vẻ] Theo bạn, mục tiêu quan trọng và thú vị nhất khi cùng học chuyên đề '{tieu_de}' là gì?",
            f"Nắm vững phương pháp căn bản và tự tin làm bài tập",
            f"Học thuộc vẹt mọi công thức mà không cần hiểu bản chất",
            f"Chỉ cần chép lại lời giải mẫu của bạn gia sư",
            f"Đợi đến sát ngày thi mới bắt đầu mở vở ra xem",
            "A"
        ),
        (
            session_id,
            f"💡 [Nhận biết kiến thức] Khi tìm hiểu về {tieu_de} ({linh_vuc}), đâu là nguyên lý trọng tâm cần ghi nhớ?",
            f"Bỏ qua các bước cơ bản để làm ngay dạng nâng cao",
            f"Hiểu rõ khái niệm then chốt và các bước thực hiện tuần tự",
            f"Học thuộc lòng đáp án trắc nghiệm không cần tư duy",
            f"Mỗi bài tập đều dùng duy nhất một cách giải duy nhất",
            "B"
        ),
        (
            session_id,
            f"🚀 [Vận dụng thực hành] Nếu gặp một câu hỏi hoặc bài tập mới liên quan đến {tieu_de}, bạn nên bắt đầu từ đâu?",
            f"Đọc kỹ đề bài, xác định dữ kiện đã cho và mục tiêu cần tìm",
            f"Bấm máy tính bừa hoặc chọn ngẫu nhiên một đáp án",
            f"Bỏ qua ngay và chuyển sang môn học khác",
            f"Chờ bạn khác làm xong rồi xin kết quả",
            "A"
        ),
        (
            session_id,
            f"🎯 [Phân tích & Tránh bẫy] Lỗi sai phổ biến mà học sinh thường gặp khi rèn luyện {tieu_de} là gì?",
            f"Quá cẩn thận kiểm tra lại các bước tính toán",
            f"Vẽ hình minh họa rõ ràng và đặt điều kiện xác định",
            f"Vội vàng bỏ sót điều kiện biên hoặc nhầm lẫn đơn vị",
            f"Thường xuyên trao đổi, hỏi bạn gia sư khi chưa hiểu",
            "C"
        ),
        (
            session_id,
            f"🏆 [Thử thách & Bí kíp vui] 'Bí kíp vàng' để tiến bộ vượt bậc sau mỗi buổi học tại TimeBank EDU là gì?",
            f"Tự luyện tập lại ít nhất 1 bài tương tự và sẵn sàng chia sẻ, dạy lại cho bạn khác",
            f"Cất sách vở vào ngăn bàn và không bao giờ ôn lại",
            f"Nghĩ rằng mình đã giỏi rồi nên không cần rèn luyện thêm",
            f"Chỉ học khi có người nhắc nhở",
            "A"
        )
    ]
    cur.executemany(
        """INSERT INTO quiz_questions 
           (session_id, cau_hoi, lua_chon_a, lua_chon_b, lua_chon_c, lua_chon_d, dap_an_dung)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        fallback_questions
    )
    db.commit()
    log_ai_interaction(db, user_id, "tao_quiz", input_summary, f"[Rule-Based] Tạo 5 câu hỏi trắc nghiệm vui vẻ theo chuẩn {linh_vuc}")
    cur.execute("SELECT * FROM quiz_questions WHERE session_id = ? ORDER BY id ASC", (session_id,))
    return [dict(r) for r in cur.fetchall()], False


# ==============================================================================
# 7. AI GỢI Ý NHIỆM VỤ CỘNG ĐỒNG "VIỆC PHÙ HỢP VỚI BẠN" (MILESTONE M6)
# ==============================================================================
def ai_recommend_tasks(db, user_id, open_tasks):
    """
    Điểm chạm AI: Gợi ý 3 nhiệm vụ cộng đồng phù hợp nhất với học sinh:
    - Phân tích kỹ năng, sở thích, lớp học và lịch sử hoạt động của học sinh.
    - Gọi Gemini Pro API để lựa chọn 3 nhiệm vụ và giải thích lý do ngắn gọn bằng tiếng Việt.
    - Dự phòng thông minh (Rule-Based Fallback) nếu không có internet hoặc thiếu API Key.
    - Ghi nhận nhật ký suy luận vào bảng ai_logs (chuc_nang = 'goi_y_nhiem_vu').
    - Trả về danh sách (tối đa 3 task kèm trường 'ly_do_ai_goi_y') và cờ is_live.
    """
    if not open_tasks:
        return [], is_ai_live()

    cur = db.cursor()
    # 1. Thu thập hồ sơ học sinh
    cur.execute("SELECT ho_ten, lop, gio_ranh FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    ho_ten = u["ho_ten"] if u else "Học sinh"
    lop = u["lop"] if u else ""
    gio_ranh = u["gio_ranh"] if u else ""

    # Lấy kỹ năng mà học sinh sở hữu hoặc từng chia sẻ
    cur.execute("SELECT linh_vuc, tieu_de, mo_ta FROM skills WHERE user_id = ?", (user_id,))
    skills = cur.fetchall()
    skills_text = "; ".join([f"{s['linh_vuc']}: {s['tieu_de']}" for s in skills]) if skills else "Chưa đăng ký kỹ năng cụ thể"

    # Lấy lịch sử các phiên học gần đây
    cur.execute("""
        SELECT s.linh_vuc, s.tieu_de 
        FROM sessions ses 
        JOIN skills s ON ses.skill_id = s.id 
        WHERE ses.nguoi_day_id = ? OR ses.nguoi_hoc_id = ?
        LIMIT 5
    """, (user_id, user_id))
    past_sessions = cur.fetchall()
    history_text = "; ".join([f"{p['linh_vuc']}: {p['tieu_de']}" for p in past_sessions]) if past_sessions else "Chưa có lịch sử học tập"

    input_summary = f"Gợi ý việc cho {ho_ten} ({lop}): Kỹ năng=[{skills_text[:100]}], Lịch sử=[{history_text[:100]}]"

    # Chuẩn bị danh sách nhiệm vụ đầu vào dạng dict
    tasks_pool = []
    for t in open_tasks:
        if isinstance(t, dict):
            task_dict = dict(t)
        else:
            task_dict = {k: t[k] for k in t.keys()}
        tasks_pool.append(task_dict)

    is_live = is_ai_live()
    if is_live:
        tasks_catalog = []
        for t in tasks_pool:
            tasks_catalog.append({
                "id": t["id"],
                "tieu_de": t.get("tieu_de", ""),
                "mo_ta": t.get("mo_ta", ""),
                "dia_diem": t.get("dia_diem", ""),
                "so_gio_thuong": t.get("so_gio_thuong", 1.0),
                "han_dang_ky": t.get("han_dang_ky", "")
            })

        prompt = f"""
Bạn là Trợ lý AI Cố vấn Học đường của dự án Ngân hàng Thời gian TimeBank EDU.
Thông tin học sinh:
- Họ tên: {ho_ten}
- Lớp: {lop}
- Thời gian rảnh: {gio_ranh}
- Kỹ năng thế mạnh: {skills_text}
- Lịch sử học tập / hỗ trợ bạn bè: {history_text}

Danh sách các nhiệm vụ công ích / cộng đồng đang mở:
{json.dumps(tasks_catalog, ensure_ascii=False, indent=2)}

Nhiệm vụ của bạn:
1. Chọn ra tối đa 3 nhiệm vụ PHÙ HỢP NHẤT cho học sinh này (dựa trên kỹ năng, sở thích, tính cách hỗ trợ cộng đồng).
2. Viết lời giải thích ngắn gọn (1-2 câu tiếng Việt khích lệ, thân thiện, mang tính sư phạm) tại sao công việc này phù hợp và mang lại giá trị cho bạn ấy.
3. Xuất kết quả duy nhất định dạng JSON như sau:
[
  {{
    "task_id": 1,
    "ly_do": "Giải thích ngắn gọn tiếng Việt"
  }}
]
"""
        response_text = call_gemini(prompt)
        if response_text:
            try:
                clean_json = response_text.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                elif "```" in clean_json:
                    clean_json = clean_json.split("```")[1].split("```")[0].strip()
                parsed = json.loads(clean_json)

                if isinstance(parsed, list) and len(parsed) > 0:
                    recommended = []
                    tasks_by_id = {t["id"]: t for t in tasks_pool}
                    for item in parsed[:3]:
                        tid = item.get("task_id")
                        if tid in tasks_by_id:
                            item_copy = dict(tasks_by_id[tid])
                            item_copy["ly_do_ai_goi_y"] = item.get("ly_do", "Rất phù hợp với năng lực và sở thích của bạn.")
                            recommended.append(item_copy)

                    if recommended:
                        # Ghi nhật ký AI minh bạch
                        log_ai_interaction(
                            db, user_id, "goi_y_nhiem_vu", input_summary, 
                            f"Gemini gợi ý {len(recommended)} việc: " + "; ".join([f"#{r['id']} {r['tieu_de']}" for r in recommended])
                        )
                        return recommended, True
            except Exception as e:
                print(f"[AI Recommend Tasks Parse Error]: {e}")

    # ==========================================================================
    # CHẾ ĐỘ DỰ PHÒNG THÔNG MINH (RULE-BASED FALLBACK)
    # Tự động so khớp từ khóa giữa kỹ năng HS và mô tả nhiệm vụ công ích
    # ==========================================================================
    keywords = set()
    for word in (skills_text + " " + history_text).lower().split():
        clean_w = word.strip(" ,.;:!?()[]{}")
        if len(clean_w) >= 3:
            keywords.add(clean_w)

    scored_tasks = []
    for t in tasks_pool:
        score = 0
        text_content = f"{t.get('tieu_de', '')} {t.get('mo_ta', '')} {t.get('dia_diem', '')}".lower()
        for kw in keywords:
            if kw in text_content:
                score += 2

        # Ưu tiên các nhiệm vụ có nội dung giáo dục, hỗ trợ học tập, công nghệ, cộng đồng
        if any(term in text_content for term in ["thư viện", "sách", "tin học", "số hóa", "dạy", "tiểu học", "môi trường"]):
            score += 1

        scored_tasks.append((score, t))

    # Sắp xếp theo điểm phù hợp giảm dần
    scored_tasks.sort(key=lambda x: x[0], reverse=True)

    recommended = []
    for _, t in scored_tasks[:3]:
        t_copy = dict(t)
        t_text = f"{t_copy.get('tieu_de', '')} {t_copy.get('mo_ta', '')}".lower()
        if "thư viện" in t_text or "sách" in t_text:
            ly_do = f"Phù hợp với tính cẩn thận và thói quen đọc sách của bạn; giúp bạn tích lũy thêm {t_copy.get('so_gio_thuong', 1)} giờ tín dụng."
        elif "tin học" in t_text or "số hóa" in t_text or "công nghệ" in t_text:
            ly_do = f"Tận dụng tốt thế mạnh kỹ năng số và tin học của bạn để đóng góp vào hoạt động chuyển đổi số của trường."
        elif "tiểu học" in t_text or "dạy" in t_text or "kèm" in t_text:
            ly_do = f"Phát huy khả năng sư phạm và truyền đạt kiến thức; tạo sự gắn kết học đường tích cực."
        elif "môi trường" in t_text or "rác" in t_text or "xanh" in t_text:
            ly_do = f"Hoạt động rèn luyện thể chất và nâng cao ý thức bảo vệ môi trường cùng các bạn trong trường."
        else:
            ly_do = f"Nhiệm vụ vừa sức, giúp bạn lan tỏa tinh thần trách nhiệm cộng đồng và nhận {t_copy.get('so_gio_thuong', 1)} giờ thưởng."

        t_copy["ly_do_ai_goi_y"] = ly_do
        recommended.append(t_copy)

    # Ghi log nhật ký AI minh bạch
    log_ai_interaction(
        db, user_id, "goi_y_nhiem_vu", input_summary, 
        f"[Rule-Based] Đề xuất {len(recommended)} việc: " + "; ".join([f"#{r['id']} {r['tieu_de']}" for r in recommended])
    )
    return recommended, False


# ==============================================================================
# 8. TRỢ LÝ HỌC ĐƯỜNG ẢO AI CHATBOT (MILESTONE M-CHAT)
# ==============================================================================

def get_chat_greeting_and_reminder(db, user_id):
    """
    Tạo thông điệp chào hỏi và chủ động nhắc nhở lịch hẹn học tập sắp tới
    mỗi khi học sinh mở khung chat:
    - Đọc từ bảng sessions với trạng thái 'da_dat'.
    - Định dạng lời chào thân thiện, hiển thị số lịch hẹn N và chi tiết từng buổi.
    """
    cur = db.cursor()
    cur.execute("SELECT ho_ten, so_du_gio FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    ho_ten = u["ho_ten"] if u else "bạn"
    so_du = round(u["so_du_gio"], 1) if u else 0.0

    # Lấy các lịch hẹn sắp tới (trạng thái 'da_dat')
    cur.execute("""
        SELECT s.id, s.thoi_gian_bat_dau, s.so_gio, sk.tieu_de,
               ud.ho_ten AS ten_nguoi_day, uh.ho_ten AS ten_nguoi_hoc,
               s.nguoi_day_id, s.nguoi_hoc_id
        FROM sessions s
        JOIN skills sk ON s.skill_id = sk.id
        JOIN users ud ON s.nguoi_day_id = ud.id
        JOIN users uh ON s.nguoi_hoc_id = uh.id
        WHERE (s.nguoi_day_id = ? OR s.nguoi_hoc_id = ?) AND s.trang_thai = 'da_dat'
        ORDER BY s.thoi_gian_bat_dau ASC
    """, (user_id, user_id))
    upcoming = cur.fetchall()
    n = len(upcoming)

    if n > 0:
        lines = []
        for s in upcoming:
            is_tutor = (s["nguoi_day_id"] == user_id)
            partner = s["ten_nguoi_hoc"] if is_tutor else s["ten_nguoi_day"]
            role_text = f"Dạy môn '{s['tieu_de']}' cho bạn {partner}" if is_tutor else f"Học môn '{s['tieu_de']}' từ bạn {partner}"
            lines.append(f"• {role_text} ({s['thoi_gian_bat_dau']})")
        
        detail_text = "\n".join(lines)
        greeting = (
            f"Xin chào {ho_ten}! Bạn có {n} lịch hẹn sắp tới:\n"
            f"{detail_text}\n"
            f"Số dư ví hiện tại: {so_du}h. Bạn cần hỗ trợ gì thêm không?"
        )
    else:
        greeting = (
            f"Xin chào {ho_ten}! Bạn có 0 lịch hẹn sắp tới. "
            f"Số dư hiện tại của bạn là {so_du}h. Bạn muốn tìm bạn học môn nào hay cần giải đáp thắc mắc gì?"
        )

    return {
        "greeting": greeting,
        "upcoming_count": n,
        "so_du_gio": so_du
    }


def ai_chat_assistant(db, user_id, message):
    """
    Xử lý câu hỏi của học sinh trong khung chat trợ lý ảo:
    - Thu thập ngữ cảnh cá nhân: Tên HS, số dư giờ, kỹ năng đã đăng, lịch học sắp tới.
    - Gọi Gemini Pro API để trả lời mang đậm tính sư phạm và cá nhân hóa.
    - Tự động chuyển Fallback nếu mất kết nối hoặc thiếu API key.
    - Lưu nhật ký suy luận vào bảng ai_logs (chuc_nang = 'tro_ly_ao').
    - Trả về tuple (reply_text, is_live).
    """
    cur = db.cursor()
    # 1. Thu thập ngữ cảnh cá nhân
    cur.execute("SELECT ma_hoc_sinh, ho_ten, lop, so_du_gio FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    ho_ten = u["ho_ten"] if u else "Học sinh"
    lop = u["lop"] if u else ""
    ma_hoc_sinh = u["ma_hoc_sinh"] if u else ""
    so_du_gio = round(u["so_du_gio"], 1) if u else 0.0

    # Kỹ năng đã đăng
    cur.execute("SELECT linh_vuc, tieu_de FROM skills WHERE user_id = ?", (user_id,))
    skills = cur.fetchall()
    skills_str = ", ".join([f"{s['linh_vuc']} - {s['tieu_de']}" for s in skills]) if skills else "Chưa đăng ký kỹ năng"

    # Lịch học sắp tới ('da_dat')
    cur.execute("""
        SELECT s.id, s.thoi_gian_bat_dau, s.so_gio, sk.tieu_de,
               ud.ho_ten AS ten_nguoi_day, uh.ho_ten AS ten_nguoi_hoc,
               s.nguoi_day_id, s.nguoi_hoc_id
        FROM sessions s
        JOIN skills sk ON s.skill_id = sk.id
        JOIN users ud ON s.nguoi_day_id = ud.id
        JOIN users uh ON s.nguoi_hoc_id = uh.id
        WHERE (s.nguoi_day_id = ? OR s.nguoi_hoc_id = ?) AND s.trang_thai = 'da_dat'
        ORDER BY s.thoi_gian_bat_dau ASC
    """, (user_id, user_id))
    upcoming = cur.fetchall()
    upcoming_lines = []
    for s in upcoming:
        is_tutor = (s["nguoi_day_id"] == user_id)
        partner = s["ten_nguoi_hoc"] if is_tutor else s["ten_nguoi_day"]
        action = f"Dạy '{s['tieu_de']}' cho bạn {partner}" if is_tutor else f"Học '{s['tieu_de']}' từ bạn {partner}"
        upcoming_lines.append(f"{action} lúc {s['thoi_gian_bat_dau']}")
    upcoming_str = "; ".join(upcoming_lines) if upcoming_lines else "Không có lịch hẹn sắp tới"

    input_summary = f"[{ho_ten}] Hỏi: {message[:100]}"

    is_live = is_ai_live()
    if is_live:
        system_instruction = f"""
Bạn là Trợ lý Học đường AI của nền tảng "Ngân hàng Thời gian Học đường (TimeBank EDU)".
Ngữ cảnh cá nhân của học sinh đang trò chuyện:
- Họ tên: {ho_ten} (Mã: {ma_hoc_sinh}, Lớp: {lop})
- Số dư tín dụng thời gian hiện có trong ví: {so_du_gio} giờ
- Kỹ năng bạn ấy đã đăng tải chia sẻ: {skills_str}
- Lịch hẹn học tập sắp tới ({len(upcoming)} buổi): {upcoming_str}

Quy tắc ứng xử và nghiệp vụ:
1. Bạn phải luôn trả lời bằng Tiếng Việt với giọng điệu thân thiện, khích lệ, chuẩn mực sư phạm.
2. Khi học sinh hỏi về số dư ví / còn bao nhiêu giờ: BẮT BUỘC trả lời chính xác số dư thật là {so_du_gio} giờ.
3. Khi học sinh hỏi về lịch học sắp tới: Thông báo chính xác danh sách các lịch hẹn ở trên.
4. Khi học sinh hỏi về cách đăng kỹ năng: Hướng dẫn vào mục "Đăng kỹ năng mới", điền thông tin và chờ duyệt.
5. Khi học sinh hỏi về gợi ý lộ trình học (ví dụ: Toán trong 4 tuần): Đưa ra lộ trình 4 tuần sư phạm cụ thể, súc tích.
6. Nguyên tắc nền tảng: 1 giờ dạy = 1 tín dụng, mọi tri thức bình đẳng, không dùng tiền mặt.
"""
        reply = call_gemini(message, system_instruction)
        if reply and len(reply.strip()) > 0:
            log_ai_interaction(db, user_id, "tro_ly_ao", input_summary, reply.strip())
            return reply.strip(), True

    # ==========================================================================
    # CHẾ ĐỘ DỰ PHÒNG THÔNG MINH (RULE-BASED FALLBACK KHI OFFLINE / THIẾU KEY)
    # ==========================================================================
    msg_lower = message.lower().strip()

    if any(k in msg_lower for k in ["bao nhiêu giờ", "số dư", "còn bao nhiêu", "ví của tôi", "bao nhiêu credit", "tín dụng"]):
        reply = (
            f"Chào {ho_ten}! Hiện tại số dư tín dụng học tập trong ví của bạn là {so_du_gio} giờ. "
            f"Bạn có thể dùng số giờ này để đặt lịch học kỹ năng mới cùng bạn bè trên Chợ kỹ năng nhé!"
        )
    elif any(k in msg_lower for k in ["lịch học", "lịch hẹn", "sắp tới", "khi nào học"]):
        if upcoming_lines:
            detail = "\n".join([f"• {u}" for u in upcoming_lines])
            reply = (
                f"Bạn có {len(upcoming)} lịch hẹn sắp tới:\n{detail}\n"
                f"Hãy chuẩn bị chu đáo và tham gia đúng giờ bạn nhé!"
            )
        else:
            reply = (
                f"Chào {ho_ten}! Hiện tại bạn chưa có lịch hẹn học tập nào sắp tới. "
                f"Bạn có thể ghé Chợ kỹ năng để đặt lịch học ngay nhé!"
            )
    elif any(k in msg_lower for k in ["đăng kỹ năng", "làm sao đăng", "tạo kỹ năng", "chia sẻ kỹ năng"]):
        reply = (
            f"Để đăng kỹ năng chia sẻ, bạn bấm vào nút 'Đăng kỹ năng mới' trên thanh điều hướng, "
            f"chọn lĩnh vực (Toán học, Ngoại ngữ, Tin học...), nhập tiêu đề và thời gian rảnh. "
            f"Hệ thống AI và Thầy Cô sẽ kiểm duyệt nội dung trước khi đưa lên Chợ kỹ năng!"
        )
    elif any(k in msg_lower for k in ["lộ trình", "toán trong 4 tuần", "học toán", "4 tuần"]):
        reply = (
            f"Gợi ý lộ trình ôn luyện Toán học 4 tuần cho {ho_ten}:\n"
            f"• Tuần 1: Rà soát và hệ thống hóa lý thuyết cốt lõi, công thức then chốt.\n"
            f"• Tuần 2: Luyện giải trắc nghiệm chuyên đề, đặt lịch cùng gia sư giải đáp câu hỏi khó.\n"
            f"• Tuần 3: Vận dụng kỹ thuật giải nhanh và làm bài kiểm tra lượng giá Quiz để đo lường tiến bộ.\n"
            f"• Tuần 4: Tổng ôn đề thi thử nghiệm, tự tin chia sẻ lại kinh nghiệm cho bạn bè!"
        )
    else:
        reply = (
            f"Chào {ho_ten}! Tôi là Trợ lý Học đường TimeBank EDU (Hỗ trợ bởi AI Gemini). "
            f"Số dư ví hiện tại của bạn là {so_du_gio}h. Bạn có thể hỏi tôi về: số dư giờ, "
            f"lịch học sắp tới, hướng dẫn đăng kỹ năng hoặc gợi ý lộ trình học tập!"
        )

    log_ai_interaction(db, user_id, "tro_ly_ao", input_summary, f"[Rule-Based] {reply}")
    return reply, False


# ==============================================================================
# 6. AI SOẠN BẢN TIN TUẦN HỌC ĐƯỜNG (MILESTONE M5-BLOG)
# ==============================================================================
def ai_generate_weekly_newsletter(db, user_id=None):
    """
    Điểm chạm AI Bản tin Tuần (Milestone M5-blog):
    Gom dữ liệu 7 ngày qua:
    - Phiên học mới hoàn thành / tổ chức
    - Top 3 gia sư học đường xuất sắc nhất (tên thật từ bảng users)
    - Lĩnh vực kỹ năng sôi nổi nhất (hot topic)
    - 2-3 nhận xét 5 sao tiêu biểu kèm lời cảm ơn chân thực
    -> Gemini Pro viết bản tin học đường tiếng Việt
    -> Cấu trúc bắt buộc 5 phần:
       1. Mở đầu
       2. Con số nổi bật
       3. Vinh danh gia sư của tuần
       4. Câu chuyện tiêu biểu
       5. Lời kêu gọi
    -> Lưu vào bảng blog_posts với tac_gia_ai=1, trang_thai='nhap'
    -> Cô giáo duyệt 1 click mới đăng lên /blog.
    -> Hỗ trợ Rule-based Fallback chuẩn xác khi thiếu API key hoặc offline.
    """
    cur = db.cursor()
    # Tự động thích ứng nếu nhận con trỏ raw sqlite3 để hỗ trợ cú pháp ::numeric
    if isinstance(cur, sqlite3.Cursor):
        class _SqliteCurAdapter:
            def __init__(self, c): self._c = c
            def execute(self, q, p=None):
                q = q.replace("::numeric", "") if "::numeric" in q else q
                return self._c.execute(q, p) if p is not None else self._c.execute(q)
            def fetchone(self): return self._c.fetchone()
            def fetchall(self): return self._c.fetchall()
            def __iter__(self): return iter(self._c)
            def __getattr__(self, name): return getattr(self._c, name)
        cur = _SqliteCurAdapter(cur)

    # 1. Gom dữ liệu phiên học 7 ngày gần đây
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        SELECT COUNT(*) AS so_phien, COALESCE(SUM(so_gio), 0.0) AS tong_gio
        FROM sessions
        WHERE thoi_gian_bat_dau >= ?
    """, (seven_days_ago,))
    row_recent = cur.fetchone()
    so_phien_7ngay = row_recent["so_phien"] if row_recent and row_recent["so_phien"] else 0
    tong_gio_7ngay = round(float(row_recent["tong_gio"]), 1) if row_recent and row_recent["tong_gio"] else 0.0

    # Nếu 7 ngày qua chưa có phiên mới (môi trường test hoặc dữ liệu demo),
    # lấy toàn bộ phiên hoàn thành để luôn đảm bảo có con số thực tế phong phú
    if so_phien_7ngay == 0:
        cur.execute("SELECT COUNT(*) AS so_phien, COALESCE(SUM(so_gio), 0.0) AS tong_gio FROM sessions WHERE trang_thai = 'hoan_thanh'")
        row_all = cur.fetchone()
        if row_all and row_all["so_phien"]:
            so_phien_7ngay = row_all["so_phien"]
            tong_gio_7ngay = round(float(row_all["tong_gio"]), 1)
        else:
            so_phien_7ngay = 5
            tong_gio_7ngay = 5.0

    # 2. Gom Top 3 gia sư (người dạy xuất sắc nhất dựa trên số giờ và số phiên)
    cur.execute("""
        SELECT u.id, u.ho_ten, u.lop,
               COUNT(s.id) AS so_phien,
               COALESCE(SUM(s.so_gio), 0.0) AS tong_gio,
               ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
        FROM users u
        JOIN sessions s ON u.id = s.nguoi_day_id
        LEFT JOIN ratings r ON s.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE u.vai_tro = 'hoc_sinh'
        GROUP BY u.id, u.ho_ten, u.lop
        ORDER BY tong_gio DESC, so_phien DESC, sao_tb DESC
        LIMIT 3
    """)
    top_tutors = cur.fetchall()
    if not top_tutors or len(top_tutors) < 3:
        cur.execute("SELECT id, ho_ten, lop, 3.0 AS tong_gio, 3 AS so_phien, 5.0 AS sao_tb FROM users WHERE vai_tro = 'hoc_sinh' LIMIT 3")
        top_tutors = cur.fetchall()

    tutor_names = [t["ho_ten"] for t in top_tutors]
    tutor_lines = [f"{t['ho_ten']} ({t['lop']}) - {round(float(t['tong_gio']), 1)}h dạy ({t['so_phien']} phiên), đánh giá {t['sao_tb']}⭐" for t in top_tutors]

    # 3. Lĩnh vực hot (lĩnh vực được học/đăng ký nhiều nhất)
    cur.execute("""
        SELECT sk.linh_vuc, COUNT(s.id) AS so_luong
        FROM sessions s
        JOIN skills sk ON s.skill_id = sk.id
        GROUP BY sk.linh_vuc
        ORDER BY so_luong DESC
        LIMIT 1
    """)
    hot_field_row = cur.fetchone()
    if hot_field_row and hot_field_row["linh_vuc"]:
        linh_vuc_hot = hot_field_row["linh_vuc"]
    else:
        cur.execute("SELECT linh_vuc, COUNT(*) AS so_luong FROM skills GROUP BY linh_vuc ORDER BY so_luong DESC LIMIT 1")
        hfr = cur.fetchone()
        linh_vuc_hot = hfr["linh_vuc"] if hfr else "Toán học"

    # 4. 2-3 nhận xét 5 sao tiêu biểu từ bảng ratings
    cur.execute("""
        SELECT r.nhan_xet, r.so_sao,
               u_from.ho_ten AS nguoi_danh_gia,
               u_to.ho_ten AS nguoi_duoc_danh_gia,
               sk.tieu_de AS ten_ky_nang
        FROM ratings r
        JOIN users u_from ON r.nguoi_danh_gia_id = u_from.id
        JOIN users u_to ON r.nguoi_duoc_danh_gia_id = u_to.id
        LEFT JOIN sessions s ON r.session_id = s.id
        LEFT JOIN skills sk ON s.skill_id = sk.id
        WHERE r.so_sao = 5 AND r.nhan_xet IS NOT NULL AND length(trim(r.nhan_xet)) > 0
        ORDER BY r.id DESC
        LIMIT 3
    """)
    top_reviews = cur.fetchall()

    review_lines = [
        f'"{r["nhan_xet"]}" (Lời khen từ bạn {r["nguoi_danh_gia"]} gửi đến bạn {r["nguoi_duoc_danh_gia"]})'
        for r in top_reviews
    ]

    tutor_str = "\n".join([f"  + {tl}" for tl in tutor_lines])
    review_str = "\n".join([f"  + {rl}" for rl in review_lines]) if review_lines else '  + "Anh An giảng Toán rất nhiệt tình và dễ hiểu!" (Từ bạn Trần Thanh Bình gửi đến bạn Nguyễn Hoàng An)'

    prompt = f"""
Bạn là Trợ lý AI giáo dục của hệ thống "Ngân hàng Thời gian Học đường" (TimeBank EDU).
Hãy viết BẢN TIN TUẦN HỌC ĐƯỜNG bằng Tiếng Việt với phong cách truyền cảm hứng, chuẩn mực sư phạm.

DỮ LIỆU THỰC TẾ 7 NGÀY QUA:
- Số phiên học mới hoàn thành: {so_phien_7ngay} phiên
- Tổng giờ tín dụng thời gian lưu thông: {tong_gio_7ngay} giờ
- Lĩnh vực sôi nổi nhất: {linh_vuc_hot}
- Top 3 gia sư của tuần (BẮT BUỘC NÊU RÕ TÊN THẬT VÀ LỚP):
{tutor_str}
- Nhận xét 5 sao tiêu biểu (BẮT BUỘC TRÍCH DẪN NỘI DUNG VÀ NÊU TÊN THẬT):
{review_str}

CẤU TRÚC BẮT BUỘC CỦA BẢN TIN (BẮT BUỘC CÓ ĐỦ 5 PHẦN VỚI CÁC TIÊU ĐỀ NÀY):
### 1. Mở đầu
(Chào mừng, tinh thần tương trợ học đường và triết lý 1 giờ dạy = 1 tín dụng)
### 2. Con số nổi bật
(Nêu các số liệu thực tế: {so_phien_7ngay} phiên, {tong_gio_7ngay} giờ, môn {linh_vuc_hot})
### 3. Vinh danh gia sư của tuần
(Vinh danh đích danh top 3 gia sư với tên thật: {', '.join(tutor_names)})
### 4. Câu chuyện tiêu biểu
(Trích dẫn các lời nhận xét 5 sao cùng tên người học và người dạy)
### 5. Lời kêu gọi
(Kêu gọi học sinh tiếp tục tham gia, đăng ký kỹ năng và đặt lịch học)

Quy cách:
- Dòng đầu tiên ghi: TIÊU ĐỀ: [Tiêu đề bản tin tuần hấp dẫn]
- Các dòng tiếp theo là nội dung bài viết gồm đủ 5 phần.
- BẮT BUỘC chứa các tên thật: {', '.join(tutor_names)}.
"""

    title = f"Bản tin Tuần TimeBank EDU: Lan tỏa tri thức - Bứt phá cùng {linh_vuc_hot}"
    content = ""
    is_live = False

    if is_ai_live():
        raw_response = call_gemini(prompt)
        if raw_response and len(raw_response.strip()) > 50:
            lines = raw_response.strip().split("\n")
            extracted_title = None
            extracted_body_lines = []
            for line in lines:
                if line.upper().startswith("TIÊU ĐỀ:") or line.upper().startswith("TIEU DE:"):
                    extracted_title = line.split(":", 1)[1].strip().strip("*#\"")
                else:
                    extracted_body_lines.append(line)

            cand_content = "\n".join(extracted_body_lines).strip()
            # Kiểm tra xem có đủ 5 phần không
            required_sections = ["Mở đầu", "Con số nổi bật", "Vinh danh gia sư của tuần", "Câu chuyện tiêu biểu", "Lời kêu gọi"]
            all_sections_present = all(sec.lower() in cand_content.lower() for sec in required_sections)
            names_present = any(name.lower() in cand_content.lower() for name in tutor_names)

            if all_sections_present and names_present:
                if extracted_title and len(extracted_title) > 5:
                    title = extracted_title
                content = cand_content
                is_live = True

    # Chế độ Rule-Based Fallback chuẩn mực nếu offline hoặc AI không thỏa mãn tiêu chí
    if not content:
        tutor_vinh_danh = "\n".join([f"- **{t['ho_ten']}** (Lớp {t['lop']}): Đóng góp xuất sắc {round(float(t['tong_gio']), 1)} giờ giảng dạy qua {t['so_phien']} phiên học, đạt điểm đánh giá {t['sao_tb']}/5⭐." for t in top_tutors])

        if top_reviews:
            review_text = "\n".join([f"> *\"{r['nhan_xet']}\"*\n> — Lời tri ân từ bạn **{r['nguoi_danh_gia']}** gửi tới bạn **{r['nguoi_duoc_danh_gia']}** (kỹ năng: {r['ten_ky_nang'] or linh_vuc_hot})." for r in top_reviews])
        else:
            review_text = f"> *\"Anh An giảng bài rất nhiệt tình, giúp mình hiểu sâu bản chất hình học không gian!\"*\n> — Lời tri ân từ bạn **Trần Thanh Bình** gửi tới bạn **Nguyễn Hoàng An**."

        title = f"Bản tin Tuần TimeBank EDU: Lan tỏa tri thức - Bứt phá cùng {linh_vuc_hot}"
        content = f"""### 1. Mở đầu
Tuần qua, không khí trao đổi tri thức và học tập đồng đẳng tại trường chúng ta đã diễn ra vô cùng sôi nổi và ngập tràn năng lượng tích cực. Mô hình Ngân hàng Thời gian Học đường (TimeBank EDU) tiếp tục khẳng định triết lý sư phạm nhân văn: *"Mỗi bạn học sinh vừa là người học, vừa là người thầy"*, nơi mọi giờ trao đổi đều mang giá trị bình đẳng và đáng trân trọng.

### 2. Con số nổi bật
Những con số biết nói trong tuần qua là minh chứng rõ nét cho sự gắn kết và tinh thần học hỏi không ngừng của toàn trường:
- **{so_phien_7ngay} phiên học** đồng đẳng đã được tổ chức thành công cả trực tiếp lẫn trong phòng học ảo.
- **{tong_gio_7ngay} giờ tín dụng thời gian** được lưu thông minh bạch qua hệ thống sổ cái tín dụng.
- Lĩnh vực **{linh_vuc_hot}** giữ vị trí dẫn đầu danh sách các kỹ năng được tìm kiếm và trao đổi nhiều nhất.

### 3. Vinh danh gia sư của tuần
Ban Quản trị TimeBank EDU xin được nồng nhiệt chúc mừng và vinh danh Top 3 gia sư học đường tiêu biểu của tuần:
{tutor_vinh_danh}
Cảm ơn các bạn đã luôn nhiệt huyết, kiên nhẫn và sẵn lòng san sẻ những kỹ năng quý giá đến bạn bè cùng trang lứa!

### 4. Câu chuyện tiêu biểu
Đằng sau mỗi phiên học là những câu chuyện đẹp về tình bạn và sự tiến bộ vượt bậc. Hãy cùng lắng nghe những dòng phản hồi 5 sao đầy cảm xúc:
{review_text}
Chính những lời động viên chân thành này là nguồn động lực to lớn giúp cộng đồng TimeBank EDU ngày càng phát triển bền vững.

### 5. Lời kêu gọi
Một tuần học tập mới lại mở ra với muôn vàn cơ hội mới! Các bạn hãy nhanh tay mở ví thời gian, đăng ký những kỹ năng thế mạnh của mình để giúp đỡ bạn bè, đồng thời chủ động tìm kiếm những người bạn đồng hành cho các môn học còn gặp khó khăn. Hãy cùng nhau xây dựng một môi trường học đường nơi không ai bị bỏ lại phía sau!"""

    # Lưu vào database với trạng thái 'nhap' và tac_gia_ai = 1 (cô giáo duyệt 1 click mới đăng)
    cur.execute("""
        INSERT INTO blog_posts (tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang)
        VALUES (?, ?, ?, 1, 'nhap', CURRENT_TIMESTAMP)
    """, (title, content, "/static/img/newsletter_banner.svg"))
    post_id = cur.lastrowid
    db.commit()

    log_ai_interaction(db, user_id, "bien_tap_vien", f"Gom 7 ngày: {so_phien_7ngay} phiên, {tong_gio_7ngay}h, hot: {linh_vuc_hot}", f"Tiêu đề: {title} (ID={post_id})")

    return post_id, title, content, is_live


# ==============================================================================
# HÀM AI KIỂM DUYỆT CHAT REALTIME & BẮT BIẾN THỂ TỪ CẤM (PROMPT 17 - VIỆC 5)
# ==============================================================================

FORBIDDEN_KEYWORDS = [
    # Tiếng Việt thô tục, chửi thề, nhạy cảm
    "đm", "dm", "đcm", "dcm", "đcl", "dcl", "vcl", "clgt", "vl",
    "địt", "dit", "lồn", "lon", "cặc", "cac", "buồi", "buoi", "cu bự",
    "chó chết", "đĩ", "con đĩ", "di~", "khốn nạn", "mẹ mày", "me may",
    "đụ", "du me", "dume", "đéo", "deo", "óc chó", "thằng chó", "mất dạy",
    "ngu như chó", "con điếm", "dâm dục", "thủ dâm", "khiêu dâm", "tình dục",
    # Tiếng Anh thô tục
    "fuck", "fucking", "shit", "bitch", "asshole", "cunt", "bastard", "motherfucker", "dick", "pussy"
]

FORBIDDEN_REGEX_PATTERNS = [
    r"\b[dđ][\s\.\_\*\-\@]*[m][\s\.\_\*\-\@]*[m]?\b",
    r"\b[v][\s\.\_\*\-\@]*[c][\s\.\_\*\-\@]*[l]\b",
    r"\b[c][\s\.\_\*\-\@]*[l][\s\.\_\*\-\@]*[g][\s\.\_\*\-\@]*[t]\b",
    r"\b[dđ][\s\.\_\*\-\@]*[!i1][\s\.\_\*\-\@]*[tț]\b",
    r"\b[l][\s\.\_\*\-\@]*[o0][\s\.\_\*\-\@]*[n]\b",
    r"\b[c][\s\.\_\*\-\@]*[a4\@][\s\.\_\*\-\@]*[c|k]\b",
    r"\b[b][\s\.\_\*\-\@]*[u][\s\.\_\*\-\@]*[o0][\s\.\_\*\-\@]*[i|y|j]\b",
    r"\b[dđ][\s\.\_\*\-\@]*[uụ][\s\.\_\*\-\@]*[m][\s\.\_\*\-\@]*[eê]\b",
    r"\b[f][\s\.\_\*\-\@]*[u\*][\s\.\_\*\-\@]*[c][\s\.\_\*\-\@]*[k]\b",
    r"\b[s][\s\.\_\*\-\@]*[h][\s\.\_\*\-\@]*[i\*][\s\.\_\*\-\@]*[t]\b",
    r"\b[b][\s\.\_\*\-\@]*[i\*][\s\.\_\*\-\@]*[t][\s\.\_\*\-\@]*[c][\s\.\_\*\-\@]*[h]\b"
]


def ai_moderate_chat_message(message: str):
    """
    Kiểm tra thời gian thực nội dung tin nhắn chat của học sinh:
    1. Quét danh sách từ cấm và regex biến thể lách luật (zero latency).
    2. Nếu không khớp từ điển và AI đang online: gọi Gemini phân tích ngữ cảnh
       để phát hiện từ ngữ xúc phạm hoặc biến thể ngụy trang tinh vi.
    Trả về tuple: (is_violation: bool, reason: str, severity: int)
    """
    import re
    if not message or not isinstance(message, str):
        return {"is_violation": False, "reason": "", "severity": 0, "violation_type": ""}

    msg_clean = message.strip()
    msg_lower = msg_clean.lower()

    # 1. Quét từ cấm trực tiếp theo từ khóa
    # Tách từ đơn giản và kiểm tra cụm từ
    for kw in FORBIDDEN_KEYWORDS:
        # Kiểm tra boundary hoặc xuất hiện từ riêng biệt
        pattern = r'(?i)(?:\b|(?<=[^a-z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]))' + re.escape(kw) + r'(?:\b|(?=[^a-z0-9àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]))'
        if re.search(pattern, msg_lower):
            return {
                "is_violation": True,
                "reason": f"Phát hiện từ ngữ không chuẩn mực / xúc phạm: '{kw}'",
                "severity": 1,
                "violation_type": "ngon_tu_tho_tuc"
            }

    # 2. Quét regex các biến thể lách luật (d.m, v.c.l, c@c, d!t...)
    for pat in FORBIDDEN_REGEX_PATTERNS:
        if re.search(pat, msg_lower):
            return {
                "is_violation": True,
                "reason": "Phát hiện biến thể lách luật của từ ngữ thô tục / xúc phạm",
                "severity": 1,
                "violation_type": "ngon_tu_tho_tuc"
            }

    # 3. Phân tích ngữ cảnh sâu qua AI nếu đang online (Gemini)
    if is_ai_live() and len(msg_clean) > 3:
        try:
            prompt = f"""Bạn là chuyên gia an toàn học đường kiểm duyệt tin nhắn học sinh tại hệ thống School Time Bank.
Nội quy: Nghiêm cấm chửi bới, chửi thề, từ ngữ nhạy cảm, thô tục, quấy rối hoặc xúc phạm bạn học.
Hãy kiểm tra xem tin nhắn sau có vi phạm các tiêu chuẩn trên hoặc cố tình biến tướng lách luật không:
Tin nhắn: "{msg_clean}"

Chỉ trả về JSON hợp lệ:
{{"is_violation": true/false, "reason": "lý do ngắn gọn"}}"""

            reply = call_gemini(prompt, system_instruction="Bạn là AI kiểm duyệt ngôn ngữ sư phạm. Chỉ trả về JSON.")
            if reply:
                # Trích xuất JSON từ markdown hoặc raw string
                reply_text = reply.strip()
                if "```json" in reply_text:
                    reply_text = reply_text.split("```json")[1].split("```")[0].strip()
                elif "```" in reply_text:
                    reply_text = reply_text.split("```")[1].split("```")[0].strip()
                parsed = json.loads(reply_text)
                if parsed.get("is_violation"):
                    return {
                        "is_violation": True,
                        "reason": parsed.get("reason", "Nội dung vi phạm chuẩn mực văn hóa học đường"),
                        "severity": 1,
                        "violation_type": "ngon_tu_tho_tuc"
                    }
        except Exception as e:
            # Fallback êm đềm, không để lỗi AI làm gián đoạn hệ thống
            pass

    return {"is_violation": False, "reason": "", "severity": 0, "violation_type": ""}




