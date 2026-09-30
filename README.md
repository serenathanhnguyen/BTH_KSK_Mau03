# Bảng Tổng Hợp KSK — công cụ Streamlit

Ứng dụng đọc file Mẫu 03 (Medinet, sheet `ThongTinHanhChinh`) và xuất ra
**Bảng Tổng Hợp Phân Loại Sức Khỏe** theo đúng khung mẫu Trạm Y tế đang dùng,
tự động tính BMI, chọn cặp thị lực, gộp phân loại lâm sàng, đánh dấu in
đậm/nghiêng cho các chỉ số cận lâm sàng ngoài tham chiếu, và sinh nhận xét mô
tả cho cột Tổng phân tích tế bào máu (CTM).

Toàn bộ quy tắc nghiệp vụ dựa trên `Khung_nguyen_tac_BTH_KSK_Streamlit_v2.md`
(bản 2, chốt 29/09/2026) và các quy tắc đã thống nhất trước đó trong
`khung-mau-bang-tong-hop-suc-khoe.md`. Mọi chỗ tài liệu gốc còn ghi "Trống"
(chưa chốt) đều được cài đặt theo hướng AN TOÀN NHẤT (để trống, không suy
diễn) trừ khi mục "Giá trị hiện tại" trong bảng mục 6 của tài liệu đã nêu rõ
câu trả lời — xem chi tiết ở mục **"Các quyết định đã tự đưa ra"** bên dưới.

## Chạy thử ở máy / môi trường của bạn

```bash
pip install -r requirements.txt
streamlit run app.py
```

Mở trình duyệt tới địa chỉ Streamlit in ra (mặc định `http://localhost:8501`),
tải lên một file Mẫu 03 `.xlsx` và làm theo các bước trên giao diện.

Đã có sẵn `sample_data/mau_03_sample_fake.xlsx` — dữ liệu **hoàn toàn hư
cấu** (không phải người thật) để bạn thử ứng dụng ngay mà không cần file
khám thật.

## Kiểm tra nhanh (không cần mở giao diện)

```bash
python3 tests/smoke_test.py
```

Script này chạy toàn bộ pipeline trên dữ liệu mẫu hư cấu và in kết quả — nếu
thấy dòng cuối `TAT CA KIEM TRA DEU PASS.` là mọi module hoạt động đúng.

## Đưa lên GitHub

```bash
cd bth_ksk_app
git init
git add .
git commit -m "Khoi tao ung dung Bang Tong Hop KSK"
git branch -M main
git remote add origin https://github.com/<tai-khoan-cua-ban>/<ten-repo>.git
git push -u origin main
```

`.gitignore` đã chặn mọi file `.xlsx` ngoại trừ file mẫu hư cấu trong
`sample_data/` — **không có nguy cơ vô tình commit file khám thật** miễn là
bạn không đổi tên file dữ liệu thật thành trùng với các ngoại lệ đó.

## Triển khai lên Streamlit Community Cloud (miễn phí)

1. Vào https://share.streamlit.io, đăng nhập bằng tài khoản GitHub.
2. Chọn "New app" → chọn repo vừa push, branch `main`, file chính `app.py`.
3. Bấm Deploy. Sau vài phút sẽ có một đường link công khai dạng
   `https://<ten-app>.streamlit.app`.
4. **Lưu ý bảo mật:** app ở chế độ public link (ai có link đều mở được).
   File khám thật của bạn chỉ nằm trong RAM của phiên làm việc trong lúc
   dùng — không được lưu lại trên Streamlit Cloud sau khi đóng tab — nhưng
   vì đây là dữ liệu sức khỏe, bạn nên cân nhắc trước khi tải file thật lên
   một dịch vụ công khai bên ngoài; có thể đặt Streamlit ở chế độ private
   (yêu cầu đăng nhập, cần gói trả phí) hoặc chạy app trên máy/server nội bộ
   của trạm thay vì dùng bản public miễn phí.

## Cấu trúc mã

| File | Vai trò |
|---|---|
| `app.py` | Giao diện Streamlit |
| `mapping.json` / `mapping.py` | Cấu hình cột đích, tách khỏi giao diện |
| `lab_reference.json` | Khoảng tham chiếu sinh hóa máu + nước tiểu |
| `cbc_reference.json` | Khoảng tham chiếu công thức máu (Hb/MCV/WBC/PLT) |
| `reader.py` | Đọc file M03 theo keyword hàng 4 (không phụ thuộc vị trí cột) |
| `transforms.py` | Các hàm chuẩn hoá/suy luận từng trường |
| `cbc_rules.py` | Logic ghép câu nhận xét cột CTM |
| `pipeline.py` | Lớp nghiệp vụ trung tâm — ghép tất cả module trên thành 1 bản ghi/người |
| `report.py` | Nhân bản `templates/BTH_KSK_template.xlsx` rồi chỉnh sửa trực tiếp (xoá cột trống, chèn/xoá dòng, remerge, điền dữ liệu + reset in đậm/nghiêng, sửa công thức) — CÙNG một phương pháp đã dùng để dựng các bảng VISSAN/Hải Thịnh/Thái Thịnh trước đó, không dựng workbook rỗng từ đầu |
| `templates/BTH_KSK_template.xlsx` | Bản mẫu chuẩn (đã xoá hết dữ liệu cá nhân ở 10 dòng mẫu, chỉ giữ định dạng) — đã có sẵn đủ cột Urê/Acid Uric/X-quang/Cảnh báo theo đúng thứ tự khung nguyên tắc, và đã đặt sẵn khổ A4 ngang + Fit to width |
| `sample_data/mau_03_sample_fake.xlsx` | Dữ liệu mẫu hư cấu để test |
| `tests/smoke_test.py` | Kiểm tra nhanh toàn bộ pipeline (đã test cả trường hợp <10 và >10 người) |

### Về việc in vừa khổ A4 (cập nhật 30/09/2026)

Phiên bản trước đã bị dựng lại `report.py` thành một workbook hoàn toàn mới
bằng code — việc này vô tình làm thay đổi cách bố trí/ánh xạ cột so với các
file Jo đã quen dùng, nên không dùng được. Đã **làm lại theo đúng cách cũ**:
`report.py` giờ chỉ thao tác trên bản sao của `templates/BTH_KSK_template.xlsx`
(xoá cột không có dữ liệu, chèn/xoá dòng, điền số liệu, sửa công thức) — cách
ánh xạ dữ liệu (`mapping.json`/`pipeline.py`/`transforms.py`) không đổi gì so
với trước. Phần MỚI duy nhất là khổ giấy: `templates/BTH_KSK_template.xlsx`
đã đặt sẵn A4 ngang + "Fit to width = 1 trang" (toàn bộ cột nằm gọn 1 trang
khi in ngang, số người nhiều thì chảy xuống nhiều trang dọc), tiêu đề cột vẫn
in đậm + căn giữa như bản gốc bạn đã cung cấp ban đầu.

## ⚠️ Cần bạn xác nhận trước khi dùng chính thức

1. **Khoảng tham chiếu Glucose và HDL-Cholesterol** (`lab_reference.json`,
   trường `can_xac_nhan: true`) — hai chỉ số này bị mâu thuẫn giữa ảnh
   "Sinh hóa máu" trước đó và phiếu xét nghiệm bệnh nhân gửi 29/09/2026.
   Đang dùng tạm giá trị đã duyệt gần nhất; ứng dụng sẽ tự hiện cảnh báo đỏ
   trên giao diện cho tới khi bạn sửa file JSON và xoá cờ `can_xac_nhan`.
2. **Khoảng tham chiếu Hb theo giới/tuổi/thai kỳ** (`cbc_reference.json`) —
   hiện chỉ có MỘT khoảng chung 11.0–17.5 g/dL lấy tạm từ phiếu minh hoạ của
   trạm, áp dụng chung cho nam và nữ không mang thai; nhóm "nữ mang thai" và
   "khác" chưa có ngưỡng nên ứng dụng sẽ báo "Chưa đủ dữ liệu đánh giá" cho
   các trường hợp đó — cần bộ phận xét nghiệm cung cấp và duyệt các khoảng
   này trước khi dùng chính thức.
3. **Đơn vị Hb thực tế trong file M03 của trạm** — header ghi (g/L) nhưng số
   liệu mẫu quan sát được có dạng g/dL; giao diện có ô chọn đơn vị thủ công
   ở bước 2, mặc định g/dL — kiểm tra lại đúng với file thật của trạm.

## Các quyết định đã tự đưa ra (theo yêu cầu "tự làm, đừng hỏi thêm")

- **Xếp loại** = giá trị lớn nhất trong TẤT CẢ các cột `*_phanloai` đọc được
  từ file gốc (trừ `theluc_phanloai` nếu có) — đúng theo mục 6 của khung
  nguyên tắc, và tương đương cách tính đã dùng trong các bảng trước đó.
- **Sản phụ khoa** = lớn nhất giữa phân loại Sản khoa và Phụ khoa; "Từ chối
  khám" được ghi là trạng thái riêng ("Từ chối khám"), không tính là một mức
  phân loại 1–5.
- **Thị lực (P/T)** = chọn cặp (không kính / kính lỗ / có kính) có tổng hai
  mắt lớn nhất trong ba cặp — mỗi người thường chỉ có một cặp có dữ liệu.
- **Ghi chú** = ưu tiên "Ghi rõ" (`de_nghi`) → "Kết luận" (`danh_muc_de_nghi`)
  → ghép ICD (phương án cuối) — quy tắc Jo đã chốt trong phiên làm việc
  trước, ưu tiên hơn phần "Trống" còn để ngỏ trong khung nguyên tắc gốc.
- **Nước tiểu** (bt/x theo Tỉ trọng/pH) — mặc định BẬT (giống thực tế đã làm
  trước đây), có thể tắt trong giao diện nếu trạm muốn để trống hoàn toàn
  như khung nguyên tắc gốc đề xuất.
- **Cholesterol / Triglycerid / HDL / LDL / Acid Uric / Siêu âm tổng quát** —
  KHÔNG tự đoán keyword; giao diện bắt người dùng chọn thủ công cột nguồn
  nếu file có đo các chỉ số này (đúng yêu cầu "không tự ghép theo tên gần
  giống" của khung nguyên tắc).
- **Siêu âm / X-quang** — giữ nguyên văn nội dung từ file gốc, không tự suy
  luận bt/x.
- **Cột trống hoàn toàn ở mọi người** (ví dụ Cholesterol khi file không đo) —
  tự động ẩn khỏi báo cáo xuất ra, đúng quy tắc đã áp dụng nhất quán từ
  trước; có nút chuyển sang "Tự chọn cột" nếu muốn ép hiện/ẩn thủ công.
- **Ngày ký cuối bảng** — luôn giữ dạng chấm chấm để trống
  ("Ngày ......... tháng ......... năm ........."), không tự điền số.
- **Báo cáo không lưu trên GitHub** — dữ liệu khám thật chỉ đi qua RAM của
  phiên Streamlit, không ghi log tên/CCCD, không commit file thật (xem
  `.gitignore`).
