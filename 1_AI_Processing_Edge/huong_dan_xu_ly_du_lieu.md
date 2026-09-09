# Hướng dẫn xử lý dữ liệu — Dataset nhận diện phương tiện giao thông (Cam góc rộng 180°)

## Mục tiêu

Chuẩn bị dữ liệu ảnh + nhãn (bounding box) để fine-tune model YOLO11n, bổ sung 2 lớp mới **xích lô (xich_lo)** và **xe kéo (xe_keo)**, đồng thời giữ nguyên khả năng nhận diện các lớp phương tiện đã có (người, xe đạp, xe máy, ô tô, xe buýt, xe tải).

---

## Quy trình từng bước

### Bước 1: Lấy dữ liệu gốc

- Vào thư mục Drive, ở folder Label theo đúng tên folder mà mình đã phân công (mỗi bạn phụ trách 1 folder cụ thể — xem trong bảng phân công riêng).
- Tải video về máy, giữ nguyên tên file gốc (dạng timestamp, ví dụ `20260817_16_55_58.mp4`) — **không đổi tên**, vì tên gốc dùng để truy vết lại video nguồn sau này nếu cần kiểm tra.

### Bước 2: Kiểm tra và xử lý sơ bộ video/ảnh

Trước khi đưa vào thư mục `kept`, kiểm tra và xử lý các trường hợp sau:

| Trường hợp | Cách xử lý |
|---|---|
| Ảnh/video quá mờ, nhòe (rung tay, xe di chuyển nhanh) | Loại ra, **không đưa vào** `kept` |
| Ảnh/video bị lặp gần như y hệt nhau (video đứng yên quá lâu tại 1 điểm) | Chỉ giữ lại 1–2 ảnh đại diện, loại phần trùng lặp |
| Video bị lật ngược (trên xuống dưới, hoặc quay 180°) | **Xoay lại đúng chiều trước**, không loại bỏ — xem hướng dẫn xoay ở phần Công cụ bên dưới |
| Video bị che ống kính, chói sáng hoàn toàn không thấy gì | Loại ra |
| Video chói sáng 1 phần nhưng vẫn thấy rõ đường/xe ở phần còn lại | **Giữ lại**, không loại — vẫn có giá trị cho model học điều kiện ánh sáng khó |

**Nếu không chắc 1 ảnh/video có nên giữ hay không → giữ lại, hỏi lại nhóm trước khi xóa.** Không tự ý xóa khi còn phân vân.

### Bước 3: Đưa vào thư mục `kept` trong `frame_extraction`, chạy pseudo-labeling

1. Copy toàn bộ ảnh đã lọc sạch (Bước 2) vào đúng thư mục:
   ```
   frame_extraction/kept/
   ```
2. Chạy lệnh sau để YOLO11 tự động gán nhãn trước (pseudo-labeling) cho các lớp đã có sẵn (người, xe đạp, xe máy, ô tô, xe buýt, xe tải):
   ```bash
   python 1_AI_Processing_Edge/pseudo_labeling/pseudo_labeler.py
   ```
3. Sau khi chạy xong, kiểm tra thư mục output có đủ 2 phần: ảnh và file nhãn `.txt` tương ứng (tên file ảnh và tên file nhãn phải trùng nhau, chỉ khác đuôi mở rộng).

### Bước 4: Upload lên Roboflow, gán nhãn bổ sung

1. Chuẩn bị 3 thứ: thư mục `images/`, thư mục `labels/` (kết quả từ Bước 3), và file `classes.txt` (lấy trên drive)
2. Nén `images/` và `labels/` (đã có `classes.txt` bên trong `labels/`) thành 1 file `.zip`, upload lên project Roboflow để xử lí.
3. Sau khi upload, duyệt qua **từng ảnh**:
   - Kiểm tra các box có sẵn (do YOLO tự gán) — sửa lại nếu box bị lệch, sai lớp, hoặc bỏ nếu box đó không đúng (false positive)
   - Với xe/vật thể trong ảnh mà **chưa có box nào bao quanh** (đặc biệt là xích lô, xe kéo — vì model gốc không tự nhận ra được) → tự vẽ tay thêm box, chọn đúng lớp `xich_lo` hoặc `xe_keo`
4. Nếu gặp ảnh có phương tiện lạ, không chắc nên xếp vào lớp nào → **để lại, đánh dấu ghi chú, hỏi nhóm** trước khi tự ý gán nhãn hoặc bỏ qua.

---

## ⚠️ Những điều cần đặc biệt lưu ý

- **Hạn chế xóa dữ liệu nhất có thể.** Hiện tại dữ liệu, đặc biệt là ảnh có xích lô/xe kéo, đang rất ít. Một ảnh tưởng như "không cần" vẫn có thể hữu ích. Nếu không chắc, giữ lại và hỏi nhóm thay vì tự xóa.
- **Video/ảnh bị lật ngược: nhớ xoay lại trước khi dùng, không bỏ qua và cũng không xóa.** Đây vẫn là dữ liệu tốt, chỉ cần chỉnh đúng chiều.
- **Không tự đổi tên file ảnh/video gốc** — giữ nguyên tên timestamp gốc để có thể truy vết lại nguồn khi cần kiểm tra hoặc sửa lỗi.
- **Ưu tiên số 1 khi duyệt ảnh: tìm và gán nhãn xích lô, xe kéo.** Đây là 2 lớp thiếu dữ liệu nhất, quan trọng nhất hiện tại — nếu thấy ảnh có 2 loại xe này, dành thời gian gán cẩn thận, chính xác.
- **Không tự thêm/sửa danh sách lớp (classes) trên Roboflow một mình.** Nếu thấy cần thêm lớp mới ngoài danh sách đã thống nhất, báo cho cả nhóm trước, tránh mỗi người tự đặt tên lớp khác nhau gây lộn xộn dữ liệu (ví dụ người gõ `xich_lo`, người gõ `xichlo`, người gõ `cyclo` — sẽ bị tính thành 3 lớp khác nhau).
- **Vẽ bounding box sát viền vật thể thật, không vẽ dư ra ngoài hoặc thiếu vào trong.** Box càng chính xác, model học càng tốt.
- **Nếu 1 vật thể bị che khuất một phần** (ví dụ xích lô bị xe khác che mất nửa) — vẫn vẽ box quanh phần nhìn thấy được, không bỏ qua hoàn toàn.
- **Làm xong phần nào, thông báo lại nhóm phần đó** (ví dụ đã xử lý xong folder nào, đã upload xong batch nào) để tránh trùng lặp công việc giữa các thành viên.
