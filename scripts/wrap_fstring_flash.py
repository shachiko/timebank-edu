with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace each of the 51 f-string flash calls with _(...) using %(var)s format or direct format
fstring_replacements = [
    # 1. Password reset
    ('flash(f"Đã gửi liên kết đặt lại mật khẩu đến email {email}. Vui lòng kiểm tra hộp thư (liên kết có hiệu lực trong 60 phút).", "success")',
     'flash(_("Đã gửi liên kết đặt lại mật khẩu đến email %(email)s. Vui lòng kiểm tra hộp thư (liên kết có hiệu lực trong 60 phút).", email=email), "success")'),

    # 2. Account creation
    ('flash(f"Mã đăng nhập \'{ma_dang_nhap}\' đã tồn tại trong hệ thống!", "danger")',
     'flash(_("Mã đăng nhập \'%(ma)s\' đã tồn tại trong hệ thống!", ma=ma_dang_nhap), "danger")'),

    ('flash(f"Đã tạo thành công tài khoản \'{ho_ten}\' ({vai_tro}) gắn với trường học ID {tid}!", "success")',
     'flash(_("Đã tạo thành công tài khoản \'%(ho_ten)s\' (%(vai_tro)s) gắn với trường học ID %(tid)s!", ho_ten=ho_ten, vai_tro=vai_tro, tid=tid), "success")'),

    # 3. Excel / CSV import read errors
    ('flash(f"Lỗi khi đọc file Excel: {str(e)}", "danger")',
     'flash(_("Lỗi khi đọc file Excel: %(err)s", err=str(e)), "danger")'),

    ('flash(f"Lỗi khi đọc file CSV: {str(e)}", "danger")',
     'flash(_("Lỗi khi đọc file CSV: %(err)s", err=str(e)), "danger")'),

    # 4. Import summary
    ('flash(f"Nhập danh sách thành công! Đã tạo {len(success_list)} tài khoản cho trường \'{school_name}\'. Vui lòng tải file Excel kết quả để phát thông tin đăng nhập cho từng người.", "success")',
     'flash(_("Nhập danh sách thành công! Đã tạo %(count)s tài khoản cho trường \'%(school)s\'. Vui lòng tải file Excel kết quả để phát thông tin đăng nhập cho từng người.", count=len(success_list), school=school_name), "success")'),

    ('flash(f"Đã tạo thành công {len(success_list)} tài khoản; {len(error_list)} dòng bị lỗi/bỏ qua. Xem bảng tổng kết chi tiết bên dưới.", "warning")',
     'flash(_("Đã tạo thành công %(sc)s tài khoản; %(ec)s dòng bị lỗi/bỏ qua. Xem bảng tổng kết chi tiết bên dưới.", sc=len(success_list), ec=len(error_list)), "warning")'),

    ('flash(f"Không có tài khoản nào được tạo. Toàn bộ {len(error_list)} dòng trong danh sách đều có lỗi.", "danger")',
     'flash(_("Không có tài khoản nào được tạo. Toàn bộ %(ec)s dòng trong danh sách đều có lỗi.", ec=len(error_list)), "danger")'),

    # 5. Codes generated
    ('flash(f"Đã sinh thành công {len(created_codes)} mã mời dạng TBEDU-XXXX-XXXX!", "success")',
     'flash(_("Đã sinh thành công %(count)s mã mời dạng TBEDU-XXXX-XXXX!", count=len(created_codes)), "success")'),

    # 6. Approvals & Rejections
    ('flash(f"Đã phê duyệt tài khoản {target[\'ho_ten\']} ({target[\'ma_hoc_sinh\']}) thành công!", "success")',
     'flash(_("Đã phê duyệt tài khoản %(name)s (%(code)s) thành công!", name=target[\'ho_ten\'], code=target[\'ma_hoc_sinh\']), "success")'),

    ('flash(f"Đã từ chối đăng ký của học sinh {target[\'ho_ten\']}.", "info")',
     'flash(_("Đã từ chối đăng ký của học sinh %(name)s.", name=target[\'ho_ten\']), "info")'),

    ('flash(f"Đã phê duyệt {count} học sinh được chọn thành công!", "success")',
     'flash(_("Đã phê duyệt %(count)s học sinh được chọn thành công!", count=count), "success")'),

    ('flash(f"Đã duyệt toàn bộ {count} học sinh trong hàng chờ thành công!", "success")',
     'flash(_("Đã duyệt toàn bộ %(count)s học sinh trong hàng chờ thành công!", count=count), "success")'),

    ('flash(f"Đã xác nhận KHÓA VĨNH VIỄN tài khoản của học sinh {target[\'ho_ten\']} ({target[\'ma_hoc_sinh\']}) theo quy chế xử lý vi phạm.", "danger")',
     'flash(_("Đã xác nhận KHÓA VĨNH VIỄN tài khoản của học sinh %(name)s (%(code)s) theo quy chế xử lý vi phạm.", name=target[\'ho_ten\'], code=target[\'ma_hoc_sinh\']), "danger")'),

    # 7. School management
    ('flash(f"Trường học \'{ten_truong}\' đã tồn tại trong hệ thống!", "danger")',
     'flash(_("Trường học \'%(name)s\' đã tồn tại trong hệ thống!", name=ten_truong), "danger")'),

    ('flash(f"Đã thêm trường học mới \'{ten_truong}\' (Mã trường ID #{next_id}) thành công!", "success")',
     'flash(_("Đã thêm trường học mới \'%(name)s\' (Mã trường ID #%(id)s) thành công!", name=ten_truong, id=next_id), "success")'),

    ('flash(f"Tên trường \'{ten_truong}\' trùng với một trường học khác đã có!", "danger")',
     'flash(_("Tên trường \'%(name)s\' trùng với một trường học khác đã có!", name=ten_truong), "danger")'),

    ('flash(f"Đã cập nhật thông tin trường \'{ten_truong}\' thành công!", "success")',
     'flash(_("Đã cập nhật thông tin trường \'%(name)s\' thành công!", name=ten_truong), "success")'),

    # 8. Skills approval & inter-school
    ('flash(f"Đã {action_label} kỹ năng #{skill_id} thành công.", "success")',
     'flash(_("Đã %(action)s kỹ năng #%(id)s thành công.", action=action_label, id=skill_id), "success")'),

    ('flash(f"Bạn cần {rem_str} giờ dạy nữa để mở khóa Cộng đồng liên trường!", "warning")',
     'flash(_("Bạn cần %(rem)s giờ dạy nữa để mở khóa Cộng đồng liên trường!", rem=rem_str), "warning")'),

    ('flash(f"Đã duyệt kỹ năng \'{sk[\'tieu_de\']}\' ({school_name}) lên Cộng đồng liên trường thành công!", "success")',
     'flash(_("Đã duyệt kỹ năng \'%(title)s\' (%(school)s) lên Cộng đồng liên trường thành công!", title=sk[\'tieu_de\'], school=school_name), "success")'),

    ('flash(f"Đã từ chối đưa kỹ năng \'{sk[\'tieu_de\']}\' lên Cộng đồng liên trường.", "info")',
     'flash(_("Đã từ chối đưa kỹ năng \'%(title)s\' lên Cộng đồng liên trường.", title=sk[\'tieu_de\']), "info")'),

    ('flash(f"Đăng ký thành công! {ly_do_luu}. Kỹ năng đã sẵn sàng trên Kho kỹ năng học đường.", "success")',
     'flash(_("Đăng ký thành công! %(reason)s. Kỹ năng đã sẵn sàng trên Kho kỹ năng học đường.", reason=ly_do_luu), "success")'),

    ('flash(f"Kỹ năng đang ở trạng thái \'Chờ duyệt\' để Giáo viên thẩm định thêm. {ly_do_luu}", "warning")',
     'flash(_("Kỹ năng đang ở trạng thái \'Chờ duyệt\' để Giáo viên thẩm định thêm. %(reason)s", reason=ly_do_luu), "warning")'),

    # 9. Booking session
    ('flash(f"Số dư tín dụng của bạn không đủ để đặt lịch buổi học này! (Hiện có: {learner[\'so_du_gio\']:.1f}h, Cần: {so_gio:.1f}h). Hãy dạy kèm bạn bè để tích thêm giờ nhé!", "danger")',
     'flash(_("Số dư tín dụng của bạn không đủ để đặt lịch buổi học này! (Hiện có: %(cur).1fh, Cần: %(need).1fh). Hãy dạy kèm bạn bè để tích thêm giờ nhé!", cur=learner[\'so_du_gio\'], need=so_gio), "danger")'),

    ('flash(f"Đặt lịch học thành công với {tutor_name} ({so_gio:.1f} giờ)! Cả hai bạn đều có thể theo dõi trong \'Lịch của tôi\'.", "success")',
     'flash(_("Đặt lịch học thành công với %(tutor)s (%(hrs).1f giờ)! Cả hai bạn đều có thể theo dõi trong \'Lịch của tôi\'.", tutor=tutor_name, hrs=so_gio), "success")'),

    # 10. Session completion & quiz
    ('flash(f"Phiên học hiện đang ở trạng thái \'{s_row[\'trang_thai\']}\', không thể điểm danh check-in!", "warning")',
     'flash(_("Phiên học hiện đang ở trạng thái \'%(st)s\', không thể điểm danh check-in!", st=s_row[\'trang_thai\']), "warning")'),

    ('flash(f"Phiên học này hiện đang ở trạng thái \'{s_row[\'trang_thai\']}\', không thể xác nhận hoàn thành lại!", "warning")',
     'flash(_("Phiên học này hiện đang ở trạng thái \'%(st)s\', không thể xác nhận hoàn thành lại!", st=s_row[\'trang_thai\']), "warning")'),

    ('flash(f"Buổi học đã hoàn thành xuất sắc! Đã cộng +{so_gio:.1f}h cho người dạy và trừ -{so_gio:.1f}h của người học.", "success")',
     'flash(_("Buổi học đã hoàn thành xuất sắc! Đã cộng +%(hrs).1fh cho người dạy và trừ -%(hrs).1fh của người học.", hrs=so_gio), "success")'),

    ('flash(f"Có lỗi xảy ra trong quá trình hoàn thành phiên học: {e}", "danger")',
     'flash(_("Có lỗi xảy ra trong quá trình hoàn thành phiên học: %(err)s", err=str(e)), "danger")'),

    ('flash(f"Chúc mừng em! Em đã làm đúng {correct_count}/{total_count} câu ({pct*100:.0f}%) — ĐẠT CHUẨN KIẾN THỨC!", "success")',
     'flash(_("Chúc mừng em! Em đã làm đúng %(c)s/%(t)s câu (%(pct).0f%%) — ĐẠT CHUẨN KIẾN THỨC!", c=correct_count, t=total_count, pct=pct*100), "success")'),

    ('flash(f"Em đã hoàn thành bài quiz: đúng {correct_count}/{total_count} câu ({pct*100:.0f}%). Hãy ôn lại các đáp án giải thích để nắm vững kiến thức hơn nhé!", "info")',
     'flash(_("Em đã hoàn thành bài quiz: đúng %(c)s/%(t)s câu (%(pct).0f%%). Hãy ôn lại các đáp án giải thích để nắm vững kiến thức hơn nhé!", c=correct_count, t=total_count, pct=pct*100), "info")'),

    # 11. Virtual room completion
    ('flash(f"Buổi học đã hoàn thành xuất sắc! Thời lượng cùng học online đạt {ti_le*100:.1f}% (≥ 80%), giờ tín dụng đã được tự động chuyển thành công.", "success")',
     'flash(_("Buổi học đã hoàn thành xuất sắc! Thời lượng cùng học online đạt %(rate).1f%% (≥ 80%%), giờ tín dụng đã được tự động chuyển thành công.", rate=ti_le*100), "success")'),

    ('flash(f"Thời lượng cùng học trực tuyến chưa đạt 80% quy định (chỉ đạt {ti_le*100:.1f}% / 80%). Phiên học đã chuyển sang trạng thái \'Cần xác minh\' để Thầy/Cô kiểm tra và phê duyệt tay.", "warning")',
     'flash(_("Thời lượng cùng học trực tuyến chưa đạt 80%% quy định (chỉ đạt %(rate).1f%% / 80%%). Phiên học đã chuyển sang trạng thái \'Cần xác minh\' để Thầy/Cô kiểm tra và phê duyệt tay.", rate=ti_le*100), "warning")'),

    ('flash(f"Đã duyệt tay thành công phiên #{session_id}! Giờ tín dụng đã được chuyển cho hai học sinh.", "success")',
     'flash(_("Đã duyệt tay thành công phiên #%(id)s! Giờ tín dụng đã được chuyển cho hai học sinh.", id=session_id), "success")'),

    ('flash(f"Đã hủy phiên học #{session_id}.", "info")',
     'flash(_("Đã hủy phiên học #%(id)s.", id=session_id), "info")'),

    # 12. Community tasks & attendance
    ('flash(f"Đã tạo thành công nhiệm vụ: \'{tieu_de}\' (+{so_gio_thuong}h thưởng)!", "success")',
     'flash(_("Đã tạo thành công nhiệm vụ: \'%(title)s\' (+%(hrs)sh thưởng)!", title=tieu_de, hrs=so_gio_thuong), "success")'),

    ('flash(f"Nhiệm vụ đã đủ số lượng người đăng ký ({task[\'so_luong_toi_da\']} bạn).", "warning")',
     'flash(_("Nhiệm vụ đã đủ số lượng người đăng ký (%(max)s bạn).", max=task[\'so_luong_toi_da\']), "warning")'),

    ('flash(f"Đăng ký tham gia \'{task[\'tieu_de\']}\' thành công! Hãy có mặt đúng giờ nhé.", "success")',
     'flash(_("Đăng ký tham gia \'%(title)s\' thành công! Hãy có mặt đúng giờ nhé.", title=task[\'tieu_de\']), "success")'),

    ('flash(f"Điểm danh thành công! Đã ghi nhận {so_ban_hoan_thanh} bạn hoàn thành (+{so_gio_thuong}h vào ví) và {so_ban_vang} bạn vắng mặt.", "success")',
     'flash(_("Điểm danh thành công! Đã ghi nhận %(done)s bạn hoàn thành (+%(hrs)sh vào ví) và %(absent)s bạn vắng mặt.", done=so_ban_hoan_thanh, hrs=so_gio_thuong, absent=so_ban_vang), "success")'),

    # 13. AI moderation
    ('flash(f"⚠️ Bài viết của bạn bị AI từ chối đăng do vi phạm quy chuẩn ngôn ngữ học đường ({reason}). Hệ thống đã ghi nhận vi phạm vào Sổ kỷ luật.", "danger")',
     'flash(_("⚠️ Bài viết của bạn bị AI từ chối đăng do vi phạm quy chuẩn ngôn ngữ học đường (%(reason)s). Hệ thống đã ghi nhận vi phạm vào Sổ kỷ luật.", reason=reason), "danger")'),

    ('flash(f"⚠️ Bình luận bị AI chặn do vi phạm quy chuẩn ngôn ngữ ({reason}). Vi phạm đã được ghi nhận vào Sổ kỷ luật.", "danger")',
     'flash(_("⚠️ Bình luận bị AI chặn do vi phạm quy chuẩn ngôn ngữ (%(reason)s). Vi phạm đã được ghi nhận vào Sổ kỷ luật.", reason=reason), "danger")'),

    # 14. Document drive upload & delete
    ('flash(f"Tệp \'{orig_name}\' vượt quá dung lượng tối đa cho phép (500MB), đã bị bỏ qua.", "danger")',
     'flash(_("Tệp \'%(name)s\' vượt quá dung lượng tối đa cho phép (500MB), đã bị bỏ qua.", name=orig_name), "danger")'),

    ('flash(f"Lỗi khi tải tệp \'{orig_name}\' lên hệ thống: {str(e)}", "danger")',
     'flash(_("Lỗi khi tải tệp \'%(name)s\' lên hệ thống: %(err)s", name=orig_name, err=str(e)), "danger")'),

    ('flash(f"Tải lên kho tạm (chưa kết nối hệ thống), vui lòng liên hệ quản trị viên. Tài liệu \'{single_title}\' đã được lưu tạm. Đã tải 1/1 thành công.", "warning")',
     'flash(_("Tải lên kho tạm (chưa kết nối hệ thống), vui lòng liên hệ quản trị viên. Tài liệu \'%(title)s\' đã được lưu tạm. Đã tải 1/1 thành công.", title=single_title), "warning")'),

    ('flash(f"🎉 Tải lên tài liệu \'{single_title}\' thành công vào thư mục {mon_hoc} trên hệ thống! Đã tải 1/1 thành công.", "success")',
     'flash(_("🎉 Tải lên tài liệu \'%(title)s\' thành công vào thư mục %(folder)s trên hệ thống! Đã tải 1/1 thành công.", title=single_title, folder=mon_hoc), "success")'),

    ('flash(f"Tải lên kho tạm (chưa kết nối hệ thống), vui lòng liên hệ quản trị viên. Đã tải {success_count}/{total_files} thành công.", "warning")',
     'flash(_("Tải lên kho tạm (chưa kết nối hệ thống), vui lòng liên hệ quản trị viên. Đã tải %(sc)s/%(tf)s thành công.", sc=success_count, tf=total_files), "warning")'),

    ('flash(f"🎉 Đã tải {success_count}/{total_files} thành công vào thư mục {mon_hoc} trên hệ thống!", "success")',
     'flash(_("🎉 Đã tải %(sc)s/%(tf)s thành công vào thư mục %(folder)s trên hệ thống!", sc=success_count, tf=total_files, folder=mon_hoc), "success")'),

    ('flash(f"Không có tài liệu nào được tải lên thành công (0/{total_files}).", "danger")',
     'flash(_("Không có tài liệu nào được tải lên thành công (0/%(tf)s).", tf=total_files), "danger")'),

    ('flash(f"Không thể tải tài liệu từ hệ thống: {str(e)}", "danger")',
     'flash(_("Không thể tải tài liệu từ hệ thống: %(err)s", err=str(e)), "danger")'),

    ('flash(f"Đã xóa tài liệu \'{doc[\'tieu_de\']}\' khỏi hệ thống thành công.", "success")',
     'flash(_("Đã xóa tài liệu \'%(title)s\' khỏi hệ thống thành công.", title=doc[\'tieu_de\']), "success")'),
]

applied = 0
for src, dst in fstring_replacements:
    if src in content:
        content = content.replace(src, dst)
        applied += 1
    else:
        print(f"Warning: fstring pattern not found:\n{src[:60]}")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Applied {applied}/{len(fstring_replacements)} fstring flash replacements in app.py")
