# Web cài đặt tại xe (Tier 1)

Công cụ để kỹ thuật viên thiết lập và căn chỉnh hệ thống vùng mù động **ngay trên xe**, bằng điện thoại hoặc iPad, không cần cắm bàn phím vào Jetson.

Chạy được **hoàn toàn không cần camera và GPS thật**: ở chế độ mô phỏng, khung hình camera được dựng bằng đúng mô hình `K + [R|T]` của `camera_calibration.py`, nên toàn bộ quy trình căn chỉnh, đo sai số và nghiệm thu hoạt động như thật. Khi có phần cứng, chỉ đổi một biến môi trường.

## Chạy nhanh

```powershell
# Backend
cd 7_Local_Setup_Web\backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080

# Frontend - chế độ phát triển (cửa sổ khác)
cd 7_Local_Setup_Web\frontend
npm install
npm run dev          # mở http://localhost:5173

# Frontend - sinh bản tĩnh để Jetson tự phục vụ
npm run build        # ghi vào backend/static, sau đó chỉ cần mở http://127.0.0.1:8080
```

Tài liệu API tự sinh: `http://127.0.0.1:8080/api/docs`

## Quy trình lắp đặt (6 bước)

| Bước | Việc | Điểm đáng chú ý |
|---|---|---|
| 1 · Hồ sơ xe | Biển số, loại thân xe, chọn mẫu cấu hình | Mã hồ sơ tự sinh từ biển số |
| 2 · Kích thước | **Chỉ 4 số từ sổ đăng kiểm** | Sơ đồ top-down vẽ lại theo từng ký tự; đặt con trỏ vào ô nào thì sơ đồ tô đỏ đúng khoảng cách cần đo |
| 3 · Lắp camera | Nguồn RTSP, ống kính, vị trí lắp | Vị trí lắp suy ra tự động từ toạ độ gương và mũi xe; nhập HFOV thay vì tiêu cự fx |
| 4 · Căn chỉnh | Chạm 4 vật mốc → giải góc lắp | Kính lúp, nhích 1 px bằng mũi tên, lưới mét chồng lên ảnh, sai số báo bằng **mét** |
| 5 · Vùng mù | Tham số + mô phỏng | Kéo thanh trượt tốc độ/góc lái xem vùng biến dạng; chạm bản đồ để kiểm tra một điểm |
| 6 · Nghiệm thu | Kiểm tra, xuất cấu hình, biên bản | Sinh `config_<hồ_sơ>.py` nạp thẳng được vào engine |

## Kiến trúc

```
7_Local_Setup_Web/
├── backend/                     FastAPI - REST + MJPEG + phục vụ SPA tĩnh
│   ├── app/domain/
│   │   ├── derive.py            Derived Config Architecture: 4 số → 25 thông số
│   │   ├── schemas.py           Schema Pydantic của hồ sơ xe
│   │   └── engine.py            Cầu nối sang engine vùng mù ở 2_BlindSpot_Risk_Calculation
│   ├── app/services/
│   │   ├── calibration.py       Giải pitch/yaw/độ cao từ vật mốc (Gauss-Newton có giảm)
│   │   ├── store.py             Lưu hồ sơ YAML + lịch sử phiên bản + bản nháp
│   │   └── exporter.py          Sinh config.py / YAML / biên bản nghiệm thu
│   ├── app/adapters/
│   │   ├── scene.py             Dựng khung hình mô phỏng từ mô hình camera thật
│   │   ├── cameras.py           MockCameraSource | JetsonCameraSource
│   │   └── telemetry.py         GPS/IMU mô phỏng hoặc thật
│   └── tests/                   42 test, gồm test đối chiếu công thức với engine
└── frontend/                    React + TypeScript + Tailwind, build ra bản tĩnh
```

### Cầu nối với engine

Engine của nhóm (`occlusion_calculator.py`, `calculator.py`) dùng `import config` phẳng và đọc hằng số ở cấp module. Web **không sửa một dòng nào** trong engine: `app/domain/engine.py` nạp module engine một lần rồi gán lại các hằng số trong module `config` theo hồ sơ đang xem, dưới một khoá. Nhờ vậy công thức chạy trên web và công thức chạy trên xe là **cùng một hàm**.

Đánh đổi: phần này không an toàn đa luồng, nên mọi lời gọi engine đều đi qua `_ENGINE_LOCK`. Với một công cụ cấu hình một người dùng thì hoàn toàn đủ.

Test `tests/test_derive_parity.py` so từng giá trị suy ra của web với module `config` thật. Nếu ai đổi tỷ lệ một bên mà không đổi bên kia, test đỏ ngay.

## Chế độ thiết bị

```
BLINDGUARD_DEVICE_BACKEND=mock     # mặc định, không cần phần cứng
BLINDGUARD_DEVICE_BACKEND=jetson   # đọc camera và GPS thật
```

Ở chế độ `jetson` cần thêm `pip install opencv-python-headless`.

Ảnh mô phỏng được vẽ từ một bộ góc **"sự thật vật lý" lệch nhẹ** so với góc mặc định trong cấu hình (`scene.TRUTH_OFFSET`). Cố ý như vậy: lưới mét chiếu từ cấu hình sẽ không khớp ngay, nên kỹ thuật viên có việc thật để làm ở bước căn chỉnh, giống hiện trường. Chóp nón nằm ở toạ độ mét đã biết, nên chạm vào rồi bấm "Giải góc lắp" sẽ khôi phục đúng pose thật (RMS = 0).

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `BLINDGUARD_DEVICE_BACKEND` | `mock` | `mock` hoặc `jetson` |
| `BLINDGUARD_SETUP_PIN` | rỗng | Mã PIN bảo vệ mọi thao tác ghi cấu hình |
| `BLINDGUARD_PORT` | `8080` | Cổng HTTP |
| `BLINDGUARD_DATA_DIR` | `backend/data` | Nơi lưu hồ sơ xe |
| `BLINDGUARD_STREAM_FPS` | `8` | Tốc độ khung luồng MJPEG |

## Bảo mật — bắt buộc làm trước khi giao xe

Web này chạy trên mạng Wi-Fi do Jetson phát. **Mặc định không có xác thực**: bất kỳ ai trong tầm phủ sóng đều sửa được file cấu hình an toàn của xe đang chạy.

Tối thiểu trước khi bàn giao:

1. Đặt `BLINDGUARD_SETUP_PIN` — mọi endpoint ghi sẽ yêu cầu header `X-Setup-Pin`.
2. Bật WPA2 cho điểm truy cập, mật khẩu riêng từng thiết bị.
3. Bind server vào đúng interface AP (`--host 192.168.4.1`), không dùng `0.0.0.0`.
4. Bật "Khoá cấu hình sau nghiệm thu" ở bước 6.

Trang chẩn đoán sẽ cảnh báo vàng khi chưa đặt PIN.

## Xuất cấu hình sang xe

Bước nghiệm thu sinh hai file:

- `config_<hồ_sơ>.py` — dùng đúng tên hằng số engine đang đọc. Copy vào `2_BlindSpot_Risk_Calculation/dynamic_blind_zone/config.py` là chạy.
- `<hồ_sơ>.yaml` — dạng chính để lưu trữ, sao lưu và **nhân bản sang xe khác cùng loại** (kích thước giữ nguyên, kết quả căn chỉnh camera bị xoá vì góc lắp trên xe mới chắc chắn khác).

Test `tests/test_exporter.py` nạp thật file `.py` sinh ra và đối chiếu từng hằng số, đồng thời kiểm tra exporter không bỏ sót hằng số nào engine cần.

## Chạy test

```powershell
cd 7_Local_Setup_Web\backend
.\.venv\Scripts\python.exe -m pytest tests -q --ignore=tests/smoke_live.py

# Kiểm tra trên server đang chạy thật (gồm cả luồng MJPEG)
.\.venv\Scripts\python.exe tests\smoke_live.py
```

## Còn thiếu / việc tiếp theo

- **Driver GPS/IMU thật**: `adapters/telemetry.py` ở chế độ `jetson` chỉ là khung. Cần đọc NMEA từ `/dev/ttyTHS1` và IMU qua I2C.
- **Script phát Wi-Fi AP**: chưa có. Đường chuẩn là `nmcli device wifi hotspot` hoặc hostapd + dnsmasq, kèm captive portal.
- **Góc roll**: engine hiện chưa áp dụng roll — `get_rotation_matrix_3d` trong `camera_calibration.py` nhận `roll_deg` và tính `r = math.radians(roll_deg)` nhưng không đưa `r` vào ma trận trả về (`Rz @ R0 @ Rx`, thiếu phép xoay quanh trục dọc). Web phát hiện việc này lúc chạy (`engine.roll_is_supported`), làm mờ ô nhập roll và loại roll khỏi bộ giải. Khi engine bổ sung, web tự bật lại, không cần sửa gì.
- **Xe thân liền**: web ép `γ = 0` ngay trong `update_kinematics`, còn công thức văng đuôi xe (rear overhang outswing) trong tài liệu mô hình toán thì engine chưa có.
