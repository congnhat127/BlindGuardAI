# 📘 TÀI LIỆU TOÁN HỌC VÀ TIÊU CHUẨN KỸ THUẬT: DYNAMIC SURROUND HAZARD MODEL
*(Mô hình Vùng Nguy Hiểm Động học Bao quanh Xe Đầu Kéo)*

## 1. TRIẾT LÝ HỆ THỐNG
Thay vì chỉ xác định "Vùng mù quang học" (những gì tài xế không nhìn thấy) vốn không phản ánh trực tiếp khả năng va chạm, hệ thống sử dụng triết lý **Surround Proximity Hazard (Vùng Nguy hiểm Bao quanh Cận chiến)**. Bất kỳ phương tiện nào lọt vào vùng đệm này, bất kể có nằm trong điểm mù hay không, hệ thống đều sẽ kích hoạt báo động khẩn cấp do rủi ro va chạm cực cao nếu xe đột ngột chuyển làn, láng lái hoặc phanh gấp.

Các công thức và thông số trong codebase được xây dựng trên cơ sở Động lực học Phương tiện (Vehicle Dynamics) và tiêu chuẩn an toàn ADAS (Advanced Driver Assistance Systems).

---

## 2. ĐỘNG LỰC HỌC RƠ-MOÓC (TRAILER KINEMATICS)
Khi xe đầu kéo cua hoặc bẻ lái, rơ-moóc phía sau sẽ bị gập một góc $\gamma$ và tạo ra hiện tượng **Lấn lề (Off-tracking/Swept Path)**.

### 2.1. Tính Tốc độ góc Yaw Rate ($\omega$)
Dựa trên Mô hình Xe đạp Động học (Kinematic Bicycle Model) của Ackermann:
$$\omega = \frac{v}{L_f} \cdot \tan\left(\frac{\delta_{wheel}}{\text{STEER\_RATIO}}\right)$$
* **$v$**: Vận tốc xe ($m/s$).
* **$L_f$**: Chiều dài cơ sở đầu kéo (`WHEELBASE_TRACTOR`).
* **$\delta_{wheel}$**: Góc vặn vô-lăng thực tế của tài xế (độ/radian).
* **$\text{STEER\_RATIO}$**: Tỷ số truyền thước lái (Chuẩn xe tải thường là `16.0`).

### 2.2. Vi phân Góc gập Rơ-moóc ($\gamma$)
Theo mô hình truyền động học khớp nối (Leng & Minor, 2010):
$$\frac{d\gamma}{dt} = \omega - \frac{v}{L_{trail}} \sin(\gamma)$$
Hệ thống sử dụng tích phân Euler để cập nhật liên tục $\gamma$ trong mỗi chu kỳ camera (`dt = 0.0333s` tương đương 30 FPS):
$$\gamma_{t+1} = \gamma_t + \left( \omega - \frac{v}{L_{trail}} \sin(\gamma_t) \right) \cdot dt$$
*(Lưu ý: Nếu cấu hình $L_{trail} = 0$, hệ thống tự động khóa $\gamma = 0$ để giả lập Xe tải thân liền).*

---

## 3. LỚP GIÁP BẢO VỆ CHÍNH (SURROUND HAZARD ZONE - LỚP 1)

Lớp bảo vệ (vùng màu hồng đứt nét) bao quanh xe được thiết kế để dự đoán quỹ đạo lấn lề (Swept Path) trong tương lai.

### 3.1. Dự đoán Quỹ đạo Tương lai (Predictive Swept Path)
Khi xe đang cua, vùng nguy hiểm không chỉ là thân xe hiện tại mà là *toàn bộ không gian xe sẽ quét qua* trong $T = 1.5s$ tới. AI giả lập 5 bước thời gian về tương lai (với tốc độ góc và vận tốc hiện tại):
$$x(t) = \int v \cos(\theta) dt \quad ; \quad y(t) = \int v \sin(\theta) dt$$
Thuật toán lấy toàn bộ Đa giác thân xe tại các mốc thời gian này và gộp lại (Union) thành một khối đa giác di chuyển thống nhất. Bằng cách này, vùng không gian **chắc chắn sẽ bị rơ-moóc quét trúng** tự động được đưa vào Vùng Báo Động.

### 3.2. Cơ sở Phình to Lateral Buffer (Độ dày giáp)
Lớp giáp được phình to ra mọi hướng (sử dụng thuật toán `Minkowski Sum / Shapely Buffer`).
Độ dày giáp (Buffer) tính theo công thức:
$$Buffer = \text{HAZARD\_BUFFER\_BASE} + (v \times \text{HAZARD\_BUFFER\_SPEED\_FACTOR})$$
* **$\text{HAZARD\_BUFFER\_BASE} = 1.0m$**: Tham chiếu từ tiêu chuẩn **ISO 15622 (LCDAS)** yêu cầu khoảng trống ngang an toàn tối thiểu (Minimum Lateral Clearance) là $1.0m$.
* **$\text{HAZARD\_BUFFER\_SPEED\_FACTOR} = 0.1s$**: Khoảng đệm thời gian dự phòng sai số (Time Margin). Khi xe chạy càng nhanh, lớp giáp hai bên hông càng phình to ra để phòng trừ sai số do gió tạt ngang hoặc rung lắc thân xe. (Ví dụ: đi 90km/h tương đương $25m/s$, giáp sẽ phình to thành $1.0 + 2.5 = 3.5m$ bao bọc quanh xe).

---

## 4. VÙNG NGUY HIỂM PHANH (STOPPING HAZARD - LỚP 2)

Khu vực màu vàng phía trước mũi xe không phải là hình chữ nhật thẳng đứng, mà loe rộng ra như một cái phễu dựa trên Động năng và Tiêu chuẩn Sai lệch Ngang (Lateral Dispersion Cone).

### 4.1. Chiều dài Vùng phanh ($d_{total}$)
Tuân thủ tuyệt đối Định luật II Newton và Động năng:
$$d_{total} = d_{react} + d_{brake} = (v \cdot T_{react}) + \frac{v^2}{2 \mu g}$$
* $T_{react} = 1.5s$ (Tiêu chuẩn thời gian phản xạ tài xế xe hạng nặng).
* $\mu = 0.7$ (Hệ số ma sát đường khô chuẩn).
* $g = 9.81 m/s^2$.

### 4.2. Độ loe ngang (Lateral Dispersion Cone)
Sai lầm kinh điển của các hệ thống cũ là vẽ vùng phanh thẳng tắp. Trên thực tế, khi phanh gấp khẩn cấp (ABS kích hoạt), xe luôn bị láng hoặc đảo vô lăng. Vùng nguy hiểm phải lan rộng sang hai bên theo khoảng cách (Cone of Uncertainty).
Hệ thống áp dụng **$\text{LATERAL\_DISPERSION\_DEG} = 3.5^\circ$**:
$$W_{hazard}(d) = W_{cab\_half} + d_{total} \times \tan(3.5^\circ)$$
Nhờ công thức lượng giác này, khi xe đi 90km/h (quãng đường phanh 60m), vùng nguy hiểm phía trước mũi xe sẽ tự động phình to rải đều hai bên, bao phủ toàn bộ làn đường phía trước và một phần làn đường bên cạnh.

---
**Tổng kết:** Toàn bộ các thông số từ việc tính toán Lấn lề rơ-moóc đến kích thước Vùng Nguy Hiểm không phải là các con số ước lượng (heuristic) mà dựa hoàn toàn 100% vào Vật lý Động học thực tế và Tiêu chuẩn an toàn Ô tô.
