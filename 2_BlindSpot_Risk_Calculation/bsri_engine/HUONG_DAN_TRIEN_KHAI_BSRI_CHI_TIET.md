# 🛡️ HƯỚNG DẪN TRIỂN KHAI CHI TIẾT ĐỘNG CƠ TÍNH TOÁN RỦI RO ĐIỂM MÙ (BSRI ENGINE)

> **Dự án**: BlindGuard AI — Hệ thống Giám sát & Cảnh báo Sớm Điểm Mù Cho Phương Tiện Cỡ Lớn  
> **Cuộc thi**: Thiết kế Điện tử Việt Nam 2026 (VEDC 2026) — Đội Nova (Trường ĐH Bách Khoa - ĐH Đà Nẵng)  
> **Phân hệ**: `2_BlindSpot_Risk_Calculation / bsri_engine`  
> **Nền tảng tham chiếu & Bối cảnh an toàn**: **ISO 8855:2011 / SAE J670_202206 (Hệ tọa độ & Thuật ngữ động học phương tiện)**, **UNECE R151 (Hệ thống thông tin điểm mù BSIS cho xe đạp — mở rộng sang mọi VRU)**, **UNECE R159 (Hệ thống thông tin khởi hành MOIS cho người đi bộ/xe đạp — mở rộng sang xe máy)**, **UNECE R158 (Khả năng quan sát & Cảnh báo lùi xe)**, **UNECE R46 (Phân vùng gương quan sát gián tiếp Class I–VI)**, **ISO 15623:2013 / ISO 22839:2013 (Khung khái niệm cảnh báo va chạm sớm)**.  
> **Nguyên tắc phân định nguồn tham số (Parameter Provenance)**: Các tiêu chuẩn quốc tế đóng vai trò định hình bối cảnh an toàn và yêu cầu chức năng. Các trọng số, ngưỡng kích hoạt số học và công thức cụ thể trong BSRI là **các tham số kỹ thuật khởi tạo của dự án (Engineering & Calibration Parameters)**, được thiết kế theo điều kiện giao thông hỗn hợp tại Việt Nam và phải được hiệu chỉnh qua dữ liệu thử nghiệm thực tế.

---

## 📌 MỤC LỤC
1. [Bản Chất & Triết Lý Hoạt Động Của BSRI](#1-bản-chất--triết-lý-hoạt-động-của-bsri)
2. [Đầu Vào & Đầu Ra Của Động Cơ BSRI](#2-đầu-vào--đầu-ra-của-động-cơ-bsri)
3. [Công Thức Toán Học & 5 Thành Phần Cốt Lõi Của BSRI](#3-công-thức-toán-học--5-thành-phần-cốt-lõi-của-bsri)
   - [3.1. Thành phần 1: Rủi ro không gian (S_spatial) & Đa giác nguy hiểm DHZ](#31-thành-phần-1-rủi-ro-không-gian-s_spatial--đa-giác-nguy-hiểm-dhz)
   - [3.2. Thành phần 2: Rủi ro thời gian (S_temporal) & Thời gian tới va chạm TTC](#32-thành-phần-2-rủi-ro-thời-gian-s_temporal--thời-gian-tới-va-chạm-ttc)
   - [3.3. Thành phần 3: Hệ số ưu tiên nhóm đối tượng (C_vru)](#33-thành-phần-3-hệ-số-ưu-tiên-nhóm-đối-tượng-c_vru)
   - [3.4. Thành phần 4: Hệ số vùng mù quang học (V_blind) & Ranh giới hình học](#34-thành-phần-4-hệ-số-vùng-mù-quang-học-v_blind)
   - [3.5. Thành phần 5: Hệ số điều chỉnh thao tác xe chủ (M_ego) từ IMU + GPS](#35-thành-phần-5-hệ-số-khuếch-đại-thao-tác-xe-chủ-m_ego-từ-imu--gps)
4. [Lớp Can Thiệp An Toàn Cho Các Kịch Bản Giao Thông Đặc Biệt](#4-xử-lý-các-kịch-bản-giao-thông-đặc-biệt--nghịch-lý-dừng-xe)
   - [4.1. Bản chất "Nghịch lý Dừng xe / Vận tốc bằng 0" (The Standstill Paradox)](#41-bản-chất-nghịch-lý-dừng-xe--vận-tốc-bằng-0-the-standstill-paradox)
   - [4.2. Danh mục 5 Kịch bản đặc biệt & Nền tảng an toàn mở rộng](#42-danh-mục-5-kịch-bản-đặc-biệt--cơ-sở-khoa-học-chuẩn-unece)
   - [4.3. Kiến trúc "Lớp Lọc Ưu Tiên" (Priority Safety Interceptor): Tại sao phải làm 5 case riêng?](#43-kiến-trúc-lớp-lọc-ưu-tiên-priority-safety-interceptor-tại-sao-phải-làm-5-case-riêng)
   - [4.4. Cơ chế nhận diện của hệ thống: Ma trận cảm biến cứng & Cây quyết định](#44-cơ-chế-nhận-diện-của-hệ-thống-làm-sao-hệ-thống-biết-xe-đang-ở-case-nào)
   - [4.5. Chi tiết thuật toán & Công thức tính điểm cho từng kịch bản](#45-chi-tiết-thuật-toán--công-thức-tính-điểm-cho-từng-kịch-bản)
   - [4.6. Hướng dẫn viết code chi tiết: Tích hợp vào BSRICalculator như thế nào?](#46-hướng-dẫn-viết-code-chi-tiết-tích-hợp-vào-bsricalculator-như-thế-nào)
5. [Phân Cấp Cảnh Báo ADAS & Bộ Giải Thích Trực Quan (Explainable AI - XAI)](#5-phân-cấp-cảnh-báo-adas--bộ-giải-thích-trực-quan-explainable-ai---xai)
6. [Bài Toán Mẫu Tính Tay Từng Bước Nhất Quán (Worked Example)](#6-bài-toán-mẫu-tính-tay-từng-bước-bằng-số-liệu-cụ-thể-worked-example)
7. [Hướng Dẫn Triển Khai Trong Mã Nguồn & Cấu Hình Thực Tế](#7-hướng-dẫn-triển-khai-trong-mã-nguồn--cấu-hình-thực-tế)
8. [Bảng Nguồn Gốc Tham Số (Parameter Provenance Matrix)](#8-bảng-nguồn-gốc-tham-số-parameter-provenance-matrix)
9. [Bảng Tài Liệu Tham Khảo (Reference Standards & Literature)](#9-bảng-tài-liệu-tham-khảo-reference-standards--literature)

---

## 1. Bản Chất & Triết Lý Hoạt Động Của BSRI

### 1.1. BSRI là gì?
**BSRI (Blind-Spot Risk Index — Chỉ số Rủi ro Điểm mù)** là một động cơ toán học định lượng rủi ro va chạm theo thời gian thực giữa xe tải cỡ lớn và các phương tiện xung quanh.

Khác với các hệ thống cảnh báo điểm mù truyền thống (chỉ đơn giản kiểm tra xem có vật thể xuất hiện hay không $\rightarrow$ gây ra báo động giả liên tục), BSRI hoạt động theo triết lý **Đánh giá Rủi ro theo Ngữ cảnh Động học (Context-Aware Risk Assessment)**:
* **Không chỉ phát hiện sự tồn tại**: Xe máy cách $4\text{m}$ chạy song song thẳng hàng sẽ có rủi ro rất thấp ($\text{BSRI} < 0.20$ — Không báo động rác).
* **Nhưng nếu xe tải bắt đầu bẻ lái ôm cua**: Điểm rủi ro sẽ lập tức tăng vọt lên mức Nguy hiểm khẩn cấp ($\text{BSRI} \ge 0.80$ — Kích hoạt còi hú và cảnh báo phanh) vì quỹ đạo lấn lề của thân xe sẽ chém trúng xe máy trong vòng $1 - 2$ giây tới!

```text
               KỊCH BẢN 1: XE CHẠY THẲNG                    KỊCH BẢN 2: XE BẺ LÁI RẼ PHẢI
        ┌────────────────────────────────────┐       ┌────────────────────────────────────┐
        │ Xe tải chạy thẳng, v = 40 km/h     │       │ Xe tải bẻ lái rẽ phải, omega < 0   │
        └────────────────────────────────────┘       └────────────────────────────────────┘
                  Xe máy chạy song song                            Xe máy đi sát sườn
                          (O)                                              (O)
                   [KHÔNG NGUY CƠ]                                  [NGUY HIỂM CẬN KỀ]
           BSRI = 0.15 -> AN TOÀN (SAFE)                    BSRI = 0.95 -> KHẨN CẤP (CRITICAL)
             (Không phát âm thanh rác)                       (Hú còi + Cảnh báo phanh gấp ngay)
```

---

## 2. Đầu Vào & Đầu Ra Của Động Cơ BSRI

Động cơ BSRI đóng vai trò là khối xử lý trung tâm, tiếp nhận thông tin từ Phân hệ Thị giác AI (Module 1) và Cụm cảm biến động học xe chủ (IMU + GPS):

```text
┌──────────────────────────────────────────────┐
│  ĐẦU VÀO 1: THỊ GIÁC AI (TRACKED OBSTACLE)   │
│  • Tọa độ mét VCS: X_vcs, Y_vcs              │
│  • Vector vận tốc vật thể: vel_x, vel_y (m/s)│
│  • Tên nhãn nhận diện: class_name            │
│  • Độ tin cậy AI: confidence                 │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║      BSRI RISK ENGINE       ║ ──────► [ĐẦU RA BSRI]
         ║  (Động cơ Tính toán Rủi ro) ║         • Điểm số BSRI: 0.00 -> 1.00
         ╚═════════════════════════════╝         • Cấp độ: SAFE / CAUTION / WARNING / CRITICAL
                       ▲                         • Chỉ số va chạm: TTC (giây)
                       │                         • Chuỗi giải trình XAI tiếng Việt
┌──────────────────────┴───────────────────────┐
│   ĐẦU VÀO 2: CẢM BIẾN XE CHỦ (EGO STATE)     │
│  • Vận tốc xe chủ từ GPS: speed_mps (m/s)    │
│  • Tốc độ góc quay từ IMU: yaw_rate_rad_s (r)│
│  • Gia tốc dọc/ngang từ IMU: accel_x, accel_y│
│  • Cấu hình loại xe: RIGID hoặc ARTICULATED  │
└──────────────────────────────────────────────┘
```

---

## 3. Công Thức Toán Học & 5 Thành Phần Cốt Lõi Của BSRI

Chỉ số BSRI tổng thể được định nghĩa bằng hàm toán học chuẩn hóa trong đoạn $[0.00, \, 1.00]$:

$$\mathbf{BSRI} = \min \left( 1.0, \, \left[ w_s \cdot S_{\text{spatial}} + w_t \cdot S_{\text{temporal}} \right] \times C_{\text{vru}} \times V_{\text{blind}} \times M_{\text{ego}} \right)$$

* **Khối Rủi ro Cơ sở $[w_s \cdot S_{\text{spatial}} + w_t \cdot S_{\text{temporal}}]$**: Là tổ hợp lồi chuẩn hóa (Convex Combination) giữa rủi ro khoảng cách không gian và rủi ro thời gian động học, với $w_s + w_t = 1.0$.
* **Các Hệ số Điều chỉnh Ngữ cảnh (Contextual Risk Modifiers)**: $C_{\text{vru}}, V_{\text{blind}}, M_{\text{ego}}$ đóng vai trò khuếch đại hoặc giảm trừ rủi ro dựa trên nhóm đối tượng, góc mù thị giác và hành vi lái của xe tải.
* **Trọng số khởi tạo cơ sở**: $w_s = 0.45$ (Spatial Weight), $w_t = 0.55$ (Temporal Weight).

> [!NOTE]
> **CĂN CỨ THIẾT KẾ TRỌNG SỐ KHỞI TẠO $w_s = 0.45$ VÀ $w_t = 0.55$**:  
> 1. **Mục tiêu chống báo động giả (False Alarm Suppression)**: Trong các hệ thống hỗ trợ lái xe chủ động (ADAS), yếu tố động học thời gian ($TTC$) có tính quyết định sống còn cao hơn khoảng cách hình học tĩnh. Một xe máy đi sát sườn ($d_{\text{border}} = 0 \implies S_{\text{spatial}} = 1.0$) nhưng đang di chuyển tạt ra xa ($v_{\text{closing}} < 0 \implies TTC \rightarrow \infty$) thì không có nguy cơ va chạm. Việc gán trọng số thời gian cao hơn ($w_t = 0.55 > w_s = 0.45$) giúp triệt tiêu các báo động giả không đáng có.
> 2. **Phân loại tham số**: $w_s = 0.45$ và $w_t = 0.55$ là **giá trị khởi tạo kỹ thuật (Initial Engineering Parameters)** của nhóm nghiên cứu. Các giá trị tối ưu cuối cùng sẽ được tinh chỉnh (calibrated) bằng phương pháp quét lưới (Grid Search) trên tập dữ liệu kiểm thử thực địa với miền tìm kiếm $w_t \in [0.40, 0.65]$.

---

### 3.1. Thành phần 1: Rủi ro không gian ($S_{\text{spatial}}$) & Đa giác nguy hiểm DHZ

Thành phần không gian định lượng mức độ đe dọa dựa trên khoảng cách giữa chướng ngại vật và **Vùng Nguy Hiểm Động (Dynamic Hazard Zone - DHZ)** của thân xe:

$$S_{\text{spatial}} = \begin{cases} 1.0 & \text{khi vật thể nằm TRỌN TRONG đa giác DHZ} \\ \exp\left( - \frac{d_{\text{border}}}{1.8} \right) & \text{khi vật thể nằm NGOÀI đa giác DHZ, cách viền } d_{\text{border}} \text{ mét} \end{cases}$$

* **$d_{\text{border}}$ (mét)**: Khoảng cách ngắn nhất từ vị trí chân vật thể $(X, Y)$ tới đường biên viền của đa giác DHZ.
* **$1.8\text{m}$**: Hằng số suy giảm khoảng cách không gian ($d_0$).

> [!NOTE]
> **CĂN CỨ THIẾT KẾ HẰNG SỐ SUY GIẢM $d_0 = 1.8\text{ mét}$**:  
> 1. **Khổ làn đường và hành lang an toàn sườn xe**: Dựa trên cẩm nang thiết kế đường bộ (tham khảo TCVN 4054:2005 và AASHTO Green Book), bề rộng tiêu chuẩn của một làn xe cơ giới là $3.50\text{m}$. Xe tải nặng có bề rộng phủ bì thân xe là $2.50\text{m}$, để lại khoảng hở sườn xe khoảng $0.50\text{m}$. Cộng với khổ rộng lưu thông tối thiểu của xe máy ($1.0\text{m} - 1.2\text{m}$), cự ly $1.7 - 1.8\text{m}$ đại diện cho **bề rộng của một hành lang thoát hiểm bên sườn xe tải**.
> 2. **Phân loại tham số**: $d_0 = 1.8\text{m}$ là **giá trị khởi tạo kỹ thuật (Engineering Initialization)**, phản ánh sự suy giảm hàm mũ tự nhiên ($e^0 = 1.0$ khi chạm viền; $e^{-1} \approx 0.37$ khi cách 1 hành lang; $e^{-2} \approx 0.14$ khi cách 2 hành lang). Tham số này sẽ được hiệu chỉnh chính xác theo dữ liệu thử nghiệm trên sa hình thực tế.

```text
                              Sườn xe bên phụ
                              │
  [Đa giác nguy hiểm DHZ]     │ ◄─── d_border = 0.0m  ──► S_spatial = 1.00 (Nguy hiểm cực đại)
──────────────────────────────┼───────────────────────────
   Hành lang an toàn 1 làn    │ ◄─── d_border = 1.8m  ──► S_spatial = 0.37 (Mức Chú ý)
   Cách xa 2 làn đường        │ ◄─── d_border = 3.6m  ──► S_spatial = 0.14 (Mức An toàn)
```

#### Cách xây dựng Đa giác DHZ cho từng loại xe:

##### A. Đối với Xe tải liền thân (`vehicle_type = "RIGID"` — như Chenglong H7, Hino, Isuzu):
Thân xe là **một khối chữ nhật phẳng duy nhất** có kích thước $L \times W$ kéo dài từ $X_{\text{rear}}$ đến $X_{\text{front}}$.  
Khi xe ôm cua rẽ, hệ thống mô hình hóa đồng thời **hai hiện tượng động học nguy hiểm**:

1. **Độ lấn cua sườn xe vào lòng cua (Inswing / Off-tracking)**: Sườn xe phía trong góc cua chém vào lòng đường theo mô hình động học:
   $$\Delta_{\text{off-tracking}} = \frac{L_{wb}^2 \cdot |\omega_z|}{2 \cdot \max(1.0, |v_{\text{ego}}|)}$$
   * $L_{wb}$ (mét): Chiều dài cơ sở từ trục lái trước đến tâm trục sau (ví dụ $5.8\text{m}$).
   * $|\omega_z|$ (rad/s): Tốc độ góc quay thân xe lấy trực tiếp từ con quay hồi chuyển IMU.
   * $v_{\text{ego}}$ (m/s): Vận tốc xe chủ lấy từ GPS.

2. **Hiện tượng văng đuôi cản sau (Tail-Swing)**: Phần cản sau nhô ra sau tâm trục sau ($L_{\text{ro}} = \text{rigid\_rear\_length}$) xoay quanh trục cầu sau và **văng ngược chiều đánh lái sang làn đường đối diện**:
   $$\Delta_{\text{tail}} = L_{\text{ro}} \cdot |\omega_z| \cdot T_{\text{preview}}$$
   * Khi xe rẽ **PHẢI** ($\omega_z < -0.03\text{ rad/s}$): Sườn phải chém cua vào trong ($Y_{\text{front, right}} = -W/2 - \Delta_{\text{off-tracking}}$), đồng thời góc đuôi xe bên **TRÁI** văng ngược ra ngoài làn đối diện ($Y_{\text{rear, left}} = +W/2 + \Delta_{\text{tail}}$).
   * Khi xe rẽ **TRÁI** ($\omega_z > 0.03\text{ rad/s}$): Sườn trái chém cua vào trong ($Y_{\text{front, left}} = +W/2 + \Delta_{\text{off-tracking}}$), đồng thời góc đuôi xe bên **PHẢI** văng ngược ra ngoài ($Y_{\text{rear, right}} = -W/2 - \Delta_{\text{tail}}$).

* **Mở rộng DHZ**: Đa giác DHZ được dựng từ đa giác quét tổng hợp (bao gồm cả đầu xe kéo dài $L_{\text{lead}} = v_{\text{ego}} \cdot T_{\text{preview}}$, bụng xe lấn cua $\Delta_{\text{off-tracking}}$ và cản sau văng đuôi $\Delta_{\text{tail}}$), sau đó nở đệm Minkowski cộng thêm khoảng an toàn $\text{buffer} = 1.0\text{m} + C_{\text{dyn}}$.  
* **Phân loại tham số**: $T_{\text{preview}} = 0.5\text{s}$, $\text{buffer} = 1.0\text{m}$ và giới hạn chiều dài $S_{\text{max}} = 12\text{m}$ là **các tham số khoanh vùng ứng viên nguy cơ ban đầu (Candidate Zone Engineering Parameters)** nhằm tối ưu hóa diện tích đa giác, không phải khoảng cách dừng xe và cần được hiệu chỉnh qua thực nghiệm test track.

##### B. Đối với Xe đầu kéo sơ-mi rơ-moóc (`vehicle_type = "ARTICULATED"`):
Thân xe gồm **2 khối gập khúc**: Cabin đầu kéo và Thùng rơ-moóc xoay quanh chốt mâm kéo (Kingpin) với góc gập $\gamma$. Đa giác DHZ được dựng bằng phép hợp (Union) các hình chiếu thân xe trong khoảng thời gian dự đoán $T_{\text{preview}} = 0.5\text{s}$ tới theo mô hình động học vi phân.

---

### 3.2. Thành phần 2: Rủi ro thời gian ($S_{\text{temporal}}$) & Thời gian tới va chạm TTC

Thành phần thời gian đánh giá tốc độ thu hẹp khoảng cách giữa vật thể và thân xe: Hai vật có đang lao vào nhau không và còn mấy giây nữa sẽ va chạm?

#### Bước 1: Tính Vận tốc tiếp cận hướng tâm (Closing Velocity)
$$v_{\text{closing}} = - \frac{X_{\text{vcs}} \cdot v_x + Y_{\text{vcs}} \cdot v_y}{r}$$

* $X_{\text{vcs}}, Y_{\text{vcs}}$: Tọa độ mét của vật thể trong hệ trục VCS xe chủ.
* $v_x, v_y$: Vector vận tốc di chuyển của vật thể $(vel_x, vel_y)$ đo trong hệ trục VCS (m/s).
* $r = \sqrt{X_{\text{vcs}}^2 + Y_{\text{vcs}}^2}$: Khoảng cách đường thẳng Euclid giữa tâm trục sau và vật thể (mét).
* **Ý nghĩa vật lý**:
  * Nếu $v_{\text{closing}} > 0$: Hai vật đang lao lại gần nhau (khoảng cách đang co ngắn lại).
  * Nếu $v_{\text{closing}} \le 0$: Hai vật đang di chuyển xa nhau ra hoặc chạy song song giữ nguyên khoảng cách.

> [!IMPORTANT]
> **LÝ GIẢI BẢN CHẤT VẬN TỐC TƯƠNG ĐỐI & TẠI SAO TUYỆT ĐỐI KHÔNG CỘNG THÊM $v_{\text{ego}}$**:  
> 1. **Vận tốc từ Camera AI đã là vận tốc tương đối**: Phân hệ Thị giác AI (Module 1 — ByteTrack kết hợp phép chiếu Homography mặt đất) đo đạc vị trí của chướng ngại vật $X_{\text{vcs}}(t), Y_{\text{vcs}}(t)$ **trực tiếp trong Hệ tọa độ Xe chủ (VCS)**. Vận tốc $(vel_x, vel_y)$ được tính bằng sai phân tọa độ giữa các khung hình liên tiếp:
>    $$vel_x = \frac{\Delta X_{\text{vcs}}}{\Delta t}, \quad vel_y = \frac{\Delta Y_{\text{vcs}}}{\Delta t}$$
>    Vì gốc tọa độ VCS di chuyển gắn liền cùng với thân xe tải, nên độ dịch chuyển $\Delta X_{\text{vcs}}, \Delta Y_{\text{vcs}}$ theo thời gian **bản chất ĐÃ CHÍNH LÀ vector vận tốc tương đối** ($\vec{v}_{\text{rel}} = \vec{v}_{\text{obs}} - \vec{v}_{\text{ego}}$) giữa chướng ngại vật và xe chủ!
> 2. **Lỗi cộng trùng vận tốc (Double-Counting Error)**: Nếu tiếp tục cộng thêm $v_{\text{ego}}$ vào công thức $v_{\text{closing}}$ như một số tài liệu cũ ghi chép, hệ thống sẽ bị lỗi cộng trùng vận tốc xe chủ đến hai lần. Khi xe tải chạy trên quốc lộ $60\text{ km/h}$ ($16.7\text{ m/s}$), việc cộng thêm $16.7\text{ m/s}$ sẽ làm $v_{\text{closing}}$ tăng vọt một cách phi lý, gây ra báo động đỏ giả (False Critical Alarm) liên tục dù xe phía sau đang chạy giữ khoảng cách hoàn toàn an toàn.
> 3. **Kết luận**: Đại lượng vận tốc tương đối **CHỈ CÓ DUY NHẤT 1 ĐẠI LƯỢNG** là $(vel_x, vel_y)$ đo trong VCS, và công thức tính $v_{\text{closing}}$ thuần túy là phép chiếu hướng tâm của vector vận tốc này: $v_{\text{closing}} = - \frac{X \cdot vel_x + Y \cdot vel_y}{r}$.

#### Bước 2: Tính Thời gian tới va chạm (TTC)
Khi $v_{\text{closing}} > 0.15\text{ m/s}$:
$$TTC = \frac{r}{v_{\text{closing}}} \quad (\text{đơn vị: giây})$$

#### Bước 3: Hàm chuẩn hóa rủi ro thời gian (Temporal Risk Function)
$$S_{\text{temporal}} = \begin{cases} 
1.0 & \text{khi } TTC \le TTC_{\text{critical}} \quad (1.2\text{s}) \\ 
1.0 - 0.70 \left( \frac{TTC - TTC_{\text{critical}}}{TTC_{\text{warning}} - TTC_{\text{critical}}} \right) & \text{khi } TTC_{\text{critical}} < TTC \le TTC_{\text{warning}} \quad (1.2\text{s} < TTC \le 3.5\text{s}) \\ 
0.30 \exp\left( - \frac{TTC - TTC_{\text{warning}}}{\tau_{\text{decay}}} \right) & \text{khi } TTC > TTC_{\text{warning}} \quad (\tau_{\text{decay}} = 3.0\text{s})
\end{cases}$$

> [!NOTE]
> **CĂN CỨ THIẾT KẾ CÁC NGƯỠNG HIỆU CHỈNH $TTC_{\text{critical}} = 1.2\text{s}$ VÀ $TTC_{\text{warning}} = 3.5\text{s}$**:  
> 1. **Ngưỡng cực hạn $TTC \le 1.2\text{ giây} \implies S_{\text{temporal}} = 1.00$**:
>    * **Thời gian nhận thức & phản ứng sinh học của con người (Perception-Response Time - PRT)**: Theo các nghiên cứu công thái học thực nghiệm (Green 2000), thời gian để người lái phát hiện tín hiệu cảnh báo bất ngờ từ điểm mù, não bộ xử lý và di chuyển chân sang bàn đạp phanh mất trung bình $0.70\text{s} - 0.85\text{s}$.
>    * **Độ trễ cơ cấu phanh khí nén (Pneumatic Brake Lag)**: Hệ thống phanh khí nén trên xe tải nặng và rơ-moóc có độ trễ cơ học từ $0.35\text{s} - 0.50\text{s}$ (thời gian để khí nén xả qua van tổng, nạp đầy các bầu búp-sen và đẩy guốc phanh ép chặt vào tang trống/đĩa phanh).
>    * $\implies$ **Tổng thời gian tối thiểu để bắt đầu phát sinh lực hãm xe**:
>      $$t_{\text{stop-init}} = t_{\text{PRT}} + t_{\text{air-lag}} \approx 0.8\text{s} + 0.4\text{s} = \mathbf{1.2\text{ giây}}!$$
>      Nếu $TTC \le 1.2\text{s}$, bất kỳ sự chậm trễ nào đều có nguy cơ va chạm vật lý trực tiếp. Do đó $S_{\text{temporal}}$ đạt mức tối đa $1.00$ để kích hoạt cảnh báo khẩn cấp.
> 2. **Ngưỡng cảnh báo $TTC_{\text{warning}} = 3.5\text{ giây}$ và mức sàn $0.30$**:
>    * $3.5\text{ giây}$ là khoảng thời gian cho phép tài xế xe tải quan sát gương chiếu hậu, đánh giá tình hình và chủ động nhả chân ga rà nhẹ phanh hoặc giữ thẳng vô-lăng mà không làm mất thăng bằng hàng hóa.
>    * Tại $TTC = 3.5\text{s}$, rủi ro thời gian hạ xuống mức sàn $0.30$ (ranh giới giữa mức Chú ý và An toàn). Tỷ số suy giảm tuyến tính $(1.0 - 0.30) / (3.5 - 1.2) = 0.70 / 2.3 \approx 0.304$ trên mỗi giây tiếp cận.
> 3. **Phân loại tham số**: $TTC_{\text{critical}} = 1.2\text{s}$, $TTC_{\text{warning}} = 3.5\text{s}$ và $\tau_{\text{decay}} = 3.0\text{s}$ là **các tham số khởi tạo kỹ thuật (Initial Engineering Parameters)** được nhóm lựa chọn dựa trên cơ sở vật lý phanh và thời gian phản ứng, không phải quy định pháp lý cố định của tiêu chuẩn; các giá trị này cần được hiệu chỉnh qua thực nghiệm test track.

---

### 3.3. Thành phần 3: Hệ số ưu tiên nhóm đối tượng ($C_{\text{vru}}$)

Hệ số $C_{\text{vru}}$ (Class Vulnerability Factor) phản ánh mức độ ưu tiên bảo vệ tính mạng cho các nhóm tham gia giao thông. Hệ thống phân chia thành 2 nhóm lớn theo chuẩn định nghĩa quốc tế (WHO / UNECE / Euro NCAP): **Nhóm dễ bị tổn thương (VRU - không có khung vỏ bảo vệ)** và **Nhóm phương tiện cơ giới có khung vỏ kín (Enclosed Vehicles)**:

| Phân nhóm đối tượng | Tên lớp (`class_name`) | Hệ số $C_{\text{vru}}$ | Căn cứ cơ sinh học & Đánh giá mức độ tổn hại thực tế |
| :--- | :--- | :---: | :--- |
| **VRU (Dễ tổn thương)**<br>*(Không có khung vỏ bảo vệ)* | **`person` (Người đi bộ)**<br>**`motorcycle` (Xe máy)**<br>**`bicycle` (Xe đạp)**<br>**`xe_keo` (Xe kéo hàng)**<br>**`xich_lo` (Xích lô)** | **$1.00$** | **Đồng hạng rủi ro sinh mạng tối đa ($C_{\text{vru}} = 1.00$)**: Khi va chạm với xe tải nặng ($15 - 40\text{ tấn}$), người đi xe máy hay người đi bộ đều không có khung thép hấp thụ xung lực (crumple zone), không có túi khí hay đai an toàn; cơ thể chịu xung lực trực tiếp từ khối thép hàng chục tấn nên nguy cơ tử vong / thương tật nặng là tương đương. |
| **Enclosed (Có bảo vệ)**<br>*(Khung thép & túi khí)* | **`car` (Ô tô con)** | **$0.70$** | Có cabin thép, đai an toàn và túi khí bảo vệ hành khách bên trong; vùng hấp thụ xung lực giúp giảm đáng kể tỷ lệ tử vong so với nhóm VRU. |
| **Heavy Vehicles**<br>*(Kích thước & khối lượng lớn)* | **`bus` (Xe khách)**<br>**`truck` (Xe tải khác)** | **$0.65$**<br>**$0.60$** | Kích thước và khối lượng đối trọng lớn, vị trí cabin cao; va chạm chủ yếu gây hư hại cơ học vỏ xe, rủi ro thương vong tài xế thấp nhất. |

> [!IMPORTANT]
> **LÝ GIẢI KHOA HỌC: TẠI SAO XE MÁY PHẢI ĐƯỢC ĐẶT $C_{\text{vru}} = 1.00$ NGANG BẰNG NGƯỜI ĐI BỘ?**  
> 1. **Khắc phục lỗi "Phạt hai lần" (Double Penalty)**: 
>    * Một số quan điểm cũ cho rằng xe máy có động cơ nên có thể tự vọt ga thoát hiểm, từ đó hạ trọng số xuống $0.85$. Tuy nhiên, khả năng cơ động và tốc độ di chuyển thuộc về **bài toán Động học (Kinematics / $v_{\text{closing}}$ / TTC)** và đã được giải quyết triệt để trong thành phần $S_{\text{temporal}}$!
>    * Nếu tiếp tục phạt xe máy xuống $0.85$ ở hệ số tổn thương sinh học $C_{\text{vru}}$, hệ thống sẽ làm suy giảm độ nhạy cảnh báo một cách phi lý ngay cả khi xe máy đang đứng yên chờ đèn đỏ sát cản trước mũi xe (vận tốc bằng 0, không kịp đề-pa).
> 2. **Đặc thù giao thông Việt Nam**: Xe máy chiếm $>70\%$ phương tiện lưu thông và là nạn nhân trong $>75\%$ các vụ tai nạn tử vong liên quan đến điểm mù xe tải nặng. Việc nâng $C_{\text{vru}} = 1.00$ bảo đảm hệ thống kích hoạt cảnh báo ở mức ưu tiên sinh mạng cao nhất.
> 3. **Phân loại tham số**: Các tiêu chuẩn Euro NCAP chỉ cung cấp kịch bản thử nghiệm đối tượng yếu thế (Pedestrian, Cyclist, Motorcyclist) mà không ấn định bảng trọng số BSRI. Bảng giá trị trên là **Engineering Calibration Parameters** của dự án nhằm đáp ứng thực tế giao thông Việt Nam.

---

### 3.4. Thành phần 4: Hệ số vùng mù quang học ($V_{\text{blind}}$)

Đánh giá mức độ che khuất tầm nhìn của tài xế theo các phân vùng quan sát (lấy cảm hứng từ phân loại gương Class I–VI theo UNECE R46):

| Phân vùng không gian (`BlindSpotZone`) | Hệ số khởi tạo $V_{\text{blind}}$ | Căn cứ thiết kế & Khả năng quan sát của tài xế |
| :--- | :---: | :--- |
| **`MIRROR_RIGHT` (Hông phụ bên phải)** | **$1.25$** | **Góc mù nguy hiểm nhất (+25% rủi ro)**: Xe tay lái thuận (bên trái theo luật VN), gương phụ cách xa mắt tài xế $> 2.5\text{m}$. Gương cầu lồi Class IV/V làm biến dạng quang học thu nhỏ vật thể, tài xế hoàn toàn không thể ngoái đầu nhìn trực tiếp. |
| **`SWEPT_PATH_RIGHT` (Bụng rơ-moóc bên phải)** | **$1.25$** | Vùng vệt quét bánh sau chém cua khi xe rẽ phải (Inswing Zone). Tài xế không có góc nhìn trực tiếp qua gương khi thân xe đã gập góc. |
| **`CAB_FRONT` (Mũi xe gầm cabin trước - Class VI)** | **$1.20$** | **Điểm mù trực diện cản trước (+20% rủi ro)**: Tài xế ngồi cao $2.5 - 3.0\text{m}$, nắp ca-pô che khuất toàn bộ không gian mặt đất trong phạm vi $0 - 1.8\text{m}$ phía trước cản xe. |
| **`REAR_TRAILER` (Đuôi xe)** | **$1.20$** | Điểm mù trực diện phía sau đuôi thùng xe khi lùi (Zero visibility qua gương chiếu hậu cabin). |
| **`MIRROR_LEFT` (Hông lái bên trái)** | **$1.10$** | Góc mù gương bên lái (+10% rủi ro): Tài xế ngồi ngay sát cửa sổ, có thể dễ dàng ngoái đầu nhìn trực tiếp (Direct Vision) nên mức độ rủi ro che khuất thấp hơn bên phụ. |
| **`SWEPT_PATH_LEFT` (Bụng rơ-moóc bên lái)** | **$1.10$** | Vùng vệt quét bánh sau khi xe ôm cua rẽ trái (+10% rủi ro). Dù gần tầm mắt tài xế hơn bên phụ, nhưng khi thùng rơ-moóc gập góc lớn, bánh sau vẫn chém vào dải phân cách hoặc ép lề xe máy bên lái. |
| **`CLEAR_ZONE` (Vùng thoáng ngoài điểm mù)** | **$0.85$** | **Hạ bớt 15% rủi ro**: Đối tượng nằm trực diện trong tầm quan sát qua kính chắn gió, tài xế có thời gian phản xạ tự nhiên tốt nhất, giảm bớt cảnh báo giả. |

> [!NOTE]
> **TÁCH BIỆT RÕ: HÌNH HỌC QUỸ ĐẠO VÀ MỨC ĐỘ MÙ THỊ GIÁC**:  
> - `SWEPT_PATH_LEFT / RIGHT` trước hết là **phân vùng hình học quỹ đạo lấn lề (Swept Path Geometry)**.  
> - `V_blind` là **hệ số điều chỉnh mức độ che khuất tầm nhìn (Visibility Occlusion Factor)**.  
> Các giá trị $1.25, 1.20, 1.10, 0.85$ là các tham số khởi tạo kỹ thuật của nhóm, không phải các số liệu do UNECE R46 ấn định trực tiếp.

#### 3.4.1. Phân định ranh giới hình học chuẩn xác & Cơ chế xoay rơ-moóc theo góc gập $\gamma$

1. **Triệt tiêu triệt để hiện tượng chồng lấn ranh giới (Clean Boundary Split)**:
   - Trong thiết kế chuẩn của hệ thống, ranh giới giữa nhóm vùng Cabin (`CAB_FRONT`, `MIRROR_RIGHT`, `MIRROR_LEFT`) và nhóm vùng Thùng rơ-moóc (`SWEPT_PATH_RIGHT`, `SWEPT_PATH_LEFT`, `REAR_TRAILER`) được **tách dứt khoát tại chốt mâm kéo Kingpin** $X = D_{\text{hitch}} \approx 0.3\text{m}$ (đối với xe đầu kéo) hoặc $X = 0.4 L_{wb}$ (đối với xe tải liền thân).
   - Vùng `MIRROR` kéo dài từ cản trước về đến đúng $X = D_{\text{hitch}}$.
   - Vùng `SWEPT_PATH` bắt đầu từ $X < D_{\text{hitch}}$ lùi về đuôi xe $X = X_{\text{trail\_rear}}$.
   - Nhờ phân tách dứt khoát tại mâm kéo, **hoàn toàn không có mét vuông nào bị trùng lặp**, triệt tiêu triệt để lỗi sinh 2 cảnh báo đồng thời cho cùng 1 vật thể.

2. **Cơ chế Xoay động học rơ-moóc theo góc gập $\gamma$ (Dynamic Trailer Rotation)**:
   - Đối với xe đầu kéo (`ARTICULATED`), khi xe bẻ lái vào cua, thùng rơ-moóc xoay quanh chốt Kingpin $(D_{\text{hitch}}, 0)$ một góc gập $\gamma$.
   - Nếu giữ cố định các hình chữ nhật cảnh báo trong hệ trục đầu kéo, vùng quét sẽ bị lệch khỏi thân thùng xe thật, bỏ lọt các va chạm nguy hiểm nhất khi xe vào cua.
   - Do đó, tọa độ vật thể $(X, Y)$ từ camera trước hết được biến đổi sang hệ tọa độ cục bộ của rơ-moóc $(X_{\text{tr}}, Y_{\text{tr}})$ bằng phép xoay 2D quanh tâm chốt Kingpin $(D_{\text{hitch}}, 0)$:
     $$X_{\text{tr}} = (X - D_{\text{hitch}})\cos\gamma - Y\sin\gamma + D_{\text{hitch}}$$
     $$Y_{\text{tr}} = (X - D_{\text{hitch}})\sin\gamma + Y\cos\gamma$$
   - Các vùng `SWEPT_PATH_RIGHT`, `SWEPT_PATH_LEFT` và `REAR_TRAILER` được kiểm tra trực tiếp trên $(X_{\text{tr}}, Y_{\text{tr}})$, đảm bảo vùng cảnh báo tự động uốn lượn chính xác $100\%$ theo thân rơ-moóc thời gian thực!

---

### 3.5. Thành phần 5: Hệ số điều chỉnh thao tác xe chủ ($M_{\text{ego}}$) từ IMU + GPS

Hệ số $M_{\text{ego}}$ phản ánh hành vi lái của xe tải làm tăng hay giảm nguy cơ tai nạn. Được tính toán trực tiếp từ **cụm cảm biến IMU 6-DOF và GPS** (hoàn toàn không cần CAN Bus hay công tắc phụ):

* **Mặc định khi xe chạy thẳng đều**: $M_{\text{ego}} = 1.0$.
* **Khi xe rẽ phải về phía có chướng ngại vật** (Con quay hồi chuyển IMU $\omega_z < -0.03\text{ rad/s}$ VÀ $Y_{\text{vcs}} < 0$):
  $$M_{\text{ego}} = M_{\text{ego}} \times \mathbf{1.35}$$
  *Căn cứ thiết kế*: Các báo cáo an toàn giao thông chỉ ra va chạm sườn khi xe tải rẽ phải là mối nguy hiểm đặc biệt lớn đối với người đi xe 2 bánh. Hệ số khuếch đại ban đầu $1.35$ phản ánh mức rủi ro gia tăng này. Ngưỡng phát hiện quay $|\omega_z| > 0.03\text{ rad/s}$ là tham số khởi tạo kỹ thuật (cần cân chỉnh theo độ ồn nền của cảm biến IMU).
* **Khi xe rẽ trái về phía có chướng ngại vật** (Con quay hồi chuyển IMU $\omega_z > +0.03\text{ rad/s}$ VÀ $Y_{\text{vcs}} > 0$):
  $$M_{\text{ego}} = M_{\text{ego}} \times \mathbf{1.35}$$
* **Khi xe đang lùi** (GPS $v_{\text{ego}} < -0.2\text{ m/s}$ VÀ $X_{\text{vcs}} < 0$):
  $$M_{\text{ego}} = M_{\text{ego}} \times \mathbf{1.40}$$
  *Căn cứ thiết kế*: Tầm nhìn trực tiếp phía sau đuôi thùng xe qua gương chiếu hậu cabin bằng $0$, cộng với quán tính khối lượng xe lùi làm tăng mức độ nguy hiểm.
* **Khi tài xế đạp phanh gấp** ($a_x < -1.5\text{ m/s}^2$ trên gia tốc kế IMU) — **Phân biệt hướng đa chiều**:
  * **Vật cản phía TRƯỚC hoặc BÊN HÔNG** ($X_{\text{vcs}} \ge 0$):
    $$M_{\text{ego}} = M_{\text{ego}} \times \mathbf{0.85}$$
    *Căn cứ thiết kế*: Gia tốc hãm $a_x < -1.5\text{ m/s}^2$ là bằng chứng vật lý khẳng định tài xế đã nhận thức được chướng ngại vật phía trước/bên sườn và chủ động đạp phanh can thiệp. Việc hạ bớt **$15\%$** điểm số giúp hệ thống chuyển từ còi hú khẩn cấp sang âm chuông nhắc nhở nhẹ nhàng, tránh gây hoảng loạn cho tài xế.
  * **Vật cản bám đuôi phía SAU XE** ($X_{\text{vcs}} < 0$):
    $$M_{\text{ego}} = M_{\text{ego}} \times \mathbf{1.25}$$
    *Căn cứ thiết kế*: Việc xe tải nặng phanh gấp đột ngột sẽ rút ngắn tức khắc cự ly an toàn của các phương tiện đang bám sau đuôi, làm tăng nguy cơ tai nạn đâm dồn đuôi xe (Rear-End Collision). Do đó hệ số khuếch đại tăng thêm **$25\%$** để cảnh báo tài xế chú ý tình trạng phía sau.

---

## 4. Xử Lý Các Kịch Bản Giao Thông Đặc Biệt & Nghịch Lý Dừng Xe

### 4.1. Bản chất "Nghịch lý Dừng xe / Vận tốc bằng 0" (The Standstill Paradox)

Trong lý thuyết va chạm ADAS truyền thống (như FCW / AEB trên ô tô con), công thức thời gian va chạm $TTC$ phụ thuộc hoàn toàn vào vận tốc tiếp cận:
$$v_{\text{closing}} = - \frac{X_{\text{vcs}} \cdot v_x + Y_{\text{vcs}} \cdot v_y}{r}$$

Khi xe tải dừng đèn đỏ hoặc dừng chờ ở giao lộ:
* Vận tốc xe chủ: $v_{\text{ego}} = 0\text{ m/s}$.
* Vật thể phía trước đứng yên (ví dụ xe máy hoặc người đi bộ đứng chờ đèn đỏ): $v_{\text{obs}} = 0\text{ m/s} \implies v_x = 0, v_y = 0$.
* Suy ra: $v_{\text{closing}} = 0\text{ m/s} \implies TTC \rightarrow \infty$ (Thời gian tới va chạm bằng vô cùng).

> [!CAUTION]
> **HIỂM HỌA CHẾT NGƯỜI CỦA NGHỊCH LÝ NÀY TRÊN XE TẢI NẶNG**:  
> Nếu áp dụng mù quáng công thức TTC động học, hệ thống sẽ kết luận $S_{\text{temporal}} \approx 0$ (Không có nguy cơ về mặt thời gian) $\rightarrow$ Không phát báo động.  
> Tuy nhiên, với xe tải hạng nặng, sàn cabin nằm cao cách mặt đất từ $2.5\text{m} - 3.0\text{m}$. Nếu một em học sinh đi bộ hoặc xe máy đỗ ngay trước cản xe ($0.5\text{m}$), **tài xế hoàn toàn không thể nhìn thấy họ qua kính chắn gió** (Điểm mù trực diện Class VI).  
> Ngay khi đèn tín hiệu chuyển xanh, tài xế nhả phanh đạp ga xuất phát, xe tải nặng hàng chục tấn sẽ **ngay lập tức cán qua người và phương tiện phía trước ở mét lăn bánh đầu tiên**!

---

### 4.2. Danh mục 5 Kịch bản Đặc biệt & Nền tảng An toàn Mở rộng

```text
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │               5 KỊCH BẢN ĐẶC BIỆT CỦA XE TẢI NẶNG TRONG THỰC TẾ                 │
 ├─────────────────────────────────────────────────────────────────────────────────┤
 │ 1. Dừng đèn đỏ & VRU đỗ sát cản trước (Moving-Off Front Hazard — UNECE R159)   │
 │ 2. Dừng chờ rẽ & Xe máy kẹp sườn phải (Turning-Side Pinch Hazard — UNECE R151) │
 │ 3. Lùi xe tại bến bãi có vật cản sau đuôi (Reversing Hazard — UNECE R158)       │
 │ 4. Chạy song song tốc độ cao ở cự ly siêu hẹp (Parallel Close-Proximity Hazard) │
 │ 5. Thân xe vào cua gắt che khuất tầm nhìn gương (Trailer Cornering Occlusion)   │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

#### Kịch bản 1: Điểm mù xuất phát phía trước (Moving-Off Front Hazard)
* **Bối cảnh**: Xe dừng đèn đỏ, dừng trước vạch sang đường hoặc kẹt xe nhích từng mét. Người đi bộ, trẻ em, xe máy dừng sát cản trước ($0.2\text{m} \le d \le 1.8\text{m}$).
* **Nền tảng tham chiếu**: **UNECE Regulation No. 159 (MOIS - Moving Off Information System)** quy định hệ thống phát hiện người đi bộ và người đi xe đạp ở vùng mù phía trước cản xe khi khởi hành ở tốc độ thấp ($\le 10\text{ km/h}$). BlindGuard **mở rộng phạm vi cảnh báo sang xe máy** (`motorcycle`) để phù hợp với đặc thù giao thông Việt Nam.
* **Cơ chế nguy cơ**: Khi dừng tĩnh, $v_{\text{closing}} = 0$, nhưng tiềm năng va chạm khi khởi hành là rất cao do tài xế bị che khuất tầm nhìn Class VI.

#### Kịch bản 2: Bẫy kẹp sườn khi dừng chờ rẽ tại ngã tư (Turning-Side Pinch Hazard)
* **Bối cảnh**: Xe tải dừng tại giao lộ hoặc bò chậm chuẩn bị ôm cua rẽ phải. Xe máy/xe đạp chen lên dừng song song ở "bụng xe" (vùng sườn hông giữa cabin và cầu sau). Khi xe vừa chớm lăn bánh và bẻ lái (Con quay hồi chuyển IMU ghi nhận $\omega_z < -0.03\text{ rad/s}$).
* **Nền tảng tham chiếu**: **UNECE Regulation No. 151 (BSIS)** quy định hệ thống phát hiện người đi xe đạp trong vùng mù sườn xe khi rẽ. BlindGuard **mở rộng sang xe máy và phương tiện thô sơ** (`motorcycle`, `xe_keo`, `xich_lo`).
* **Cơ chế nguy cơ**: Khi dừng, người đi xe máy cảm giác an toàn vì xe chưa chạy. Nhưng ngay khoảnh khắc xe lăn bánh và bẻ lái vào cua, vệt quét bánh sau (rear wheel off-tracking) sẽ chém sát vào lề và gây nguy cơ ép kẹp trước khi người lái xe máy kịp nhận thức.

#### Kịch bản 3: Chuyển động lùi xe tại bến bãi (Reversing Hazard)
* **Bối cảnh**: Xe tải chuyển động lùi (GPS ghi nhận $v_{\text{ego}} < -0.1\text{ m/s}$ hoặc gia tốc kế IMU nhận diện xung giật lùi $a_x < 0$). Có người đi bộ, công nhân đứng sau đuôi thùng xe trong vùng ứng viên ($0 < |X - X_{\text{tail}}| \le 2.5\text{m}$).
* **Nền tảng tham chiếu**: **UNECE Regulation No. 158 (Reversing Motion)** quy định về khả năng quan sát và cảnh báo khi lùi. Ngưỡng cự ly $2.5\text{m}$ là tham số khoanh vùng ứng viên nguy cơ ban đầu do nhóm lựa chọn, cần được hiệu chỉnh qua thực nghiệm.
* **Cơ chế nguy cơ**: Điểm mù phía sau đuôi thùng xe là tuyệt đối qua gương chiếu hậu cabin.

#### Kịch bản 4: Chạy song song tốc độ cao ở cự ly siêu hẹp (Parallel Close-Proximity Hazard)
* **Bối cảnh**: Xe tải chạy $v_{\text{ego}} \ge 8.0\text{ m/s}$ ($>30\text{ km/h}$), xe máy chạy song song cùng chiều với độ chênh lệch vận tốc rất nhỏ ($|v_{\text{closing}}| \le 0.5\text{ m/s}$) và khoảng cách sườn cực hẹp ($d_{\text{lateral}} \le 0.8\text{m}$).
* **Bản chất rủi ro**: Trong tình huống chạy song song cùng tốc độ, công thức TTC cổ điển bị suy biến ($v_{\text{closing}} \approx 0 \implies TTC \to \infty$). Khoảng cách hông quá hẹp tiềm ẩn rủi ro va quệt rất cao khi chỉ cần xe tải lách nhẹ hoặc xe máy chao đảo do luồng gió xoáy/chênh lệch áp suất dọc thân xe. BSRI áp dụng thành phần rủi ro áp sát ngang $S_{\text{lateral}}$ để kích hoạt cảnh báo duy trì khoảng cách an toàn (lưu ý: hệ thống không dùng định luật Bernoulli để tính trực tiếp lực hút cơ học mà coi đây là tình huống rủi ro cận kề cần cảnh báo).

#### Kịch bản 5: Che khuất tầm nhìn gương khi thân xe vào cua gắt (Trailer Cornering Occlusion Hazard)
* **Bối cảnh**: Xe tải ôm cua gắt (IMU ghi nhận $|\omega_z| > 0.08\text{ rad/s}$) hoặc xe đầu kéo có góc gập thùng $\gamma \neq 0$ (ước tính từ mô hình vi phân động học $\dot{\gamma} = \omega_z - \frac{v}{L_t}\sin\gamma$ qua IMU + GPS).
* **Cơ chế nguy cơ**: Thân thùng rơ-moóc tạo thành một góc gấp che khuất góc nhìn qua gương chiếu hậu bên phụ (tham chiếu phân vùng UNECE R46). Hệ thống tự động nâng hệ số rủi ro góc mù $V_{\text{blind}}$ để bù trừ việc suy giảm tầm nhìn gián tiếp của người lái.

---

### 4.3. Kiến Trúc "Lớp Lọc Ưu Tiên" (Priority Safety Interceptor): Tại Sao Phải Làm 5 Case Riêng?

Việc tách riêng 5 kịch bản xử lý ưu tiên xuất phát từ **3 lý do kỹ thuật và an toàn then chốt**:

```text
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │           TẠI SAO BẮT BUỘC PHẢI CHIA THÀNH 5 CASE RIÊNG BIỆT?                    │
 ├──────────────────────────────────────────────────────────────────────────────────┤
 │ 1. KHẮC PHỤC SUY BIẾN TOÁN HỌC KHI VẬN TỐC = 0 (Mathematical Singularity):       │
 │    Công thức TTC truyền thống TTC = r / v_closing bị chia cho 0 khi cả hai đứng  │
 │    yên (TTC -> vô cùng), làm hệ thống bị "mù toán học" trước các hiểm họa ngay   │
 │    sát cản trước hoặc sườn xe.                                                   │
 │                                                                                  │
 │ 2. CAN THIỆP AN TOÀN TỨC THỜI (Safety Risk Override):                            │
 │    Trong các tình huống tính mạng bị đe dọa cận kề (xe sắp lăn bánh đè lên       │
 │    người trước mũi, hoặc đang lùi trúng người sau đuôi), hệ thống áp đặt mức     │
 │    rủi ro khẩn cấp ngay lập tức dựa trên điều kiện hình học mà không cần chờ đợi │
 │    chu kỳ hội tụ vận tốc tương đối.                                              │
 │                                                                                  │
 │ 3. KIẾN TRÚC HAI TẦNG XỬ LÝ (Two-Tier Processing Pipeline):                      │
 │    - Tầng 1 (Fast-Path Gatekeeper): Kiểm tra 5 kịch bản đặc biệt. Nếu thỏa mãn   │
 │      điều kiện -> Trả về kết quả khẩn cấp ngay (Early Exit).                     │
 │    - Tầng 2 (Continuous Risk Pipeline): Nếu không thuộc kịch bản đặc biệt ->     │
 │      Chạy công thức BSRI liên tục chuẩn hóa (w_s*S_s + w_t*S_t) * C * V * M.     │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

* **Nếu cố tình "nhồi nhét" vào một công thức duy nhất**: Công thức đó sẽ phải chứa hàng loạt hàm phi tuyến tính, đạo hàm ngắt quãng và hàm nhảy Heaviside. Kết quả là công thức trở thành một hàm số cồng kềnh, cực kỳ khó tinh chỉnh (hard to tune), dễ sinh nhiễu và gây báo động giả (False Positives).
* **Mô hình Lớp Lọc Ưu Tiên (Priority Interceptor Pattern)**: Đây là kiến trúc chuẩn mực được sử dụng trong các hệ thống ADAS công nghiệp. Kịch bản đặc biệt đóng vai trò là "lính gác cổng" (Gatekeeper) phản ứng nhanh, bảo vệ xe khỏi các điểm chết toán học.

---

### 4.4. Cơ Chế Nhận Diện Của Hệ Thống: "Làm Sao Hệ Thống Biết Xe Đang Ở Case Nào?"

Hệ thống **hoàn toàn không sử dụng mô hình AI "đoán mò" ngữ cảnh** (vốn có độ trễ cao và tính bất định). Việc nhận diện kịch bản dựa trên **Bộ điều kiện tiên quyết từ Cảm biến cứng (Sensor Truth Conditions)** kết hợp **Tọa độ hình học mặt đất Bird's Eye View (VCS Coordinates)** từ Camera AI.

#### 1. Nguồn Dữ Liệu Cảm Biến Đầu Vào (100% Thuần GPS + IMU 6-DOF + Camera AI)
Hệ thống được thiết kế theo nguyên lý **Độc lập phần cứng tối đa**, hoàn toàn **KHÔNG CAN THIỆP CAN BUS**, **KHÔNG CẦN CÔNG TẮC ĐÈN XI-NHAN**, **KHÔNG CẦN CÔNG TẮC ĐÈN LÙI** và **KHÔNG CẦN CẢM BIẾN KHỚP NỐI CƠ HỌC**:

```text
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │           3 NGUỒN DỮ LIỆU CẢM BIẾN DUY NHẤT CỦA TOÀN BỘ HỆ THỐNG                 │
 ├──────────────────────────────────────────────────────────────────────────────────┤
 │ 1. GPS / GNSS MODULE:                                                            │
 │    - Đo vận tốc di chuyển thực của xe chủ: v_ego (m/s).                          │
 │    - Dừng hẳn: |v_ego| < 0.2 m/s (< 0.7 km/h).                                   │
 │    - Lùi xe: v_ego < -0.1 m/s (vận tốc âm qua hiệu ứng Doppler vệ tinh).        │
 │    - Tốc độ cao: v_ego >= 8.0 m/s (> 30 km/h).                                   │
 │                                                                                  │
 │ 2. CỤM CẢM BIẾN QUÁN TÍNH IMU 6-DOF (Gia tốc kế + Con quay hồi chuyển):          │
 │    - Con quay hồi chuyển (Gyroscope omega_z - yaw rate): Đo trực tiếp vận tốc    │
 │      góc xoay quanh trục thẳng đứng Z của thân xe (độ trễ < 5ms):                │
 │        * omega_z < -0.04 rad/s: Xe đang đánh lái ôm cua rẽ phải (THAY XI-NHAN!). │
 │        * omega_z > +0.04 rad/s: Xe đang đánh lái ôm cua rẽ trái.                 │
 │        * |omega_z| <= 0.04 rad/s: Xe chạy thẳng hoặc đứng yên.                   │
 │    - Gia tốc kế dọc (Accelerometer a_x):                                         │
 │        * a_x < -1.5 m/s²: Xe đang đạp phanh gấp.                                 │
 │        * a_x < 0 kèm giật lùi: Xác nhận trạng thái bắt đầu lùi xe.               │
 │                                                                                  │
 │ 3. PHÂN HỆ THỊ GIÁC MÁY TÍNH CAMERA AI (YOLO + ByteTrack + Homography):          │
 │    - Tọa độ mặt đất VCS (X_vcs, Y_vcs) mét: Định vị vật cản ở trước cản mũi,     │
 │      dọc sườn hông hay sau đuôi thùng xe.                                        │
 │    - Vận tốc tương đối (v_x, v_y, v_closing) từ bộ lọc Kalman tracking.          │
 │    - Phân loại đối tượng (class_name): Nhận diện nhóm đối tượng dễ tổn thương     │
 │      (VRU: person, motorcycle, bicycle, xe_keo, xich_lo) so với ô tô.            │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

> [!NOTE]
> **Giải pháp kỹ thuật cho Xe rơ-moóc khi không có cảm biến góc khớp nối**:
> * **Đối với xe tải liền thân (Rigid Truck)**: Thân xe là một khối khung sắt-xi duy nhất, góc gập $\gamma \equiv 0$ cố định, không có khớp quay.
> * **Đối với xe đầu kéo kéo rơ-moóc (Articulated Truck)**: Hệ thống sử dụng **Mô hình động học vi phân Single-Track (Kinematic Bicycle Estimator)** để tự động ước lượng góc $\gamma$ thời gian thực thuần túy từ IMU $\omega_z$ và GPS $v_{\text{ego}}$:
>   $$\frac{d\gamma}{dt} = \omega_z - \frac{v_{\text{ego}}}{L_{\text{trailer}}} \sin\gamma$$
>   Do đó, hệ thống có thể **ước lượng liên tục góc gập rơ-moóc** mà không cần gắn cảm biến góc quay cơ học vào mâm kéo (Fifth Wheel Kingpin). Lưu ý: vì là phép ước lượng tích phân từ cảm biến quán tính, hệ thống tích hợp cơ chế tự cân bằng trôi (zero-drift calibration) khi xe chạy thẳng đều.

---

#### 2. Ma Trận Sự Thật Phân Loại Kịch Bản (Sensor Truth Matrix)

Mỗi kịch bản được kích hoạt dựa trên sự giao thoa khách quan giữa trạng thái IMU/GPS của xe chủ và tọa độ/vận tốc từ Camera:

| Tín hiệu Cảm biến | Case 1: MOIS cản trước (Bối cảnh R159) | Case 2: BSIS bẫy kẹp sườn (Bối cảnh R151) | Case 3: Lùi bến bãi (Bối cảnh R158) | Case 4: Kẹp sườn áp sát hẹp | Case 5: Mất góc gương khi vào cua |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Vận tốc GPS ($v_{\text{ego}}$)** | **$< 0.2\text{ m/s}$ (Dừng hẳn)** | **$< 2.5\text{ m/s}$ (Dừng / Bò chậm)** | **$< -0.1\text{ m/s}$ (Đang lùi)** | **$\ge 8.0\text{ m/s}$ ($> 30\text{ km/h}$)** | Bất kỳ |
| **Con quay IMU ($\omega_z$)** | $\|\omega_z\| \le 0.04$ (Thẳng/Dừng) | **$\omega_z < -0.04\text{ rad/s}$ (Rẽ phải)** | $\|\omega_z\| \le 0.05$ | $\|\omega_z\| \le 0.03$ (Chạy thẳng) | **$\|\omega_z\| > 0.08\text{ rad/s}$ (Cua gắt)** |
| **Gia tốc IMU ($a_x$)** | $a_x \approx 0$ | Bất kỳ | $a_x < 0$ (Xung giật lùi) | Bất kỳ | Bất kỳ |
| **Tọa độ dọc Camera ($X_{\text{vcs}}$)** | **Trước mũi xe**: $X_{\text{front}} \le X \le X_{\text{front}} + 1.8\text{m}$ | **Dọc sườn xe**: $-L_{\text{rear}} \le X \le 0.7 X_{\text{front}}$ | **Sau đuôi xe**: $X < X_{\text{rear}}$ VÀ $\|X - X_{\text{rear}}\| \le 2.5\text{m}$ | **Dọc sườn**: $-L_{\text{rear}} \le X \le X_{\text{front}}$ | Dọc sườn xe |
| **Tọa độ ngang Camera ($Y_{\text{vcs}}$)** | **Trực diện cản**: $\|Y\| \le \frac{W}{2} + 0.3\text{m}$ | **Sườn phụ bên phải**: $-2.5\text{m} \le Y \le -\frac{W}{2}$ | **Phía sau đuôi**: $\|Y\| \le \frac{W}{2} + 0.6\text{m}$ | **Sát mép hông**: $0 \le d_{\text{lat}} \le 0.8\text{m}$ | **Sườn phụ bên phải**: $-2.5\text{m} \le Y \le -\frac{W}{2}$ |
| **Nhóm đối tượng Camera (`class`)** | **VRU** (Người, xe máy...) | **VRU** (Xe máy, xe đạp...) | **Mọi chướng ngại vật** | **Phương tiện 2 bánh (VRU)** | Mọi vật thể vùng gương |
| **Vận tốc tiếp cận ($v_{\text{closing}}$)** | Không phụ thuộc ($v \approx 0$) | Không phụ thuộc | **$> 0.1\text{ m/s}$ (Đang áp sát đuôi)** | **$\|v_{\text{closing}}\| \le 0.50\text{ m/s}$** | Không phụ thuộc |
| **Hành vi can thiệp của BSRI** | **Override BSRI $\ge 0.85$** (Đỏ rực, còi hú) | **Override BSRI $\ge 0.85$** (Đỏ rực, còi hú) | **Override BSRI $\ge 0.95$** (Đỏ rực, phanh khẩn) | **Nâng $S_{\text{temporal}}$ theo $S_{\text{lateral}}$** | **Tăng hệ số $V_{\text{blind}} = 1.35$** |

---

#### 3. Sơ Đồ Cây Quyết Định Thuần Cảm Biến Cứng (Decision Tree Flowchart)

Tại mỗi chu kỳ xử lý frame ($30\text{ FPS}$), khi nhận diện được một chướng ngại vật `obs` từ Camera và dữ liệu từ IMU/GPS:

```text
                     [BẮT ĐẦU ĐÁNH GIÁ CHƯỚNG NGẠI VẬT]
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │  GPS: v_ego < -0.1 m/s       │
                      │  (Xe đang chuyển động lùi?)   │
                      └──────────────┬───────────────┘
                                     │
                   ┌─────────────────┴─────────────────┐
               [CÓ - XE LÙI]                     [KHÔNG - XE TIẾN/DỪNG]
                   │                                   │
                   ▼                                   ▼
        ┌─────────────────────┐             ┌─────────────────────┐
        │Camera: Vật sau đuôi?│             │ GPS: |v_ego| < 0.2  │
        │d <= 2.5m & Y sau xe │             │ (Xe đang dừng hẳn?) │
        └──────────┬──────────┘             └──────────┬──────────┘
             ┌─────┴─────┐                       ┌─────┴─────┐
            [CÓ]       [KHÔNG]                  [CÓ]       [KHÔNG]
             │           │                       │           │
             ▼           │                       ▼           ▼
        ╔═════════╗      │            ┌─────────────────┐ ┌────────────────┐
        ║ CASE 3  ║      │            │Camera: VRU trước│ │GPS: v >= 8 m/s │
        ║(LÙI XE  ║      │            │mũi cản d <= 1.8m│ │(Chạy > 30km/h)?│
        ║ R158)   ║      │            └────────┬────────┘ └───────┬────────┘
        ╚═════════╝      │               ┌─────┴─────┐        ┌───┴───┐
                         │              [CÓ]       [KHÔNG]   [CÓ]   [KHÔNG]
                         │               │           │        │       │
                         │               ▼           │        │       ▼
                         │          ╔═════════╗      │        │ ┌──────────────┐
                         │          ║ CASE 1  ║      │        │ │IMU: |w_z|>0.08│
                         │          ║(MOIS    ║      │        │ │(Cua gắt &    │
                         │          ║ R159)   ║      │        │ │ khuất gương)?│
                         │          ╚═════════╝      │        │ └──────┬───────┘
                         │                           │        │   ┌────┴────┐
                         │                           ▼        │  [CÓ]     [KHÔNG]
                         │                  ┌─────────────────┐│   │         │
                         │                  │IMU: w_z < -0.04 ││   ▼         │
                         │                  │(hoặc dừng xe) VÀ││╔═════════╗  │
                         │                  │VRU ở sườn phải? ││║ CASE 5  ║  │
                         │                  └────────┬────────┘│║(GẬP GÓC/║  │
                         │                     ┌─────┴─────┐  │║CUA GẮT) ║  │
                         │                    [CÓ]       [KHÔNG╚═════════╝  │
                         │                     │           │                 │
                         │                     ▼           │                 │
                         │                ╔═════════╗      │                 │
                         │                ║ CASE 2  ║      │                 │
                         │                ║(BSIS    ║      │                 │
                         │                ║ R151)   ║      │                 │
                         │                ╚═════════╝      │                 │
                         │                                 │                 │
                         │                  ┌──────────────┘                 │
                         │                  │  ┌─────────────────────────────┘
                         │                  │  │
                         │                  ▼  ▼
                         │        ┌─────────────────────────┐
                         │        │Camera: VRU sát hông     │
                         │        │d_lat <= 0.8m & v_clos~0?│
                         │        └────────────┬────────────┘
                         │               ┌─────┴─────┐
                         │              [CÓ]       [KHÔNG]
                         │               │           │
                         │               ▼           │
                         │          ╔═════════╗      │
                         │          ║ CASE 4  ║      │
                         │          ║(BERNO-  ║      │
                         │          ║ ULLI)   ║      │
                         │          ╚═════════╝      │
                         │                           │
                         └───────────────────────────┼─────────────────┐
                                                     │                 │
                                                     ▼                 ▼
                                     ╔═══════════════════════════════════╗
                                     ║ KHÔNG THỎA MÃN KỊCH BẢN ĐẶC BIỆT  ║
                                     ║ -> CHUYỂN TIẾP TRƠN TRU SANG      ║
                                     ║ CÔNG THỨC BSRI CHUẨN LIÊN TỤC:    ║
                                     ║ BSRI = (w_s*S_s + w_t*S_t)*W*V*M  ║
                                     ╚═══════════════════════════════════╝
```

---

#### 4. Thứ Tự Ưu Tiên & Cơ Chế Xử Lý Xung Đột (Priority Cascade & Conflict Resolution)

Một băn khoăn thực tế:  
> *"Nếu cùng một thời điểm có nhiều chướng ngại vật ở các vị trí khác nhau (ví dụ: xe dừng đèn đỏ, có xe máy ở ngay trước cản mũi VÀ cũng có xe máy dừng bên sườn phải), hệ thống sẽ cảnh báo cái nào?"*

Hệ thống xử lý phân cấp qua **2 nguyên tắc cốt tử**:

1. **Nguyên tắc Phân cấp Ưu tiên can thiệp (Precedence Cascade)**:
   Mỗi đối tượng được duyệt qua chuỗi kiểm tra theo thứ tự ưu tiên tuyệt đối từ cao xuống thấp:
   * **Ưu tiên 1 (Tối cao - Highest)**: **Case 3 (Lùi xe - R158)**. Vì phía sau đuôi xe là vùng mù $100\%$, người đứng phía sau hoàn toàn không có cơ hội phản xạ né tránh nếu xe lùi.
   * **Ưu tiên 2 (Cực cao - Critical)**: **Case 1 (Mũi xe xuất phát - MOIS R159)**. Bảo vệ trực diện hướng chuyển động lăn bánh đầu tiên của xe. Nếu đè trúng người phía trước, hậu quả là tử vong tức thì.
   * **Ưu tiên 3 (Rất cao - High)**: **Case 2 (Bẫy kẹp sườn phải - BSIS R151)**. Bảo vệ vệt quét bánh sau khi xe ôm cua.
   * **Ưu tiên 4 (Cao - Medium-High)**: **Case 4 (Kẹp sườn tốc độ cao Bernoulli)**. Bảo vệ xe máy chạy áp sát trên quốc lộ.
   * **Ưu tiên 5 (Bù trừ tầm nhìn - Support)**: **Case 5 (Gập góc rơ-moóc)**. Tự động nâng hệ số mù $V_{\text{blind}} = 1.35$ nếu đối tượng rơi vào vùng gương bị che khuất.
   * **Mặc định**: Nếu không trúng case nào, chạy công thức BSRI thông thường.

2. **Nguyên tắc Chọn Mối Nguy Xấu Nhất Toàn Xe (Worst-Case Max-Pooling)**:
   * Nếu có $N$ chướng ngại vật xung quanh xe, hệ thống sẽ tính điểm BSRI độc lập cho từng đối tượng $i$:
     $$\text{BSRI}_{\text{ego\_overall}} = \max_{i=1 \dots N} (\text{BSRI}_i)$$
   * Màn hình HUD buồng lái sẽ **ưu tiên hiển thị cảnh báo bằng giọng nói/chuỗi chữ đỏ của đối tượng có $\text{BSRI}$ cao nhất**. Các đối tượng nguy cơ khác được hiển thị dưới dạng các biểu tượng cảnh báo phụ trợ trên sơ đồ mặt bằng xe.

---

### 4.5. Chi Tiết Thuật Toán & Công Thức Tính Điểm Cho Từng Kịch Bản

#### Kịch bản 1: Cảnh báo khởi hành dừng đèn đỏ (Moving-Off Front Hazard)
* **Nguyên lý**: Xe dừng hẳn ($|v_{\text{ego}}| < 0.2\text{ m/s}$), có đối tượng VRU nằm trong vùng cản trước ($0 \le X - X_{\text{front}} \le 1.8\text{m}$). Ta tính thời gian va chạm đề-pa tiềm tàng:
  $$d_{\text{front}} = \max(0.1, \, X_{\text{vcs}} - X_{\text{front}})$$
  $$TTC_{\text{takeoff}} = \sqrt{\frac{2 \cdot d_{\text{front}}}{a_{\text{takeoff}}}} \quad (\text{với gia tốc đề-pa danh định ban đầu } a_{\text{takeoff}} = 1.2\text{ m/s}^2)$$
* **Định lượng**: Nếu $d_{\text{front}} = 0.5\text{m} \implies TTC_{\text{takeoff}} \approx 0.91\text{s} \le 1.2\text{s}$ (Ngưỡng khẩn cấp).  
  $$\implies S_{\text{temporal}} = 1.00, \quad S_{\text{spatial}} = 1.00, \quad V_{\text{blind}} = 1.20, \quad M_{\text{ego}} = 1.25$$
  $$\mathbf{BSRI} = \min(1.0, \, 1.00 \times C_{\text{vru}} \times 1.20 \times 1.25) \ge \mathbf{0.85} \implies \text{\textbf{CRITICAL}}$$
* **XAI HUD**: `[MOIS KHẨN CẤP] Xe máy #12 đỗ sát cản trước 0.5m! KHÔNG ĐƯỢC NHẢ PHANH XUẤT PHÁT!`

#### Kịch bản 2: Bẫy kẹp sườn khi dừng chờ ôm cua (Turning-Side Pinch Hazard)
* **Nguyên lý**: Xe đang dừng hoặc bò chậm ($|v_{\text{ego}}| < 2.5\text{ m/s}$) và Con quay hồi chuyển IMU bắt đầu ghi nhận xu hướng quay bẻ lái rẽ phải ($\omega_z < -0.03\text{ rad/s}$). Có xe máy nằm ở "bụng xe" bên phụ (vùng quét chém cua của bánh sau).
* **Định lượng**: Áp đặt trạng thái chuẩn bị xâm nhập vùng vệt quét bánh sau:
  $$S_{\text{spatial}} = 1.00, \quad S_{\text{temporal}} = 0.85, \quad V_{\text{blind}} = 1.25, \quad M_{\text{ego}} = 1.35$$
  $$\mathbf{BSRI} = \min(1.0, \, (0.45 \times 1.0 + 0.55 \times 0.85) \times C_{\text{vru}} \times 1.25 \times 1.35) \ge \mathbf{0.80} \implies \text{\textbf{CRITICAL}}$$
* **XAI HUD**: `[BẪY KẸP CUA] Xe máy #08 dừng sát sườn phụ! Bánh sau sẽ chém trúng khi ôm cua! Chờ xe đi qua!`

#### Kịch bản 3: Chuyển động lùi xe tại bến bãi (Reversing Hazard)
* **Nguyên lý**: GPS ghi nhận xe lùi ($v_{\text{ego}} < -0.1\text{ m/s}$) hoặc gia tốc kế IMU nhận diện xung giật lùi $a_x < 0$, có vật cản sau đuôi xe trong phạm vi ứng viên $2.5\text{m}$.
* **Định lượng**: Điểm mù trực diện sau thùng xe:
  $$d_{\text{rear}} = \max(0.1, \, |X_{\text{vcs}} - X_{\text{rear}}|)$$
  $$TTC_{\text{reverse}} = \sqrt{\frac{2 \cdot d_{\text{rear}}}{a_{\text{rev}}}} \quad (\text{với gia tốc lùi danh định } a_{\text{rev}} = 0.8\text{ m/s}^2)$$
  $$\text{Áp đặt: } V_{\text{blind}} = 1.40, \; M_{\text{ego}} = 1.40 \implies \mathbf{BSRI \ge 0.90} \implies \text{\textbf{CRITICAL}}$$
* **XAI HUD**: `[ĐIỂM MÙ LÙI] Có Người đi bộ #03 đứng ngay sau đuôi xe 1.2m! ĐẠP PHANH DỪNG XE NGAY!`

#### Kịch bản 4: Kẹp sườn song song tốc độ cao (Parallel Close-Proximity Hazard)
* **Nguyên lý**: Xe chạy $v_{\text{ego}} \ge 8.0\text{ m/s}$ ($>30\text{ km/h}$), xe máy chạy song song cùng chiều độ lệch vận tốc cực nhỏ ($|v_{\text{closing}}| \le 0.50\text{ m/s}$), khoảng cách hông cực hẹp ($d_{\text{lateral}} \le 0.8\text{m}$).
* **Định lượng**: Bổ sung thành phần rủi ro áp sát ngang $S_{\text{lateral}}$:
  $$S_{\text{lateral}} = \exp\left( - \frac{\max(0.0, \, d_{\text{lateral}})}{0.40} \right)$$
  $$S_{\text{temporal}} = \max(S_{\text{temporal}}, \, S_{\text{lateral}})$$
* **XAI HUD**: `[KẸP SƯỜN TỐC ĐỘ CAO] Xe máy #15 chạy quá sát sườn 0.4m! Nguy cơ chao đảo mất lái! Giữ thẳng lái!`

#### Kịch bản 5: Che khuất tầm nhìn gương khi thân xe vào cua gắt (Trailer Cornering Occlusion Hazard)
* **Nguyên lý**: Xe ôm cua gắt (Con quay IMU ghi nhận $|\omega_z| > 0.08\text{ rad/s}$) hoặc xe đầu kéo có góc gập $\gamma > 20^\circ$ (ước tính thời gian thực từ vi phân động học $\dot{\gamma} = \omega_z - \frac{v}{L_t}\sin\gamma$).
* **Định lượng**: Tự động tăng hệ số góc mù $V_{\text{blind}}$ lên **$1.35$** (tăng thêm $10\%$ so với mức thông thường $1.25$) để bù trừ việc gương chiếu hậu bên phụ bị thân thùng xe che khuất hoàn toàn.

---

### 4.6. Hướng Dẫn Viết Code Chi Tiết: Tích Hợp Vào BSRICalculator Như Thế Nào?

Một câu hỏi cốt lõi từ các kỹ sư phần mềm:  
> **"Code sẽ được viết như thế nào trong class `BSRICalculator`? Làm sao để gọi hàm này mà không phá vỡ mã nguồn hiện có?"**

Dưới đây là cấu trúc kiến trúc gọi hàm (Software Call Flow) và mã nguồn triển khai chi tiết:

##### 1. Luồng Gọi Hàm Trong Kiến Trúc Phần Mềm (Execution Flow)

Hàm `check_special_scenarios()` hoạt động như một **lớp bẫy ưu tiên (Safety Gatekeeper)** được đặt ngay tại Bước 0 của hàm đánh giá chướng ngại vật `evaluate_obstacle()`:

```text
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │  BSRICalculator.evaluate_scene(ego_state, obstacles)                        │
 │    │                                                                        │
 │    ├─► Lặp qua từng obstacle trong danh sách chướng ngại vật:               │
 │    │     │                                                                  │
 │    │     ▼                                                                  │
 │    │   evaluate_obstacle(obs, ego_state, dhz_poly):                         │
 │    │     │                                                                  │
 │    │     ├─► [BƯỚC 0]: special_res = check_special_scenarios(obs, ego)      │
 │    │     │       │                                                          │
 │    │     │       ├─► [NẾU CÓ KẾT QUẢ != None] (Trúng 1 trong 5 case)        │
 │    │     │       │     └─► RETURN NGAY (Early Exit / Fast Return)!          │
 │    │     │       │         (Bỏ qua tính DHZ khoảng cách, TTC, phanh)        │
 │    │     │       │                                                          │
 │    │     │       └─► [NẾU == None] (Không thuộc kịch bản đặc biệt)          │
 │    │     │             │                                                    │
 │    │     │             ▼                                                    │
 │    │     ├─► [BƯỚC 1 - 6]: Chạy công thức BSRI chuẩn liên tục:              │
 │    │     │             S_spatial = exp(- dist_to_dhz / 1.8)                 │
 │    │     │             S_temporal, ttc = calculate_temporal_risk(...)       │
 │    │     │             raw_bsri = (w_s*S_s + w_t*S_t) * W * V * M           │
 │    │     │             return BSRIResult(...)                               │
 │    │                                                                        │
 │    └─► Chọn max BSRI trong danh sách -> Báo cáo tổng thể xe chủ             │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

#### 2. Vị Trí Cắm Code Khung (Skeleton Integration Code)

Trong file `bsri_calculator.py`, phương thức đánh giá chính được tổ chức như sau:

```python
class BSRICalculator:
    # ... Các thuộc tính khởi tạo cấu hình xe ...

    def evaluate_obstacle(self, obs: TrackedObstacle, ego: EgoVehicleState, dhz_poly: Optional[Polygon] = None) -> BSRIResult:
        """Tính toán chỉ số BSRI đầy đủ cho 1 chướng ngại vật."""
        
        # =========================================================================
        # BƯỚC 0: KIỂM TRA LỚP LỌC ƯU TIÊN 5 KỊCH BẢN ĐẶC BIỆT (FAST-PATH GATEKEEPER)
        # =========================================================================
        special_result = self.check_special_scenarios(obs, ego)
        if special_result is not None:
            # Ngắt sớm và trả về kết quả khẩn cấp tức thì (tiết kiệm thời gian xử lý)
            bsri_score, risk_level, explanation, recommendation = special_result
            zone = self.classify_blind_spot_zone(obs.vcs_x, obs.vcs_y, ego)
            vru_w = self.VRU_WEIGHTS.get(obs.class_name.lower(), 0.70)
            return BSRIResult(
                track_id=obs.track_id,
                class_name=obs.class_name,
                bsri_score=bsri_score,
                risk_level=risk_level,
                zone=zone,
                is_in_dhz=True if risk_level == RiskLevel.CRITICAL else False,
                dist_to_dhz=0.0 if risk_level == RiskLevel.CRITICAL else 0.5,
                ttc_seconds=0.5 if risk_level == RiskLevel.CRITICAL else None,
                vru_weight=vru_w,
                spatial_risk=1.00 if risk_level == RiskLevel.CRITICAL else 0.70,
                temporal_risk=1.00 if risk_level == RiskLevel.CRITICAL else 0.70,
                maneuver_factor=1.35,
                blind_factor=self.calculate_blind_spot_factor(zone),
                explanation=explanation,
                recommendation=recommendation
            )

        # =========================================================================
        # BƯỚC 1-6: NẾU KHÔNG THUỘC KỊCH BẢN ĐẶC BIỆT -> CHẠY CÔNG THỨC LIÊN TỤC
        # =========================================================================
        # S_spatial = exp(- dist_to_dhz / 1.8)
        # S_temporal, ttc = self.calculate_temporal_risk(obs, ego)
        # raw_bsri = (self.w_spatial * spatial_risk + self.w_temporal * temporal_risk) * vru_w * blind_factor * maneuver_factor
        # return BSRIResult(...)
```

---

#### 3. Mã Nguồn Python Hoàn Chỉnh của Hàm `check_special_scenarios`

Dưới đây là hàm mẫu hoàn chỉnh, chuẩn PEP-8, hỗ trợ cả **xe tải liền thân (`RIGID`)** và **xe đầu kéo rơ-moóc (`ARTICULATED`)**:

```python
def check_special_scenarios(
    self, obs: TrackedObstacle, ego: EgoVehicleState
) -> Optional[Tuple[float, RiskLevel, str, str]]:
    """
    Kiểm tra và xử lý ưu tiên các kịch bản giao thông đặc biệt (Safety Gatekeeper).
    Được thiết kế theo tiêu chuẩn ISO 26262 ASIL-D và UNECE R151 / R158 / R159.

    ĐẦU VÀO PHẦN CỨNG THỰC TẾ (100% KHÔNG CAN BUS / KHÔNG CÔNG TẮC CƠ):
        1. GPS: ego.speed_mps (Vận tốc dọc có dấu).
        2. IMU 6-DOF: ego.yaw_rate_rad_s (Tốc độ góc yaw r), ego.accel_x_mps2 (Gia tốc dọc a_x).
        3. Camera AI: obs (Tọa độ mặt đất vcs_x, vcs_y, vận tốc vel_x, vel_y, class_name).

    Returns:
        Tuple (bsri_score, risk_level, explanation, recommendation) nếu thỏa mãn kịch bản.
        None nếu không thuộc diện đặc biệt -> Chuyển tiếp sang công thức BSRI thông thường.
    """
    # 1. Trích xuất thông số kích thước hình học theo loại xe (VCS Center)
    if ego.vehicle_type == VehicleType.RIGID:
        ego_front_x = self.rigid_front_length   # Mũi xe cản trước (m)
        ego_rear_x = -self.rigid_rear_length    # Đuôi thùng xe (m)
        cab_half_w = self.rigid_half_w          # Nửa chiều rộng xe (m)
    else:
        ego_front_x = self.cab_front_x          # Mũi cabin đầu kéo (m)
        ego_rear_x = self.trail_rear_x          # Đuôi rơ-moóc kéo theo (m)
        cab_half_w = self.cab_half_w            # Nửa chiều rộng cabin (m)

    # 2. Các cờ trạng thái cơ bản từ cảm biến phần cứng (GPS + IMU)
    is_standstill = abs(ego.speed_mps) < 0.20  # Dừng hẳn (< 0.7 km/h)
    is_vru = obs.class_name.lower() in ["person", "motorcycle", "bicycle", "xe_keo", "xich_lo"]

    # =========================================================================
    # ƯU TIÊN 1: KỊCH BẢN 3 - UNECE R158 REVERSING (LÙI BẾN BÃI)
    # Nhận diện: GPS vận tốc âm (v_ego < -0.1 m/s) VÀ có vật cản sau đuôi xe <= 2.5m
    # =========================================================================
    is_reversing = (ego.speed_mps < -0.10) or (ego.accel_x_mps2 < -0.50 and obs.vcs_x < ego_rear_x and obs.vel_x > 0.10)
    if is_reversing and (obs.vcs_x < ego_rear_x):
        d_rear = abs(obs.vcs_x - ego_rear_x)
        if d_rear <= 2.50 and abs(obs.vcs_y) <= (cab_half_w + 0.60):
            bsri = 0.950
            exp = (
                f"NGUY HIỂM TỐI CẤP! [ĐIỂM MÙ LÙI R158] Có {obs.class_name} #{obs.track_id} "
                f"đứng ngay sau đuôi xe ({d_rear:.1f}m)! Tầm nhìn sau bằng 0!"
            )
            rec = "ĐẠP PHANH DỪNG XE NGAY LẬP TỨC! KHÔNG ĐƯỢC TIẾP TỤC LÙI!"
            return bsri, RiskLevel.CRITICAL, exp, rec

    # =========================================================================
    # ƯU TIÊN 2: KỊCH BẢN 1 - UNECE R159 MOIS (DỪNG ĐÈN ĐỎ & SÁT CẢN TRƯỚC)
    # Nhận diện: GPS đứng yên (|v_ego| < 0.2 m/s) VÀ Camera thấy VRU đỗ sát cản trước 0 - 1.8m
    # =========================================================================
    in_front_bumper = (ego_front_x <= obs.vcs_x <= ego_front_x + 1.80) and (abs(obs.vcs_y) <= cab_half_w + 0.30)
    if is_standstill and in_front_bumper and is_vru:
        d_front = max(0.10, obs.vcs_x - ego_front_x)
        # Tính TTC takeoff ảo với gia tốc đề-pa danh định 1.2 m/s^2
        ttc_takeoff = math.sqrt((2.0 * d_front) / 1.20)
        vru_w = self.VRU_WEIGHTS.get(obs.class_name.lower(), 0.85)
        raw_score = 1.00 * vru_w * 1.20 * 1.25  # S_spatial=1.0, V_blind=1.2, M_ego=1.25
        bsri = round(float(min(1.0, max(0.85, raw_score))), 3)
        exp = (
            f"KHẨN CẤP! [MOIS R159] {obs.class_name} #{obs.track_id} ĐỖ SÁT CẢN TRƯỚC ({d_front:.1f}m, "
            f"TTC đề-pa: {ttc_takeoff:.1f}s)! Mũi xe che khuất hoàn toàn!"
        )
        rec = "GIỮ CHẶT CHÂN PHANH! KHÔNG ĐƯỢC XUẤT PHÁT! BẤM CÒI CẢNH BÁO CHO ĐỐI TƯỢNG TRÁNH ĐƯỜNG!"
        return bsri, RiskLevel.CRITICAL, exp, rec

    # =========================================================================
    # ƯU TIÊN 3: KỊCH BẢN 2 - UNECE R151 BSIS (BẪY KẸP CUA SƯỜN PHẢI)
    # Nhận diện: Con quay IMU (yaw_rate < -0.03 rad/s) hoặc xe dừng/bò chậm VÀ có VRU ở bụng xe bên phụ
    # =========================================================================
    is_turning_right = (ego.yaw_rate_rad_s < -0.03) or (ego.turn_signal == "RIGHT")
    in_pinch_x = (ego_rear_x <= obs.vcs_x <= ego_front_x * 0.70)
    in_pinch_y = (-2.50 <= obs.vcs_y <= -cab_half_w)

    if (is_turning_right or (is_standstill and obs.distance_m < 2.0)) and in_pinch_x and in_pinch_y and is_vru:
        bsri = 0.850
        lateral_gap = abs(obs.vcs_y) - cab_half_w
        exp = (
            f"CẢNH BÁO KHẨN! [BẪY KẸP CUA R151] {obs.class_name} #{obs.track_id} dừng sát sườn phụ "
            f"(cách hông {lateral_gap:.1f}m)! Bánh sau sẽ chém trúng khi ôm cua!"
        )
        rec = "GIỮ PHANH CHỜ XE MÁY ĐI HẾT HOẶC MỞ RỘNG GÓC CUA! BẤM CÒI CẢNH BÁO!"
        return bsri, RiskLevel.CRITICAL, exp, rec

    # =========================================================================
    # ƯU TIÊN 4: KỊCH BẢN 4 - HIỆU ỨNG KHÍ ĐỘNG HỌC BERNOULLI (KẸP SƯỜN TỐC ĐỘ CAO)
    # Nhận diện: GPS chạy nhanh (v_ego >= 8.0 m/s), VRU áp sát hông (d_lat <= 0.8m) VÀ v_closing ~ 0
    # =========================================================================
    r = obs.distance_m
    v_clos = - (obs.vcs_x * obs.vel_x + obs.vcs_y * obs.vel_y) / max(0.1, r)
    d_lat = abs(obs.vcs_y) - cab_half_w
    in_flank_x = (ego_rear_x <= obs.vcs_x <= ego_front_x)
    if (ego.speed_mps >= 8.0) and (0.0 <= d_lat <= 0.80) and in_flank_x and is_vru and (abs(v_clos) <= 0.50):
        # Tính rủi ro khí động học áp sát ngang theo hàm mũ suy giảm
        s_lateral = math.exp(-max(0.0, d_lat) / 0.40)
        bsri = round(float(min(1.0, 0.65 + 0.35 * s_lateral)), 3)
        r_level = RiskLevel.CRITICAL if bsri >= 0.80 else RiskLevel.WARNING
        exp = (
            f"CẢNH BÁO! [KẸP SƯỜN TỐC ĐỘ CAO] {obs.class_name} #{obs.track_id} chạy áp sát sườn "
            f"({d_lat:.1f}m)! Nguy cơ chênh lệch áp suất gió hút ngã vào gầm!"
        )
        rec = "GIỮ VÔ-LĂNG THẲNG! TUYỆT ĐỐI KHÔNG ĐÁNH LÁI GẤP SANG PHẢI! GIẢM TỐC TỪ TỪ!"
        return bsri, r_level, exp, rec

    # =========================================================================
    # ƯU TIÊN 5: KỊCH BẢN 5 - CHE KHUẤT TẦM NHÌN GƯƠNG KHI VÀO CUA GẮT
    # Nhận diện: Con quay IMU quay gắt (|yaw_rate| > 0.08 rad/s) VÀ vật cản ở vùng hông phụ
    # =========================================================================
    is_sharp_turn = abs(ego.yaw_rate_rad_s) > 0.08
    if is_sharp_turn and (-2.50 <= obs.vcs_y <= -cab_half_w) and in_flank_x:
        bsri = 0.820
        exp = (
            f"CẢNH BÁO KHẨN! [MẤT GÓC GƯƠNG] Xe đang ôm cua gắt (tốc độ góc {abs(ego.yaw_rate_rad_s):.2f} rad/s) "
            f"che khuất gương phụ! Có {obs.class_name} #{obs.track_id} trong khe mù!"
        )
        rec = "CHÚ Ý QUAN SÁT! TRẢ BỚT LÁI ĐỂ MỞ RỘNG TẦM NHÌN!"
        return bsri, RiskLevel.CRITICAL, exp, rec

    # Không thỏa mãn kịch bản đặc biệt nào -> Trả về None để chạy công thức BSRI thông thường
    return None
```

---

## 5. Phân Cấp Cảnh Báo ADAS & Bộ Giải Thích Trực Quan (Explainable AI - XAI)

### 5.1. Bảng 4 cấp độ phân loại an toàn

| Điểm số BSRI | Cấp độ cảnh báo (`RiskLevel`) | Màu sắc HUD | Phản ứng hệ thống & Khuyến nghị tài xế |
| :---: | :---: | :---: | :--- |
| **$\text{BSRI} < 0.30$** | **AN TOÀN (SAFE)** | Xanh lá | Không có nguy cơ. Xe chạy bình thường. Không phát cảnh báo. |
| **$0.30 \le \text{BSRI} < 0.55$** | **CHÚ Ý (CAUTION)** | Vàng | Phương tiện tiếp cận gần góc mù. Bật đèn vàng HUD trên cabin. |
| **$0.55 \le \text{BSRI} < 0.80$** | **CẢNH BÁO (WARNING)** | Cam | Nguy cơ va chạm cao trong $2 - 3\text{s}$. Đèn cam nhấp nháy, rung vô lăng, rà nhẹ chân phanh, hoãn đánh lái. |
| **$\text{BSRI} \ge 0.80$** | **NGUY HIỂM KHẨN CẤP (CRITICAL)** | Đỏ rực | **VA CHẠM CẬN KỀ ($< 1.5\text{s}$) HOẶC ĐÃ LỌT VÀO VỆT QUÉT BÁNH XE! HÚ CÒI BÁO ĐỘNG + ĐẠP PHANH GẤP NGAY LẬP TỨC!** |

---

### 5.2. Cơ chế sinh câu giải trình tự động (XAI Engine)

Thay vì chỉ kêu "bíp bíp" như một hộp đen bí ẩn, BSRI tự động tạo chuỗi văn bản tiếng Việt giải thích lý do cảnh báo hiển thị trên thanh HUD phía dưới màn hình:

$$\text{Cấu trúc: } [\text{CẤP ĐỘ}] + [\text{Tên đối tượng \& ID}] + [\text{Lý do không gian}] + [\text{Lý do thời gian TTC}] + [\text{Khuyến nghị hành động}]$$

* **Ví dụ thực tế**:
  * *Dòng giải trình*: `KHẨN CẤP! Xe máy #20 đã XÂM NHẬP VÙNG QUÉT NGUY HIỂM (cách 3.5m tại Sườn phải thùng xe, TTC: 1.5s)!`
  * *Dòng khuyến nghị*: `-> PHANH GẤP NGAY LẬP TỨC! BẤM CÒI CẢNH BÁO!`

---

## 6. Bài Toán Mẫu Tính Tay Từng Bước Nhất Quán (Worked Example)

Để hiểu sâu sắc từng phép tính toán bên trong BSRI và đảm bảo mọi đại lượng đều được suy dẫn toán học nhất quán từ đầu vào, hãy theo dõi bài toán mẫu sau:

### 6.1. Dữ liệu đầu vào:
* **Loại xe**: Xe tải liền thân Chenglong H7 4 chân ($L = 10.2\text{m}, W = 2.5\text{m}, L_{wb} = 5.8\text{m}$, cản trước $X_{\text{front}} = 7.8\text{m}$, đuôi xe $X_{\text{rear}} = -2.4\text{m}$, nửa rộng $W/2 = 1.25\text{m}$).
* **Trạng thái xe chủ**:
  * $v_{\text{ego}} = 5.0\text{ m/s}$ ($18\text{ km/h}$, đang bò vào cua ngã tư).
  * $\omega_z = -0.06\text{ rad/s}$ (đang bẻ lái rẽ phải).
  * $a_x = -0.2\text{ m/s}^2$ (chưa đạp phanh).
* **Chướng ngại vật phát hiện**:
  * Đối tượng: Xe máy (`motorcycle`), ID `#20`.
  * Tọa độ VCS: $X = +2.4\text{m}, Y = -1.8\text{m}$ (ở sườn phải bên phụ xe tải).
  * Vector vận tốc di chuyển trong VCS: $vel_x = -1.6\text{ m/s}, vel_y = +1.2\text{ m/s}$ (xe máy đang di chuyển chéo áp sát về phía tâm xe).

---

### 6.2. Tính toán từng bước:

#### Bước 1: Tính khoảng cách hình học và kiểm tra xâm nhập DHZ
* Khoảng cách Euclid thẳng:
  $$r = \sqrt{X^2 + Y^2} = \sqrt{2.4^2 + (-1.8)^2} = \sqrt{5.76 + 3.24} = \sqrt{9.00} = \mathbf{3.00\text{ m}}$$
* Độ lấn cua sườn xe bên phải theo mô hình kinematic off-tracking:
  $$\Delta_{\text{off-tracking}} = \frac{L_{wb}^2 \cdot |\omega_z|}{2 \cdot v_{\text{ego}}} = \frac{5.8^2 \times 0.06}{2 \times 5.0} = \mathbf{0.20\text{ m}}$$
* Mép phải nguy hiểm của DHZ (kèm đệm an toàn khởi tạo $1.2\text{m}$):
  $$Y_{\text{border}} = -1.25\text{m (nửa rộng xe)} - 0.20\text{m (lấn lề)} - 1.20\text{m (đệm)} = \mathbf{-2.65\text{ m}}$$
* Xe máy ở $Y = -1.8\text{m}$, nằm lọt sâu bên trong biên $-2.65\text{m}$!
  $$\implies \text{Xe máy ĐÃ XÂM NHẬP VÙNG QUÉT NGUY HIỂM} \implies \mathbf{S_{\text{spatial}} = 1.00}$$

#### Bước 2: Tính Vận tốc tiếp cận và Thời gian va chạm (TTC) nhất quán
* Vận tốc tiếp cận hướng tâm được tính trực tiếp từ tọa độ và vận tốc:
  $$v_{\text{closing}} = - \frac{X \cdot vel_x + Y \cdot vel_y}{r} = - \frac{2.4 \times (-1.6) + (-1.8) \times 1.2}{3.00} = - \frac{-3.84 - 2.16}{3.00} = \frac{6.00}{3.00} = \mathbf{2.00\text{ m/s}}$$
* Thời gian tới va chạm được suy dẫn chính xác từ khoảng cách và vận tốc tiếp cận:
  $$TTC = \frac{r}{v_{\text{closing}}} = \frac{3.00\text{ m}}{2.00\text{ m/s}} = \mathbf{1.50\text{ giây}}$$
* Chuẩn hóa $S_{\text{temporal}}$ theo hàm thời gian (với $TTC_{\text{critical}} = 1.2\text{s}, TTC_{\text{warning}} = 3.5\text{s}$):
  $$S_{\text{temporal}} = 1.0 - 0.70 \times \left( \frac{1.50 - 1.20}{3.50 - 1.20} \right) = 1.0 - 0.70 \times \frac{0.30}{2.30} \approx 1.0 - 0.0913 = \mathbf{0.909}$$

#### Bước 3: Tra cứu các hệ số điều chỉnh ngữ cảnh
* Hệ số ưu tiên đối tượng: $C_{\text{vru}} = \mathbf{0.85}$ (nhóm xe máy).
* Phân vùng: Sườn phải xe tải (`SWEPT_PATH_RIGHT`) $\implies V_{\text{blind}} = \mathbf{1.25}$.
* Thao tác lái: Xe rẽ phải ($\omega_z < -0.03$) và xe máy ở bên phụ ($Y < 0$) $\implies M_{\text{ego}} = 1.0 \times 1.35 = \mathbf{1.35}$.

#### Bước 4: Tổng hợp điểm BSRI
* Điểm cơ sở kết hợp lồi:
  $$\text{Base Score} = 0.45 \times S_{\text{spatial}} + 0.55 \times S_{\text{temporal}} = 0.45 \times 1.00 + 0.55 \times 0.909 = 0.45 + 0.500 = \mathbf{0.950}$$
* Nhân với các hệ số điều chỉnh ngữ cảnh:
  $$\text{Raw BSRI} = 0.950 \times 0.85 \times 1.25 \times 1.35 \approx \mathbf{1.362}$$
* Giới hạn chuẩn hóa $[0.0, 1.0]$:
  $$\mathbf{BSRI} = \min(1.0, \, 1.362) = \mathbf{1.000} \implies \text{\textbf{NGUY HIỂM KHẨN CẤP (CRITICAL)}}$$

---

## 7. Hướng Dẫn Triển Khai Trong Mã Nguồn & Cấu Hình Thực Tế

### 7.1. Cấu trúc mã nguồn Phân hệ BSRI

```text
2_BlindSpot_Risk_Calculation/bsri_engine/
├── risk_models.py           # Định nghĩa cấu trúc dữ liệu: EgoVehicleState, TrackedObstacle, RiskLevel, VehicleType
├── bsri_calculator.py       # LÕI TOÁN HỌC: Class BSRICalculator (hỗ trợ cả RIGID và ARTICULATED, xoay rơ-moóc theo gamma)
├── demo_bsri_live.py        # Ứng dụng chạy Video trực quan với HUD cảnh báo thời gian thực
└── test_bsri.py             # Bộ 11 kịch bản Unit Test tự động bao phủ toàn diện (100% PASS)
```

---

### 7.2. Hướng dẫn gọi BSRICalculator trong code Python

#### Ví dụ 1: Cấu hình cho Xe tải liền thân (Rigid Truck)
```python
from bsri_calculator import BSRICalculator
from risk_models import EgoVehicleState, TrackedObstacle, VehicleType

# 1. Khởi tạo BSRI Engine với cấu hình xe tải liền thân
bsri_calc = BSRICalculator(
    vehicle_type="RIGID",        # Loại xe: "RIGID"
    rigid_front_length=7.8,      # Khoảng cách từ tâm trục sau tới cản trước (m)
    rigid_rear_length=2.4,       # Khoảng cách từ tâm trục sau tới cản sau (m)
    rigid_width=2.5,             # Chiều rộng thùng xe (m)
    rigid_wheelbase=5.8          # Chiều dài cơ sở (m)
)

# 2. Khai báo trạng thái xe chủ từ IMU và GPS (Không cần CAN bus hay công tắc cơ)
ego_state = EgoVehicleState(
    speed_mps=5.0,               # Vận tốc 18 km/h từ GPS
    yaw_rate_rad_s=-0.06,        # Tốc độ quay từ Gyroscope IMU (< 0: xe đang bẻ lái rẽ phải)
    vehicle_type="RIGID"
)

# 3. Tạo danh sách các đối tượng theo dõi được từ Module 1
obstacles = [
    TrackedObstacle(
        track_id=20,
        class_name="motorcycle",
        confidence=0.88,
        bbox_xyxy=(500, 300, 560, 450),
        vcs_x=2.4,               # Tọa độ X (mét)
        vcs_y=-1.8,              # Tọa độ Y (mét)
        vel_x=-1.6,
        vel_y=1.2
    )
]

# 4. Đánh giá toàn cảnh hiện trường
all_results, highest_threat = bsri_calc.evaluate_scene(ego_state, obstacles)

# 5. Đọc kết quả
print(f"Đối tượng nguy hiểm nhất: ID #{highest_threat.track_id} ({highest_threat.class_name})")
print(f"Điểm BSRI: {highest_threat.bsri_score:.2f}")
print(f"Cấp độ cảnh báo: {highest_threat.risk_level.label_vi}")
print(f"Giải thích XAI: {highest_threat.explanation}")
print(f"Khuyến nghị: {highest_threat.recommendation}")
```

#### Ví dụ 2: Cấu hình cho Xe đầu kéo sơ-mi rơ-moóc (Articulated Truck)
```python
bsri_calc = BSRICalculator(
    vehicle_type="ARTICULATED",
    wheelbase_tractor=3.6,
    cab_width=2.5,
    trailer_length=12.0,
    trailer_width=2.5
)
```

---

### 7.3. Lệnh chạy Demo Video trực quan thời gian thực

Mở PowerShell tại thư mục gốc của dự án và chạy:

```powershell
.\2_BlindSpot_Risk_Calculation\.venv\Scripts\python.exe 2_BlindSpot_Risk_Calculation/bsri_engine/demo_bsri_live.py --vehicle-type RIGID
```

#### Các phím tắt tương tác trên cửa sổ hiển thị:
* <kbd>V</kbd>: **Chuyển đổi tức thì loại kiến trúc xe** (`RIGID` $\longleftrightarrow$ `ARTICULATED`) để quan sát đa giác DHZ tự động biến đổi thời gian thực.
* <kbd>T</kbd>: **Đổi tuần hoàn chế độ lái từ cảm biến IMU** (`RẼ PHẢI` $\omega_z < 0 \rightarrow$ `RẼ TRÁI` $\omega_z > 0 \rightarrow$ `ĐI THẲNG` $\omega_z = 0$) để xem điểm BSRI tự động đổi màu.
* <kbd>SPACE</kbd>: **Tạm dừng / Tiếp tục video** để soi chi tiết tọa độ mét $[X, Y]$ và chỉ số TTC của từng vật thể.
* <kbd>Q</kbd> hoặc <kbd>ESC</kbd>: **Thoát chương trình**.

---

### 7.4. Chạy kiểm thử tự động (Unit Test)

```powershell
.\2_BlindSpot_Risk_Calculation\.venv\Scripts\python.exe 2_BlindSpot_Risk_Calculation/bsri_engine/test_bsri.py
```

Bộ kiểm thử bao gồm **11 bài test tự động bao phủ toàn bộ trường hợp cơ sở và 5 kịch bản đặc biệt**:
1. **Test 1**: Người đi bộ tại điểm mù hông phụ khi xe rẽ phải $\rightarrow$ `CRITICAL` [PASS].
2. **Test 2**: Ô tô con chạy song song ở cự ly xa $\rightarrow$ `SAFE` (Zero False Alarm) [PASS].
3. **Test 3**: Xe máy tiếp cận nhanh từ phía sau (TTC thấp) $\rightarrow$ `CRITICAL` [PASS].
4. **Test 4**: Xe kéo (`xe_keo`) trong vùng lấn lề $\rightarrow$ `WARNING` [PASS].
5. **Test 5**: Đánh giá toàn cảnh đa đối tượng, trích xuất mối đe dọa cao nhất $\rightarrow$ [PASS].
6. **Test 6**: Xe tải liền thân 4 chân (Chenglong H7 10.2m) lấn cua sườn phải $\rightarrow$ `CRITICAL` [PASS].
7. **Test 7 (Case 1)**: Dừng đèn đỏ & Xe máy đỗ sát cản trước (Moving-Off Front Hazard) $\rightarrow$ `CRITICAL` [PASS].
8. **Test 8 (Case 2)**: Dừng chờ ôm cua & Xe máy lọt bẫy kẹp sườn (Turning Pinch Hazard) $\rightarrow$ `CRITICAL` [PASS].
9. **Test 9 (Case 3)**: Lùi xe tại bến bãi có chướng ngại vật sau đuôi (Reversing Hazard) $\rightarrow$ `CRITICAL` [PASS].
10. **Test 10 (Case 4)**: Chạy song song tốc độ cao áp sát sườn (Parallel Close-Proximity Hazard) $\rightarrow$ `CRITICAL/WARNING` [PASS].
11. **Test 11 (Case 5)**: Thân xe ôm cua gắt che khuất tầm nhìn gương phụ $\rightarrow$ `CRITICAL` [PASS].

**Kết quả: 11/11 bài kiểm thử đều vượt qua xuất sắc (Exit code 0)!**

---

## 8. Bảng Nguồn Gốc Tham Số (Parameter Provenance Matrix)

Nhằm đảm bảo tính minh bạch học thuật và giải trình trước hội đồng chuyên môn, mọi biến số và tham số trong hệ thống BSRI đều được phân loại rõ nguồn gốc theo bảng dưới đây:

| Ký hiệu biến / Tham số | Ý nghĩa kỹ thuật | Nguồn gốc dữ liệu / Cơ sở xác định | Phân loại tham số |
| :--- | :--- | :--- | :--- |
| **$v_{\text{ego}}$** | Vận tốc di chuyển dọc của xe chủ (m/s) | Module GPS / GNSS (đo trực tiếp) | **Sensor-measured** |
| **$\omega_z$** | Vận tốc góc xoay quanh trục đứng (rad/s) | Gyroscope IMU 6-DOF (đo trực tiếp) | **Sensor-measured** |
| **$a_x, a_y$** | Gia tốc dọc và ngang của xe chủ ($\text{m/s}^2$) | Accelerometer IMU 6-DOF (đo trực tiếp) | **Sensor-measured** |
| **$X_{\text{vcs}}, Y_{\text{vcs}}$** | Tọa độ mặt đất của vật cản trong VCS (m) | Camera AI + ByteTrack + Ma trận Homography mặt phẳng đường | **Algorithm-derived** |
| **$vel_x, vel_y$** | Vector vận tốc tương đối trong VCS (m/s) | ByteTrack Kalman Filter qua sai phân thời gian liên khung hình | **Algorithm-derived** |
| **$v_{\text{closing}}$** | Vận tốc tiếp cận hướng tâm (m/s) | Tính hình học: $-(X \cdot vel_x + Y \cdot vel_y) / r$ | **Algorithm-derived** |
| **$TTC$** | Thời gian tới va chạm giả định thẳng (s) | Tính hình học: $r / v_{\text{closing}}$ | **Algorithm-derived** |
| **$\gamma$** | Góc gập rơ-moóc xe đầu kéo (rad) | Mô hình vi phân Single-Track ước lượng từ $\omega_z, v_{\text{ego}}, L_{\text{trail}}$ | **Estimated State** |
| **$L_{wb}, L_{\text{trail}}, W_c, W_{\text{trail}}$** | Kích thước cơ sở và hình học thân xe (m) | Sổ đăng kiểm xe & Thước dây đo thực tế | **Vehicle Configuration** |
| **$X_{\text{front}}, X_{\text{rear}}$** | Tọa độ mép cản trước và cản sau trong VCS (m) | Cấu hình hình học xe đo thực tế | **Vehicle Configuration** |
| **$T_{\text{preview}} = 0.5\text{s}$** | Khoảng thời gian dự đoán candidate DHZ | Thiết kế khoanh vùng ngắn hạn của nhóm Nova $\to$ Cần calibration | **Engineering / Calibration** |
| **$S_{\text{max}} = 12\text{m}$** | Chiều dài giới hạn tối đa của đa giác DHZ | Giới hạn bao nhằm ngăn đa giác phình to ở tốc độ cao $\to$ Cần calibration | **Engineering / Calibration** |
| **$\text{buffer} = 1.0\text{m}$** | Khoảng đệm an toàn mở rộng quanh đa giác | Khoảng hở an toàn hình học ban đầu $\to$ Cần calibration test track | **Engineering / Calibration** |
| **$d_0 = 1.8\text{m}$** | Hằng số suy giảm hàm mũ khoảng cách biên | Ước lượng từ khổ làn đường và làn xe máy $\to$ Cần calibration | **Engineering / Calibration** |
| **$w_s = 0.45, w_t = 0.55$** | Trọng số rủi ro không gian và thời gian | Thiết kế ưu tiên động học TTC nhằm giảm báo động giả $\to$ Grid Search | **Engineering / Calibration** |
| **$C_{\text{vru}}$** | Hệ số ưu tiên bảo vệ theo phân lớp đối tượng | Thiết kế ban đầu theo đặc thù giao thông VN $\to$ Cần dataset calibration | **Engineering / Calibration** |
| **$V_{\text{blind}}$** | Hệ số khuếch đại rủi ro theo góc mù | Ước lượng mức độ che khuất tầm nhìn $\to$ Cần calibration | **Engineering / Calibration** |
| **$M_{\text{ego}}$** | Hệ số điều chỉnh hành vi lái của xe chủ | Thiết kế rủi ro theo thao tác rẽ/lùi/phanh $\to$ Cần calibration | **Engineering / Calibration** |
| **$TTC_{\text{critical}} = 1.2\text{s}$** | Ngưỡng rủi ro thời gian cực hạn ($S_t = 1.0$) | Tổng PRT lái xe ($0.8\text{s}$) + Độ trễ phanh khí nén ($0.4\text{s}$) $\to$ Calibration | **Engineering / Calibration** |
| **$TTC_{\text{warning}} = 3.5\text{s}$** | Ngưỡng rủi ro thời gian cảnh báo sớm | Thời gian quan sát gương và chuẩn bị giảm tốc $\to$ Calibration | **Engineering / Calibration** |
| **$\tau_{\text{decay}} = 3.0\text{s}$** | Hằng số suy giảm hàm mũ cho cự ly xa | Làm mượt đường cong rủi ro thời gian $\to$ Calibration | **Engineering / Calibration** |

---

## 9. Bảng Tài Liệu Tham Khảo (Reference Standards & Literature)

| Ký hiệu | Tên tài liệu / Tiêu chuẩn | Liên kết nguồn chính thức (Official Link) | Phạm vi hỗ trợ trong dự án BlindGuard AI | Phạm vi KHÔNG dùng để khẳng định |
| :---: | :--- | :---: | :--- | :--- |
| **[R1]** | **ISO 8855:2011** — *Road vehicles — Vehicle dynamics and road-holding ability — Vocabulary* | [Trang chuẩn ISO 8855](https://www.iso.org/standard/51180.html) | Định nghĩa hệ tọa độ xe (Vehicle Coordinate System - VCS) và chiều dương các trục ($X$ tiến, $Y$ trái, $Z$ lên). | Không quy định vị trí đặt gốc $(0,0)$ cụ thể của dự án và không quy định trọng số BSRI. |
| **[R2]** | **SAE J670_202206** — *Vehicle Dynamics Terminology* | [Trang chuẩn SAE J670](https://www.sae.org/standards/content/j670_202206/) | Thuật ngữ động học phương tiện, hệ trục tọa độ bánh xe và góc bẻ lái. | Không quy định các ngưỡng kích hoạt cảnh báo của BSRI. |
| **[R3]** | **UN Regulation No. 151** — *Blind Spot Information System for the Detection of Bicycles (BSIS)* | [Văn bản UNECE R151](https://unece.org/transport/vehicle-regulations/un-regulation-no-151-blind-spot-information-system-detection-bicycles) | Bối cảnh an toàn và yêu cầu cảnh báo điểm mù sườn xe bên phụ khi rẽ. | Tiêu chuẩn chỉ áp dụng cho xe đạp; việc BlindGuard mở rộng sang xe máy là thiết kế riêng của dự án. |
| **[R4]** | **UN Regulation No. 159** — *Moving Off Information System (MOIS)* | [Văn bản UNECE R159](https://unece.org/transport/vehicle-regulations/un-regulation-no-159-moving-off-information-system) | Bối cảnh an toàn phát hiện người đi bộ và xe đạp ở vùng mù cản trước khi khởi hành tốc độ thấp ($\le 10\text{km/h}$). | Không quy định phát hiện xe máy; BlindGuard mở rộng sang xe máy theo đặc thù giao thông Việt Nam. |
| **[R5]** | **UN Regulation No. 158** — *Devices for Means of Rear Visibility or Detection* | [Văn bản UNECE R158](https://unece.org/transport/vehicle-regulations/un-regulation-no-158-devices-means-rear-visibility-or-detection) | Bối cảnh an toàn quan sát và phát hiện chướng ngại vật phía sau khi lùi xe. | Không quy định điểm BSRI $= 0.95$ hay ngưỡng ứng viên $2.5\text{m}$ của nhóm. |
| **[R6]** | **UN Regulation No. 46** — *Devices for Indirect Vision* | [Văn bản UNECE R46](https://unece.org/transport/vehicle-regulations/un-regulation-no-46-devices-indirect-vision) | Định nghĩa các vùng quan sát gián tiếp qua gương chiếu hậu Class I đến Class VI. | Không quy định các hệ số nhân $V_{\text{blind}} = 1.25, 1.20, 1.10$. |
| **[R7]** | **ISO 15623:2013** — *Forward Vehicle Collision Warning Systems* | [Trang chuẩn ISO 15623](https://www.iso.org/standard/56381.html) | Khái niệm và nguyên lý cảnh báo va chạm sớm phía trước dựa trên thời gian tới va chạm (TTC). | Không quy định công thức tổ hợp BSRI hay trọng số của nhóm. |
| **[R8]** | **ISO 15622:2018** — *Adaptive Cruise Control Systems (ACC)* | [Trang chuẩn ISO 15622](https://www.iso.org/standard/70073.html) | Khung tham chiếu về hệ thống điều khiển hành trình thích ứng và tương tác người lái. | Không dùng làm nguồn quy định trực tiếp cho ngưỡng TTC $1.2\text{s}$ hay $3.5\text{s}$ của BSRI. |
| **[R9]** | **ISO 22839:2013** — *Forward Vehicle Collision Mitigation Systems* | [Trang chuẩn ISO 22839](https://www.iso.org/standard/51624.html) | Khái niệm giảm thiểu va chạm phía trước và ảnh hưởng của thao tác phanh chủ động. | Không quy định các hệ số phanh định hướng $0.85$ và $1.25$ của nhóm. |
| **[R10]** | **Euro NCAP VRU Test Protocol (v4.5.1)** | [Euro NCAP VRU Protocol](https://www.euroncap.com/en/for-engineers/protocols/vulnerable-road-user-vru-protection/) | Quy trình kịch bản thử nghiệm đối tượng yếu thế (Pedestrian, Cyclist, Motorcyclist). | Không cung cấp bảng trọng số số học $C_{\text{vru}} = 1.00$ cho thuật toán BSRI. |
| **[R11]** | **FHWA — Low-Speed Offtracking** | [Tài liệu FHWA DOT](https://ops.fhwa.dot.gov/freight/publications/size_regs_final_rule/) | Khái niệm và mô hình quỹ đạo lấn lề (Off-tracking / Inswing) của xe tải nặng và rơ-moóc. | Không quy định công thức BSRI. |
| **[R12]** | **S. M. LaValle — Planning Algorithms (Ch. 13)** | [Cambridge University Press / UIUC Ch.13](https://planning.cs.uiuc.edu/node660.html) | Mô hình động học vi phân của hệ xe kéo và rơ-moóc xoay quanh khớp nối hitch: $\dot{\gamma} = \omega_z - \frac{v}{L_t}\sin\gamma$. | Không quy định các ngưỡng kích hoạt của BSRI. |
| **[R13]** | **Eggert & Puphal (2023)** — *Continuous Risk Measures for Driving Support* | [Bản in điện tử arXiv:2303.08007](https://arxiv.org/abs/2303.08007) | Khái niệm đo lường rủi ro liên tục dựa trên không gian chiếm dụng (spatial occupancy) và thời gian (TTC/TTCE). | Bài báo nghiên cứu tham khảo, không phải tiêu chuẩn bắt buộc. |
| **[R14]** | **Tang et al. (2023)** — *Right-Hook Turn Blind Spot Alert System for Semi-Trailer Trucks* | [Bản in điện tử arXiv:2303.11223](https://arxiv.org/abs/2303.11223) | Nghiên cứu về rủi ro va chạm điểm mù sườn phụ khi xe đầu kéo rẽ phải. | Bối cảnh nghiên cứu tham khảo. |
| **[R15]** | **TCVN 4054:2005** — *Đường ô tô — Yêu cầu thiết kế* | [Văn bản pháp luật TCVN 4054](https://vanbanphapluat.co/tcvn-4054-2005-duong-o-to-yeu-cau-thiet-ke) | Kích thước bề rộng làn đường tiêu chuẩn ($3.5\text{m}$) và xe thiết kế tại Việt Nam. | Không suy ra trực tiếp khoảng đệm an toàn hay hằng số suy giảm của BSRI. |

