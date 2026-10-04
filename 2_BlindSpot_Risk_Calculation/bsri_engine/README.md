# 🛡️ BlindGuard AI — BSRI Engine (Blind-Spot Risk Index)

> **Phân hệ 2: Tính toán Chỉ số Rủi ro Điểm mù Động theo Thời gian thực**  
> Dự án: **BlindGuard AI** — Giải pháp AI Edge hỗ trợ an toàn điểm mù cho xe tải nặng & xe đầu kéo.  
> Cơ sở kỹ thuật tham chiếu: **ISO 8855 / SAE J670 (Quy ước trục tọa độ VCS)**; Khái niệm an toàn mở rộng từ **UNECE R46, R151, R158, R159** và **ISO 15623, ISO 22839**.

---

## 📌 MỤC LỤC
1. [Giới thiệu & Triết lý BSRI](#1-giới-thiệu--triết-lý-bsri)
2. [Hệ tọa độ & Quy ước Vật lý (VCS ISO 8855)](#2-hệ-tọa-độ--quy-ước-vật-lý-vcs-iso-8855)
3. [Mô hình Toán học & Công thức BSRI](#3-mô-hình-toán-học--công-thức-bsri)
   - [3.1. Rủi ro Không gian (Spatial Risk)](#31-rủi-ro-không-gian-spatial-risk-s_spatial)
   - [3.2. Rủi ro Thời gian & Va chạm (Temporal Risk & TTC)](#32-rủi-ro-thời-gian--va-chạm-temporal-risk--ttc-s_temporal)
   - [3.3. Hệ số Ưu tiên Nhóm Đối tượng (Class Vulnerability Factor)](#33-hệ-số-ưu-tiên-nhóm-đối-tượng-c_vru)
   - [3.4. Hệ số Điểm mù Quang học (Blind Spot Factor)](#34-hệ-số-điểm-mù-quang-học-blind-spot-factor-v_blind)
   - [3.5. Hệ số Thao tác Xe chủ (Ego Maneuver Factor)](#35-hệ-số-thao-tác-xe-chủ-ego-maneuver-factor-m_ego)
   - [3.6. Công thức Tổng hợp BSRI Chuẩn hóa](#36-công-thức-tổng-hợp-bsri-chuẩn-hóa)
4. [Bảng Phân cấp Rủi ro & Tác vụ Phần cứng](#4-bảng-phân-cấp-rủi-ro--tác-vụ-phần-cứng)
5. [Cấu trúc Module Code & API](#5-cấu-trúc-module-code--api)
6. [Hướng dẫn Chạy Thử & Kiểm thử (Unit Tests)](#6-hướng-dẫn-chạy-thử--kiểm-thử-unit-tests)
7. [Tích hợp với Module 1 (ByteTrack + Homography)](#7-tích-hợp-với-module-1-bytetrack--homography)

---

## 1. Giới thiệu & Triết lý BSRI

Trong các hệ thống cảnh báo điểm mù truyền thống (như cảm biến siêu âm hay radar góc cố định), hệ thống thường gặp hai lỗi nghiêm trọng:
1. **Cảnh báo giả liên tục (False Alarm):** Báo động inh ỏi chỉ vì có xe con đang chạy song song ở làn bên cạnh dù hai xe không có nguy cơ đụng nhau.
2. **Bỏ sót hiểm họa lấn lề (Missed Hazard):** Khi xe đầu kéo rẽ phải, thùng rơ-moóc bị gập góc và quét vào lề đường (hiện tượng **Swept Path / Off-tracking**), bánh sau rơ-moóc nghiền nát người đi bộ hoặc xe máy đang đứng chờ đèn đỏ mà cảm biến cố định không hề quét tới.

**BSRI (Blind-Spot Risk Index)** giải quyết triệt để vấn đề này bằng triết lý **Đánh giá rủi ro theo Ngữ cảnh Động học (Context-aware Risk Assessment)**:
* BSRI không chỉ hỏi: *"Có vật thể ở đó không?"*
* BSRI trả lời: **"Với tốc độ, góc đánh lái hiện tại của xe tải, và hướng di chuyển của vật thể, xác suất xảy ra va chạm trong 1–3 giây tới là bao nhiêu? Vật thể đó có phải đối tượng dễ tổn thương (VRU) không? Tài xế có đang bị che mắt hoàn toàn không?"**

Kết quả trả về là một chỉ số liên tục $BSRI \in [0.00, 1.00]$, được gán nhãn giải thích rõ ràng (Explainable AI) phục vụ đồng thời cho **màn hình Cabin HUD** và **vi điều khiển ESP32** kích hoạt phản ứng khẩn cấp.

---

## 2. Hệ tọa độ & Quy ước Vật lý (VCS ISO 8855)

Tất cả các đại lượng khoảng cách, vị trí và vận tốc trong BSRI Engine đều tuân thủ **Hệ tọa độ xe (Vehicle Coordinate System - VCS)** theo quy ước chiều dương chuẩn quốc tế **ISO 8855 / SAE J670**:

```text
               Y+ (Bên Trái xe)
               ^
               |   [CABIN ĐẦU KÉO]
               |      +-------+
               |      |       |  ---> X+ (Hướng tiến của xe)
---------------+------[ (0,0) ]---------------------------->
               |   (Tâm trục sau)
               |      |       |
               |      +-------+
               |   [THÙNG RƠ-MOÓC]
               |      |       |
               |      +-------+
               v
               Y- (Bên Phải xe - Điểm mù hông phụ)
```

* **Gốc tọa độ $(0, 0, 0)$:** Đặt tại tâm trục bánh sau đầu kéo (Rear Axle Center, lựa chọn thiết kế của dự án nhằm triệt tiêu $v_y = 0$ khi quay vòng Ackermann), mặt đường phẳng $Z = 0$.
* **Trục $X$ (Longitudinal):** Trục dọc thân xe.
  * $X > 0$: Về phía trước mũi xe (đầu cabin).
  * $X < 0$: Về phía sau thân xe (thùng rơ-moóc).
* **Trục $Y$ (Lateral):** Trục ngang thân xe.
  * $Y > 0$: Bên **Trái** xe (phía hông tài xế ngồi).
  * $Y < 0$: Bên **Phải** xe (phía hông phụ — **điểm mù nguy hiểm nhất**).
* **Tốc độ góc Yaw Rate $\omega_z$ ($rad/s$):**
  * $\omega_z > 0$: Xe đang rẽ trái (ngược chiều kim đồng hồ).
  * $\omega_z < 0$: Xe đang rẽ phải (thuận chiều kim đồng hồ).

---

## 3. Mô hình Toán học & Công thức BSRI

Chỉ số rủi ro $BSRI$ của mỗi vật thể $i$ được tổng hợp từ cơ chế kết hợp lồi rủi ro cơ sở nhân các hệ số điều chỉnh ngữ cảnh (Contextual Risk Modifiers):

$$\mathbf{BSRI} = \text{clip}\left( \Big( w_s \cdot S_{spatial} + w_t \cdot S_{temporal} \Big) \cdot C_{vru} \cdot V_{blind} \cdot M_{ego}, \quad 0.0, \quad 1.0 \right)$$

Trong đó:
* $w_s = 0.45$ (Trọng số rủi ro không gian, Engineering Calibration Parameter).
* $w_t = 0.55$ (Trọng số rủi ro thời gian / va chạm cận kề, Engineering Calibration Parameter).

---

### 3.1. Rủi ro Không gian ($S_{spatial}$)
Rủi ro không gian phản ánh mức độ áp sát của chướng ngại vật đối với **Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ)** của xe tải:

* Đa giác $DHZ$ là hợp của các hình chiếu thân xe trong tương lai gần $T = 0.5s$ cộng khoảng đệm an toàn vật lý $C = 1.5m + C_{dyn}$:
  $$DHZ = \text{Buffer}\left(\bigcup_{t=0}^{T} P_{vehicle}(t), \quad C \right)$$
* Nếu đối tượng **đã nằm trong $DHZ$**:
  $$S_{spatial} = 1.0$$
* Nếu đối tượng **ở ngoài $DHZ$** cách đường biên viền một khoảng $d_{DHZ}$ (mét):
  $$S_{spatial} = \exp\left( - \frac{d_{DHZ}}{d_0} \right) \quad (\text{với } d_0 = 1.8\text{m, Engineering Calibration})$$
  *(Khoảng cách $d_{DHZ} = 0\text{m} \rightarrow 1.0$; tại $1.8\text{m} \rightarrow 0.37$; tại $3.6\text{m} \rightarrow 0.14$; xa hơn $5\text{m} \rightarrow 0.06$)*.

---

### 3.2. Rủi ro Thời gian & Va chạm ($S_{temporal}$ & TTC)
Rủi ro thời gian trả lời: *Hai vật thể có đang lao vào nhau không và còn bao nhiêu giây nữa sẽ chạm mặt?*

1. Tính khoảng cách Euclid thẳng:
   $$R = \sqrt{X^2 + Y^2}$$
2. Tính **Vận tốc tiếp cận hướng tâm (Closing Velocity)** từ vận tốc tương đối Camera VCS:
   $$v_{closing} = - \frac{X \cdot v_{rel,x} + Y \cdot v_{rel,y}}{R}$$
3. Nếu $v_{closing} > 0.15\text{ m/s}$ (khoảng cách đang thu hẹp lại):
   * **Thời gian tới va chạm (Time-To-Collision - TTC):**
     $$\text{TTC} = \frac{R}{v_{closing}}$$
   * Điểm rủi ro thời gian theo đường cong suy giảm kỹ thuật (dựa trên thời gian phản xạ người lái và độ trễ phanh khí nén xe tải):
     $$S_{temporal} = \begin{cases} 
     1.0 & \text{khi } \text{TTC} \le 1.2\text{s} \quad (\text{Khẩn cấp, tài xế không kịp đạp phanh}) \\
     1.0 - 0.70 \times \frac{\text{TTC} - 1.2}{3.5 - 1.2} & \text{khi } 1.2\text{s} < \text{TTC} \le 3.5\text{s} \\
     0.30 \times \exp\left(-\frac{\text{TTC} - 3.5}{3.0}\right) & \text{khi } \text{TTC} > 3.5\text{s}
     \end{cases}$$
4. Nếu $v_{closing} \le 0.15\text{ m/s}$ (đối tượng đứng yên hoặc đang đi xa dần):
   $$S_{temporal} = 0.20 \times \exp\left(-\frac{R}{4.0}\right) \le 0.20$$
   *(Không có nguy cơ va chạm khẩn về mặt động học)*.

---

### 3.3. Hệ số Ưu tiên Nhóm Đối tượng ($C_{vru}$)
Phân loại chuẩn hóa theo định nghĩa an toàn giao thông quốc tế (WHO / UNECE / Euro NCAP): **Nhóm không có khung vỏ bảo vệ (VRU)** và **Nhóm phương tiện cơ giới có khung vỏ kín (Enclosed Vehicles)**:

| Loại đối tượng (`class_name`) | Hệ số $C_{vru}$ | Phân loại & Cơ sở an toàn kỹ thuật |
| :--- | :---: | :--- |
| **`person` (Người đi bộ)** | **`1.00`** | **VRU (Không vỏ bọc)**: Nguy cơ tử vong tối đa khi va chạm với xe tải nặng |
| **`motorcycle` (Xe máy)** | **`1.00`** | **VRU (Không vỏ bọc)**: Nguy cơ sinh mạng tương đương người đi bộ, đối tượng gặp nạn nhiều nhất tại VN |
| **`bicycle` (Xe đạp)** | **`1.00`** | **VRU (Không vỏ bọc)**: Thăng bằng kém, dễ ngã vào gầm xe |
| **`xe_keo` (Xe kéo hàng)** | **`1.00`** | **VRU (Không vỏ bọc)**: Cồng kềnh, người kéo đi bộ sát lòng đường |
| **`xich_lo` (Xích lô)** | **`1.00`** | **VRU (Không vỏ bọc)**: Người điều khiển và hành khách ngồi hở |
| **`car` (Ô tô con)** | **`0.70`** | **Enclosed**: Có khung thép hấp thụ xung lực, đai an toàn và túi khí bảo vệ |
| **`truck` / `bus` (Xe lớn khác)** | **`0.60` / `0.65`** | **Heavy**: Khối lượng đối trọng tương đương, sàn xe cao |

---

### 3.4. Hệ số Điểm mù Quang học ($V_{blind}$)
Dựa trên phân vùng góc nhìn gián tiếp qua gương (tham chiếu phân loại gương UNECE R46) và xoay theo góc gập rơ-moóc $\gamma$:

| Phân vùng (`BlindSpotZone`) | Tọa độ VCS ($X, Y$ mét) | Hệ số $V_{blind}$ | Mức độ nguy hiểm |
| :--- | :---: | :---: | :--- |
| **`MIRROR_RIGHT` (Hông phụ)** | $X \in [d_{hitch}, X_{front}], Y \in [-3.5, -W/2]$ | **`1.25`** | **Cao nhất:** Điểm mù gương cầu phụ, tài xế bị che bởi cửa sổ phụ |
| **`SWEPT_PATH_RIGHT` (Bụng cua phải)** | $X_{tr} \in [X_{rear}, d_{hitch}], Y_{tr} \in [-4.5, -W/2]$ | **`1.25`** | Vùng vệt quét rơ-moóc ôm cua lấn làn bên phụ |
| **`CAB_FRONT` (Mũi xe gầm cao)** | $X \in [L_f, X_{front}+2.0], \|Y\| \le W/2+0.8$ | **`1.20`** | Điểm mù trực diện gầm cao (Class VI) khi xe bắt đầu lăn bánh |
| **`REAR_TRAILER` (Đuôi rơ-moóc)** | $X_{tr} \in [X_{rear}-3.5, X_{rear}], \|Y_{tr}\| \le W/2+1.0$ | **`1.20`** | Điểm mù lùi hoàn toàn phía sau thùng xe |
| **`MIRROR_LEFT` / `SWEPT_PATH_LEFT`** | Phía bên trái xe ($Y > W/2$) | **`1.10`** | Hông lái (tài xế có thể ngoái đầu nhìn qua cửa kính lái) |
| **`CLEAR_ZONE` (Vùng thoáng)** | Ngoài các vùng trên | **`0.85`** | Tài xế quan sát trực tiếp dễ dàng |

---

### 3.5. Hệ số Thao tác Xe chủ ($M_{ego}$)
Hệ thống kết nối trực tiếp với cảm biến góc lái, xi-nhan và gia tốc xe tải:

* **Xe chuẩn bị rẽ vào phía đối tượng:**  
  * Nếu xe đang rẽ phải ($\omega_z < -0.03\text{ rad/s}$ hoặc bật xi-nhan phải) **VÀ** đối tượng đang ở bên phải ($Y < 0$):  
    $$\mathbf{M_{ego} = 1.35}$$
  * Nếu xe đang rẽ trái ($\omega_z > 0.03\text{ rad/s}$ hoặc bật xi-nhan trái) **VÀ** đối tượng ở bên trái ($Y > 0$):  
    $$\mathbf{M_{ego} = 1.35}$$
* **Xe đang lùi ($gear = 'R'$ hoặc $v < -0.2\text{ m/s}$) và vật thể ở phía sau ($X < 0$):**  
  $$\mathbf{M_{ego} = 1.40}$$
* **Xe đang phanh gấp ($a_x < -1.5\text{ m/s}^2$):**  
  * Vật cản phía trước/bên hông ($X \ge 0$): $M_{ego} = 0.85$ *(Tài xế đang chủ động phanh để tránh)*.  
  * Vật cản phía sau đuôi ($X < 0$): $M_{ego} = 1.25$ *(Phanh gấp làm tăng nguy cơ bị đâm đuôi từ sau)*.
* **Trạng thái bình thường:**  
  $$M_{ego} = 1.00$$

---

## 4. Bảng Phân cấp Rủi ro & Tác vụ Phần cứng

Chỉ số $BSRI$ được chia thành 4 cấp độ rõ ràng:

| Ngưỡng BSRI | Cấp độ (`RiskLevel`) | Màu sắc | Tác vụ trên Cabin HUD | Tác vụ Phần cứng ESP32 |
| :---: | :---: | :---: | :--- | :--- |
| **$< 0.30$** | **`LEVEL 0: SAFE`** | 🟢 Xanh lá | Hiển thị khung viền xanh, icon mờ | Không kích hoạt buzzer |
| **`0.30 – 0.54`** | **`LEVEL 1: CAUTION`** | 🟡 Vàng chanh | Viền vàng, hiển thị khoảng cách mét | Bật LED vàng trên gương chiếu hậu |
| **`0.55 – 0.79`** | **`LEVEL 2: WARNING`** | 🟠 Cam | Viền cam nhấp nháy, hiện TTC (giây) | Rung vô-lăng + Còi bíp ngắt quãng (2Hz) |
| **$\ge 0.80$** | **`LEVEL 3: CRITICAL`** | 🔴 Đỏ rực | Viền đỏ đậm, pop-up banner cảnh báo khẩn | **Còi hú liên tục + Đèn chớp đỏ + Tín hiệu phanh khẩn cấp** |

---

## 5. Cấu trúc Module Code & API

Toàn bộ phân hệ BSRI được đóng gói độc lập trong thư mục `2_BlindSpot_Risk_Calculation/bsri_engine/`:

```text
2_BlindSpot_Risk_Calculation/bsri_engine/
├── __init__.py           # Export các class công khai
├── risk_models.py       # Định nghĩa Enums, Dataclasses (EgoVehicleState, TrackedObstacle, BSRIResult)
├── bsri_calculator.py   # Lõi thuật toán tính BSRI và phân loại rủi ro
├── test_bsri.py         # Bộ 5 bài kiểm thử kịch bản tự động
└── README.md            # Tài liệu kỹ thuật chi tiết này
```

### Ví dụ Sử dụng trong Code Python

```python
from bsri_engine import BSRICalculator, EgoVehicleState, TrackedObstacle

# 1. Khởi tạo bộ tính toán BSRI
calculator = BSRICalculator(wheelbase_tractor=3.6, trailer_length=12.0)

# 2. Cập nhật trạng thái xe tải (từ GPS/IMU và Vô-lăng)
ego = EgoVehicleState(
    speed_mps=5.0,              # Xe đang chạy ~18 km/h
    yaw_rate_rad_s=-0.07,       # Đang vào cua phải
    steering_angle_deg=-12.0,
    turn_signal="RIGHT"         # Xi-nhan phải
)

# 3. Tạo danh sách đối tượng từ Module AI Tracking (sau khi chuyển đổi Homography)
obstacles = [
    TrackedObstacle(
        track_id=15,
        class_name="xich_lo",
        confidence=0.88,
        bbox_xyxy=(850, 420, 1020, 680),
        vcs_x=1.8,              # Cách trục sau 1.8m về phía trước
        vcs_y=-1.9,             # Cách sườn xe 1.9m về bên phải
        vel_x=-0.2,             # Tốc độ tương đối
        vel_y=0.1
    )
]

# 4. Đánh giá rủi ro toàn hiện trường
all_results, highest_threat = calculator.evaluate_scene(ego, obstacles)

# 5. Đọc kết quả
print(f"Đối tượng nguy hiểm nhất: {highest_threat.class_name} #{highest_threat.track_id}")
print(f"Điểm BSRI: {highest_threat.bsri_score} -> Cấp độ: {highest_threat.risk_level.label_vi}")
print(f"Giải thích: {highest_threat.explanation}")
print(f"Khuyến nghị: {highest_threat.recommendation}")
```

---

## 6. Hướng dẫn Chạy Thử & Kiểm thử (Unit Tests)

Bộ kiểm thử [test_bsri.py](file:///d:/Programing/BlindGuardAI/2_BlindSpot_Risk_Calculation/bsri_engine/test_bsri.py) bao gồm **5 kịch bản giao thông thực tế**:
1. **Test 1:** Người đi bộ lọt vào hông phụ bên phải khi xe tải đang rẽ phải $\rightarrow$ Kỳ vọng `CRITICAL`.
2. **Test 2:** Ô tô con ở cự ly xa bên trái (14m) đang chạy ra xa $\rightarrow$ Kỳ vọng `SAFE` (Không báo giả).
3. **Test 3:** Xe máy phóng nhanh tiếp cận từ phía sau vào điểm mù ($TTC < 1.5s$) $\rightarrow$ Kỳ vọng `CRITICAL` kèm tính toán TTC chính xác.
4. **Test 4:** Xe kéo tự chế (`xe_keo`) của Việt Nam nằm trong vùng lấn lề rơ-moóc $\rightarrow$ Kỳ vọng `WARNING/CRITICAL` nhờ trọng số VRU cao ($0.92$).
5. **Test 5:** Hiện trường đa đối tượng $\rightarrow$ Kiểm tra khả năng tự động lọc ra mục tiêu nguy cơ cao nhất.

### Lệnh chạy kiểm thử:
```powershell
python 2_BlindSpot_Risk_Calculation/bsri_engine/test_bsri.py
```

**Kết quả xác thực thực tế:**
```text
===========================================================================
          BLINDGUARD AI - KIỂM THỬ PHÂN HỆ TÍNH TOÁN RỦI RO BSRI           
===========================================================================
--- [TEST 1]: Người đi bộ tại điểm mù hông phụ khi xe rẽ phải ---
  + Điểm BSRI: 1.000 -> NGUY HIỂM KHẨN CẤP (CRITICAL)
  => [PASS] Đã phát hiện chính xác mối đe dọa khẩn cấp!

--- [TEST 2]: Ô tô con ở cự ly xa, đi xa dần ---
  + Điểm BSRI: 0.198 -> AN TOÀN (SAFE)
  => [PASS] Không phát sinh cảnh báo giả (Zero False Alarm)!

--- [TEST 3]: Xe máy tiếp cận nhanh từ phía sau (TTC thấp) ---
  + TTC: 0.83s | Điểm BSRI: 1.000 -> NGUY HIỂM KHẨN CẤP (CRITICAL)
  => [PASS] Đo đạc TTC và cảnh báo va chạm trước thời gian chính xác!

--- [TEST 4]: Xe kéo (xe_keo) trong vùng lấn lề rơ-moóc ---
  + Điểm BSRI: 0.723 -> CẢNH BÁO (WARNING)
  => [PASS] Đã áp dụng chuẩn xác trọng số phương tiện đặc thù Việt Nam!

--- [TEST 5]: Đánh giá toàn cảnh đa đối tượng (Multi-object Scene) ---
  => ĐỐI TƯỢNG NGUY HIỂM NHẤT TRÍCH XUẤT: ID #11 (person) - BSRI 1.00
  => [PASS] Bộ giải mã ưu tiên hiện trường hoạt động chính xác 100%!
===========================================================================
      [V] TẤT CẢ 5/5 BÀI KIỂM THỬ KỊCH BẢN BSRI ĐÃ VƯỢT QUA XUẤT SẮC!      
===========================================================================
```

---

## 7. Tích hợp với Module 1 (ByteTrack + Homography)

Quy trình tích hợp giữa Module 1 (Vision) và Module 2 (BSRI) được thực hiện theo chu trình khép kín:

```text
[Camera Fisheye 180°]
         │
         ▼
[YOLOv11n Detection] ──> Bounding Boxes (x1, y1, x2, y2)
         │
         ▼
[ByteTrack MOT] ───────> Track ID liên tục + Vệt quỹ đạo
         │
         ▼
[Homography Calibrator] 
  Lấy điểm chạm đất u = (x1+x2)/2, v = y2
  Chiếu qua ma trận H: (u, v) ──> (X_vcs, Y_vcs) mét mặt đất
         │
         ▼
[BSRI Engine Calculator]
  Kết hợp tọa độ (X, Y) + Vận tốc (vx, vy) + GPS/IMU xe tải
  Tính BSRI Score + Risk Level + Zone + TTC
         │
         ├───> [Màn hình Cabin HUD]: Vẽ Bounding Box theo màu nguy hiểm + Banner giải thích
         └───> [UART / Socket ESP32]: Bắn mã cảnh báo (LEVEL 1/2/3) kích hoạt còi/đèn
```

