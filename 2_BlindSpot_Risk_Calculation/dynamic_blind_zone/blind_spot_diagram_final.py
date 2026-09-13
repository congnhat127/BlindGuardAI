import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import calculator as calc_module
import config

def draw_static_pdf_diagram(ax):
    """
    Vẽ lại hình ảnh vùng mù tĩnh (Static Blind Zone) thường thấy trong các tài liệu PDF 
    của FMCSA hoặc chuẩn Châu Âu để đối chiếu.
    """
    hw_c = config.CAB_HALF_W
    hw_t = config.TRAIL_HALF_W
    
    # Thân xe cơ bản
    cab = Polygon([
        (config.CAB_FRONT_X, hw_c), (config.CAB_FRONT_X, -hw_c),
        (config.CAB_REAR_X, -hw_c), (config.CAB_REAR_X, hw_c)
    ], fc='gray', ec='black', lw=2)
    
    trailer = Polygon([
        (config.CAB_REAR_X, hw_t), (config.CAB_REAR_X, -hw_t),
        (config.D_HITCH - config.L_TRAIL, -hw_t), (config.D_HITCH - config.L_TRAIL, hw_t)
    ], fc='darkgray', ec='black', lw=2)
    
    ax.add_patch(cab)
    ax.add_patch(trailer)
    
    # 1. Vùng mù phía trước (Thường là một hình chữ nhật cố định ~3-6 mét)
    front = Polygon([
        (config.CAB_FRONT_X, hw_c), (config.CAB_FRONT_X + 4.0, hw_c),
        (config.CAB_FRONT_X + 4.0, -hw_c), (config.CAB_FRONT_X, -hw_c)
    ], fc='red', alpha=0.3, ec='red', label='Front Blind Spot')
    ax.add_patch(front)
    
    # 2. Vùng mù hông phải (Thường là một hình quạt hoặc hình thang rất lớn, bao trùm 1-2 làn đường)
    right_side = Polygon([
        (config.CAB_FRONT_X, -hw_c), (config.CAB_FRONT_X - 2.0, -hw_c - 5.0),
        (config.D_HITCH - config.L_TRAIL, -hw_c - 5.0), (config.D_HITCH - config.L_TRAIL, -hw_c)
    ], fc='orange', alpha=0.3, ec='orange', label='Right Side (Passenger) Blind Spot')
    ax.add_patch(right_side)
    
    # 3. Vùng mù hông trái (Thường nhỏ hơn, sát cabin tài xế)
    left_side = Polygon([
        (config.CAB_FRONT_X - 1.0, hw_c), (config.CAB_FRONT_X - 3.0, hw_c + 3.0),
        (config.CAB_REAR_X - 2.0, hw_c + 3.0), (config.CAB_REAR_X - 2.0, hw_c)
    ], fc='yellow', alpha=0.4, ec='yellow', label='Left Side (Driver) Blind Spot')
    ax.add_patch(left_side)
    
    # 4. Vùng mù phía sau (Thường là hình chữ nhật khổng lồ kéo dài 10-30 mét)
    rear = Polygon([
        (config.D_HITCH - config.L_TRAIL, hw_t), (config.D_HITCH - config.L_TRAIL - 15.0, hw_t),
        (config.D_HITCH - config.L_TRAIL - 15.0, -hw_t), (config.D_HITCH - config.L_TRAIL, -hw_t)
    ], fc='purple', alpha=0.3, ec='purple', label='Rear Blind Spot')
    ax.add_patch(rear)
    
    ax.set_xlim(-25, 10)
    ax.set_ylim(-10, 10)
    ax.set_title("Biểu đồ Vùng Mù Tĩnh (Static) trong Tài liệu PDF", fontweight='bold')
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.grid(True, linestyle='--', alpha=0.5)

def draw_dynamic_model_diagram(ax):
    """
    Vẽ biểu đồ vùng mù động từ thuật toán của chúng ta (v = 30km/h, thẳng)
    """
    calc = calc_module.BlindZoneCalculator()
    v_mps = 30 / 3.6
    res = calc.compute(v_mps, 0.0)
    
    # Thân xe
    veh = res["vehicle"]
    for part in ["cab", "chassis", "trailer"]:
        ax.add_patch(Polygon(veh[part], fc='#455a64', ec='black', lw=2))
        
    # Vùng mù
    for name, pts in res["red_zones"].items():
        ax.add_patch(Polygon(pts, fc='red', alpha=0.35, ec='darkred'))
        
    # Điểm mắt tài xế
    ax.scatter([config.EYE_X], [config.EYE_Y], color='cyan', marker='*', s=150, zorder=5, label='Mắt tài xế')
    
    ax.set_xlim(-25, 15)
    ax.set_ylim(-10, 10)
    ax.set_title("Mô hình Vùng Mù Động (Dynamic) của BlindGuard AI\n(Tính toán từ vị trí mắt tài xế & Vận tốc)", fontweight='bold')
    ax.set_xlabel("X (m)")
    ax.grid(True, linestyle='--', alpha=0.5)

def main():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))
    plt.subplots_adjust(hspace=0.3)
    
    draw_static_pdf_diagram(ax1)
    draw_dynamic_model_diagram(ax2)
    
    # Ghi chú so sánh
    comparison_text = (
        "SO SÁNH SỰ KHÁC BIỆT:\n"
        "1. PDF (Tĩnh): Vùng mù được vẽ theo kinh nghiệm (khối chữ nhật/thang lớn). Không đổi theo tốc độ.\n"
        "   BlindGuard (Động): Tính chính xác bằng phép chiếu hình học từ Mắt Tài Xế (Occlusion Shadow). Co giãn theo Vận tốc.\n"
        "2. Điểm mù Cột A: PDF thường bỏ qua. BlindGuard tính toán chi tiết góc che khuất của cột A.\n"
        "3. Vùng mù phía trước: PDF cố định ~3-4m. BlindGuard kéo dài linh hoạt theo Quãng đường phanh an toàn.\n"
        "4. Điểm mù thân xe: PDF vẽ thành mảng lớn bao trọn làn đường. BlindGuard tính độ vát chính xác theo góc nhìn của gương chiếu hậu."
    )
    fig.text(0.1, 0.02, comparison_text, fontsize=11, bbox=dict(facecolor='lightyellow', alpha=0.8), family='monospace')
    
    plt.savefig('2_BlindSpot_Risk_Calculation/dynamic_blind_zone/blind_spot_diagram_final.png', dpi=150)
    print("Đã tạo file ảnh so sánh: blind_spot_diagram_final.png")
    plt.show()

if __name__ == "__main__":
    main()
