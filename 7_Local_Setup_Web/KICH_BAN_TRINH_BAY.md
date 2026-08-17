# Kịch bản trình bày — Web cài đặt tại xe (Tier 1)

> Tài liệu này để **đọc/nói trước nhóm**, không phải tài liệu kỹ thuật. Tài liệu kỹ thuật đầy đủ xem ở `README.md` cùng thư mục.

Thời lượng gợi ý: 8–10 phút nói + 5 phút demo tay + hỏi đáp.

---

## 1. Mở đầu — vấn đề đang giải quyết (1 phút)

> "Hệ thống vùng mù động của mình cần biết 2 thứ để hoạt động đúng trên một xe cụ thể: **kích thước xe** và **góc lắp của 4 camera**. Hai thông tin này khác nhau hoàn toàn giữa xe A và xe B — đầu kéo container khác xe bus, camera lắp lệch 5 độ là vùng mù vẽ sai vị trí.
>
> Trước đây, muốn nhập 2 thông tin này thì phải **tự sửa file Python** — file `config.py` — với hơn 25 con số. Việc này đòi hỏi biết code, dễ nhập sai đơn vị (cm với m), sai dấu (trái/phải), và quan trọng nhất là **không có cách nào tự kiểm tra góc camera đúng hay chưa** trước khi chạy thật.
>
> Mình làm web này để kỹ thuật viên lắp xe — người không biết code — có thể tự làm hết việc đó, ngay trên xe, bằng điện thoại, và có số liệu chứng minh là đã làm đúng."

---

## 2. Cho xem: chạy được ngay, không cần chờ phần cứng (1 phút)

> "Điểm quan trọng đầu tiên: cái này chạy đầy đủ **ngay trên laptop**, không cần Jetson, không cần camera, không cần GPS. Vì sao làm được — mình vẽ ảnh camera giả bằng **đúng công thức toán của camera thật** (ma trận K và [R|T] mà anh Nhật đã viết trong `camera_calibration.py`), không phải ảnh vẽ bừa. Nên toàn bộ quy trình test, demo, và thậm chí unit test tự động đều chạy được mà không cần đợi ráp xong phần cứng."

*(Demo: mở `http://127.0.0.1:8080`, chỉ nói 1 câu, chuyển sang phần luồng chính)*

---

## 3. Luồng 6 bước (3–4 phút, vừa nói vừa demo)

> "Toàn bộ quy trình lắp đặt gói trong 6 bước."

### Bước 1 — Hồ sơ xe
> "Nhập biển số, chọn loại xe. Có 2 loại: **đầu kéo + sơ-mi rơ-moóc** (có khớp nối, thân xe gập được khi rẽ) và **xe thân liền** (bus, xe bồn — không có khớp nối). Chọn mẫu có sẵn để điền nhanh kích thước gần đúng, đỡ gõ từ đầu."

### Bước 2 — Kích thước
> "Chỉ cần đo **5 số bằng thước dây** — chiều dài cơ sở, rộng cabin, dài/rộng rơ-moóc, chiều cao tài xế. Hệ thống tự tính ra 25 thông số hình học còn lại — vị trí mắt tài xế, vị trí gương, vị trí cột A, cột B... Sơ đồ xe vẽ lại ngay khi mình gõ số, và tô đỏ đúng đoạn cần đo khi con trỏ đặt vào ô đó."

*(Demo: gõ số vào 1 ô, cho xem sơ đồ đổi theo)*

### Bước 3 — Lắp camera
> "4 camera: phải, trái, trước, sau. Nhập địa chỉ camera và góc nhìn ống kính — số này ghi sẵn trên hộp máy, ví dụ 120 độ. Vị trí lắp mặc định lấy tự động theo vị trí gương/mũi xe/đuôi xe đã tính ở bước trước."

### Bước 4 — Căn chỉnh (bước quan trọng nhất, nói kỹ)
> "Đây là bước giải quyết đúng vấn đề ban đầu: làm sao biết góc camera đúng mà không cần đo góc trực tiếp.
>
> Cách làm: đặt 4 chóp nón ngoài bãi, đo khoảng cách từng chóp nón đến xe bằng thước dây, nhập số đo vào đây. Rồi chạm vào ảnh camera, đúng vị trí chân từng chóp nón. Bấm 'Giải góc lắp' — hệ thống tự tìm ra góc chúi và góc quay của camera, và **báo sai số bằng mét**. Đạt khi sai số dưới 0.3 mét.
>
> Đây không phải mình tự nghĩ ra công thức — nó gọi thẳng hàm chiếu camera trong `camera_calibration.py`, chạy ngược lại để tìm góc."

*(Demo: chạm 4 điểm, bấm giải góc, cho xem số RMS ra 0.000 vì là mô phỏng khớp hoàn hảo — nói rõ đây là môi trường test, ngoài thực tế con số sẽ khác 0 một chút)*

### Bước 5 — Vùng mù
> "Xem trước 4 vùng mù chính khớp với 4 camera. Kéo thanh trượt tốc độ và góc rẽ để xem vùng mù **biến dạng khi xe rẽ** — đây chính là công thức toán vùng mù động của đề tài, lấy thẳng từ `occlusion_calculator.py`, không có công thức riêng nào ở web."

*(Demo: kéo thanh trượt góc rẽ, cho xem vùng mù méo đi)*

### Bước 6 — Nghiệm thu
> "Kiểm tra danh sách việc cần làm, xuất file cấu hình, in biên bản bàn giao có chữ ký."

---

## 4. Cách nối với code toán của nhóm — điểm cần nhấn mạnh (1–2 phút)

> "Điểm mình muốn nhấn ở đây: **web này không viết lại một công thức toán nào**. Toàn bộ công thức — suy hình học xe, chiếu camera, tính vùng mù — đều gọi thẳng vào code mà anh Nhật đã viết ở `2_BlindSpot_Risk_Calculation`. Web chỉ là lớp giao diện đứng trước.
>
> Cách làm: mình nạp module `config.py` gốc, rồi mỗi lần tính thì gán lại các hằng số trong module đó theo đúng xe đang xem, rồi gọi hàm tính của engine. Nên **công thức chạy trên web và công thức chạy thật trên xe là cùng một hàm Python** — không phải hai bản có thể lệch nhau theo thời gian.
>
> Có bộ test tự động kiểm tra điều này: nếu sau này ai sửa công thức bên engine mà quên sửa bên web, test sẽ báo lỗi ngay, không phải chờ chạy thật mới phát hiện."

---

## 5. Xuất file — kết quả cuối cùng (1 phút)

> "Sau khi làm xong 6 bước, bấm xuất ra file `config.py` — copy đè vào đúng vị trí trong `2_BlindSpot_Risk_Calculation`, không cần sửa gì thêm, hệ thống nhận diện chạy được ngay với xe đó."

---

## 6. Việc còn thiếu — nói thẳng, không giấu (30 giây)

> "3 việc chưa làm, cần làm khi có phần cứng thật:
> 1. Đọc GPS/IMU thật qua cổng UART/I2C — hiện đang là số giả để demo.
> 2. Script cho Jetson tự phát Wi-Fi để điện thoại kết nối vào — hiện phải chạy trên máy có sẵn mạng.
> 3. Góc lắc hông (roll) của camera — phát hiện ra công thức xoay trong `camera_calibration.py` đang thiếu 1 phép xoay, chưa sửa vì đó là code của anh Nhật, cần thống nhất trước khi sửa."

---

## 7. Câu hỏi dự kiến & cách trả lời

**"Sao không dùng OpenCV/ArUco để tự nhận diện chóp nón, đỡ phải chạm tay?"**
> Có thể làm được, nhưng đó là cải tiến sau. Chạm tay hiện tại đơn giản, không phụ thuộc điều kiện ánh sáng, và MVP cần chạy được trước.

**"Nếu kỹ thuật viên nhập sai số đo thì sao?"**
> Có 2 lớp chặn: (1) cảnh báo tự động khi số đo nằm ngoài khoảng hợp lý (ví dụ nghi nhập cm thay vì m), (2) sai số RMS sau khi giải góc sẽ cao bất thường nếu số đo sai, kỹ thuật viên biết ngay để đo lại.

**"Ai cũng vào sửa được cấu hình xe không?"**
> Mặc định thì có, vì đang chạy trên Wi-Fi mở. Đã có sẵn cơ chế mã PIN bảo vệ, chỉ cần bật lên trước khi giao xe cho khách — có ghi rõ trong tài liệu.

**"Cái này chạy trên Jetson khác gì trên laptop?"**
> Code giống 100%, chỉ đổi 1 biến môi trường để chuyển từ ảnh giả sang camera thật. Không có bước biên dịch/flash riêng.
