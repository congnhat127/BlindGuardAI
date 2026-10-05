# TÀI LIỆU ĐẶC TẢ KỸ THUẬT & MÔ HÌNH TOÁN HỌC HỆ THỐNG BLINDGUARD AI
## SYSTEM MATHEMATICAL MODEL & PARAMETRIC VERIFICATION SPECIFICATION

> **Phiên bản tài liệu:** 2.0 (Toàn diện & Độc lập)  
> **Phân hệ mục tiêu:** Thư mục `BlindGuard_App/` — Hệ thống hỗ trợ an toàn & cảnh báo rủi ro điểm mù thời gian thực cho xe tải nặng và xe đầu kéo sơ-mi rơ-moóc  
> **Mục đích tài liệu:** Cung cấp toàn bộ công thức toán học, không gian trạng thái, ma trận chuyển đổi tọa độ, ngưỡng số học (thresholds), trọng số (weights) và các tham số kỹ thuật để phục vụ quá trình phản biện, thẩm định độc lập (AI-to-AI Verification & Peer Review) theo các tiêu chuẩn quốc tế ISO, SAE và UNECE.

---

## MỤC LỤC
1. [Tổng Quan Kiến Trúc & Cấu Trúc Thư Mục `BlindGuard_App/`](#1-tổng-quan-kiến-trúc--cấu-trúc-thư-mục-blindguard_app)
2. [Hệ Quy Chiếu Tọa Độ Xe Chủ (VCS - ISO 8855 / SAE J670)](#2-hệ-quy-chiếu-tọa-độ-xe-chủ-vcs---iso-8855--sae-j670)
3. [Mô Hình Hình Học Thân Xe (Vehicle Geometric Footprint)](#3-mô-hình-hình-học-thân-xe-vehicle-geometric-footprint)
4. [Mô Hình Chuyển Đổi Phối Cảnh Homography 4 Camera Mặt Đất](#4-mô-hình-chuyển-đổi-phối-cảnh-homography-4-camera-mặt-đất)
5. [Động Học Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ)](#5-động-học-vùng-nguy-hiểm-động-dynamic-hazard-zone---dhz)
6. [Mô Hình Phân Vùng Điểm Mù Không Gian (Blind Spot Zones & Factor)](#6-mô-hình-phân-vùng-điểm-mù-không-gian-blind-spot-zones--factor)
7. [Chỉ Số Rủi Ro Điểm Mù BSRI (Blind Spot Risk Index Engine)](#7-chỉ-số-rủi-ro-điểm-mù-bsri-blind-spot-risk-index-engine)
8. [Bộ Lọc An Toàn 5 Kịch Bản Đặc Biệt (Fast-Path Safety Gatekeeper)](#8-bộ-lọc-an-toàn-5-kịch-bản-đặc-biệt-fast-path-safety-gatekeeper)
9. [Bảng Tra Cứu Toàn Bộ Tham Số, Biến Số & Cơ Sở Khoa Học](#9-bảng-tra-cứu-toàn-bộ-tham-số-biến-số--cơ-sở-khoa-học)
10. [Tài Liệu Nghiên Cứu & Tiêu Chuẩn Quốc Tế Dẫn Chiếu (Verification References)](#10-tài-liệu-nghiên-cứu--tiêu-chuẩn-quốc-tế-dẫn-chiếu-verification-references)

---

## 1. TỔNG QUAN KIẾN TRÚC & CẤU TRÚC THƯ MỤC `BlindGuard_App/`

Hệ thống được thiết kế theo triết lý **Phi xâm lấn (Non-invasive Architecture)**: Tuyệt đối không đấu nối vật lý vào mạng CAN-bus hoặc cổng chẩn đoán OBD-II của xe thương mại nhằm đảm bảo điều kiện bảo hành của hãng sản xuất và phòng chống rủi ro can nhiễu an toàn mạng (Cybersecurity ISO 21434).

```
BlindGuard_App/
│
├── config/
│   ├── system_config.json          # Cấu hình kích thước hình học xe và ma trận Homography 4 camera
│   └── bytetrack_fisheye.yaml      # Tham số bộ theo dõi ByteTrack tối ưu cho góc nhìn camera điểm mù
│
├── core/
│   ├── __init__.py
│   ├── config_loader.py            # Module nạp, cập nhật và lưu trữ system_config.json
│   ├── risk_models.py              # Định nghĩa cấu trúc dữ liệu, Enums (RiskLevel, BlindSpotZone, VehicleType)
│   ├── homography_manager.py       # Quản lý ma trận chiếu H, quy đổi pixel -> VCS và xử lý tỉ lệ khung hình
│   ├── motion_analyzer.py          # Ước tính trạng thái động học xe chủ phi xâm lấn (IMU/GPS/Video Context)
│   ├── bsri_calculator.py          # Bộ lõi toán học tính toán chỉ số rủi ro BSRI, DHZ, TTC và 5 kịch bản
│   └── hud_renderer.py             # Bộ dựng hình giao diện buồng lái Cabin HUD giải thích trực quan (XAI)
│
├── system_configurator/
│   └── run_configurator_gui.py     # Trình GUI hướng dẫn thiết lập 2 bước (Wizard): Xe Profile -> Homography 4 Cam
│
├── run_demo.py                     # Chương trình chạy Demo đầu-cuối tích hợp GUI Launcher chọn video & camera
├── run_demo.bat                    # File batch 1-click khởi chạy Demo Launcher trên Windows
├── run_config.bat                  # File batch 1-click khởi chạy Trình cấu hình hình học & Homography
└── SYSTEM_MATHEMATICAL_MODEL.md   # [Tài liệu hiện tại] Bản đặc tả toán học và tham số thẩm định
```

---

## 2. HỆ QUY CHIẾU TỌA ĐỘ XE CHỦ (VCS - ISO 8855 / SAE J670)

Toàn bộ tính toán không gian và động học trong BlindGuard AI tuân thủ nghiêm ngặt **Hệ tọa độ xe chủ (Vehicle Coordinate System - VCS)** theo chuẩn **ISO 8855:2011** và **SAE J670**:

- **Gốc tọa độ $O (0, 0, 0)$:** Đặt tại hình chiếu của **tâm trục sau xe đầu kéo (Tractor Rear Axle Center)** đối với xe đầu kéo sơ-mi rơ-moóc (`ARTICULATED`), hoặc **tâm trục sau xe tải** đối với xe tải liền thân (`RIGID`) xuống mặt đường phẳng.
- **Trục $X_{\text{vcs}}$ (Longitudinal Axis - Trục dọc):** Nằm ngang mặt đường, hướng thẳng về phía trước mũi xe là chiều dương ($X > 0$); hướng về phía sau đuôi xe là chiều âm ($X < 0$).
- **Trục $Y_{\text{vcs}}$ (Lateral Axis - Trục ngang):** Nằm ngang mặt đường, hướng sang bên trái xe (phía ghế tài xế với xe tay lái thuận) là chiều dương ($Y > 0$); hướng sang bên phải xe (phía gương phụ) là chiều âm ($Y < 0$).
- **Trục $Z_{\text{vcs}}$ (Vertical Axis - Trục đứng):** Vuông góc với mặt đường, hướng lên trời là chiều dương ($Z > 0$). Mặt đất tiếp xúc quy ước $Z = 0$.

```
                     +X (Phía trước mũi xe)
                               ▲
                               │
                [Cabin Phụ]    │    [Cabin Lái]
                (-Y, Phải)     │    (+Y, Trái)
                     ──────────┼──────────► +Y (Bên trái)
                               │  O (Tâm trục sau)
                               │
                               │
                     -X (Phía sau đuôi rơ-moóc/thùng)
```

---

## 3. MÔ HÌNH HÌNH HỌC THÂN XE & PHÂN ĐỊNH THÔNG SỐ (VEHICLE GEOMETRIC FOOTPRINT)

Hệ thống biểu diễn hình bao vật lý của phương tiện qua hệ tọa độ VCS $Z = 0$ (Gốc $O$ tại tâm trục cầu sau xe/đầu kéo, trục $+X$ hướng tới trước mũi xe, trục $+Y$ hướng sang trái). 

Để đảm bảo người dùng và kỹ sư vận hành thuận tiện nhất khi cài đặt từ Giấy chứng nhận Đăng kiểm phương tiện hoặc Catalogue kỹ thuật, **hệ thống phân định rõ rệt 100% giữa thông số BẮT BUỘC NHẬP TAY và thông số TỰ ĐỘNG TÍNH TOÁN**:

---

### 3.1. Xe Đầu Kéo Sơ-Mi Rơ-Moóc (`ARTICULATED`)

Bao gồm hai khối cứng độc lập liên kết qua khớp quay mâm xoay (Kingpin/Fifth-Wheel):

#### A. BẢNG PHÂN ĐỊNH THÔNG SỐ NHẬP TAY VS TỰ ĐỘNG TÍNH TOÁN

| STT | Tên thông số | Ký hiệu | Giá trị chuẩn | Loại thông số | Nguồn / Công thức xác định | Ý nghĩa vật lý / Động lực học |
|:---:|---|:---:|:---:|:---:|---|---|
| **1** | Chiều rộng Cabin đầu kéo | $W_{\text{cab}}$ | $2.50\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe đầu kéo | Xác định mép sườn Cabin trái/phải ($Y = \pm 1.25\text{ m}$) |
| **2** | Chiều rộng thùng rơ-moóc | $W_{\text{trailer}}$ | $2.50\text{ m}$ | **NHẬP TAY** | Đăng kiểm sơ-mi rơ-moóc | Xác định mép sườn thùng rơ-moóc ($Y = \pm 1.25\text{ m}$) |
| **3** | Chiều dài cơ sở đầu kéo | $L_f$ ($L_{\text{wb\_tractor}}$) | $3.60\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe (Tâm trục trước $\to$ Tâm trục sau) | Bán kính quay vòng của đầu kéo |
| **4** | Độ nhô cản trước đầu kéo | $L_{\text{foh\_tractor}}$ | $1.35\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe (Tâm trục trước $\to$ Mép cản trước) | Khoảng cách nhô mũi xe đầu bằng COE |
| **5** | Vị trí chốt mâm xoay Kingpin | $d_{\text{hitch}}$ | $0.30\text{ m}$ | **NHẬP TAY** | Khoảng cách từ tâm trục sau tới chốt Kingpin | Tâm quay tự do của rơ-moóc trên khung xe |
| **6** | Chiều dài cơ sở rơ-moóc | $L_{\text{wb\_trailer}}$ | $8.20\text{ m}$ | **NHẬP TAY** | Chốt Kingpin $\to$ Tâm cụm trục rơ-moóc | **Quyết định độ lấn cua Inswing rơ-moóc** ($\propto L_{\text{wb\_trailer}}^2$) |
| **7** | Độ nhô cản sau rơ-moóc | $L_{\text{roh\_trailer}}$ | $2.80\text{ m}$ | **NHẬP TAY** | Tâm cụm trục $\to$ Mép cản sau thùng hàng | **Quyết định độ văng đuôi Tail-Swing rơ-moóc** |
| **8** | Độ nhô đầu thùng rơ-moóc | $L_{\text{foh\_trailer}}$ | $1.00\text{ m}$ | **NHẬP TAY** | Chốt Kingpin $\to$ Mép trước thùng rơ-moóc | Phần thùng nhô về trước phủ lên mâm xoay |
| **⚡ 9** | **Mũi cản trước đầu kéo** | $X_{\text{front}}$ | **$+4.95\text{ m}$** | **TỰ TÍNH** | $= L_f + L_{\text{foh\_tractor}} = 3.60 + 1.35$ | Tọa độ mép trước cùng của xe trong VCS |
| **⚡ 10** | **Tâm cụm trục rơ-moóc** | $X_{\text{axle\_trailer}}$ | **$-7.90\text{ m}$** | **TỰ TÍNH** | $= d_{\text{hitch}} - L_{\text{wb\_trailer}} = 0.30 - 8.20$ | Tâm quay bánh sau rơ-moóc, tâm chém cua |
| **⚡ 11** | **Mép cản sau rơ-moóc** | $X_{\text{rear}}$ | **$-10.70\text{ m}$** | **TỰ TÍNH** | $= d_{\text{hitch}} - (L_{\text{wb\_trailer}} + L_{\text{roh\_trailer}})$ | Điểm đuôi xa nhất của đoàn xe khi $\gamma = 0$ |
| **⚡ 12** | **Tổng chiều dài thùng rơ-moóc** | $L_{\text{trailer}}$ | **$12.00\text{ m}$** | **TỰ TÍNH** | $= L_{\text{foh\_trailer}} + L_{\text{wb\_trailer}} + L_{\text{roh\_trailer}}$ | Chiều dài kết cấu thùng rơ-moóc (40 feet) |
| **⚡ 13** | **Tổng chiều dài đoàn xe (OAL)** | $L_{\text{total}}$ | **$15.65\text{ m}$** | **TỰ TÍNH** | $= X_{\text{front}} - X_{\text{rear}} = 4.95 - (-10.70)$ | Chiều dài phủ bì toàn bộ tổ hợp xe |

#### B. ĐỘNG HỌC QUAY KHỚP NỐI MÂM XOAY (ARTICULATION KINEMATICS)
Khi rơ-moóc quay một góc gập $\gamma$ quanh khớp mâm xoay $(x_h, y_h) = (d_{\text{hitch}}, 0)$:
Tọa độ một điểm $(p_x, p_y)$ trên rơ-moóc được biến đổi xoay theo ma trận:
$$\begin{bmatrix} p'_x \\ p'_y \end{bmatrix} = \begin{bmatrix} \cos(-\gamma) & -\sin(-\gamma) \\ \sin(-\gamma) & \cos(-\gamma) \end{bmatrix} \begin{bmatrix} p_x - d_{\text{hitch}} \\ p_y \end{bmatrix} + \begin{bmatrix} d_{\text{hitch}} \\ 0 \end{bmatrix}$$
Đa giác thân xe tổng hợp:
$$\mathcal{F}_{\text{art}}(\gamma) = \mathcal{P}_{\text{cabin}} \cup \mathcal{P}_{\text{chassis}} \cup \mathcal{P}_{\text{trailer}}(\gamma)$$

---

### 3.2. Xe Tải Liền Thân / Thùng Cố Định (`RIGID`)

Gồm một khối cứng duy nhất với 4 thông số cơ bản:

#### A. BẢNG PHÂN ĐỊNH THÔNG SỐ NHẬP TAY VS TỰ ĐỘNG TÍNH TOÁN

| STT | Tên thông số | Ký hiệu | Giá trị chuẩn | Loại thông số | Nguồn / Công thức xác định | Ý nghĩa vật lý / Động lực học |
|:---:|---|:---:|:---:|:---:|---|---|
| **1** | Chiều rộng toàn bộ xe | $W_{\text{rigid}}$ | $2.50\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe tải | Xác định mép sườn xe ($Y \in [-1.25\text{ m}, +1.25\text{ m}]$) |
| **2** | Chiều dài cơ sở | $L_{\text{wb}}$ | $5.80\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe (Tâm trục trước $\to$ Tâm trục sau) | Quyết định bán kính quay và độ lấn cua xe |
| **3** | Độ nhô cản trước xe | $L_{\text{foh}}$ | $1.35\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe (Tâm trục trước $\to$ Mép cản trước) | Phần nhô cabin xe tải thùng |
| **4** | Độ nhô cản sau xe | $L_{\text{roh}}$ | $2.40\text{ m}$ | **NHẬP TAY** | Đăng kiểm xe (Tâm trục sau $\to$ Mép cản sau thùng) | **Quyết định độ văng đuôi Tail-Swing xe tải** |
| **⚡ 5** | **Mũi cản trước xe** | $X_{\text{front}}$ | **$+7.15\text{ m}$** | **TỰ TÍNH** | $= L_{\text{wb}} + L_{\text{foh}} = 5.80 + 1.35$ | Tọa độ cản trước cách gốc trục sau |
| **⚡ 6** | **Mép cản sau xe** | $X_{\text{rear}}$ | **$-2.40\text{ m}$** | **TỰ TÍNH** | $= -L_{\text{roh}} = -2.40$ | Tọa độ cản sau thùng sau trục sau |
| **⚡ 7** | **Tổng chiều dài xe (OAL)** | $L_{\text{total}}$ | **$9.55\text{ m}$** | **TỰ TÍNH** | $= X_{\text{front}} - X_{\text{rear}} = 7.15 - (-2.40)$ | Chiều dài toàn bộ thân xe từ cản trước đến cản sau |

> **Lưu ý giải thích độ lệch:** Ở các bản phác thảo cũ từng xuất hiện con số $L_{\text{front}} = 7.80\text{ m}$ khi chiều dài cơ sở là $5.80\text{ m}$. Điều này ngầm định đầu nhô ra $2.00\text{ m}$ là phi thực tế đối với kết cấu xe tải cabin lật/cabin đầu bằng tại Việt Nam (thực tế chỉ $1.25 - 1.40\text{ m}$). Hệ thống BlindGuard AI chuẩn hóa chính xác: $X_{\text{front}} = 5.80 + 1.35 = 7.15\text{ m}$.

---

## 4. MÔ HÌNH CHUYỂN ĐỔI PHỐI CẢNH HOMOGRAPHY 4 CAMERA MẶT ĐẤT

### 4.1. Ánh xạ Homography Phẳng ($Z = 0$)
Do các camera điểm mù quan sát mặt đường phẳng ($Z = 0$), mối quan hệ giữa tọa độ điểm ảnh pixel $\mathbf{p} = [u, v, 1]^T$ và tọa độ mặt đất thế giới thực VCS $\mathbf{P} = [X_{\text{vcs}}, Y_{\text{vcs}}, 1]^T$ là một phép biến đổi xạ ảnh phẳng (Planar Projective Transformation) qua ma trận $3 \times 3$ mang tính khả nghịch:

$$s \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \mathbf{H}_{\text{vcs}\to\text{pixel}} \begin{bmatrix} X_{\text{vcs}} \\ Y_{\text{vcs}} \\ 1 \end{bmatrix}$$

$$\lambda \begin{bmatrix} X_{\text{vcs}} \\ Y_{\text{vcs}} \\ 1 \end{bmatrix} = \mathbf{H}_{\text{pixel}\to\text{vcs}} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \mathbf{H}_{\text{vcs}\to\text{pixel}}^{-1} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$

Giải hệ phương trình với mẫu số đồng nhất:
$$X_{\text{vcs}} = \frac{H_{00} u + H_{01} v + H_{02}}{H_{20} u + H_{21} v + H_{22}}, \quad Y_{\text{vcs}} = \frac{H_{10} u + H_{11} v + H_{12}}{H_{20} u + H_{21} v + H_{22}}$$

### 4.2. Khử Kỳ Dị & Lọc Đường Chân Trời (Horizon Filtering)
Khi $w = H_{20} u + H_{21} v + H_{22} \to 0$, điểm ảnh nằm trên hoặc gần đường chân trời (vanishing line), ánh xạ ra vô cực. Hệ thống áp dụng bộ lọc bảo vệ:
$$\text{Hợp lệ} \iff |w| \ge 10^{-6} \quad \text{và} \quad \text{sign}(w) = \text{sign}(w_{\text{ground}})$$
Nếu không thỏa mãn, điểm chạm đất bị loại bỏ để tránh tạo ra tọa độ giả lập sai lệch.

### 4.3. Bất Biến Độ Phân Giải (Resolution Scaling Invariance)
Khi video đầu vào có độ phân giải $(W_{\text{curr}}, H_{\text{curr}})$ khác với độ phân giải chuẩn lúc hiệu chuẩn $(W_{\text{calib}}, H_{\text{calib}}) = (1280, 720)$, hệ thống tự động co giãn tọa độ pixel trước khi nhân ma trận:
$$u_{\text{norm}} = u \cdot \frac{W_{\text{calib}}}{W_{\text{curr}}}, \quad v_{\text{norm}} = v \cdot \frac{H_{\text{calib}}}{H_{\text{curr}}}$$

### 4.4. Điểm Mốc Hiệu Chuẩn Chuẩn & Ma Trận Thực Tế Trong `system_config.json`
Được xây dựng từ phép giải DLT (Direct Linear Transformation) qua SVD:

| Camera Key | Vị trí lắp đặt | 4 Điểm Pixel $[u, v]$ (px) | 4 Điểm Chuẩn VCS $[X, Y]$ (m) | Sai số tái chiếu |
|---|---|---|---|:---:|
| `MIRROR_RIGHT` | Chân gương phụ (hông phải) | $P_1(850, 680), P_2(1200, 680)$<br>$P_3(750, 420), P_4(1050, 420)$ | $P_1(1.0, -1.6), P_2(1.0, -3.8)$<br>$P_3(-4.5, -1.6), P_4(-4.5, -3.8)$ | **0.000 m** |
| `MIRROR_LEFT` | Chân gương lái (hông trái) | $P_1(430, 680), P_2(80, 680)$<br>$P_3(530, 420), P_4(230, 420)$ | $P_1(1.0, 1.6), P_2(1.0, 3.8)$<br>$P_3(-4.5, 1.6), P_4(-4.5, 3.8)$ | **0.000 m** |
| `CAB_FRONT` | Cản trước gầm cabin | $P_1(400, 680), P_2(880, 680)$<br>$P_3(480, 400), P_4(800, 400)$ | $P_1(4.5, 1.2), P_2(4.5, -1.2)$<br>$P_3(9.0, 1.2), P_4(9.0, -1.2)$ | **0.000 m** |
| `REAR_TRAILER` | Mép trên cản sau rơ-moóc | $P_1(400, 680), P_2(880, 680)$<br>$P_3(480, 400), P_4(800, 400)$ | $P_1(-12.5, 1.2), P_2(-12.5, -1.2)$<br>$P_3(-18.0, 1.2), P_4(-18.0, -1.2)$ | **0.000 m** |

*Ghi chú: Toàn bộ ma trận thỏa mãn $\mathbf{H} \cdot \mathbf{H}^{-1} = \mathbf{I}$ với sai số chuẩn số học $\approx 10^{-15}$.*

---

## 5. ĐỘNG HỌC VÙNG NGUY HIỂM ĐỘNG (DYNAMIC HAZARD ZONE - DHZ)

Đa giác DHZ không phải là hình chữ nhật tĩnh cố định, mà là vùng không gian chiếm dụng động (Dynamic Swept Occupancy) được tính toán theo thời gian chân trời dự báo $T_{\text{horizon}} = 0.50\text{ s}$ kết hợp khoảng đệm an toàn động.

### 5.1. Khoảng Đệm An Toàn Vật Lý Động (Dynamic Buffer)
$$d_{\text{buffer}} = d_{\text{base}} + d_{\text{dynamic}}$$
- $d_{\text{base}} = 1.50\text{ m}$: Khoảng cách an toàn cơ sở cho phương tiện dễ tổn thương (VRU) theo khuyến cáo an toàn đường bộ quốc tế.
- $d_{\text{dynamic}} = \min\left(0.75\text{ m}, \frac{1}{2} |a_y| \cdot t_{\text{react}}^2\right)$: Bù trừ gia tốc lắc ngang $a_y$ khi xe đánh lái đột ngột với thời gian phản xạ $t_{\text{react}} = 0.50\text{ s}$.

### 5.2. Động Học DHZ Đối Với Xe Tải Liền Thân (`RIGID`)
Khi xe tải rẽ góc với tốc độ góc $\omega_z = \text{yaw\_rate}$ (rad/s) và tốc độ dọc $v$ (m/s):
1. **Độ lấn cua sườn xe & bánh sau vào lòng cua (Off-tracking / Inswing) theo mô hình Ackermann / SAE J695:**
   Bán kính quay vòng của trục trước và sau lệch nhau:
   $$\Delta_{\text{inswing}} = \frac{L_{\text{wb}}^2 \cdot |\omega_z|}{2 \cdot \max(1.0, |v|)} = \frac{L_{\text{wb}}^2}{2 R_{\text{turn}}}$$
   Với $L_{\text{wb}} = 5.80\text{ m}$.
2. **Độ văng cản sau ra hướng đối diện (Tail-Swing / Rear Overhang Kickout):**
   Khi đầu xe bẻ vào cua, phần nhô sau trục bánh ($L_{\text{rear}} = 2.40\text{ m}$) văng ngược chiều đánh lái ra làn bên cạnh:
   $$\Delta_{\text{tail-swing}} = L_{\text{rear}} \cdot |\omega_z| \cdot T_{\text{horizon}}$$
3. **Đa giác quét tổng hợp (Swept Polygon):**
   Mép sườn trước/giữa xe mở rộng vào phía trong góc rẽ một lượng $\Delta_{\text{inswing}}$, mép cản sau mở rộng ra phía ngoài một lượng $\Delta_{\text{tail-swing}}$:
   $$\text{DHZ}_{\text{rigid}} = \text{Buffer}\left( \mathcal{F}_{\text{rigid}} \cup \mathcal{P}_{\text{swept}}, d_{\text{buffer}} \right)$$

### 5.3. Động Học DHZ Đối Với Xe Đầu Kéo Sơ-Mi Rơ-Moóc (`ARTICULATED`)
Góc gập $\gamma$ (Articulation angle) giữa đầu kéo và sơ-mi rơ-moóc tuân theo phương trình vi phân động học một vết (Kinematic single-track tractor-semitrailer model - Ellis 1969 / SAE J695):
$$\frac{d\gamma}{dt} = \omega_z - \frac{v \cdot \sin(\gamma) + d_{\text{hitch}} \cdot \omega_z \cdot \cos(\gamma)}{L_{\text{wb\_trailer}}}$$

- Trong đó:
  - $L_{\text{wb\_trailer}} = 8.20\text{ m}$: Chiều dài cơ sở rơ-moóc (khoảng cách từ khớp chốt xoay Kingpin tới tâm cụm trục bánh sau rơ-moóc). *Lưu ý cốt tử: Phương trình vi phân chi phối bởi khoảng cách tới trục bánh sau $L_{\text{wb\_trailer}}$ chứ không phải tổng chiều dài thùng chở hàng $L_{\text{trail}}$.*
  - $d_{\text{hitch}} = 0.30\text{ m}$: Khoảng cách dời mâm xoay trước trục sau đầu kéo.
  - Vận tốc góc tuyệt đối của rơ-moóc: $\omega_{\text{trailer}} = \omega_z - \frac{d\gamma}{dt} = \frac{v \cdot \sin(\gamma) + d_{\text{hitch}} \cdot \omega_z \cdot \cos(\gamma)}{L_{\text{wb\_trailer}}}$.

1. **Độ lấn cua sườn rơ-moóc (Semitrailer Inswing / Off-tracking):**
   Vệt quét của bánh sau rơ-moóc chém sâu vào phía trong tâm góc cua tỉ lệ thuận với bình phương chiều dài cơ sở:
   $$\Delta_{\text{inswing\_trailer}} = \frac{L_f^2 + L_{\text{wb\_trailer}}^2 - d_{\text{hitch}}^2}{2 R_{\text{turn}}} \approx \frac{(3.6)^2 + (8.2)^2 - (0.3)^2}{2 R_{\text{turn}}} = \frac{80.11}{2 R_{\text{turn}}}$$
   *(Lấn cua của tổ hợp đầu kéo rơ-moóc lớn gấp ~2.4 lần so với xe tải liền thân $5.8\text{m}$).*

2. **Độ văng đuôi cản sau rơ-moóc (Trailer Tail-Swing):**
   Do rơ-moóc có độ nhô cản sau $L_{\text{roh\_trailer}} = 2.80\text{ m}$ phía sau cụm trục bánh, khi rơ-moóc đổi hướng thì mép cản sau quét lệch ngược chiều với biên độ:
   $$\Delta_{\text{tail-swing\_trailer}} = L_{\text{roh\_trailer}} \cdot |\omega_{\text{trailer}}| \cdot T_{\text{horizon}}$$

3. **Tích phân số dự báo vết quét thân xe:**
   Tích phân góc gập qua giải thuật Euler với $N = 5$ bước, $\Delta t = \frac{T_{\text{horizon}}}{N} = 0.10\text{ s}$:
   $$\gamma_{k+1} = \gamma_k + \Delta t \left( \omega_z - \frac{v \cdot \sin(\gamma_k) + d_{\text{hitch}} \cdot \omega_z \cdot \cos(\gamma_k)}{L_{\text{wb\_trailer}}} \right)$$
   Hợp nhất các đa giác vết thân xe qua từng bước thời gian:
   $$\text{DHZ}_{\text{art}} = \text{Buffer}\left( \bigcup_{k=0}^{N} \mathcal{F}_{\text{art}}(\gamma_k), d_{\text{buffer}} \right)$$

---

## 6. MÔ HÌNH PHÂN VÙNG ĐIỂM MÙ KHÔNG GIAN (BLIND SPOT ZONES & FACTOR)

Phân loại đối tượng tại $(X, Y)$ vào các vùng quang học theo chuẩn Châu Âu **2003/97/EC** và **UNECE R151/R158/R159**:

```
        ▲ +X
        │
┌───────┴───────┐  [Zone 1: CAB_FRONT] (Class VI)
│  Gầm cản trước│  X in [L_f, x_front + 2.0m], |Y| <= W/2 + 0.8m
└───────┬───────┘
        │
   ┌────┴────┐     [Zone 2 & 3: MIRROR_RIGHT / MIRROR_LEFT] (Class IV/V)
   │  Cabin  │     X in [d_hitch, x_front], Y in [-3.5m, -W/2] hoặc [W/2, 3.5m]
   └────┬────┘
        │
 ╔══════╧══════╗   [Zone 4 & 5: SWEPT_PATH_RIGHT / SWEPT_PATH_LEFT]
 ║ Thùng / Rơ- ║   Bụng cua quét sườn rơ-moóc/xe tải khi ôm cua
 ║    moóc     ║   X in [x_rear, d_hitch], |Y| in [W/2, 4.5m]
 ╚══════╤══════╝
        │
┌───────┴───────┐  [Zone 6: REAR_TRAILER] (UNECE R158)
│Điểm mù lùi sau│  X in [x_rear - 3.5m, x_rear], |Y| <= W/2 + 1.0m
└───────────────┘
```

### Bảng Hệ Số Góc Mù Quang Học ($V_{\text{blind}}$)

| Phân Vùng Điểm Mù | Mã Vùng | Tiêu Chuẩn Quốc Tế | $V_{\text{blind}}$ | Cơ sở lý luận kỹ thuật |
|---|---|---|:---:|---|
| **Điểm mù lùi xe** | `REAR_TRAILER` | UNECE R158 | **1.35** | Không có tầm nhìn qua gương chiếu hậu; chiều dài thùng $\ge 12\text{m}$ che khuất 100% tầm nhìn trực tiếp. |
| **Bụng cua sườn phụ** | `SWEPT_PATH_RIGHT` | UNECE R151 | **1.30** | Vùng nguy hiểm chết người do bánh rơ-moóc chém cua (Inswing), người đi xe máy/xe đạp bị hút vào gầm. |
| **Hông phụ Cabin** | `MIRROR_RIGHT` | Class IV / V | **1.25** | Vị trí xa mắt tài xế nhất (xe tay lái thuận), góc quan sát gương bị hẹp và dễ bị cột A/B che khuất. |
| **Gầm cản trước mũi xe** | `CAB_FRONT` | UNECE R159 (MOIS) | **1.20** | Điểm mù cản trước xe đầu kéo buồng lái phẳng (COE - Cab-Over-Engine), tầm nhìn dưới kính chắn gió $< 2.0\text{m}$. |
| **Bụng cua sườn lái** | `SWEPT_PATH_LEFT` | UNECE R151 | **1.15** | Vùng lấn cua sườn bên trái khi rẽ trái. |
| **Hông lái Cabin** | `MIRROR_LEFT` | Class II / IV | **1.00** | Cạnh cửa sổ tài xế, có thể quan sát trực tiếp bằng mắt (Direct Vision). |
| **Vùng ngoài điểm mù** | `CLEAR_ZONE` | Standard Area | **0.40** | Nằm ngoài các góc mù vật lý, tài xế dễ dàng quan sát bình thường. |

---

## 7. CHỈ SỐ RỦI RO ĐIỂM MÙ BSRI (BLIND SPOT RISK INDEX ENGINE)

Công thức tổng hợp chỉ số rủi ro BSRI cho mỗi đối tượng theo dõi $i$:

$$\text{BSRI}_i = \min\left(1.0, \Big( w_{\text{spatial}} \cdot S_{\text{spatial}} + w_{\text{temporal}} \cdot S_{\text{temporal}} \Big) \cdot C_{\text{vru}} \cdot V_{\text{blind}} \cdot M_{\text{ego}}\right)$$

### 7.1. Trọng Số Thành Phần Cơ Sở
- $w_{\text{spatial}} = 0.45$: Trọng số thành phần rủi ro không gian.
- $w_{\text{temporal}} = 0.55$: Trọng số thành phần rủi ro thời gian (ưu tiên tính cấp bách của động học va chạm).

### 7.2. Rủi Ro Không Gian ($S_{\text{spatial}}$)
Gọi $P_{\text{obs}} = (X_{\text{vcs}}, Y_{\text{vcs}})$ là điểm tiếp đất của chướng ngại vật:
- Nếu $P_{\text{obs}} \in \text{DHZ}$ (xâm nhập vùng nguy hiểm động):
  $$S_{\text{spatial}} = 1.0$$
- Nếu $P_{\text{obs}} \notin \text{DHZ}$: Tính khoảng cách Euclid ngắn nhất từ điểm tới biên đa giác $d_{\text{dhz}} = \text{dist}(P_{\text{obs}}, \text{DHZ})$. Rủi ro suy giảm theo hàm mũ:
  $$S_{\text{spatial}} = \exp\left( -\frac{d_{\text{dhz}}}{d_0} \right), \quad \text{với } d_0 = 1.80\text{ m}$$

### 7.3. Rủi Ro Thời Gian ($S_{\text{temporal}}$) & Thời Gian Tới Va Chạm (TTC)
Tính toán khoảng cách ngắn nhất từ chướng ngại vật tới **bề mặt thân xe (Vehicle Footprint)** thay vì tâm trục sau để tránh coi các phương tiện chạy song song dọc sườn là đang lao tới:
$$\mathbf{n} = P_{\text{obs}} - P_{\text{nearest\_footprint}}, \quad r = \|\mathbf{n}\|$$
Vận tốc tiếp cận hướng tâm vào thân xe (Closing velocity):
$$v_{\text{closing}} = -\frac{n_x \cdot v_{x,\text{rel}} + n_y \cdot v_{y,\text{rel}}}{r}$$
- **Trường hợp $v_{\text{closing}} > 0.15\text{ m/s}$ (Khoảng cách đang bị thu hẹp):**
  $$\text{TTC} = \frac{r}{v_{\text{closing}}} \quad (\text{giây})$$
  Đường cong đánh giá rủi ro thời gian:
  $$S_{\text{temporal}} = \begin{cases} 
  1.0 & \text{khi } \text{TTC} \le \text{TTC}_{\text{crit}} = 1.20\text{ s} \\
  1.0 - 0.70 \left( \frac{\text{TTC} - 1.20}{3.50 - 1.20} \right) & \text{khi } 1.20\text{ s} < \text{TTC} \le \text{TTC}_{\text{warn}} = 3.50\text{ s} \\
  0.30 \cdot \exp\left( -\frac{\text{TTC} - 3.50}{3.00} \right) & \text{khi } \text{TTC} > 3.50\text{ s}
  \end{cases}$$
- **Trường hợp $v_{\text{closing}} \le 0.15\text{ m/s}$ (Đối tượng giữ nguyên khoảng cách hoặc đi xa dần):**
  $$S_{\text{temporal}} = 0.20 \cdot \exp\left( -\frac{r}{4.00} \right), \quad \text{TTC} = \text{None}$$

### 7.4. Trọng Số Nhóm Đối Tượng Dễ Tổn Thương ($C_{\text{vru}}$)
Tuân thủ định nghĩa **Vulnerable Road Users (VRU)** theo ISO 26262 và UNECE R151/R159:

| Lớp Đối Tượng (YOLOv11) | $C_{\text{vru}}$ | Giải thích phân cấp rủi ro sinh mạng |
|---|:---:|---|
| `person` (Người đi bộ) | **1.00** | Hoàn toàn không có khung vỏ bảo vệ, rủi ro tử vong cực cao khi va chạm. |
| `motorcycle` (Xe máy) | **1.00** | Phương tiện cơ giới 2 bánh phổ biến nhất tại Việt Nam, rủi ro chấn thương nặng tương đương người đi bộ. |
| `bicycle` (Xe đạp) | **1.00** | Không có khung bảo vệ; đối tượng trọng tâm của chuẩn UNECE R151. |
| `xe_keo` (Xe kéo hàng) | **1.00** | Phương tiện thô sơ có người kéo đi bộ trên lòng đường tại đô thị Việt Nam. |
| `xich_lo` (Xích lô) | **1.00** | Phương tiện 3 bánh thô sơ chở người/hàng, vận tốc chậm. |
| `car` (Ô tô con) | **0.70** | Có cabin vỏ thép, dây đai an toàn và hệ thống túi khí bảo vệ người ngồi trong. |
| `bus` (Xe buýt) | **0.65** | Khối lượng lớn, kết cấu khung vỏ kiên cố. |
| `truck` (Xe tải khác) | **0.60** | Khối lượng và kích thước tương đương xe chủ. |

### 7.5. Hệ Số Thao Tác Xe Chủ ($M_{\text{ego}}$)
Hệ số khuếch đại rủi ro dựa trên thao tác đánh lái và hướng chuyển động của xe:
$$M_{\text{ego}} = \text{clip}\left( \prod k_j, 0.80, 2.00 \right)$$
- Khi xe rẽ phải ($\omega_z < -0.03\text{ rad/s}$ hoặc xi-nhan phải):
  - Đối tượng ở bên phải ($Y < -W/2$): $\times 1.30$.
  - Nếu đối tượng nằm trong vùng bụng cua (`SWEPT_PATH_RIGHT`): $\times 1.40$.
- Khi xe rẽ trái ($\omega_z > 0.03\text{ rad/s}$ hoặc xi-nhan trái):
  - Đối tượng ở bên trái ($Y > W/2$): $\times 1.25$.
- Khi xe lùi ($v < -0.20\text{ m/s}$ hoặc Gear = 'R'):
  - Đối tượng nằm phía sau cản sau ($X < x_{\text{rear}}$): $\times 1.45$.

### 7.6. Bảng Phân Cấp Ngưỡng Cảnh Báo (Risk Levels)

| Cấp Độ Rủi Ro | Dải Điểm BSRI | Mã Màu BGR | Phản Ứng Hệ Thống / Cabin HUD / Phần Cứng ESP32 |
|---|:---:|:---:|---|
| `SAFE` | $[0.00, 0.30)$ | `(0, 230, 118)` Xanh | Trạng thái bình thường. Không cảnh báo. LED xanh sáng. |
| `CAUTION` | $[0.30, 0.55)$ | `(0, 214, 255)` Vàng | Chú ý. Đèn LED vàng bật sáng trên HUD. Không hú còi. |
| `WARNING` | $[0.55, 0.80)$ | `(0, 109, 255)` Cam | Cảnh báo nguy hiểm. Bíp ngắt quãng chu kỳ 300ms, đèn cam nháy. |
| `CRITICAL` | $[0.80, 1.00]$ | `(0, 0, 213)` Đỏ | **Khẩn cấp tối cao.** HUD nhấp nháy 4Hz viền đỏ, còi rú dồn dập/liên tục, khuyến nghị phanh gấp. |

---

## 8. BỘ LỌC AN TOÀN 5 KỊCH BẢN ĐẶC BIỆT (FAST-PATH SAFETY GATEKEEPER)

Nhằm đảm bảo an toàn tuyệt đối và tuân thủ các quy chuẩn UNECE, trước khi tính BSRI thông thường, hệ thống quét qua **5 Kịch bản Đặc biệt** với quyền ưu tiên ghi đè (Safety Override):

### 8.1. Kịch bản 1: UNECE R159 MOIS (Moving-Off Information System)
- **Tình huống:** Xe dừng đèn đỏ hoặc dừng chờ khởi hành ($|v| < 0.20\text{ m/s}$), có VRU đứng sát ngay trước cản cabin ($x \in [x_{\text{front}}, x_{\text{front}} + 1.80\text{ m}]$ và $|y| \le W/2 + 0.30\text{ m}$).
- **Vấn đề toán học:** Vì cả xe và người đều đứng yên, $v_{\text{closing}} \approx 0 \implies \text{TTC} = \text{None}$, công thức vận tốc tương đối bị vô hiệu hóa.
- **Giải thuật vật lý:** Tính thời gian va chạm giả định khi xe đạp ga đề-pa với gia tốc khởi hành chuẩn của xe tải nặng $a_{\text{takeoff}} = 1.20\text{ m/s}^2$:
  $$\text{TTC}_{\text{takeoff}} = \sqrt{\frac{2 \cdot d_{\text{front}}}{a_{\text{takeoff}}}}, \quad \text{với } d_{\text{front}} = X_{\text{vcs}} - x_{\text{front}}$$
- **Đầu ra:** $\text{BSRI} = 1.00$, Phân cấp `CRITICAL`, giải thích XAI cảnh báo tài xế giữ chặt chân phanh, cấm xuất phát.

### 8.2. Kịch bản 2: UNECE R151 BSIS (Blind Spot Information System) — Bẫy Kẹp Cua Sườn Phải
- **Tình huống:** Xe đang xi-nhan phải hoặc bắt đầu đánh lái rẽ phải ($\omega_z < -0.03\text{ rad/s}$), có VRU di chuyển hoặc đứng trong vùng kẹp cua $X \in [x_{\text{rear}}, 0.70 x_{\text{front}}]$, $Y \in [-2.50\text{ m}, -W/2]$.
- **Đầu ra:** $\text{BSRI} = 0.850$, Phân cấp `CRITICAL`, cảnh báo bánh rơ-moóc sẽ chém trúng đối tượng do hiện tượng Inswing, khuyến nghị dừng chờ hoặc mở rộng góc cua.

### 8.3. Kịch bản 3: UNECE R158 Reversing — Điểm Mù Lùi Xe Bến Bãi
- **Tình huống:** Xe đang cài số lùi (Gear = 'R') hoặc có vận tốc lùi ($v < -0.10\text{ m/s}$), có chướng ngại vật đứng phía sau đuôi ($X < x_{\text{rear}}$) trong phạm vi $d_{\text{rear}} \le 2.50\text{ m}$ và $|Y| \le W/2 + 0.60\text{ m}$.
- **Giải thuật vật lý:**
  $$\text{TTC}_{\text{rev}} = \frac{d_{\text{rear}}}{|v|}$$
- **Đầu ra:** $\text{BSRI} = 0.950$, Phân cấp `CRITICAL`, kích hoạt còi báo động khẩn cấp và yêu cầu đạp phanh dừng xe lập tức.

### 8.4. Kịch bản 4: Chạy Áp Sát Song Song Cự Ly Cực Hẹp Ở Tốc Độ Cao
- **Tình huống:** Xe chạy tốc độ cao ($v \ge 8.00\text{ m/s} \approx 28.8\text{ km/h}$), có VRU (xe máy) chạy song song cùng chiều với khoảng cách ngang cực hẹp $d_{\text{lat}} = |Y| - W/2 \in [0.0, 0.80\text{ m}]$.
- **Vấn đề toán học:** Vận tốc tương đối dọc $v_{x,\text{rel}} \approx 0 \implies v_{\text{closing}} \approx 0$, nhưng nguy cơ va chạm do lực hút khí động học (Venturi effect) và biên độ lạng lái vô cùng lớn.
- **Giải thuật vật lý:** Tính suy giảm hàm mũ theo cự ly ngang:
  $$S_{\text{lateral}} = \exp\left( -\frac{d_{\text{lat}}}{0.40} \right)$$
  $$\text{BSRI} = \min\left(1.0, 0.65 + 0.35 \cdot S_{\text{lateral}}\right) \in [0.65, 1.00]$$
- **Đầu ra:** Phân cấp `WARNING` hoặc `CRITICAL`, khuyến nghị giữ thẳng lái, không đánh lái gấp sang phải.

### 8.5. Kịch bản 5: Che Khuất Tầm Nhìn Gương Khi Vào Cua Gắt (Scissors Occlusion)
- **Tình huống:** Xe ôm cua gắt ($|\omega_z| > 0.08\text{ rad/s}$), góc nghiêng cabin hoặc rơ-moóc bẻ gập che khuất hoàn toàn tầm nhìn trong gương chiếu hậu. Có đối tượng nằm trong khe mù $Y \in [-2.50\text{ m}, -W/2]$.
- **Đầu ra:** $\text{BSRI} = 0.820$, Phân cấp `CRITICAL`.

---

## 9. BẢNG TRA CỨU TOÀN BỘ THAM SỐ, BIẾN SỐ & CƠ SỞ KHOA HỌC

Bảng tổng hợp dành cho các mô hình AI hoặc chuyên gia đánh giá độc lập (Peer Reviewers) tiến hành kiểm chứng:

| Ký hiệu | Tên Biến Số / Hằng Số | Giá Trị Số Học | Đơn Vị | Vị trí file trong Code | Cơ sở khoa học & Tiêu chuẩn dẫn chiếu |
|---|---|:---:|:---:|---|---|
| $L_f$ | Chiều dài cơ sở đầu kéo (Wheelbase) | `3.60` | m | `bsri_calculator.py:67` | Tiêu chuẩn xe đầu kéo 2 cầu phổ biến (6x4 tractor). |
| $L_{\text{art\_foh}}$ | Độ nhô cản trước đầu kéo (Front Overhang) | `1.35` | m | `bsri_calculator.py:68` | Mép cản trước cabin đầu bằng COE (Hyundai, Hino, Howo). Mũi cản trước $x_{\text{front}} = 4.95\text{m}$. |
| $W_c$ | Chiều rộng cabin | `2.50` | m | `bsri_calculator.py:69` | Giới hạn chiều rộng khổ xe cơ giới đường bộ (QCVN 09:2015/BGTVT). |
| $L_{\text{trail}}$ | Chiều dài sơ-mi rơ-moóc | `12.00` | m | `bsri_calculator.py:70` | Chiều dài chuẩn sơ-mi rơ-moóc 40ft chở container. |
| $d_{\text{hitch}}$ | Chốt mâm xoay Kingpin trước trục sau | `0.30` | m | `bsri_calculator.py:72` | Bố trí trọng tải chuẩn phân bố lên mâm kéo đầu kéo. |
| $L_{\text{wb}}$ | Chiều dài cơ sở xe liền thân | `5.80` | m | `bsri_calculator.py:73` | Chiều dài cơ sở xe tải nặng 3 chân (6x2 / 6x4 rigid truck). |
| $L_{\text{rig\_foh}}$ | Độ nhô cản trước xe liền thân | `1.35` | m | `bsri_calculator.py:74` | Mép cản trước xe tải 3 chân phổ biến tại VN. |
| $L_{\text{front}}$ | Trục sau tới cản trước (Rigid) | `7.15` | m | `bsri_calculator.py:117` | Tổng chiều dài đầu xe = $L_{\text{wb}} (5.8\text{m}) + L_{\text{rig\_foh}} (1.35\text{m})$. |
| $L_{\text{rear}}$ | Độ nhô cản sau (Rigid) | `2.40` | m | `bsri_calculator.py:75` | Độ nhô cản sau thực tế quyết định góc văng Tail-Swing (ECE R58). |
| $d_{\text{base}}$ | Khoảng đệm an toàn cơ sở | `1.50` | m | `bsri_calculator.py:78` | Khoảng cách an toàn tối thiểu khi vượt xe đạp/người đi bộ (ISO 8855). |
| $w_{\text{spatial}}$ | Trọng số rủi ro không gian | `0.45` | - | `bsri_calculator.py:79` | Mô hình kết hợp lồi đa tiêu chí (Convex Multi-criteria Combination). |
| $w_{\text{temporal}}$ | Trọng số rủi ro thời gian | `0.55` | - | `bsri_calculator.py:80` | Ưu tiên tính cấp bách của thời gian va chạm. |
| $d_0$ | Khoảng cách suy giảm DHZ | `1.80` | m | `bsri_calculator.py:561` | Hằng số suy giảm hàm mũ khoảng cách tiếp cận biên an toàn. |
| $\text{TTC}_{\text{crit}}$ | Ngưỡng TTC khẩn cấp | `1.20` | s | `bsri_calculator.py:355` | Tổng thời gian phản xạ tài xế ($0.8\text{s}$) + trễ phanh khí nén ($0.4\text{s}$). |
| $\text{TTC}_{\text{warn}}$ | Ngưỡng TTC cảnh báo sớm | `3.50` | s | `bsri_calculator.py:357` | Tiêu chuẩn UNECE R151 mục 5.3.1 (Phát hiện và cảnh báo trước 3.5s). |
| $a_{\text{takeoff}}$ | Gia tốc đề-pa khởi hành xe tải | `1.20` | $\text{m/s}^2$ | `bsri_calculator.py:467` | Gia tốc xuất phát trung bình của xe tải nặng chở hàng (Green 2000). |
| $T_{\text{horizon}}$ | Chân trời dự báo đa giác DHZ | `0.50` | s | `bsri_calculator.py:185` | Thời gian phản xạ thao tác đánh lái ngắn hạn. |
| $\text{Thresh}_{\text{crit}}$ | Ngưỡng BSRI khẩn cấp | `0.80` | - | `bsri_calculator.py:61` | Ngưỡng kích hoạt còi hú và phanh dừng xe. |
| $\text{Thresh}_{\text{warn}}$ | Ngưỡng BSRI cảnh báo | `0.55` | - | `bsri_calculator.py:62` | Ngưỡng rung vô-lăng / chuông bíp cảnh báo sớm. |
| $\text{Thresh}_{\text{caut}}$ | Ngưỡng BSRI chú ý | `0.30` | - | `bsri_calculator.py:63` | Ngưỡng hiển thị đèn vàng thông báo trên màn hình Cabin HUD. |

---

## 10. TÀI LIỆU NGHIÊN CỨU & TIÊU CHUẨN QUỐC TẾ DẪN CHIẾU (VERIFICATION REFERENCES)

Nhằm phục vụ quá trình xác thực độc lập, các công thức và tham số trên được xây dựng trực tiếp dựa trên các tài liệu khoa học và tiêu chuẩn kỹ thuật sau:

1. **ISO 8855:2011**: *Road vehicles — Vehicle dynamics and road-holding ability — Vocabulary.* Tổ chức tiêu chuẩn hóa quốc tế (Quy định hệ trục tọa độ VCS và các chuyển động góc Yaw, Pitch, Roll).
2. **SAE J670e**: *Vehicle Dynamics Terminology.* Hiệp hội Kỹ sư Ô tô Hoa Kỳ.
3. **UNECE Regulation No. 151 (R151)**: *Uniform provisions concerning the approval of motor vehicles with regard to the Blind Spot Information System for the Detection of Bicycles (BSIS).* E/ECE/TRANS/505/Rev.3/Add.150 (Quy định phạm vi giám sát, độ lấn cua và thời gian cảnh báo va chạm xe đạp).
4. **UNECE Regulation No. 158 (R158)**: *Uniform provisions concerning the approval of devices for reversing motion and motor vehicles with regard to the driver's awareness of vulnerable road users behind vehicles when reversing.* (Quy định vùng điểm mù sau đuôi xe khi lùi).
5. **UNECE Regulation No. 159 (R159)**: *Uniform provisions concerning the approval of motor vehicles with regard to the Moving Off Information System for the Detection of Pedestrians and Cyclists (MOIS).* (Quy định vùng điểm mù cản trước khi xuất phát).
6. **Directive 2003/97/EC & 2007/38/EC of the European Parliament**: *Relating to the type-approval of devices for indirect vision and of vehicles equipped with these devices.* (Định nghĩa góc mù quang học các lớp gương Class II, IV, V, VI).
7. **Ellis, J. R. (1969)**: *Vehicle Dynamics.* London Books. (Nền tảng toán học cho phương trình động học góc gập $\gamma$ của xe đầu kéo sơ-mi rơ-moóc).
8. **Wong, J. Y. (2001)**: *Theory of Ground Vehicles (3rd ed.).* John Wiley & Sons. (Công thức lý thuyết về bán kính quay vòng, độ trượt góc bên và đặc tính động lực học xe nhiều trục).
9. **SAE Technical Paper 933056**: *Off-Tracking and Clearance Requirements for Articulated Commercial Vehicles.* (Cơ sở toán học cho công thức tính Inswing $\frac{L_{\text{wb}}^2}{2R}$).
10. **Green, M. (2000)**: *“How long does it take to stop?” Methodological analysis of driver perception-response time.* Transportation Human Factors, 2(3), 195-216. (Cơ sở xác lập ngưỡng phản xạ người lái $0.75 - 1.2\text{s}$).
11. **Fambro, D. B. et al. (1997)**: *Determination of Stopping Sight Distances.* NCHRP Report 400, Transportation Research Board. (Phân tích độ trễ phản hồi của hệ thống phanh khí nén xe tải $0.3 - 0.5\text{s}$, dẫn tới ngưỡng $\text{TTC}_{\text{crit}} = 1.20\text{s}$).
12. **QCVN 09:2015/BGTVT**: *Quy chuẩn kỹ thuật quốc gia về chất lượng an toàn kỹ thuật và bảo vệ môi trường đối với xe ô tô.* Bộ Giao thông Vận tải Việt Nam.

