# BlindGuard AI — Vùng nguy hiểm động từ GPS và IMU

## 1. Mục tiêu và phạm vi

**Dynamic Hazard Zone — DHZ (Vùng nguy hiểm động)** là vùng không gian quanh xe cần được đặc biệt cảnh giác do hình học và trạng thái chuyển động hiện tại của chính xe. DHZ được tính trước, kể cả khi đường hoàn toàn không có người hay phương tiện khác:

```text
DHZ = f(GPS/GNSS, IMU, thông số hình học xe)
```

- **GPS/GNSS (Hệ thống định vị vệ tinh):** cung cấp vận tốc xe.
- **IMU — Inertial Measurement Unit (Khối đo quán tính):** cung cấp tốc độ quay và gia tốc.
- **Vehicle geometry (Thông số hình học xe):** chiều dài, chiều rộng, chiều dài cơ sở, vị trí chốt kéo và kích thước rơ-moóc.

DHZ trả lời: **“Với trạng thái vận hành hiện tại, vùng nào quanh xe cần được đặc biệt cảnh giác?”** DHZ không trả lời có chắc chắn sắp va chạm hay không.

**Blind-Spot Risk Index — BSRI (Chỉ số rủi ro điểm mù)** là tầng xử lý khác:

```text
BSRI = f(DHZ, vị trí/vận tốc/quỹ đạo đối tượng,
         TTC/PET, khả năng quan sát, loại đối tượng)
```

- **Object (Đối tượng):** người đi bộ, xe đạp, xe máy hoặc phương tiện khác.
- **TTC — Time To Collision (Thời gian còn lại tới va chạm).**
- **PET — Post-Encroachment Time (Khoảng thời gian giữa hai lượt chiếm cùng vùng xung đột).**

DHZ không sử dụng camera (máy ghi hình), YOLO (mô hình phát hiện đối tượng thời gian thực), đối tượng, TTC, PET hay BSRI. Tài liệu này chỉ mô tả DHZ.

## 2. Công thức tổng quát

```text
DHZ = Buffer(P_swept, C)
P_swept = Union(P_vehicle(t)), 0 <= t <= T
C = C0 + C_dynamic
```
Trong đó:

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `P_vehicle(t)` | **Vehicle footprint (Hình chiếu diện tích thân xe xuống mặt đường)** tại thời điểm `t` | m² |
| `P_swept` | **Swept occupancy (Vùng chiếm dụng quét):** hợp của các hình chiếu thân xe trong thời gian dự đoán | m² |
| `Buffer(P,C)` | **Phép nở vùng:** mở rộng biên đa giác `P` ra ngoài một khoảng `C` | — |
| `C0` | **Base clearance (Khoảng đệm cơ sở)** | m |
| `C_dynamic` | **Dynamic clearance (Khoảng đệm động)** | m |
| `T` | **Prediction horizon (Khoảng thời gian dự đoán)** | s |
| `DHZ` | Vùng chiếm dụng quét sau khi cộng khoảng đệm vật lý | m² |

Mô hình có hai thành phần:

1. `P_swept` trả lời **xe sẽ quét qua đâu** nếu trạng thái GPS/IMU hiện tại tiếp tục trong thời gian ngắn.
2. `C` trả lời **cần chừa thêm bao nhiêu khoảng đệm** do sai số cơ sở và phần động học ngang mà mô hình quay lý tưởng chưa giải thích.

## 3. Hệ tọa độ và quy ước dấu

**VCS — Vehicle Coordinate System (Hệ tọa độ gắn với xe)** tại thời điểm hiện tại:

- Gốc `(0,0)`: tâm trục sau đầu kéo.
- Trục `X+`: hướng tiến của đầu kéo.
- Trục `Y+`: bên trái đầu kéo.
- `ψ > 0`: đầu kéo quay ngược chiều kim đồng hồ, tức quay trái.
- `r = dψ/dt > 0`: đầu kéo đang tăng góc hướng về bên trái.
- `v > 0`: xe đi tiến; `v < 0`: xe đi lùi; `v=0`: đứng yên.
- `a_x > 0`: gia tốc hướng `X+`; `a_x < 0`: gia tốc hướng `X-`. Khi xe đang lùi, `a_x>0` làm xe lùi chậm lại chứ không phải tăng độ lớn vận tốc.
- `a_y > 0`: gia tốc ngang hướng sang trái.
- `γ = ψ_tractor - ψ_trailer`: góc gập giữa đầu kéo và rơ-moóc.

Mọi khoảng cách dùng mét, thời gian dùng giây, vận tốc dùng m/s và góc nội bộ dùng radian. Giao diện có thể hiển thị km/h và độ nhưng phải đổi đơn vị trước khi tính.

## 4. Đầu vào GPS/IMU

| Đại lượng | Nguồn | Ý nghĩa | Đơn vị trong công thức |
|---|---|---|---:|
| `v0` | GPS/GNSS + hướng thân xe | Vận tốc dọc có dấu: dương khi tiến, âm khi lùi | m/s |
| `r` | IMU | **Yaw rate (Tốc độ quay quanh trục đứng)** của đầu kéo | rad/s |
| `a_x` | IMU | **Longitudinal acceleration (Gia tốc dọc)** | m/s² |
| `a_y` | IMU | **Lateral acceleration (Gia tốc ngang)** | m/s² |

IMU phải được hiệu chỉnh độ lệch không, loại thành phần trọng lực và đổi về hệ tọa độ xe. GPS và IMU phải được **time synchronization (đồng bộ thời gian)** và lọc nhiễu trước khi đưa vào bộ tính.

GPS thường trả vector vận tốc theo hệ tọa độ thế giới, không trực tiếp trả “tốc độ âm”. Vận tốc dọc có dấu được chiếu lên trục tiến của xe:

```text
v0 = v_GNSS,x cosψ + v_GNSS,y sinψ
```

`v_GNSS,x`, `v_GNSS,y` là hai thành phần vector vận tốc GNSS; `ψ` là hướng thân đầu kéo. Khi xe lùi, vector chuyển động ngược hướng thân nên tích vô hướng trên âm. Gần `v=0`, GNSS không xác định hướng chuyển động tin cậy; hệ thống thật nên dùng thêm tín hiệu số tiến/lùi của xe để xác nhận.

Bốn thanh trượt trong `demo_dynamic_zone_v2.py` chính là bốn đại lượng trên. `r` không phải góc gập `γ`; nó là tốc độ thay đổi góc hướng của đầu kéo.

## 5. Thông số hình học xe

| Ký hiệu | Biến cấu hình | Ý nghĩa | Giá trị minh họa |
|---|---|---|---:|
| `L_f` | `WHEELBASE_TRACTOR` | Chiều dài cơ sở đầu kéo | 3,60 m |
| `W_c` | `CAB_WIDTH` | Chiều rộng cabin | 2,50 m |
| `L_body` | `L_TRAIL` | Chiều dài thân rơ-moóc để dựng đa giác | 12,00 m |
| `W_t` | `W_TRAIL` | Chiều rộng thân rơ-moóc | 2,50 m |
| `L_t` | `TRAILER_KINGPIN_TO_AXLE` | Khoảng cách chốt kéo tới tâm cụm trục rơ-moóc | 8,00 m |
| `M` | `D_HITCH` | Độ lệch chốt kéo về trước so với tâm trục sau đầu kéo | 0,288 m |
| `γ_max` | `MECHANICAL_MAX_GAMMA_DEG` | Giới hạn cơ khí của góc gập | ±65° |

Các đa giác cơ sở được dựng từ các tọa độ góc:

```text
P_cab = {(CAB_FRONT_X, ±CAB_HALF_W),
         (CAB_REAR_X,  ±CAB_HALF_W)}
trail_front = D_HITCH + TRAIL_OVERHANG
trail_rear  = D_HITCH - L_body
P_trailer = {(trail_front, ±TRAIL_HALF_W),
             (trail_rear,  ±TRAIL_HALF_W)}
```

Các kích thước phụ hiện được suy ra trong `config.py`:

```text
CAB_HALF_W      = W_c/2
TRAIL_HALF_W    = W_t/2
CHASSIS_HALF_W  = 0.18 W_c
CAB_FRONT_X     = L_f + 0.40
CAB_REAR_X      = 0.61 L_f
D_HITCH = M     = 0.08 L_f
TRAIL_OVERHANG  = 0.25 L_f
```

Các hệ số `0,18`, `0,61`, `0,08`, `0,25` và phần nhô `0,40 m` chỉ phục vụ dựng hình xe minh họa; chúng không phải tỉ lệ tiêu chuẩn hay kết quả nghiên cứu. Khi có xe thật phải nhập trực tiếp số đo thay vì tiếp tục suy ra bằng các hệ số này.

`L_body` và `L_t` không được dùng thay nhau: `L_body` dựng hình thân xe, còn `L_t` nằm trong phương trình động học rơ-moóc. Tất cả giá trị hiện là số liệu minh họa và phải được thay bằng số đo xe thật.

## 6. Dự đoán vận tốc dọc

Trong khoảng dự đoán ngắn, mã nguồn giả sử `a_x` không đổi:

```text
v(t) = v0 + a_x t
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `v0` | Vận tốc dọc có dấu ở đầu khoảng dự đoán | m/s |
| `a_x` | Gia tốc dọc có dấu đo bởi IMU | m/s² |
| `t` | Thời gian tính từ hiện tại | s |

**Lý do sử dụng:** đây là công thức chuyển động thẳng biến đổi đều từ động học Newton. Trong khoảng `T = 0,50 s`, giả thiết gia tốc không đổi đủ đơn giản để tính thời gian thực và tốt hơn giả thiết vận tốc luôn không đổi.

Để không tự suy diễn xe đổi từ số tiến sang số lùi (hoặc ngược lại), nếu `v(t)` chạm 0 trong horizon thì mã nguồn dừng dự đoán tại thời điểm đó. Muốn dự đoán qua thời điểm đổi chiều phải có thêm trạng thái hộp số/ý định điều khiển.

Độ dài vệt quét và độ dịch chuyển có dấu là hai đại lượng khác nhau:

```text
s_path = integral(|v(t)| dt), 0 <= t <= T
s_signed = integral(v(t) dt), 0 <= t <= T
```

- `s_path >= 0`: tổng chiều dài quãng đường đã quét.
- `s_signed > 0`: dịch chuyển chủ yếu về phía trước; `s_signed < 0`: dịch chuyển chủ yếu về phía sau.

Nếu xe không dừng hoặc đổi chiều trong khoảng `T`:

```text
s_signed = v0 T + 0.5 a_x T²
```

Không có giới hạn cố định 12 m. Với `a_x=0`, `T=0,50 s`: tiến 30 km/h quét 4,17 m về trước; lùi 30 km/h quét 4,17 m về sau; tiến 90 km/h quét 12,50 m. `T` là tham số bắt buộc vì mọi dự đoán tương lai phải kết thúc tại một thời điểm hữu hạn; giá trị 0,50 s là cấu hình thử nghiệm cần hiệu chỉnh theo độ trễ và dữ liệu thực tế.

## 7. Quỹ đạo đầu kéo từ yaw-rate

Trong khoảng thời gian dự đoán ngắn, mã nguồn giả sử yaw-rate `r` gần như không đổi:

```text
dψ/dt = r
dx/dt = v(t) cos(ψ)
dy/dt = v(t) sin(ψ)
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `ψ` | **Yaw angle (Góc hướng quay quanh trục đứng)** của đầu kéo | rad |
| `r` | Yaw-rate của đầu kéo | rad/s |
| `x,y` | Vị trí tâm trục sau đầu kéo trong VCS hiện tại | m |
| `v(t)` | Vận tốc tịnh tiến tức thời | m/s |

**Lý do sử dụng:** đây là quan hệ động học phẳng của vật rắn khi vector vận tốc dọc theo hướng thân xe. GPS/INS (định vị vệ tinh/hệ dẫn đường quán tính) thường cung cấp vận tốc, hướng và yaw-rate cho bài toán ước lượng trạng thái xe. Mô hình phù hợp cho dự đoán ngắn khi trượt ngang chưa lớn.

Độ cong và bán kính quay tại thời điểm hiện tại:

```text
κ = r/v0
R = 1/|κ| = |v0/r|
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `κ` | **Curvature (Độ cong quỹ đạo)** | 1/m |
| `R` | **Turning radius (Bán kính quay)** | m |

Khi `v0` quá nhỏ hoặc `r≈0`, mã nguồn không dùng phép chia này; `κ=0` và `R=∞` được hiểu là đứng yên/đi thẳng. Nếu xe gần đứng yên nhưng IMU báo yaw-rate lớn, trạng thái bị đánh dấu không hợp lý và bộ tính không cho xe quay tại chỗ.

Nếu yaw-rate được suy ra từ hai heading (góc hướng) GPS liên tiếp, mã nguồn dùng hiệu góc có xử lý điểm nhảy `+180°/-180°`:

```text
Δψ = atan2(sin(ψ_current-ψ_previous),
           cos(ψ_current-ψ_previous))
r = Δψ/Δt
```

`atan2(y,x)` là hàm góc phần tư đầy đủ, giúp hiệu góc luôn nằm trong `[-π,π]`; `ψ_previous` và `ψ_current` lần lượt là hướng trước và sau; `Δt` là thời gian giữa hai mẫu. Cách này tránh việc chuyển từ `179°` sang `-179°` bị hiểu sai thành quay `-358°`.

Mã nguồn tích phân bằng **midpoint method (Phương pháp điểm giữa)** với bước `Δt = 0,05 s`:

```text
v_mid = v_k + 0.5 a_x Δt
ψ_mid = ψ_k + 0.5 r Δt
x_(k+1) = x_k + v_mid cos(ψ_mid) Δt
y_(k+1) = y_k + v_mid sin(ψ_mid) Δt
ψ_(k+1) = ψ_k + r Δt
```

Ở đây `k` là chỉ số bước hiện tại, `k+1` là bước kế tiếp, `mid` là giá trị tại giữa bước; `sin` và `cos` là các hàm lượng giác. Phương pháp điểm giữa có sai số tích phân thấp hơn Euler tiến trong khi vẫn đủ nhẹ cho cập nhật thời gian thực.

## 8. Động học góc gập rơ-moóc

Với `γ = ψ_tractor - ψ_trailer`, mô hình chốt kéo lệch trục dùng:

```text
dγ/dt = r(1 - (M/L_t)cosγ) - (v/L_t)sinγ
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `γ` | **Articulation angle (Góc gập khớp nối)** giữa đầu kéo và rơ-moóc | rad |
| `r` | Yaw-rate đầu kéo | rad/s |
| `M` | Độ lệch chốt kéo so với trục sau đầu kéo | m |
| `L_t` | Khoảng cách chốt kéo–tâm cụm trục rơ-moóc | m |
| `v` | Vận tốc đầu kéo | m/s |

Nếu chốt kéo nằm đúng trên trục sau (`M=0`), phương trình trở thành:

```text
dγ/dt = r - (v/L_t)sinγ
```

Mã nguồn tích phân góc gập bằng phương pháp điểm giữa. Đặt:

```text
g(v,r,γ) = r(1-(M/L_t)cosγ) - (v/L_t)sinγ
γ_mid = clamp(γ_k + 0.5 Δt g(v_mid,r,γ_k), -γ_max, γ_max)
γ_(k+1) = clamp(γ_k + Δt g(v_mid,r,γ_mid), -γ_max, γ_max)
```

`g` là tốc độ biến thiên góc gập; `γ_k`, `γ_mid`, `γ_(k+1)` là góc gập ở đầu, giữa và cuối bước; `γ_max` là giới hạn cơ khí.

**Cơ sở khoa học:** phương trình xuất phát từ **nonholonomic no-slip constraint (ràng buộc không toàn vẹn: bánh xe không trượt ngang)** của hệ đầu kéo–rơ-moóc. Thành phần `r` làm đầu kéo tạo góc với rơ-moóc; thành phần `-(v/L_t)sinγ` làm rơ-moóc tự bám theo và trở về thẳng khi đầu kéo đi thẳng. Hệ số chứa `M` hiệu chỉnh vận tốc của chốt kéo khi chốt không nằm đúng tâm trục sau. Mô hình động học tractor–semitrailer (đầu kéo–sơ-mi rơ-moóc) và vai trò của articulation angle (góc gập khớp nối) được trình bày trong [Xue và cộng sự, Sensors 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9319227/) và [LaValle, A Car Pulling Trailers](https://msl.cs.uiuc.edu/planning/node661.html).

Mã nguồn cũng tích phân `γ` bằng phương pháp điểm giữa và chặn tại giới hạn cơ khí `±65°`.

### 8.1. Vì sao cùng phương trình dùng được khi đi lùi?

Phương trình dùng vận tốc **có dấu**. Khi lùi, `v<0`, nên thành phần tự căn thẳng đổi dấu. Xét đi thẳng (`r=0`) và góc nhỏ (`sinγ≈γ`):

```text
Đi tiến, v>0:  dγ/dt ≈ -(v/L_t)γ       → γ giảm, hệ ổn định
Đi lùi,  v<0:  dγ/dt ≈ +(|v|/L_t)γ     → γ tăng, hệ không ổn định
```

Đây là hành vi vật lý đúng: khi kéo tiến, rơ-moóc có xu hướng tự thẳng; khi đẩy lùi, một sai lệch nhỏ có thể tăng nhanh thành **jackknife (gập chữ V/mất ổn định khớp nối)**. Vì vậy engine vẫn dự đoán được một horizon ngắn khi lùi, nhưng độ tin cậy phụ thuộc mạnh vào `γ` ban đầu và không được dùng nghiệm trạng thái xác lập như một số đo thật.

Dấu của `r` vẫn là tốc độ quay thực đo bởi IMU. Khi `v<0`, độ cong `κ=r/v` đổi dấu; điều này phản ánh hướng cong của quỹ đạo theo chiều chuyển động lùi.

### 8.2. Ước lượng gamma trong chương trình minh họa

Hệ thống chạy thật cập nhật `γ` liên tục từ lịch sử mẫu GPS/IMU bằng `update_articulation(v,r,dt)`. Chương trình minh họa không có lịch sử trước khi người dùng kéo thanh trượt. Khi đi tiến, nó dùng nghiệm **steady state (trạng thái xác lập)** để khởi tạo hình. Khi đi lùi, nghiệm này không ổn định nên demo giả định `γ0=0` (xe bắt đầu thẳng hàng) rồi dự đoán `γ` trong horizon:

```text
κ = r/v
q = Mκ
A = sqrt(1 + q²)
γ_ss = asin(clamp(L_t κ/A, -1, 1)) - atan(q)
```

| Ký hiệu/hàm | Nghĩa |
|---|---|
| `κ` | Độ cong quỹ đạo ở trạng thái hiện tại |
| `q=Mκ` | Đại lượng không thứ nguyên biểu diễn ảnh hưởng độ lệch chốt kéo |
| `A` | Hệ số chuẩn hóa để giải phương trình lượng giác |
| `γ_ss` | Góc gập ở trạng thái xác lập |
| `sqrt(z)` | Căn bậc hai của `z` |
| `asin(z)` | Hàm nghịch đảo của sin, trả về một góc |
| `atan(z)` | Hàm nghịch đảo của tan, trả về một góc |
| `clamp(z,-1,1)` | Giới hạn `z` vào đoạn từ `-1` tới `1` để `asin` luôn xác định |

Nghiệm này thu được bằng cách đặt `dγ/dt=0` trong phương trình động học. `γ_ss` không phải số đo trực tiếp và không nên thay thế cảm biến góc gập khi cần độ chính xác cao. Giới hạn `±30°/s` trên thanh yaw-rate chỉ là phạm vi điều khiển giao diện; góc gập vẫn có giới hạn cơ khí riêng `±65°`.

## 9. Tạo vùng chiếm dụng quét

Tại mỗi bước tích phân, mã nguồn dựng ba đa giác: cabin, chassis (khung gầm) và rơ-moóc. Một điểm cục bộ `(p_x,p_y)` được đưa tới tư thế dự đoán `(x,y,ψ)` bằng phép quay–tịnh tiến:

```text
p'_x = p_x cosψ - p_y sinψ + x
p'_y = p_x sinψ + p_y cosψ + y
```

`p_x,p_y` là tọa độ điểm trên xe trước biến đổi; `p'_x,p'_y` là tọa độ sau biến đổi. Với chốt kéo `(M,0)`, một điểm rơ-moóc được xoay góc `-γ` quanh chốt bằng:

```text
p_trailer,x = M + (p_x-M)cosγ + p_y sinγ
p_trailer,y =    -(p_x-M)sinγ + p_y cosγ
```

Sau đó toàn bộ xe được biến đổi theo tư thế đầu kéo bằng công thức quay–tịnh tiến phía trên.

Hợp hình học:

```text
P_vehicle(t) = P_cab(t) ∪ P_chassis(t) ∪ P_trailer(t)
P_swept = Union(P_vehicle(t_k)), k=0..N
```

`P_cab`, `P_chassis`, `P_trailer` lần lượt là đa giác cabin, khung gầm và rơ-moóc; `t_k` là thời điểm bước `k`; `N` là tổng số bước tích phân. `Union` nghĩa là phép hợp đa giác: mọi điểm từng bị thân xe chiếm trong khoảng thời gian dự đoán đều thuộc `P_swept`.

**Lý do sử dụng:** chỉ mô phỏng đường tâm hoặc vệt bánh là chưa đủ vì góc cabin, thân rơ-moóc và đuôi xe có thể quét ra ngoài đường tâm. Dùng toàn bộ hình chiếu thân xe làm cho hai hiện tượng tự xuất hiện:

- **Offtracking (Lệch vệt bánh):** trục sau/rơ-moóc không đi đúng vệt trục lái; ở cua chậm khi đi tiến thường lệch vào phía trong.
- **Tail swing (Quét đuôi):** phần thân phía sau trục quay quét ra phía ngoài khi bắt đầu rẽ.

### 9.1. Công thức tham chiếu offtracking ở vòng quay xác lập

Với chuyển động tròn đều tốc độ thấp:

```text
R_r = |v/r|
R_s = sqrt(R_r² + L_f²)
R_h = sqrt(R_r² + M²)
R_t = sqrt(R_h² - L_t²)
OT_ss = R_s - R_t
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `R_r` | Bán kính quỹ đạo tâm trục sau đầu kéo | m |
| `R_s` | Bán kính quỹ đạo tâm trục lái đầu kéo | m |
| `R_h` | Bán kính quỹ đạo chốt kéo | m |
| `R_t` | Bán kính quỹ đạo tâm cụm trục rơ-moóc | m |
| `OT_ss` | Độ lệch vệt bánh xác lập giữa trục lái và trục rơ-moóc | m |

Công thức `R_t` chỉ có nghĩa khi `R_h > L_t`. Chỉ số này được trả về dưới tên `steady_state_offtracking_reference_m` để đối chiếu; DHZ không cộng `OT_ss` như một buffer vì polygon rơ-moóc đã được mô phỏng trực tiếp. Trong chuyển động quá độ và đặc biệt khi lùi, phải dùng các đường trục tích phân thay vì coi `OT_ss` là kết quả chính xác.

### 9.2. Công thức tham chiếu tail swing

Khoảng nhô từ tâm trục rơ-moóc tới tâm đuôi xe:

```text
b = L_body - L_t
Δψ_t = (ψ - γ) - (0 - γ0) = ψ - γ + γ0
TS_center = b |sin(Δψ_t)|
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `b` | Chiều dài phần thân phía sau tâm cụm trục rơ-moóc | m |
| `ψ-γ` | Góc hướng rơ-moóc ở tư thế dự đoán | rad |
| `γ0` | Góc gập tại thời điểm bắt đầu | rad |
| `Δψ_t` | Mức thay đổi góc hướng rơ-moóc | rad |
| `TS_center` | Thành phần quét ngang do quay của tâm đuôi | m |

`TS_center` chỉ là chỉ số giải thích thành phần quay. Tail swing thật còn phụ thuộc chiều rộng thân và tịnh tiến của xe. Vì vậy engine theo dõi trực tiếp cả hai góc sau rơ-moóc, biến đổi chúng bằng công thức đa giác và đưa toàn bộ vùng chúng quét qua vào `P_swept`. Đây mới là phần được dùng để tạo DHZ.

Khi đi lùi, mã nguồn không trả `OT_ss` vì trạng thái xác lập đó không ổn định; giá trị được đặt là `None` (không áp dụng). Khi ấy phải xem trực tiếp vệt trục rơ-moóc và vùng polygon quét.

Engine trả thêm các đường tham chiếu `tractor_steer_axle`, `tractor_rear_axle`, `trailer_axle` và hai đường góc đuôi. Demo vẽ vệt trục lái và vệt trục rơ-moóc để nhìn trực tiếp offtracking.

[FHWA — Cục Quản lý Đường cao tốc Liên bang Hoa Kỳ](https://www.fhwa.dot.gov/policy/otps/truck/wusr/chap06.cfm) mô tả low-speed offtracking (lệch vệt bánh ở tốc độ thấp) và chỉ ra ảnh hưởng của khoảng cách trục và bán kính quay. Nghiên cứu [Sustainability 2022](https://www.mdpi.com/2071-1050/14/16/9805/xml) cho thấy tốc độ quay và bán kính quay ảnh hưởng quy mô vùng chênh lệch vệt bánh trong khi xe sơ-mi rơ-moóc quay.

## 10. Công thức khoảng đệm động

### 10.1. Gia tốc ngang kỳ vọng

Trong chuyển động tròn phẳng, gần trạng thái xác lập và trượt ngang nhỏ:

```text
a_y,expected = v0 r = v0² κ
```

Đây là công thức gia tốc hướng tâm `a=v²/R`, vì `r=v/R`. Cơ sở vehicle dynamics (động lực học ô tô) được trình bày trong [Rajamani, Vehicle Dynamics and Control — Động lực học và điều khiển ô tô](https://link.springer.com/doi/10.1007/978-1-4614-1433-9).

### 10.2. Phần dư gia tốc ngang

```text
a_y,residual = a_y,measured - a_y,expected
```

| Ký hiệu | Nghĩa | Đơn vị |
|---|---|---:|
| `a_y,measured` | Gia tốc ngang sau hiệu chỉnh do IMU đo | m/s² |
| `a_y,expected` | Gia tốc ngang mô hình quay lý tưởng dự đoán | m/s² |
| `a_y,residual` | **Residual (Phần dư):** phần số đo chưa được mô hình giải thích | m/s² |

Nếu dùng trực tiếp toàn bộ `|a_y|` để mở rộng DHZ thì cùng một lần cua bị tính hai lần: yaw-rate đã làm cong `P_swept`, sau đó `a_y` lại làm phình vùng. Dùng phần dư tránh việc cộng trùng này.

### 10.3. Quy đổi phần dư thành khoảng đệm

Từ quan hệ dịch chuyển dưới gia tốc không đổi `d=0,5at²`:

```text
C_dynamic = min(0.5 |a_y,residual| T_c², C_dynamic,max)
C = C0 + C_dynamic
```

| Ký hiệu | Nghĩa | Giá trị thử nghiệm |
|---|---|---:|
| `C0` | Khoảng đệm cơ sở cho sai số kích thước, định vị và rời rạc tích phân | 1,50 m |
| `T_c` | **Clearance response time (Khoảng thời gian quy đổi phần dư thành độ dịch chuyển)** | 0,50 s |
| `C_dynamic,max` | Giới hạn phần khoảng đệm tăng thêm | 0,75 m |
| `C` | Tổng khoảng đệm dùng để tạo DHZ | m |

Cuối cùng:

```text
DHZ = Buffer(P_swept, C)
```

Mã nguồn dùng `join_style=2`, tức **mitre join (kiểu nối góc nhọn)**, để biên nở giữ dạng góc của hình thân xe thay vì bo tròn hoàn toàn.

Ví dụ `a_y,residual=2 m/s²`:

```text
C_dynamic = 0.5 × 2 × 0.5² = 0.25 m
C = 1.50 + 0.25 = 1.75 m
```

**Phân định cơ sở khoa học:**

- Công thức `a_y=v r`, phương trình chuyển động và quan hệ `d=0,5at²` có cơ sở vật lý.
- Việc dùng phần dư `a_y-vr` làm khoảng đệm DHZ là **baseline (mô hình cơ sở ban đầu) do dự án đề xuất**, không phải công thức DHZ do ISO hay FHWA ban hành.
- `C0`, `T_c` và `C_dynamic,max` là tham số thử nghiệm. Chúng phải được hiệu chỉnh bằng sai số giữa vùng dự đoán và vùng thân xe thật đã quét qua.

Phần dư có thể đến từ **transient motion (Chuyển động quá độ)**, **sideslip (Trượt ngang)**, độ nghiêng mặt đường, rung/roll (lắc ngang thân xe), vị trí IMU, sai số đồng bộ hoặc nhiễu cảm biến. Công thức hiện tại không phân biệt các nguyên nhân đó; nó chỉ tăng mức thận trọng.

## 11. Kiểm tra tính hợp lý của đầu vào

Mã nguồn gắn `state_is_plausible=False` (trạng thái không hợp lý) khi:

```text
|v0| < 0.5 m/s và |r| > 0.05 rad/s
```

hoặc:

```text
|a_y| > 3.0 m/s²
```

Mục đích là phát hiện tổ hợp dữ liệu đáng ngờ, ví dụ xe gần đứng yên nhưng IMU báo quay mạnh. Cờ này không phải chứng nhận ổn định hay an toàn; hệ thống tích hợp phải giảm độ tin cậy, kiểm tra lại cảm biến hoặc chuyển sang **degraded mode (Chế độ suy giảm chức năng)**.

## 12. Trình tự tính toán đầy đủ

```text
Bước 1: Nhận v0 từ GPS; r, a_x, a_y từ IMU
Bước 2: Kiểm tra đơn vị, thời gian và tính hợp lý
Bước 3: Cập nhật góc gập γ từ lịch sử v0, r
Bước 4: Tích phân v, x, y, ψ, γ trong T giây
Bước 5: Dựng footprint (hình chiếu thân xe) tại từng bước
Bước 6: Hợp các footprint thành P_swept
Bước 7: Tính a_y,expected = v0 r
Bước 8: Tính a_y,residual = a_y - v0 r
Bước 9: Tính C = C0 + C_dynamic
Bước 10: DHZ = Buffer(P_swept, C)
```

Không bước nào cần đối tượng hay máy ghi hình.

## 13. Kết quả trả về từ mã nguồn

`DynamicHazardZoneCalculator.compute(...)` trả:

| Trường | Nghĩa tiếng Việt |
|---|---|
| `vehicle` | Các đa giác cabin, khung gầm và rơ-moóc hiện tại |
| `current_footprint` | Hình chiếu thân xe hiện tại |
| `current_safety_envelope` | Hình chiếu hiện tại cộng khoảng đệm cơ sở `C0` |
| `raw_swept_path` | Vùng chiếm dụng quét chưa cộng khoảng đệm |
| `dynamic_hazard_zone` | DHZ cuối cùng |
| `reference_paths` | Đường tâm trục lái, trục sau đầu kéo, trục rơ-moóc và hai góc đuôi để kiểm chứng lệch vệt/quét đuôi |
| `metrics` | Các đại lượng trung gian để giải thích và kiểm tra |

Các đại lượng giải thích gồm chiều dài quãng quét, dịch chuyển có dấu, chế độ tiến/lùi, độ cong, bán kính quay, offtracking tham chiếu, tail swing tham chiếu, yaw-rate, `a_x`, `a_y`, phần dư, khoảng đệm, góc gập và cờ tính hợp lý.

Luồng dùng trong chương trình thật:

```python
calculator.update_articulation(v, yaw_rate, dt)
result = calculator.compute(v, yaw_rate, ax, ay)
dhz_polygon = result["dynamic_hazard_zone"]
```

## 14. Chạy chương trình minh họa

Từ thư mục `dynamic_blind_zone`:

```powershell
..\.venv\Scripts\python.exe -B .\demo_dynamic_zone_v2.py
```

Hoặc:

```powershell
..\.venv\Scripts\python.exe -B .\occlusion_visualizer.py
```

Màu sắc và đường tham chiếu:

- Xanh nhạt: `raw_swept_path` — vùng chiếm dụng quét của chính xe.
- Cam: `dynamic_hazard_zone` — DHZ sau khoảng đệm động.
- Hồng đứt: thân xe hiện tại cộng khoảng đệm cơ sở.
- Xanh lá đứt: vệt tâm trục lái đầu kéo.
- Tím chấm: vệt tâm cụm trục rơ-moóc.

Thanh vận tốc là `v_x` có dấu: giá trị dương mô phỏng đi tiến, giá trị âm mô phỏng đi lùi. Thanh yaw-rate có phạm vi `±30°/s` chỉ để thao tác giao diện. Nó không phải giới hạn góc gập và không khẳng định mọi tổ hợp tốc độ/yaw-rate trong phạm vi đó đều khả thi.

## 15. Giả thiết và giới hạn

1. Mặt đường được xem là phẳng.
2. Yaw-rate và gia tốc được xem gần như không đổi trong `T=0,50 s`.
3. Mô hình động học giả sử bánh xe không trượt ngang đáng kể.
4. High-speed offtracking (lệch vệt bánh ở tốc độ cao) do tải, độ đàn hồi lốp, hệ thống treo và trượt ngang chưa được mô tả đầy đủ.
5. Góc gập tích phân từ GPS/IMU đầu kéo có thể **drift (trôi ước lượng)** và cần khởi tạo; cảm biến góc gập riêng sẽ chính xác hơn.
6. Gia tốc ngang phải được bù trọng lực và ảnh hưởng độ nghiêng mặt đường.
7. Các kích thước xe và tham số khoảng đệm hiện chưa phải số liệu xe thật.
8. Khi đi lùi, hệ khớp nối không ổn định; sai số `γ` tăng nhanh. Dự đoán chỉ đáng tin trong horizon ngắn khi `γ` ban đầu được ước lượng tốt.
9. GPS đơn lẻ không xác nhận số tiến/lùi khi xe gần đứng yên; triển khai thật nên lấy thêm trạng thái hộp số.

Vì vậy “đúng” ở đây có nghĩa công thức, đơn vị, quy ước dấu và mã nguồn thống nhất trong phạm vi giả thiết; không có nghĩa mô hình đã được chứng nhận để sử dụng an toàn trên đường công cộng.

## 16. Cách kiểm chứng độc lập

DHZ có thể kiểm chứng mà không cần YOLO hay máy ghi hình:

1. Đo hình học xe thật.
2. Ghi **sensor log (Nhật ký cảm biến)** đồng bộ gồm `v,r,a_x,a_y`.
3. Chạy các tình huống đi thẳng, cua trái/phải, cua gắt, tăng/giảm tốc và chuyển làn.
4. So `P_swept` với **ground truth (Dữ liệu chuẩn đối chiếu)** từ máy ghi hình trên cao, GNSS chính xác cao hoặc dấu vệt bánh.
5. Tính sai số khoảng cách từ biên dự đoán tới biên thật.
6. Chọn `C0`, `T_c`, `C_dynamic,max` theo P95/P99 (phân vị 95%/99%) thay vì chọn bằng cảm giác.
7. Kiểm tra riêng dữ liệu khô/ướt, xe không tải/có tải và nhiều bán kính quay.

Chỉ sau khi DHZ đạt yêu cầu mới ghép máy ghi hình, quỹ đạo đối tượng và BSRI.

## 17. Cơ sở nghiên cứu

1. [FHWA — Roadway Geometry and Offtracking (Hình học đường và lệch vệt bánh)](https://www.fhwa.dot.gov/policy/otps/truck/wusr/chap06.cfm): định nghĩa lệch vệt bánh tốc độ thấp, ảnh hưởng của cấu hình trục và bán kính quay.
2. [Exploring the Influencing Factors and Formation of the Blind Zone of a Semitrailer Truck — Khảo sát yếu tố hình thành vùng mù khi sơ-mi rơ-moóc quay, Sustainability 2022](https://www.mdpi.com/2071-1050/14/16/9805/xml): ảnh hưởng của tốc độ và bán kính quay tới vùng chênh lệch vệt bánh.
3. [Adaptive Articulation Angle Preview-Based Path-Following — Điều khiển bám đường dựa trên dự báo góc gập, Sensors 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9319227/): vai trò góc gập trong mô hình đầu kéo–rơ-moóc.
4. [LaValle — A Car Pulling Trailers (Xe kéo rơ-moóc)](https://msl.cs.uiuc.edu/planning/node661.html): động học không trượt của hệ xe kéo.
5. [Rajamani — Vehicle Dynamics and Control (Động lực học và điều khiển ô tô)](https://link.springer.com/doi/10.1007/978-1-4614-1433-9): nền tảng yaw, gia tốc ngang và mô hình động lực học xe.
6. [Real-time States Estimation Using GPS/INS — Ước lượng trạng thái thời gian thực bằng GPS/hệ dẫn đường quán tính](https://link.springer.com/article/10.1007/s10291-020-01051-5): khả năng quan sát vận tốc, hướng và yaw-rate từ GPS/INS.
7. [NHVR Performance-Based Standards — Tiêu chuẩn dựa trên hiệu năng xe tải nặng](https://www.nhvr.gov.au/road-access/performance-based-standards/the-standards): rearward amplification (khuếch đại chuyển động về phía sau) và hiện tượng trục sau lệch ra ngoài vệt trục lái trong thao tác đột ngột.

Các nguồn trên hỗ trợ nền tảng động học và hiện tượng lệch vệt bánh. Chúng không quy định trực tiếp công thức khoảng đệm từ phần dư hoặc các tham số `1,50 m`, `0,50 s`, `0,75 m`; những phần đó là giả thuyết kỹ thuật phải kiểm chứng.

## 18. Bảng thuật ngữ Anh–Việt

| Thuật ngữ | Nghĩa tiếng Việt |
|---|---|
| Dynamic Hazard Zone (DHZ) | Vùng nguy hiểm động/vùng nguy cơ vật lý tiềm tàng |
| Potential Hazard Envelope | Bao vùng nguy cơ tiềm tàng |
| Ego vehicle | Xe chủ thể đang được hệ thống giám sát |
| Vehicle state | Trạng thái chuyển động của xe |
| Vehicle geometry | Thông số hình học xe |
| Vehicle footprint | Hình chiếu diện tích thân xe xuống mặt đường |
| Swept path / Swept occupancy | Vệt quét/vùng chiếm dụng quét |
| Dynamic clearance | Khoảng đệm động |
| Base clearance | Khoảng đệm cơ sở |
| Buffer | Phép nở/mở rộng biên đa giác |
| Prediction horizon | Khoảng thời gian dự đoán |
| Preview distance | Quãng đường dự đoán trước |
| Yaw angle | Góc hướng quay quanh trục đứng |
| Yaw rate | Tốc độ quay quanh trục đứng |
| Curvature | Độ cong quỹ đạo |
| Turning radius | Bán kính quay |
| Articulation angle | Góc gập khớp nối đầu kéo–rơ-moóc |
| Offtracking | Lệch vệt bánh |
| Tail swing | Quét đuôi xe |
| Longitudinal acceleration | Gia tốc dọc |
| Lateral acceleration | Gia tốc ngang |
| Residual | Phần dư/sai khác chưa được mô hình giải thích |
| Steady state | Trạng thái xác lập |
| Transient motion | Chuyển động quá độ |
| Sideslip | Trượt ngang |
| No-slip constraint | Ràng buộc không trượt ngang tại bánh xe |
| Midpoint method | Phương pháp tích phân điểm giữa |
| Plausibility check | Kiểm tra tính hợp lý |
| Real-time | Thời gian thực |
| Sensor fusion | Hợp nhất cảm biến |
| Time synchronization | Đồng bộ thời gian |
| Latency | Độ trễ xử lý |
| Drift | Trôi sai số ước lượng |
| Ground truth | Dữ liệu chuẩn dùng để đối chiếu |
| Baseline | Mô hình cơ sở ban đầu |
| Degraded mode | Chế độ suy giảm chức năng |
| Clamp | Phép giới hạn một giá trị vào một khoảng |
| Union | Phép hợp các vùng/đa giác |
| Code | Mã nguồn/chương trình |
| Engine | Bộ tính toán |
| Demo | Chương trình minh họa |
| Metric | Đại lượng đo/đại lượng giải thích |

*Nội dung các nguồn trực tuyến đã được diễn giải lại để tuân thủ giới hạn bản quyền.*
