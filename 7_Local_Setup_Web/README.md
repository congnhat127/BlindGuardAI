# Web cài đặt tại xe (BlindGuard AI — Tier 1)

Công cụ để kỹ thuật viên **tự thiết lập và căn chỉnh** hệ thống vùng mù động ngay trên xe, bằng điện thoại hoặc iPad — không cần cắm bàn phím/màn hình vào Jetson, không cần biết code.

Đặc điểm quan trọng nhất: **chạy được đầy đủ khi chưa có camera/GPS thật.** Ở chế độ mô phỏng, hệ thống tự vẽ khung hình camera bằng đúng công thức toán camera thật (`K + [R|T]`), nên toàn bộ quy trình — nhập kích thước, căn chỉnh camera, tính sai số, xuất file — chạy và kiểm tra được ngay trên laptop. Khi có phần cứng thật, chỉ đổi 1 biến môi trường, không sửa code.

---

## 1. Tóm tắt cho người không đọc code

Hệ thống vùng mù động cần biết 2 thứ để hoạt động đúng trên một xe cụ thể:

1. **Kích thước xe** (dài, rộng, có rơ-moóc hay không) — để biết vùng mù nằm ở đâu quanh xe.
2. **Góc lắp của 4 camera** (chúi xuống bao nhiêu độ, quay sang hướng nào) — để biết camera đang nhìn thấy đúng phần mặt đường nào.

Nếu không có công cụ này, kỹ thuật viên phải **tự tay sửa file Python** (`config.py`) để nhập 25+ con số — việc này cần biết code, dễ nhập sai đơn vị, sai dấu, và không thể tự kiểm tra góc camera có đúng hay không.

Web này thay thế việc đó bằng 6 bước có giao diện, kèm cách đo/nhập rõ ràng, và **tự kiểm tra bằng số** (sai số căn chỉnh tính bằng mét) trước khi xác nhận xong.

---

## 2. Quy trình 6 bước (cho người dùng cuối)

| Bước | Tên | Kỹ thuật viên làm gì |
|---|---|---|
| 1 | **Hồ sơ xe** | Nhập biển số, chọn loại xe (đầu kéo + rơ-moóc / thân liền), chọn mẫu có sẵn để điền nhanh |
| 2 | **Kích thước** | Đo 5 số bằng thước dây (chiều dài cơ sở, rộng cabin, dài/rộng rơ-moóc, chiều cao tài xế). Hệ thống tự suy ra 25 thông số còn lại và vẽ lại sơ đồ xe ngay khi gõ số |
| 3 | **Lắp camera** | Nhập nguồn tín hiệu (địa chỉ camera) và góc nhìn ống kính (ghi trên hộp máy) cho 4 camera: phải, trái, trước, sau |
| 4 | **Căn chỉnh** | Đặt 4 chóp nón ngoài bãi, đo khoảng cách bằng thước, nhập số đo, chạm vào ảnh camera đúng vị trí từng chóp nón, bấm "Giải góc lắp" → hệ thống tự tính góc và báo sai số bằng mét |
| 5 | **Vùng mù** | Xem trước 4 vùng mù (phải/trái/trước/sau) vẽ trên sơ đồ, kéo thanh trượt tốc độ/góc rẽ để xem vùng biến dạng khi xe rẽ |
| 6 | **Nghiệm thu** | Kiểm tra danh sách các việc cần hoàn thành, xuất file cấu hình, in biên bản bàn giao |

### Chi tiết bước 4 — vì sao phải làm vậy

Không thể đo góc lắp camera bằng mắt hay bằng thước đo góc thông thường. Cách làm chuẩn trong xử lý ảnh (và duy nhất cách web này hỗ trợ):

1. Đặt 4 chóp nón trên mặt đường quanh xe.
2. Đo khoảng cách từng chóp nón đến **tâm trục sau đầu kéo** bằng thước dây (đây là gốc toạ độ, xem mục 4).
3. Nhập 4 cặp số đo đó vào web.
4. Chạm vào ảnh camera, đúng vị trí chân từng chóp nón trong ảnh (theo đúng thứ tự số 1–4, có 4 màu phân biệt).
5. Bấm "Giải góc lắp" — hệ thống tìm góc chúi (pitch) và góc quay (yaw) sao cho nếu camera lắp đúng góc đó, 4 điểm chạm trong ảnh phải khớp với 4 số đo thật.
6. Đọc **sai số RMS** (tính bằng mét) — đạt khi ≤ 0.30 m. Nếu chưa đạt, đo lại khoảng cách hoặc chạm lại điểm cho chính xác hơn.

Có lưới ô vuông 1×1 m chiếu lên ảnh để kiểm tra bằng mắt: camera nhìn chéo xuống mặt đường nên lưới sẽ méo dần thành hình thang theo khoảng cách (ô gần to, ô xa nhỏ) — **đây là bình thường**, không phải lỗi. Cách kiểm tra đúng: nếu 2 chóp nón cách nhau đúng 1 m ngoài thực tế, trên ảnh khoảng cách giữa chúng phải rơi đúng 1 ô lưới (dù ô đó to hay nhỏ), không cần các ô trông vuông đều bằng mắt.

### Chưa có camera thật thì căn chỉnh kiểu gì?

Ở chế độ mô phỏng, web tự vẽ ảnh camera giả có sẵn 4 chóp nón đặt ở toạ độ đã biết trước, và tự "làm lệch" góc thật đi một chút so với góc đang lưu trong cấu hình. Nhờ vậy kỹ thuật viên vẫn có việc thật để làm — chạm điểm, giải góc, đọc sai số — giống hoàn toàn quy trình ngoài hiện trường, chỉ khác là ảnh do máy vẽ ra thay vì camera chụp.

Khi camera thật đã lắp, bấm **"Tải ảnh camera lên"** để chụp ảnh thật (bằng điện thoại) thay cho ảnh vẽ, rồi làm đúng quy trình 6 bước ở trên trên ảnh thật.

---

## 3. Mô hình toán dùng cho camera — K + [R|T]

Đây là cách chuẩn trong thị giác máy tính để mô tả một camera bằng số:

- **K** (ma trận nội tại): đặc tính riêng của ống kính — tiêu cự và tâm ảnh. Suy ra từ "góc nhìn ngang" ghi trên datasheet camera (nhập độ, ví dụ 120°, hệ thống tự tính ra K).
- **[R|T]**: **R** là hướng camera đang chỉ (góc chúi, góc quay), **T** là vị trí lắp trên xe (x, y, z). Đây là phần thay đổi theo từng xe/từng lần lắp, và chính là thứ bước 4 đi tìm.

Công thức chiếu: `pixel_ảnh = K × [R|T] × điểm_toạ_độ_mét`. Chiều ngược (từ pixel suy ra vị trí mét trên mặt đường) dùng để giải góc lắp ở bước 4.

**Quan trọng: công thức này không phải web viết ra.** Nó gọi trực tiếp hàm `get_rotation_matrix_3d` trong `camera_calibration.py` — module do nhóm tự viết ở `2_BlindSpot_Risk_Calculation/dynamic_blind_zone/`. Web chỉ là lớp giao diện đứng trước, không có công thức toán riêng nào khác với công thức chạy thật trên xe.

---

## 4. Hệ toạ độ dùng chung (bắt buộc hiểu trước khi nhập số)

Mọi số đo trong toàn bộ hệ thống — kích thước xe, vị trí camera, toạ độ chóp nón — đều theo **một hệ duy nhất**:

- **Gốc (0, 0)**: tâm trục bánh sau của đầu kéo (điểm chạm đất, giữa 2 bánh sau).
- **Trục X**: hướng dọc xe. Phía trước mũi xe là **số dương**, phía sau đuôi xe là **số âm**.
- **Trục Y**: hướng ngang xe. Bên trái xe (phía tài xế) là **số dương**, bên phải xe là **số âm**.
- **Đơn vị**: mét, cho tất cả.

Ví dụ: một chóp nón đặt cách tâm trục sau 1 m về phía trước và 2.5 m sang bên phải → nhập `x = 1.0`, `y = -2.5`.

Nhầm dấu Y là lỗi phổ biến nhất — sẽ làm vùng mù/camera tính lệch sang bên kia xe hoàn toàn.

---

## 5. Vùng mù — lấy nguyên từ engine, không viết lại

Toàn bộ hình dạng vùng mù (4 vùng chính: phải, trái, trước, sau) lấy **thẳng** từ hàm `PureOcclusionCalculator.compute_all()` trong `occlusion_calculator.py` — module toán học do nhóm tự viết. Web không tính lại một công thức hình học nào; chỉ gọi hàm đó, lấy kết quả, vẽ lên sơ đồ.

Các vùng phụ nhỏ hơn (cột A, cột B, cảnh báo cự ly phanh) là thành phần con của 4 vùng chính, mặc định ẩn, xem được khi bấm "Xem chi tiết" ở bước 5 — đây chỉ là cách hiển thị, không đổi số liệu.

Xem chi tiết cầu nối này ở mục 8.

---

## 6. Chạy web

### Cài lần đầu

```powershell
# Backend — cần Python 3.11 (khớp môi trường JetPack trên Jetson)
cd 7_Local_Setup_Web\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Frontend
cd ..\frontend
npm install
```

### Chạy để phát triển/sửa giao diện (có hot-reload)

```powershell
# Cửa sổ 1 — backend
cd 7_Local_Setup_Web\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload

# Cửa sổ 2 — frontend
cd 7_Local_Setup_Web\frontend
npm run dev
```

Mở `http://localhost:5173` (frontend tự gọi sang backend ở cổng 8080).

### Chạy giống thật (1 process, giống cách chạy trên Jetson)

```powershell
cd 7_Local_Setup_Web\frontend
npm run build          # ghi bản tĩnh vào backend/static

cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Mở `http://127.0.0.1:8080` — chỉ 1 cổng, 1 process, đúng cách nó sẽ chạy trên Jetson.

Tài liệu API tự sinh (Swagger): `http://127.0.0.1:8080/api/docs`

---

## 7. Cài lên Jetson thật khác gì laptop

Code là **một bộ y hệt**. Khác nhau chỉ ở biến môi trường và phần cứng cắm vào:

| | Laptop (đang dùng) | Jetson thật |
|---|---|---|
| `BLINDGUARD_DEVICE_BACKEND` | `mock` | `jetson` |
| Ảnh camera | Web tự vẽ bằng công thức camera | `cv2.VideoCapture` đọc RTSP/USB thật |
| GPS/IMU | Số giả dao động theo hàm sin | Đọc NMEA thật (`/dev/ttyTHS1`) + IMU qua I2C — **chưa viết, xem mục 9** |
| Truy cập | `http://127.0.0.1:8080` trên máy | Jetson tự phát Wi-Fi, thợ vào `http://192.168.4.1` bằng điện thoại — **script phát Wi-Fi chưa viết, xem mục 9** |
| Cần cài thêm | Không | `pip install opencv-python-headless` |

Không có bước "nạp firmware" hay "flash" nào — chỉ là copy thư mục `7_Local_Setup_Web` sang Jetson, cài Python + Node, build frontend, chạy uvicorn.

**Lưu ý:** ESP32 (`3_Hardware_Embedded/`) không liên quan đến web này. ESP32 chỉ nhận tín hiệu cảnh báo (còi/đèn) từ Jetson ở tầng vận hành thực tế, không tham gia vào việc cấu hình xe.

---

## 8. Cách web nối với engine tính toán (cho người đọc code)

Engine của nhóm (`occlusion_calculator.py`, `calculator.py`, `camera_calibration.py`, `config.py`) được viết theo kiểu `import config` phẳng — đọc hằng số ở cấp module, không nhận tham số qua hàm. Web **không sửa một dòng nào** trong 4 file đó. Thay vào đó:

`app/domain/engine.py` nạp module `config` một lần, rồi **trước mỗi lần tính** gán lại các hằng số trong module đó theo đúng hồ sơ xe đang xem (dưới một khoá `_ENGINE_LOCK` vì cách này không an toàn đa luồng — nhưng công cụ 1 người dùng thì không sao). Nhờ vậy:

> Công thức chạy trên web và công thức chạy thật trên xe là **cùng một hàm Python**, không phải hai bản viết riêng có thể lệch nhau.

Cấu trúc backend:

```
7_Local_Setup_Web/backend/app/
├── domain/
│   ├── derive.py     4 số cơ bản → 25 thông số hình học (công thức PHẢI khớp
│   │                 tuyệt đối với config.py — có test canh giữ điều này)
│   ├── schemas.py     Cấu trúc dữ liệu hồ sơ xe (Pydantic)
│   └── engine.py      Cầu nối gọi engine, tính vùng mù, chiếu camera
├── services/
│   ├── calibration.py Giải góc lắp camera từ 4 điểm đo (Gauss-Newton)
│   ├── store.py       Lưu hồ sơ ra YAML, giữ lịch sử phiên bản, bản nháp
│   └── exporter.py     Sinh file config.py / YAML / dữ liệu biên bản
├── adapters/
│   ├── scene.py        Vẽ ảnh camera giả lập (chế độ mock)
│   ├── cameras.py       Nguồn ảnh: mock hoặc camera thật
│   └── telemetry.py     Nguồn GPS/IMU: mock hoặc thật
└── api/                 Các endpoint REST
```

Test `tests/test_derive_parity.py` so từng giá trị suy ra của web với module `config` thật (bằng cách nạp thẳng module đó và đối chiếu số). Nếu ai đổi công thức bên engine mà không đổi bên `derive.py`, test đỏ ngay — đây là lớp bảo vệ quan trọng nhất của cả hệ thống: sai một dòng ở đây, vùng mù sẽ vẽ sai vị trí trên xe thật.

Test `tests/test_exporter.py` nạp thật file `config.py` mà web xuất ra, rồi so từng hằng số với hồ sơ gốc — đảm bảo file xuất ra luôn nạp được vào engine mà không lỗi.

---

## 9. Xuất file — dùng file nào, dùng thế nào

Bước Nghiệm thu (bước 6) sinh ra 2 file:

| File | Mục đích | Cách dùng |
|---|---|---|
| **`config_<mã_hồ_sơ>.py`** | **File chạy thật trên xe** | Tải xuống, đổi tên thành `config.py`, copy đè vào `2_BlindSpot_Risk_Calculation/dynamic_blind_zone/config.py` trên Jetson. Xong — không sửa gì thêm. |
| **`<mã_hồ_sơ>.yaml`** | Lưu trữ / sao lưu / nhân bản sang xe khác | Không nạp trực tiếp vào engine. Dùng để backup, hoặc khi lắp xe thứ 2 cùng loại, import vào web để lấy sẵn kích thước (kết quả căn chỉnh camera bị xoá vì góc lắp xe mới chắc chắn khác). |

**Quy trình đầy đủ khi bàn giao xe:**

1. Hoàn thành 6 bước, bấm "Lưu hồ sơ".
2. Vào bước Nghiệm thu, kiểm tra danh sách việc cần làm đều đạt (xanh).
3. Bấm nút tải `config_<mã_hồ_sơ>.py`.
4. Copy file đó lên Jetson, đè vào đúng đường dẫn `2_BlindSpot_Risk_Calculation/dynamic_blind_zone/config.py`.
5. Khởi động lại phần mềm nhận diện trên Jetson — nó tự đọc `config.py` mới.

> ⚠️ File `config_<mã_hồ_sơ>.py` chỉ nên nằm trong `2_BlindSpot_Risk_Calculation/dynamic_blind_zone/config.py` khi đưa vào chạy thật. Nếu để nhiều file `config_*.py` rải trong thư mục đó (ví dụ khi tải thử nhiều hồ sơ để test), engine không tự biết dùng file nào — phải đổi tên đúng thành `config.py`.

---

## 10. Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `BLINDGUARD_DEVICE_BACKEND` | `mock` | `mock` (giả lập) hoặc `jetson` (phần cứng thật) |
| `BLINDGUARD_SETUP_PIN` | rỗng | Mã PIN bảo vệ mọi thao tác ghi cấu hình — **bắt buộc đặt trước khi giao xe** |
| `BLINDGUARD_HOST` | `127.0.0.1` | Địa chỉ IP server lắng nghe |
| `BLINDGUARD_PORT` | `8080` | Cổng HTTP |
| `BLINDGUARD_DATA_DIR` | `backend/data` | Nơi lưu hồ sơ xe |
| `BLINDGUARD_STREAM_FPS` | `8` | Tốc độ khung hình luồng xem trực tiếp |
| `BLINDGUARD_JPEG_QUALITY` | `82` | Chất lượng ảnh JPEG |

Copy `backend/.env.example` thành `backend/.env` rồi sửa giá trị.

---

## 11. Bảo mật — bắt buộc làm trước khi giao xe cho khách

Web này chạy trên mạng Wi-Fi do Jetson tự phát. **Mặc định không có mật khẩu bảo vệ cấu hình** — bất kỳ ai kết nối vào Wi-Fi đó đều sửa được cấu hình an toàn của xe đang chạy.

Trước khi bàn giao, tối thiểu phải:

1. Đặt `BLINDGUARD_SETUP_PIN` — mọi thao tác lưu/sửa sẽ cần đúng mã PIN này.
2. Bật WPA2 cho điểm phát Wi-Fi, đặt mật khẩu riêng cho từng xe.
3. Chạy server đúng vào địa chỉ IP của điểm phát Wi-Fi (ví dụ `--host 192.168.4.1`), không dùng `0.0.0.0` (mở ra mọi mạng).
4. Bấm "Khoá cấu hình sau nghiệm thu" ở bước 6 — sau đó phải nhập lại PIN mới sửa được.

Trang "Chẩn đoán" trong web sẽ tự cảnh báo (màu vàng) nếu chưa đặt PIN.

---

## 12. Chạy kiểm thử (test)

```powershell
cd 7_Local_Setup_Web\backend

# Toàn bộ test tự động (46 test, không cần server chạy)
.\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/smoke_live.py

# Kiểm tra trên server đang chạy thật, gồm cả luồng xem trực tiếp
# (chạy uvicorn ở cổng 8080 trước, rồi mới chạy dòng dưới)
.\.venv\Scripts\python.exe tests\smoke_live.py
```

```powershell
cd 7_Local_Setup_Web\frontend
npm run typecheck      # kiểm tra kiểu TypeScript, không build
npm run build           # build thật + kiểm tra kiểu
```

---

## 13. Những gì đã làm xong

- Wizard 6 bước đầy đủ: hồ sơ xe → kích thước → lắp camera → căn chỉnh → vùng mù → nghiệm thu.
- Suy 25 thông số hình học xe từ 4 số đo cơ bản (Derived Config Architecture), có cảnh báo khi số đo bất thường (nghi sai đơn vị).
- Căn chỉnh camera bằng 4 điểm đo thật, giải góc tự động, báo sai số bằng mét theo đúng tiêu chí kỹ thuật (RMS ≤ 0.30 m).
- Tải ảnh camera thật lên để căn chỉnh trên ảnh thật (thay ảnh mô phỏng).
- Mô phỏng vùng mù biến dạng khi xe rẽ (kéo thanh trượt tốc độ/góc lái), có thể chạm vào sơ đồ để kiểm tra một điểm cụ thể có nguy hiểm không.
- Xe thân liền hiển thị đúng là một khối nguyên, xe đầu kéo hiển thị 3 khối có khớp nối — không vẽ giống nhau.
- Xuất file `config.py` nạp thẳng vào engine, xuất YAML để lưu trữ/nhân bản, in biên bản nghiệm thu.
- Lưu bản nháp tự động (chống mất dữ liệu khi rớt Wi-Fi), lưu lịch sử phiên bản, khoá cấu hình sau nghiệm thu.
- Chạy đầy đủ ở chế độ mô phỏng — không cần bất kỳ phần cứng nào để demo hoặc test.
- 46 test tự động, gồm test đối chiếu công thức với engine thật và test nạp lại file xuất ra.

## 14. Còn thiếu / việc tiếp theo

- **Driver GPS/IMU thật**: `adapters/telemetry.py` ở chế độ `jetson` mới là khung rỗng. Cần đọc NMEA từ `/dev/ttyTHS1` và IMU qua I2C.
- **Script phát Wi-Fi AP + captive portal** trên Jetson: chưa viết. Hướng chuẩn là `nmcli device wifi hotspot` hoặc `hostapd` + `dnsmasq`.
- **Góc lắc hông camera (roll)**: engine hiện chưa áp dụng — hàm `get_rotation_matrix_3d` trong `camera_calibration.py` nhận `roll_deg` nhưng không đưa vào ma trận xoay trả về (thiếu phép xoay quanh trục dọc). Web tự phát hiện việc này lúc chạy và tạm ẩn/loại roll khỏi bước giải góc; khi engine bổ sung, web tự nhận ra và bật lại, không cần sửa gì thêm bên web.
- **Công thức văng đuôi xe khi rẽ** (rear overhang outswing) cho xe thân liền: có trong tài liệu mô hình toán của nhóm nhưng engine `occlusion_calculator.py` chưa hiện thực — web chỉ đang ép góc gập bằng 0 cho xe thân liền, chưa tính phần văng đuôi.
- **Đo lại tốc độ thực tế trên phần cứng Jetson** (giải góc, mã hoá ảnh) — hiện chỉ đo trên laptop.
