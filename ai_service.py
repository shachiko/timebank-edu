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

# Cố gắng khởi tạo Google Generative AI
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        genai.configure(api_key=api_key)
        GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


def is_ai_live():
    """Kiểm tra xem Gemini API có sẵn sàng hoạt động hay đang ở chế độ dự phòng."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(key) and GEMINI_AVAILABLE


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
        print(f"[AI Log Error]: Không thể ghi log AI: {e}")


def call_gemini(prompt, system_instruction=""):
    """
    Hàm gọi Gemini API với cơ chế dự phòng an toàn và giới hạn thời gian (timeout < 20s).
    Trả về nội dung văn bản phản hồi hoặc None nếu thất bại.
    """
    if not is_ai_live():
        return None
        
    try:
        # Thử sử dụng mô hình gemini-1.5-flash hoặc gemini-pro
        model_name = "gemini-1.5-flash"
        try:
            model = genai.GenerativeModel(model_name)
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = model.generate_content(full_prompt, request_options={"timeout": 18})
            if response and response.text:
                return response.text.strip()
        except Exception:
            # Fallback sang gemini-pro nếu model mới chưa hỗ trợ
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(prompt, request_options={"timeout": 18})
            if response and response.text:
                return response.text.strip()
    except Exception as e:
        print(f"[Gemini Call Warning]: {e}")
        return None
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
        GROUP BY u.id
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
        GROUP BY r.nguoi_danh_gia_id, r.nguoi_duoc_danh_gia_id
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
