# BSRI — KẾT QUẢ REVIEW & ĐỀ XUẤT CHỈNH SỬA V2

**Dự án:** BlindGuard AI  
**Phân hệ:** `2_BlindSpot_Risk_Calculation / bsri_engine`  
**Bản review:** 02/10/2026  
**Căn cứ:** `HUONG_DAN_TRIEN_KHAI_BSRI_CHI_TIET.md` và các tài liệu nguồn của dự án; đối chiếu thêm nguồn chính thức ISO/UNECE/SAE/Euro NCAP.

---

## 1. Kết luận review

Bản BSRI hiện tại có nền tảng tốt về mặt kiến trúc: tách **spatial risk**, **temporal risk**, **optical blind spot**, **ego maneuver** và có lớp xử lý các trường hợp đặc biệt. Tuy nhiên, tài liệu đang có một vấn đề quan trọng về **truy xuất nguồn gốc tham số (parameter provenance)**:

> Nhiều giá trị số đang được trình bày như thể được quy định trực tiếp bởi ISO/UNECE/Euro NCAP, trong khi các nguồn này chủ yếu cung cấp định nghĩa, phạm vi áp dụng, yêu cầu chức năng hoặc phương pháp thử; chúng không cung cấp trực tiếp các trọng số BSRI và nhiều ngưỡng nội bộ của BlindGuard.

Do đó, V2 cần phân biệt rõ 3 loại giá trị:

1. **Standard-derived:** giá trị/định nghĩa lấy trực tiếp từ tiêu chuẩn hoặc nguồn chính thức.
2. **Vehicle/configuration-derived:** lấy từ kích thước xe, calibration camera, cấu hình trailer hoặc cảm biến thực tế.
3. **Engineering/calibration parameter:** giá trị khởi tạo của nhóm, phải được hiệu chỉnh bằng dữ liệu test và không được ghi là “theo tiêu chuẩn”.

### Các thay đổi bắt buộc

| Hạng mục review | Kết quả V2 |
|---|---|
| Kiểm tra nguồn tham chiếu | Đã kiểm tra lại nguồn chính thức; loại các cách diễn giải quá mức |
| Mục 3.3 `W_vru` | Phải sửa mạnh: Euro NCAP không cung cấp bảng trọng số 1.00/0.90/0.85/... cho BSRI |
| Mục 3.4 | `SWEPT_PATH_LEFT` đã có trong bản hiện tại; V2 chuẩn hóa đối xứng và tách “hình học quỹ đạo” khỏi “mức độ mù” |
| Tham số số học | Bổ sung bảng provenance cho từng tham số |
| Công thức cảm biến | Ghi rõ nguồn từng biến: IMU/GPS/Camera/MOT/vehicle configuration |
| Case đặc biệt | Chuẩn hóa thành điều kiện kích hoạt + cơ chế risk override; không gắn nhãn “chuẩn UNECE” cho phần mở rộng của nhóm |
| Tài liệu tham khảo | Bổ sung bảng tham chiếu ở cuối tài liệu |
| Claim “ASIL-D / <2 ms / tiết kiệm 85% CPU” | Loại khỏi tài liệu nếu không có bằng chứng/thiết kế safety case và benchmark tương ứng |
| Case Bernoulli | Hạ từ “cơ sở chắc chắn” xuống “tình huống engineering cần kiểm chứng”; không dùng Bernoulli làm căn cứ định lượng nếu chưa có mô hình khí động hoặc dữ liệu thử |

---

# 2. Các phát hiện quan trọng cần sửa

## 2.1. `ISO 15622` đang bị dùng sai ngữ cảnh

Bản hiện tại dùng ISO 15622 để làm căn cứ cho ngưỡng TTC 1.2 s và 3.5 s.

Điều này không nên giữ.

ISO 15622:2018 là tiêu chuẩn về **Adaptive Cruise Control (ACC)**. Trang ISO mô tả nó là tiêu chuẩn về chiến lược điều khiển, chức năng tối thiểu, giao diện người lái, chẩn đoán và thử nghiệm ACC. Nó không phải nguồn quy định các trọng số hoặc ngưỡng TTC 1.2 s / 3.5 s của BSRI.

**Cách sửa:**

- Có thể giữ ISO 15622 ở phần tham khảo nền tảng ADAS/ACC.
- Không viết: “Theo ISO 15622, TTC = 3.5 s là ngưỡng cảnh báo của BSRI”.
- Không viết: “ISO 15622 quy định PRT = 0.7–0.85 s”.
- TTC thresholds của BSRI phải được ghi là **engineering/calibration parameters** và hiệu chỉnh bằng dữ liệu thực tế.

ISO 15623 mới là nguồn phù hợp hơn khi nói về **forward vehicle collision warning**, nhưng nó cũng không phải nguồn quy định trực tiếp các trọng số BSRI.

---

## 2.2. UNECE R151 không phải tiêu chuẩn chung cho mọi VRU

Tên chính thức của UN Regulation No. 151 là:

> Blind Spot Information System for the Detection of Bicycles.

Vì vậy không nên viết:

> “UNECE R151 quy định mức nguy hiểm cho motorcycle/person/bicycle”

hoặc dùng R151 làm căn cứ trực tiếp cho trọng số VRU.

R151 có thể được dùng để hỗ trợ phần **blind-spot detection đối với bicycle** và các điều kiện thử tương ứng.

Nếu BlindGuard muốn mở rộng sang `person`, `motorcycle`, `xe_keo`, `xich_lo`, đó là **phạm vi mở rộng của dự án**, cần nói rõ.

---

## 2.3. UNECE R159 phù hợp với moving-off nhưng đối tượng cần ghi đúng

UN Regulation No. 159 là **Moving Off Information System (MOIS)**.

Nguồn UNECE mô tả R159 về phát hiện **pedestrians and cyclists** ở vùng mù phía trước khi xe chuẩn bị chuyển động hoặc chạy thẳng ở tốc độ thấp, tới 10 km/h.

Vì vậy:

- `person`: phù hợp phạm vi R159.
- `bicycle`: phù hợp phạm vi R159.
- `motorcycle`: nếu BlindGuard cảnh báo motorcycle trong case này thì phải ghi là **project extension**, không phải “R159 yêu cầu”.

---

## 2.4. UNECE R158 không chứng minh ngưỡng 2.5 m của nhóm

R158 liên quan đến khả năng phát hiện phía sau khi lùi.

Nguồn UNECE mô tả vùng yêu cầu phát hiện/visibility theo các phạm vi cụ thể của quy định; nó không phải căn cứ để nói:

> “R158 quy định BSRI phải cảnh báo trong 2.5 m”

Do đó `2.5 m` nếu tiếp tục sử dụng phải được ghi là:

> **Giới hạn candidate zone do nhóm lựa chọn ban đầu, cần calibration bằng test track.**

Không ghi là “theo R158”.

---

# 3. Sửa mục 3.3 — `W_vru`

## 3.3.1. Vấn đề của bản hiện tại

Bản hiện tại có:

```text
person       = 1.00
bicycle      = 0.90
xe_keo       = 0.88
xich_lo      = 0.88
motorcycle   = 0.85
car          = 0.65
bus          = 0.65
truck        = 0.60
```

và chú thích rằng bảng này được “xếp hạng theo chuẩn Euro NCAP VRU Protection”.

Cách ghi này **không đủ căn cứ**.

Euro NCAP có các protocol đánh giá pedestrian, bicyclist và motorcyclist/VRU, nhưng không cung cấp một bảng `W_vru` để đưa trực tiếp vào công thức BSRI với các giá trị trên.

### Đề xuất sửa

Không coi các số trên là “trọng số theo Euro NCAP”.

Thay bằng khái niệm:

### `C_vru` — hệ số ưu tiên nhóm đối tượng

`C_vru` là một **feature của mô hình BSRI**, dùng để biểu diễn mức độ ưu tiên an toàn của nhóm đối tượng.

Ở phiên bản baseline:

```text
C_vru = 1.0
```

cho tất cả class trong công thức lõi.

Phân nhóm VRU/non-VRU vẫn được giữ lại để:

- phân tích XAI;
- thiết kế case đặc biệt;
- xây dựng dataset calibration;
- hiệu chỉnh trọng số sau khi có dữ liệu.

Sau khi có dữ liệu test đủ lớn, nhóm có thể học/hiệu chỉnh:

```text
C_vru(class) = f(class, severity, observed outcome)
```

với mục tiêu tối ưu các metric đã xác định trước, ví dụ:

- false negative;
- false positive;
- detection-to-warning latency;
- recall đối với VRU.

### Nếu vẫn muốn giữ trọng số class trong V2

Phải đổi cách gọi thành:

> “Giá trị khởi tạo kỹ thuật của nhóm, không phải giá trị do Euro NCAP/UNECE quy định.”

và bắt buộc bổ sung nguồn dữ liệu dùng để calibration.

---

# 4. Sửa mục 3.4 — `V_blind` và `SWEPT_PATH_LEFT`

## 4.1. `SWEPT_PATH_LEFT` đã tồn tại nhưng cần chuẩn hóa

Bản hiện tại thực tế đã có:

```text
SWEPT_PATH_RIGHT
SWEPT_PATH_LEFT
```

Điểm cần sửa không còn là “thêm tên biến”, mà là **cách định nghĩa**.

### Định nghĩa V2

`SWEPT_PATH_LEFT/RIGHT` trước hết là **phân vùng hình học của swept path**, không tự động đồng nghĩa với mức độ mù quang học.

Nên tách:

```text
Geometry:
    swept_path_side ∈ {LEFT, RIGHT}

Visibility:
    C_visibility ∈ [0,1]

Risk:
    C_blind = f(visibility evidence)
```

Điều này tránh lỗi:

> “xe đang quét sang trái” → tự động kết luận tài xế mù 10%.

Swept path là bài toán **quỹ đạo/hình học**; blind visibility là bài toán **field of view/occlusion**.

---

## 4.2. Không nên mặc định `RIGHT = 1.25`, `LEFT = 1.10`

Các giá trị này hiện chưa có nguồn chính thức đủ mạnh để khẳng định.

Đề xuất baseline:

```text
CLEAR_ZONE         : C_blind = 0
MIRROR_LEFT        : C_blind = calibration
MIRROR_RIGHT       : C_blind = calibration
SWEPT_PATH_LEFT    : C_blind = calibration
SWEPT_PATH_RIGHT   : C_blind = calibration
CAB_FRONT          : C_blind = calibration
REAR_TRAILER       : C_blind = calibration
```

Nếu implementation hiện tại cần một scalar nhân vào BSRI, hãy đặt giá trị baseline theo một calibration document riêng thay vì gắn trực tiếp với UNECE R46.

---

# 5. Bảng provenance — mọi biến phải ghi nguồn

Đây là bảng cần đưa vào tài liệu BSRI.

| Biến | Ý nghĩa | Nguồn dữ liệu | Loại |
|---|---|---|---|
| `v_ego` | vận tốc xe chủ | GPS/GNSS | Sensor |
| `heading` | hướng chuyển động | GPS/GNSS | Sensor |
| `omega_z` | yaw rate | IMU gyroscope | Sensor |
| `a_x`, `a_y` | gia tốc dọc/ngang | IMU accelerometer | Sensor |
| `X_vcs`, `Y_vcs` | vị trí vật thể trong VCS | Camera + calibration/homography | Derived |
| `v_x`, `v_y` | vận tốc vật thể trong VCS | ByteTrack/Kalman + timestamp | Derived |
| `v_closing` | vận tốc khép gần | tính từ vị trí + vận tốc tương đối | Derived |
| `TTC` | time-to-collision | tính từ relative motion | Derived |
| `gamma` | góc gập trailer | tích phân mô hình động học + `omega_z`, `v_ego`, kích thước trailer | Estimated |
| `L_trailer` | chiều dài trailer | cấu hình/đo xe thực tế | Vehicle configuration |
| `W_vehicle` | bề rộng xe | cấu hình/đo xe thực tế | Vehicle configuration |
| `L_wb` | wheelbase | cấu hình/đo xe thực tế | Vehicle configuration |
| `X_front` | vị trí đầu xe trong VCS | vehicle geometry | Vehicle configuration |
| `X_rear` | vị trí đuôi xe trong VCS | vehicle geometry | Vehicle configuration |
| `T_preview` | horizon candidate zone | nhóm lựa chọn | Calibration |
| `S_max` | giới hạn preview distance | nhóm lựa chọn | Calibration |
| `buffer` | vùng cận kề swept path | nhóm lựa chọn | Calibration |
| `sigma_d` | độ dốc suy giảm theo khoảng cách | nhóm lựa chọn | Calibration |
| `w_s`, `w_t` | trọng số spatial/temporal | nhóm lựa chọn → calibration | Calibration |
| `C_vru` | ưu tiên class | nhóm lựa chọn → calibration | Calibration |
| `C_blind` | mức độ mù | visibility model → calibration | Derived + calibration |
| `M_ego` | ảnh hưởng thao tác xe chủ | mô hình nhóm → calibration | Calibration |

### Nguyên tắc bắt buộc

Không được viết:

```text
omega_z = 0.03 rad/s theo UNECE
```

nếu UNECE không quy định giá trị đó.

Phải viết:

```text
omega_z được đo từ IMU.
Ngưỡng |omega_z| > 0.03 rad/s là ngưỡng phát hiện quay do nhóm
khởi tạo và phải calibration theo noise floor của IMU + dữ liệu chạy thử.
```

---

# 6. Căn cứ cho hệ tọa độ và mô hình động học

## 6.1. VCS

Có thể giữ ISO 8855 và SAE J670 làm nguồn cho terminology/vehicle dynamics.

ISO 8855:2011 là tiêu chuẩn về vocabulary cho vehicle dynamics và áp dụng cả commercial vehicles và multi-unit vehicle combinations.

SAE J670_202206 là Recommended Practice về Vehicle Dynamics Terminology, bao gồm axis systems, vehicle bodies, steering, brakes, tires và vehicle responses.

Nhưng:

> ISO 8855 / SAE J670 không phải nguồn xác nhận mọi lựa chọn origin `(0,0)` cụ thể của BlindGuard.

Do đó:

```text
ISO/SAE:
    hỗ trợ terminology + coordinate convention.

BlindGuard:
    tự định nghĩa origin VCS cụ thể của implementation.
```

Origin cần ghi rõ là **design choice của hệ thống**.

---

## 6.2. `gamma` của trailer

Mô hình:

```text
dγ/dt = omega_z - (v/L_trailer) sin(γ)
```

có thể giữ như mô hình động học của hệ xe kéo–rơ-moóc.

Nguồn LaValle có phần riêng về `a car pulling trailers` và mô tả cấu hình/hitch length của hệ xe kéo–rơ-moóc.

Tuy nhiên:

- `L_trailer` phải lấy từ cấu hình xe;
- `gamma_0` phải được khởi tạo;
- tích phân IMU/GPS có thể drift;
- không nên viết “đo được gamma 100%” khi không có cảm biến khớp nối.

Nên dùng:

> “ước lượng góc gập trailer (`gamma`)”

thay cho:

> “đo trực tiếp góc gập”.

---

# 7. Chuẩn hóa các tham số của DHZ

## 7.1. `T_preview = 0.5 s`

Giữ được như **initial engineering parameter**.

Không gọi là “tiêu chuẩn”.

Lý do hợp lý để giữ:

- mục tiêu của DHZ là candidate filtering ngắn hạn;
- không phải stopping distance;
- horizon ngắn giúp giới hạn vùng candidate.

Nhưng phải có calibration plan:

```text
T_preview ∈ {0.3, 0.5, 0.7, 1.0 s}
```

và đánh giá:

- candidate recall;
- false-positive rate;
- latency;
- diện tích polygon.

Chọn giá trị cuối cùng từ dữ liệu test.

---

## 7.2. `S_max = 12 m`

Đây cũng là engineering parameter.

Không có căn cứ để viết:

> “12 m là giới hạn theo tiêu chuẩn”.

Nên viết:

> “12 m là giới hạn candidate-zone được đặt để ngăn polygon phình quá lớn ở tốc độ cao; giá trị cuối phải calibration.”

---

## 7.3. `buffer = 1.0 m`

Không được suy ra từ “làn đường 3.5 m + xe 2.5 m” rồi kết luận 1.8 m là chính xác cho hazard zone.

TCVN 4054:2005 có thể cung cấp thông tin về chiều rộng làn và kích thước xe thiết kế, nhưng:

```text
3.5 - 2.5
```

không tự động suy ra:

```text
buffer = 1.0 m
```

hay:

```text
d0 = 1.8 m
```

Đề xuất:

```text
buffer_initial = 1.0 m
```

là engineering initialization, sau đó calibration theo test track.

---

# 8. Sửa `S_temporal`

Công thức hiện tại:

```text
TTC <= 1.2 s          -> 1.00

1.2 < TTC <= 3.5 s    -> tuyến tính

TTC > 3.5 s           -> 0.30 * exp(...)
```

không nên gắn trực tiếp các mốc 1.2 s và 3.5 s với ISO/UNECE.

### Đề xuất cách trình bày

```text
TTC_critical = calibration parameter
TTC_warning  = calibration parameter
tau_decay    = calibration parameter
```

và:

```text
S_temporal = f(TTC;
               TTC_critical,
               TTC_warning,
               tau_decay)
```

Trong đó:

- `TTC` lấy từ relative motion;
- `TTC_critical`, `TTC_warning`, `tau_decay` được calibration.

### Một điểm quan trọng

TTC cổ điển chỉ có ý nghĩa khi giả định relative motion hiện tại tiếp tục.

Do đó cần ghi:

> TTC là chỉ số động học dựa trên giả định quỹ đạo/vận tốc hiện tại tiếp tục; với turning/trajectory crossing, cần ưu tiên predicted trajectory hoặc TTCE/occupancy-based measure.

Nguồn Continuous Risk Measures for Driving Support có thảo luận TTC, TTCE và spatial occupancy như các risk measures liên tục.

---

# 9. Chuẩn hóa 5 case đặc biệt

Không nên viết:

```text
Case 1 = chuẩn R159
Case 2 = chuẩn R151
...
```

vì implementation của BlindGuard là **mở rộng** các quy định đó.

Nên đổi thành:

| Case | Tên V2 | Căn cứ nguồn | Phần của BlindGuard |
|---|---|---|---|
| 1 | Moving-off front hazard | UNECE R159 | mở rộng detection/risk logic cho class ngoài phạm vi R159 |
| 2 | Turning-side pinch hazard | UNECE R151 + vehicle swept-path model | BlindGuard mở rộng từ bicycle sang các class khác |
| 3 | Reverse hazard | UNECE R158 | BlindGuard xây dựng object-level risk layer |
| 4 | Parallel close-proximity | risk/vehicle-dynamics literature | engineering scenario, cần test |
| 5 | Trailer cornering occlusion | UNECE R46 + vehicle geometry | BlindGuard kết hợp visibility + trailer geometry |

---

# 10. Các ngưỡng case đặc biệt cần đổi trạng thái

Các giá trị sau **không được ghi là giá trị chuẩn UNECE/ISO** nếu không có điều khoản cụ thể:

```text
|v_ego| < 0.20 m/s
v_ego < -0.10 m/s
v_ego >= 8.0 m/s
omega_z > 0.03 rad/s
omega_z > 0.04 rad/s
|omega_z| > 0.08 rad/s
a_x < -1.5 m/s²
a_takeoff = 1.2 m/s²
a_rev = 0.8 m/s²
d_front <= 1.8 m
d_rear <= 2.5 m
d_lateral <= 0.8 m
sigma_lateral = 0.40 m
BSRI override = 0.85 / 0.95
V_blind = 1.35
```

### Cách ghi chuẩn

Ví dụ:

```text
Ngưỡng phát hiện quay:
|omega_z| > omega_turn_threshold

omega_turn_threshold là calibration parameter.
Giá trị initial = 0.03 rad/s.
Giá trị final phải được chọn theo noise floor, sampling rate,
low-pass filter và dữ liệu chạy thử của IMU.
```

---

# 11. Case 4 — Bernoulli cần hạ mức độ khẳng định

Bản hiện tại mô tả:

> “Theo định luật Bernoulli, luồng khí ... tạo lực hút chân không kéo xe máy ngã vào bánh sau”

Không nên dùng câu này như một kết luận định lượng nếu nhóm chưa có:

- mô hình CFD;
- phép đo áp suất;
- đo lateral force;
- hoặc dữ liệu thực nghiệm.

V2 nên ghi:

> “Khoảng cách ngang rất nhỏ khi hai phương tiện chạy song song là một tình huống cần cảnh báo. Ảnh hưởng khí động học có thể là một yếu tố góp phần, nhưng mức độ ảnh hưởng phải được xác minh thực nghiệm; BSRI không sử dụng Bernoulli như một công thức vật lý để tính trực tiếp lực hút.”

Như vậy tài liệu an toàn hơn về mặt khoa học.

---

# 12. Công thức BSRI — vấn đề cần xem xét lại

Công thức hiện tại:

```text
BSRI =
min(
    1,
    (ws*S_spatial + wt*S_temporal)
    * W_vru
    * V_blind
    * M_ego
)
```

có một vấn đề toán học:

`ws*S_spatial + wt*S_temporal` là convex combination nếu `ws+wt=1`, nhưng sau đó nhân với nhiều hệ số >1 thì toàn bộ biểu thức không còn là một convex combination.

Vì vậy không nên gọi toàn bộ công thức là:

> “Convex Combination chuẩn hóa”.

### Khuyến nghị V2

Nên cân nhắc chuyển sang:

```text
BSRI =
clip(
    w_s*S_spatial
  + w_t*S_temporal
  + w_b*C_blind
  + w_v*C_vru
  + w_m*C_maneuver,
    0,
    1
)
```

với:

```text
w_s + w_t + w_b + w_v + w_m = 1
```

và tất cả component nằm trong `[0,1]`.

Ưu điểm:

- dễ giải thích;
- dễ calibration;
- tránh saturation quá sớm;
- không cần các hệ số `1.25`, `1.35`, `1.40` để “khuếch đại” điểm.

Nếu nhóm muốn giữ multiplicative model, phải gọi chúng là **risk modifiers** và calibration toàn bộ pipeline bằng dataset; không gọi là convex combination.

---

# 13. Trọng số `0.45 / 0.55`

Không nên viết:

> “ISO 15622/NHTSA quy định temporal phải chiếm 55%”.

Không có căn cứ đủ trực tiếp cho claim đó.

Có thể giữ:

```text
w_s = 0.45
w_t = 0.55
```

nhưng phải ghi:

> “Initial engineering weights, selected to prioritize imminent relative-motion risk; final values require calibration.”

Sau đó chạy grid search:

```text
w_t ∈ {0.40, 0.45, 0.50, 0.55, 0.60, 0.65}
w_s = 1 - w_t
```

và chọn theo metric đã thống nhất.

---

# 14. Tham số nào lấy từ đâu — quy tắc viết trong tài liệu

Mỗi công thức nên có block:

```text
Nguồn tham số:
- omega_z: IMU gyroscope
- v_ego: GPS/GNSS
- X_vcs, Y_vcs: camera + calibration/homography
- v_x, v_y: tracker/Kalman
- L_trailer: vehicle configuration
- W_vehicle: vehicle measurement/configuration
- gamma: estimated from kinematic model
- TTC: derived quantity
- threshold: engineering/calibration parameter
```

Đây nên trở thành quy tắc chung cho toàn bộ chương 3 và 4.

---

# 15. Worked Example cũng phải sửa

Ví dụ hiện tại có điểm chưa ổn:

```text
v_x = -0.5
v_y = +0.2
```

được dùng để tính `v_closing`, nhưng sau đó TTC lại được gán:

```text
TTC = 1.5 s
```

mà không tính từ công thức tương ứng.

Đây là lỗi cần sửa.

### V2

Nếu:

```text
v_closing = 0.53 m/s
distance = d
```

thì phải tính:

```text
TTC = d / v_closing
```

hoặc nếu sử dụng predicted trajectory:

```text
TTC = first_time_at_which(
    predicted_object_geometry intersects predicted_vehicle_geometry
)
```

Không được vừa tính `v_closing`, vừa gán TTC thủ công mà không giải thích.

---

# 16. Các claim nên loại hoặc đổi cách diễn đạt

### Loại bỏ / sửa:

- “Tỷ lệ tử vong ... gần như 100%”
- “R151 chứng minh 35–42%”
- “R158 = tăng 40%”
- “phanh khí nén = 0.35–0.50 s theo UNECE R13” nếu không có điều khoản cụ thể
- “ASIL-D bắt buộc direct trip <2 ms”
- “Kalman smoothing latency 300–500 ms”
- “tiết kiệm 85% CPU”
- “SWEPT_PATH_RIGHT nguy hiểm hơn theo UNECE”
- “Euro NCAP quy định W_vru”
- “3.5 s là ngưỡng tiêu chuẩn”
- “1.2 s là tổng PRT + brake lag tiêu chuẩn”

Nếu muốn giữ các con số này, cần đưa nguồn nghiên cứu cụ thể và đúng ngữ cảnh vào bảng tham chiếu.

---

# 17. Bảng tài liệu tham khảo V2

| ID | Tài liệu | Dùng để hỗ trợ | Không dùng để khẳng định |
|---|---|---|---|
| [R1] | ISO 8855:2011 — Road vehicles — Vehicle dynamics and road-holding ability — Vocabulary | terminology, vehicle dynamics, coordinate concepts | không quy định BSRI weights |
| [R2] | SAE J670_202206 — Vehicle Dynamics Terminology | axis systems, vehicle dynamics terminology | không quy định BSRI thresholds |
| [R3] | UN Regulation No. 151 — Blind Spot Information System for the Detection of Bicycles | bicycle blind-spot detection/test context | không phải trọng số VRU chung |
| [R4] | UN Regulation No. 159 — Moving Off Information System | pedestrian/cyclist moving-off/front blind spot | không quy định motorcycle BSRI weight |
| [R5] | UN Regulation No. 158 — Devices for means of rear visibility or detection | reversing/rear detection context | không quy định BSRI = 0.95 hay 2.5 m |
| [R6] | UN Regulation No. 46 — Devices for indirect vision | indirect vision / mirror classes | không quy định `V_blind = 1.25` |
| [R7] | ISO 15623:2013 — Forward vehicle collision warning systems | FCW/TTC-related system context | không quy định BlindGuard weights |
| [R8] | ISO 15622:2018 — Adaptive cruise control systems | ACC context | không dùng làm nguồn trực tiếp cho TTC 1.2/3.5 s |
| [R9] | ISO 22839:2013 — Forward vehicle collision mitigation systems | forward collision mitigation concepts | không quy định BlindGuard lateral blind-zone weights |
| [R10] | Euro NCAP AEB/LSS VRU Test Protocol | pedestrian/bicyclist/motorcyclist VRU testing | không cung cấp `W_vru` của BlindGuard |
| [R11] | FHWA — Low-Speed Offtracking | off-tracking concept | không quy định BSRI weights |
| [R12] | S. M. LaValle — Planning Algorithms, Chapter 13 | kinematic model of car pulling trailers | không quy định BlindGuard thresholds |
| [R13] | Eggert & Puphal, “Continuous Risk Measures for Driving Support”, arXiv:2303.08007 | TTC, TTCE, spatial occupancy/risk measures | không phải tiêu chuẩn bắt buộc |
| [R14] | Tang, “A semi-trailer truck right-hook turn blind spot alert system...”, arXiv:2303.11223 | right-hook truck blind-spot research context | không phải nguồn quy định BSRI |
| [R15] | TCVN 4054:2005 — Đường ô tô — Yêu cầu thiết kế | reference cho kích thước đường/làn và một số kích thước thiết kế | không suy ra trực tiếp buffer BSRI |

---

# 18. Nguồn đã kiểm tra

## ISO

- ISO 8855:2011 — trang ISO chính thức.
- ISO 15622:2018 — trang ISO chính thức; hiện ISO đang phát triển ISO/DIS 15622 bản mới.
- ISO 15623:2013 — trang ISO chính thức.
- ISO 22839:2013 — trang ISO chính thức.

## UNECE

- UN Regulation No. 151 — Blind Spot Information System for the Detection of Bicycles.
- UN Regulation No. 158 — Devices for means of rear visibility or detection.
- UN Regulation No. 159 — Moving Off Information System.
- UN Regulation No. 46 — Devices for indirect vision.

## SAE

- SAE J670_202206 — Vehicle Dynamics Terminology.

## Euro NCAP

- AEB/LSS VRU Test Protocol, version 4.5.1.
- VRU assessment protocol.

## Research / technical references

- LaValle — Planning Algorithms, Chapter 13.
- Eggert & Puphal — Continuous Risk Measures for Driving Support.
- Tang — semi-trailer truck right-hook blind-spot alert research.
- FHWA — Low-Speed Offtracking.
- TCVN 4054:2005.

---

# 19. Checklist trước khi chốt tài liệu

- [ ] Mọi tiêu chuẩn có link/reference chính thức.
- [ ] Mỗi con số trong công thức có một trong ba nhãn: Standard / Vehicle / Calibration.
- [ ] Không viết “theo ISO/UNECE” nếu nguồn không quy định trực tiếp con số.
- [ ] `W_vru` được đổi thành calibrated engineering feature.
- [ ] `SWEPT_PATH_LEFT` và `SWEPT_PATH_RIGHT` được định nghĩa đối xứng về geometry.
- [ ] Visibility được tách khỏi swept-path geometry.
- [ ] `omega_z`, `a_x`, `v_ego`, `v_x`, `v_y` đều có nguồn sensor/algorithm rõ ràng.
- [ ] `gamma` được gọi là estimated state, không phải measured state.
- [ ] Worked Example tính TTC nhất quán từ dữ liệu đầu vào.
- [ ] Các special cases được gọi là “BlindGuard extensions” khi vượt phạm vi của UNECE.
- [ ] Case Bernoulli không được dùng như định luật định lượng nếu chưa có thực nghiệm.
- [ ] Xem lại công thức multiplicative BSRI; cân nhắc weighted-sum toàn bộ.
- [ ] Ngưỡng SAFE/CAUTION/WARNING/CRITICAL được calibration từ dataset.
- [ ] Các claim “11/11 PASS”, “85% CPU”, “<2 ms” chỉ giữ nếu có log/benchmark có thể xuất trình.
- [ ] Bảng tham chiếu được đặt ở cuối tài liệu BSRI chính.

---

## 20. Kết luận triển khai

Bản V2 không cần thay đổi triết lý cốt lõi của BlindGuard:

```text
Camera
  ↓
Detection
  ↓
Tracking
  ↓
VCS + object velocity
  ↓
Swept-path / Dynamic Hazard Candidate Zone
  ↓
Spatial + Temporal + Visibility + Object + Ego-state
  ↓
BSRI
  ↓
Warning
```

Điểm cần thay đổi là **mức độ khoa học của cách trình bày**:

> Tiêu chuẩn cung cấp nền tảng và ràng buộc hệ thống; mô hình BSRI là thiết kế của BlindGuard; còn các trọng số/ngưỡng số phải được chứng minh bằng calibration và test data.

Đây là cách trình bày an toàn hơn khi hội đồng hỏi:

> “Con số 1.25, 0.85, 0.03 rad/s hoặc 0.5 s này lấy từ đâu?”

Câu trả lời phải luôn chỉ ra được **sensor → công thức → nguồn tham chiếu hoặc calibration procedure**.
