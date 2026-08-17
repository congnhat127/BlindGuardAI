# BÁO CÁO TOÀN DIỆN MÔ HÌNH TOÁN HỌC HỆ THỐNG VÙNG MÙ ĐỘNG (BLINDGUARD AI)

> [!NOTE]
> Tài liệu này hệ thống hóa toàn bộ đại lượng, thông số hình học, phương trình vi phân động học, lý thuyết quang hình học chiếu tia (Ray-Casting Occlusion), kiến trúc tự động suy luận thông số từ tiêu chuẩn ô tô quốc tế, mô hình đa hình xe thân liền, quy trình tích hợp Multi-Camera Real-time và Từ điển Thuật ngữ Kỹ thuật Anh - Việt.

---

## 1. HỆ TỌA ĐỘ VÀ KIẾN TRÚC TỰ ĐỘNG SUY LUẬN THÔNG SỐ (DERIVED CONFIG ARCHITECTURE)

### 1.1. Hệ tọa độ Gán trên Phương tiện (Body-Fixed Frame $O_{tractor}-XY$)
Hệ tọa độ $2\text{D}$ chính được chọn làm chuẩn chuẩn hóa (Ego-Centric Frame) có:
* **Gốc tọa độ $(0,0)$**: Đặt tại tâm trục sau của xe Đầu kéo (Tractor Rear Axle Center).
* **Trục $X$ (Trục dọc xe)**: Hướng về phía trước cabin ($X > 0$ là phía trước, $X < 0$ là phía sau).
* **Trục $Y$ (Trục ngang xe)**: Hướng sang bên trái cabin theo quy ước bàn tay trái ($Y > 0$ là bên trái/tài xế, $Y < 0$ là bên phải/phụ xe).

```
                      +Y (Bên trái / Tài xế)
                        ^
                        |       [CABIN]
                        |  +----------------+
   (Sau rơ-moóc) <-- ---+--|--- (0,0) ------|---> +X (Mũi xe / Phía trước)
                        |  +----------------+
                        |
                      -Y (Bên phụ / Phụ xe)
```

---

### 1.2. Cơ chế Tự động Suy luận Thông số từ 4 Số Đăng kiểm
Để loại bỏ hoàn toàn việc đo đạc thủ công 25+ thông số hình học phức tạp, hệ thống áp dụng **Kiến trúc Tự động Suy luận (Derived Config Architecture)**. Người dùng **chỉ cần nhập 4 thông số cơ bản** trích xuất từ Sổ Đăng kiểm / Catalog kỹ thuật của xe:

1. `WHEELBASE_TRACTOR` ($L_f$): Chiều dài cơ sở đầu kéo ($3.6\text{m}$).
2. `CAB_WIDTH` ($W_{cab}$): Chiều rộng cabin ($2.5\text{m}$).
3. `L_TRAIL` ($L_{trail}$): Chiều dài rơ-moóc ($12.0\text{m}$).
4. `W_TRAIL` ($W_{trail}$): Chiều rộng rơ-moóc ($2.5\text{m}$).

---

### 1.3. Bảng Cơ sở Tiêu chuẩn Kỹ thuật Ô tô Quốc tế & Việt Nam

Toàn bộ 25 thông số vị trí chi tiết được suy ra tự động dựa trên các quy chuẩn kỹ thuật ô tô chuẩn hóa:

| Đại lượng phụ | Công thức suy luận tự động | Giá trị mẫu | Đơn vị | Tiêu chuẩn Kỹ thuật căn cứ |
| :--- | :--- | :--- | :--- | :--- |
| **Mũi xe** `CAB_FRONT_X` | $L_f + 0.40\text{m}$ | $4.0$ | $\text{m}$ | **QCVN 09:2015/BGTVT**: Độ nhô cản trước cố định $40\text{cm}$ so với trục lái bánh trước. |
| **Đuôi cabin** `CAB_REAR_X` | $L_f \times 0.61$ | $2.2$ | $\text{m}$ | Khảo sát hình học cabin đầu bằng (COE Cab-Over-Engine). |
| **Chốt kéo** `D_HITCH` | $L_f \times 0.08$ | $0.3$ | $\text{m}$ | **SAE J694 / ISO 1726**: Mâm xoay lệch $7.5\% - 8.5\%$ trước trục sau để phân bổ $33\%$ tải lên cầu trước. |
| **Nhô rơ-moóc** `TRAIL_OVERHANG`| $L_f \times 0.25$ | $0.9$ | $\text{m}$ | Tiêu chuẩn bán kính quay mâm xoay kéo container. |
| **Mắt tài xế** `EYE_X, EYE_Y` | $X_E = L_f \times 0.78$; $Y_E = W_{cab} \times 0.20$ | $(2.8, 0.5)$ | $\text{m}$ | **SAE J941 (Eyellipse Standard)**: Định vị vùng oval mắt tài xế chuẩn xe tải hạng nặng. |
| **Gương hậu** `MIRROR_R_X, MIRROR_R_Y`| $X_M = L_f \times 0.97$; $Y_M = \pm(W_{half} + 0.10)$ | $(3.5, \pm 1.35)$| $\text{m}$ | **QCVN 09:2015/BGTVT**: Gương gắn sát chân kính trước và vươn ra ngoài hông xe $10\text{cm}$. |
| **Cột A** `A_PILLAR_X, A_PILLAR_Y`| $X_A = X_M - 0.10$; $Y_A = \pm(W_{half} - 0.05)$ | $(3.4, \pm 1.20)$| $\text{m}$ | Khung gia cường cửa sổ phía trước cabin. |
| **Cột B** `B_PILLAR_X, B_PILLAR_Y`| $X_B = X_{rear}$; $Y_B = \pm W_{half}$ | $(2.2, \pm 1.25)$| $\text{m}$ | Vách kim loại kín sau cửa sổ chắn tầm nhìn ngoái vai. |

---

## 2. MÔ HÌNH ĐỘNG HỌC KHỚP NỐI RƠ-MOÓC (TRAILER KINEMATICS - LENG & MINOR 2010)

### 2.1. Phương trình Vi phân Góc Gập ($\gamma$)

$$\frac{d\gamma(t)}{dt} = \omega(t) - \frac{v(t)}{L_{TRAIL}} \sin\gamma(t)$$

#### 2.1.1. Định nghĩa Đại lượng & Đơn vị
* $\gamma(t)$: Góc gập tương đối giữa rơ-moóc và đầu kéo. Đơn vị: Radian ($\text{rad}$).
* $\frac{d\gamma(t)}{dt}$: Tốc độ biến thiên góc gập rơ-moóc. Đơn vị: Radian trên giây ($\text{rad/s}$).
* $\omega(t)$: Tốc độ góc quay Yaw của xe đầu kéo. Đơn vị: Radian trên giây ($\text{rad/s}$).
* $v(t)$: Vận tốc tịnh tiến của đầu kéo. Đơn vị: Mét trên giây ($\text{m/s}$).
* $L_{TRAIL}$: Chiều dài cơ sở rơ-moóc ($12.0\text{m}$).

#### 2.1.2. Ứng dụng trong Mã nguồn (`occlusion_calculator.py`)
```python
d_gamma = self.yaw_rate - (v / config.L_TRAIL) * math.sin(self.gamma)
self.gamma += d_gamma * dt
```

---

### 2.2. Chuyển đổi từ Góc Bẻ Lái Vô-lăng ($\delta_{wheel}$) sang Yaw Rate ($\omega$)

$$\delta_{front} = \frac{\delta_{wheel}}{\text{STEER\_RATIO}}, \quad \omega = \frac{v}{\text{WHEELBASE\_TRACTOR}} \cdot \tan(\delta_{front})$$

---

## 3. MÔ HÌNH ĐA HÌNH CHO XE THÂN LIỀN CỐ ĐỊNH (RIGID VEHICLE MODEL)

Đối với các dòng xe không có khớp nối gập (như Xe buýt, Xe tải thùng 1 thân, Xe SUV, Xe Dump Truck), mô hình toán học tự động suy biến thành **Xe Thân liền Cố định (Rigid Body)**:

1. **Triệt tiêu Động học khớp nối:**
   $$\gamma(t) \equiv 0, \quad \frac{d\gamma(t)}{dt} \equiv 0$$
2. **Hình học Thân xe:** Suy biến từ 2 khối đa giác uốn gập thành **1 khối đa giác hình chữ nhật duy nhất** ($L_{vehicle} \times W_{vehicle}$).
3. **Quỹ đạo lấn lề Đuôi xe văng (Rear Overhang Outswing):**
   Vùng nguy hiểm khi rẽ của xe thân liền do độ nhô đuôi xe văng ra phía ngoài bán kính cua:
   $$\Delta y_{outswing} = \sqrt{R_{rear}^2 + L_{rear\_overhang}^2} - R_{rear}$$

---

## 4. CHI TIẾT MÔ HÌNH QUANG HÌNH HỌC TỔNG QUÁT (RAY-CASTING SILHOUETTE SHADOW)

### 4.1. Phương trình Tia Sáng Chiếu (Ray Projection Equation)

$$\vec{P}(t) = \vec{O} + R \cdot \frac{\vec{P}_{target} - \vec{O}}{\|\vec{P}_{target} - \vec{O}\|}$$

---

### 4.2. Vùng mù Quang học Phía trước Cabin 3D (Front Bonnet / Windshield Projection)

$$d_{front\_ground} = Z_{bonnet} \cdot \frac{X_{front\_cab} - X_{eye}}{Z_{eye} - Z_{bonnet}}$$

---

### 4.3. Thuật toán Bắn tia Đỉnh nổi 2D Tổng quát cho Gương Chiếu Hậu (Rearward Normalized Silhouette Ray-Casting)

$$\theta_{norm} = \begin{cases} \theta_{raw} + \pi & \text{nếu } \theta_{raw} \le 0 \\ \theta_{raw} - \pi & \text{nếu } \theta_{raw} > 0 \end{cases}$$

---

## 5. PIPELINE TÍCH HỢP MULTI-CAMERA AI REAL-TIME

```
 [ Hardware ]                                 [ Real-Time Software Pipeline ]
--------------                                -------------------------------
 (1) Multi-Cameras ──> [ Frame Capture ] ──> [ 2. YOLO11 Detection ] 
                                                      │
                                                      ▼ (Footprint u, v)
 (2) CAN-Bus/GPS   ──> [ Speed v, Steer δ ] ──> [ 3. Homography 2D->3D ] ──> [ 4. Point-in-Polygon ] ──> [ 5. Driver Alert ]
                                                      ▲                                                   (Còi / Màn hình)
                                                      │
                       [ 1. Ray-Casting Dynamic Occlusion Engine (occlusion_calculator.py) ]
```

### 5.1. Bảng Khai báo Ánh xạ Camera trong `config.py` (`CAMERAS_EXTRINSICS`)

| Camera (`camera_name`) | Tọa độ Lắp đặt ($X, Y, Z$) | Góc quay ($Pitch, Yaw$) | Tập Vùng mù Quản lý tương ứng (`monitored_blind_zones`) |
| :--- | :--- | :--- | :--- |
| **`MIRROR_R`** | $(MIRROR\_R\_X, MIRROR\_R\_Y, EYE\_Z)$ | Pitch: $-15^\circ$, Yaw: $-165^\circ$ | `right_side_occlusion`, `a_pillar_right`, `b_pillar_right`, `swept_path_right` |
| **`MIRROR_L`** | $(MIRROR\_L\_X, MIRROR\_L\_Y, EYE\_Z)$ | Pitch: $-15^\circ$, Yaw: $+165^\circ$ | `left_side_occlusion`, `a_pillar_left`, `b_pillar_left`, `swept_path_left` |
| **`FRONT_CAM`** | $(CAB\_FRONT\_X, 0.0, EYE\_Z + 0.3)$ | Pitch: $-10^\circ$, Yaw: $0^\circ$ | `front_bonnet`, `stopping_hazard` |

---

### 5.2. Công thức Chiếu ngược Homography 2D-to-3D (`camera_calibration.py`)
Từ điểm bàn chân đối tượng $(u_{foot}, v_{foot})$ thu được bởi YOLO11, vector hướng tia nhìn trong hệ tọa độ camera:
$$\vec{v}_{cam} = \mathbf{K}^{-1} \cdot \begin{bmatrix} u_{foot} \\ v_{foot} \\ 1 \end{bmatrix}$$
Chuyển sang hệ tọa độ xe VCS bằng ma trận xoay $R_{cam}$:
$$\vec{v}_{vcs} = R_{cam} \cdot \vec{v}_{cam}$$
Tọa độ thực mét $(X_{vcs}, Y_{vcs})$ trên mặt đường $Z_{vcs} = 0$:
$$\lambda = \frac{-T_{cam\_z}}{v_{vcs\_z}}, \quad X_{vcs} = T_{cam\_x} + \lambda \cdot v_{vcs\_x}, \quad Y_{vcs} = T_{cam\_y} + \lambda \cdot v_{vcs\_y}$$

---

## 6. TỪ ĐIỂN THUẬT NGỮ VÀ KHÁI NIỆM KỸ THUẬT ANH - VIỆT (TECHNICAL GLOSSARY)

### 6.1. Chi tiết 3 Góc Định hướng Không gian (Orientation Angles)
* **Yaw (Góc dạt / Góc quay hướng)**: Góc quay của xe hoặc ống kính camera quanh **trục đứng Z** (hướng vuông góc mặt đất). Khi tài xế rẽ trái/phải, xe thay đổi góc Yaw với tốc độ góc gọi là **Yaw Rate ($\omega$)**.
* **Pitch (Góc cúi / Góc ngẩng)**: Góc quay quanh **trục ngang Y** (trục song song bánh xe). Đối với camera, việc chúi ống kính xuống đường chính là góc Pitch (`pitch_deg = -15.0°`).
* **Roll (Góc nghiêng lắc hông)**: Góc quay quanh **trục dọc X** (trục chạy dài theo thân xe). Khi xe nghiêng hông trên đèo dốc là hiện tượng Roll.

---

### 6.2. Thuật ngữ Kỹ thuật Hệ thống

| Thuật ngữ Tiếng Anh | Thuật ngữ Tiếng Việt tương đương | Ý nghĩa trong Hệ thống BlindGuard AI |
| :--- | :--- | :--- |
| **Yaw Rate ($\omega$)** | Tốc độ góc dạt / Tốc độ quay đầu xe | Tốc độ xe quay tròn quanh trục đứng (đơn vị: rad/s hoặc deg/s). |
| **Articulation Angle ($\gamma$)**| Góc gập khớp nối rơ-moóc | Góc lệch giữa trục dọc xe đầu kéo và trục dọc rơ-moóc. |
| **Jackknife** | Lỗi gấp dao găm (Va quẹt khớp rơ-moóc)| Lỗi nguy hiểm khi rơ-moóc bị trượt dạt gập sát vào hông cabin đầu kéo. |
| **Swept Path** | Quỹ đạo quét / Vùng quét lấn lề | Vùng mặt đường bị bánh xe sau của rơ-moóc (hoặc đuôi xe) quét qua khi rẽ. |
| **Rear Overhang Outswing** | Vùng văng đuôi xe | Vùng đuôi xe nhô ra sau trục bánh văng sang hông ngược chiều rẽ. |
| **Ray-Casting** | Thuật toán Bắn tia chiếu bóng | Phương pháp mô phỏng tia sáng từ mắt/gương bắn ra để xác định bóng khuất. |
| **Occlusion Shadow** | Bóng khuất / Vùng mù vật lý | Vùng mặt đường bị các cấu trúc xe (Cột A, Cột B, Thùng xe) che khuất tầm nhìn. |
| **Ego-Vehicle / Ego-Centric** | Phương tiện trung tâm (Xe chủ) | Chiếc xe tải/đầu kéo thực tế đang mang hệ thống cảm biến BlindGuard AI. |
| **Vehicle Coordinate System (VCS)**| Hệ tọa độ xe chủ | Hệ tọa độ gắn liền trên xe có gốc $(0,0)$ tại tâm trục sau đầu kéo. |
| **Homography (Inverse Projection)**| Phép biến đổi đồng dạng phối cảnh | Thuật toán quy đổi tọa độ 2D từ ảnh Pixel Camera ra mét thực trên mặt đường. |
| **Bounding Box Footprint** | Điểm tiếp xúc mặt đường của đối tượng| Điểm chân của khung bao AI (YOLO11) tại vị trí người/xe chạm mặt đất. |
| **Point-in-Polygon (PiP)** | Thuật toán Điểm trong Đa giác | Kiểm tra tọa độ người/xe có nằm bên trong vùng mù nguy hiểm hay không. |
| **Intrinsic Matrix ($K$)** | Ma trận Nội tại Camera | Các hằng số quang học nội bộ ống kính: Tiêu cự ($f_x, f_y$) và Tâm ảnh ($c_x, c_y$). |
| **Extrinsic Matrix ($[R \mid T]$)** | Ma trận Ngoại tại Camera | Tọa độ vị trí lắp đặt ($T$) và Góc xoay hướng ($R$) của camera trên thân xe. |
| **Derived Config Architecture**| Kiến trúc Tự động Suy luận Thông số | Cơ chế tự động tính 25 thông số phụ chỉ từ 4 thông số Sổ Đăng kiểm cơ bản. |

---

> **Kết luận:** Mô hình toán học BlindGuard AI đã hoàn thiện toàn diện từ cơ sở lý thuyết, các tiêu chuẩn ô tô quốc tế, kiến trúc suy luận rút gọn thông số, mô hình đa hình loại xe, pipeline tích hợp Multi-Camera Homography Real-time đến Bảng Từ điển Thuật ngữ Kỹ thuật Anh - Việt!
