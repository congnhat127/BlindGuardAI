# ==============================================================================
# OCCLUSION_VISUALIZER.PY - MÔ PHỎNG SO SÁNH MÔ HÌNH TOÁN HỌC QUANG HỌC THUẦN TÚY
# (PURE OCCLUSION VS SWEPT PATH VS HAZARD ZONE COMPARISON VISUALIZER)
# ==============================================================================
import math
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
import occlusion_calculator as occ_module
import config

def rotate_pt(x, y, angle_rad, pivot=(0,0)):
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    px, py = pivot
    return ((x - px) * c - (y - py) * s + px, (x - px) * s + (y - py) * c + py)

def rotate_poly(poly, angle_rad, pivot=(0,0)):
    return [rotate_pt(x, y, angle_rad, pivot) for x, y in poly]

def main():
    calc = occ_module.PureOcclusionCalculator()
    fig, ax = plt.subplots(figsize=(15, 9.5))
    plt.subplots_adjust(bottom=0.25, right=0.74)

    ax.set_title("PURE OCCLUSION GEOMETRY & KINEMATIC MODEL COMPARISON", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("X (m) [Gốc (0,0) = Tâm trục sau đầu kéo]", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.35)

    # Bảng thông số kỹ thuật bên phải
    info = fig.text(0.76, 0.95, '', fontsize=8.5, va='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.6', facecolor='#0f172a', alpha=0.95), color='#f8fafc')

    # Chú giải phân biệt các phân hệ
    legend_items = [
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#334155', ms=10, label='Cabin đầu kéo'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#0284c7', ms=10, label='Thùng Rơ-moóc'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#ef4444', ms=10, label='1. Mù Gương (Mirror Occlusion)', alpha=0.5),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#f97316', ms=10, label='   - Cột A (A-Pillar Assembly)', alpha=0.6),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#a855f7', ms=10, label='   - Cột B / Khung cửa (Shoulder)', alpha=0.5),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#38bdf8', ms=10, label='2. Quỹ Đạo Bánh Quét (Swept Path)', alpha=0.4),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#fef08a', ms=10, label='3. Nguy Hiểm Phanh (Hazard Zone)', alpha=0.3),
        Line2D([0],[0], marker='*', color='w', markerfacecolor='cyan', ms=12, label='Mắt tài xế E'),
    ]
    ax.legend(handles=legend_items, loc='lower right', fontsize=8, framealpha=0.9)

    patches = []

    # State biến điều khiển
    state = {
        'view_mode': 'AI View (Đầu kéo cố định)',
        'input_type': 'Tốc độ góc yaw (deg/s)',
        'show_swept': True,
        'show_hazard': True,
        'show_occlusion': True
    }

    def draw(v_kmh, input_val_deg):
        v = v_kmh / 3.6
        val_rad = math.radians(input_val_deg)
        is_steer = (state['input_type'] == 'Góc bẻ lái vô-lăng (deg)')

        calc.reset()
        dt = 0.0333
        theta_world = 0.0

        # Tích hợp bước thời gian 2 giây mô phỏng (60 timesteps)
        for _ in range(60):
            res = calc.compute_all(v, val_rad, dt, is_steering_angle=is_steer)
            theta_world += calc.yaw_rate * dt

        for p in patches:
            p.remove()
        patches.clear()

        # Áp dụng ma trận biến đổi tọa độ theo View Mode
        def transform(pts):
            if state['view_mode'] == 'Đầu kéo xoay (Rơ-moóc cố định)':
                return rotate_poly(pts, res['gamma_rad'], pivot=(config.D_HITCH, 0))
            elif state['view_mode'] == 'World View (Toàn cảnh)':
                return rotate_poly(pts, theta_world, pivot=(0,0))
            return pts

        def transform_pt(x, y):
            if state['view_mode'] == 'Đầu kéo xoay (Rơ-moóc cố định)':
                return rotate_pt(x, y, res['gamma_rad'], pivot=(config.D_HITCH, 0))
            elif state['view_mode'] == 'World View (Toàn cảnh)':
                return rotate_pt(x, y, theta_world, pivot=(0,0))
            return (x, y)

        # 1. VÙNG NGUY HIỂM PHANH (Hazard Stopping Zone)
        if state['show_hazard']:
            hazard_pts = res["stopping_hazard"]["front_hazard_polygon"]
            p = Polygon(transform(hazard_pts), closed=True, fc='#fef08a', ec='#ca8a04', lw=1.5, ls='--', alpha=0.3, zorder=2)
            ax.add_patch(p); patches.append(p)

        # 2. QUỸ ĐẠO BÁNH QUÉT (Kinematic Swept Path)
        if state['show_swept'] and res["swept_path"]["swept_path"]:
            swept_pts = res["swept_path"]["swept_path"]
            p = Polygon(transform(swept_pts), closed=True, fc='#38bdf8', ec='#0284c7', lw=1.8, hatch='//', alpha=0.4, zorder=3)
            ax.add_patch(p); patches.append(p)

        # 3. VÙNG MÙ QUANG HỌC THUẦN TÚY (Pure Occlusion Geometry)
        if state['show_occlusion']:
            occ_zones = res["occlusion_zones"]
            # Vùng mù trước cabin (Front Bonnet Windshield Projection)
            if "front_bonnet" in occ_zones:
                p_fb = Polygon(transform(occ_zones["front_bonnet"]), closed=True, fc='#dc2626', ec='#991b1b', lw=1.2, alpha=0.45, zorder=4)
                ax.add_patch(p_fb); patches.append(p_fb)

            # Cột A (A-Pillar Assembly Shadow)
            for key in ["a_pillar_right", "a_pillar_left"]:
                p = Polygon(transform(occ_zones[key]), closed=True, fc='#f97316', ec='#c2410c', lw=1.2, alpha=0.55, zorder=4)
                ax.add_patch(p); patches.append(p)

            # Cột B & Thành Cabin (B-Pillar Shoulder Direct Vision Obstruction)
            for key in ["b_pillar_right", "b_pillar_left"]:
                p = Polygon(transform(occ_zones[key]), closed=True, fc='#a855f7', ec='#7e22ce', lw=1.2, alpha=0.45, zorder=4)
                ax.add_patch(p); patches.append(p)

            # Bóng khuất Gương chiếu hậu (Mirror Occlusion Shadows)
            p_r = Polygon(transform(occ_zones["right_side_occlusion"]), closed=True, fc='#ef4444', ec='#b91c1c', lw=1.2, alpha=0.35, zorder=4)
            ax.add_patch(p_r); patches.append(p_r)
            p_l = Polygon(transform(occ_zones["left_side_occlusion"]), closed=True, fc='#f87171', ec='#dc2626', lw=1.2, alpha=0.30, zorder=4)
            ax.add_patch(p_l); patches.append(p_l)

        # 4. HÌNH HỌC THÂN XE
        veh = res["vehicle"]
        p1 = Polygon(transform(veh["cab"]), closed=True, fc='#334155', ec='black', lw=2, zorder=6)
        ax.add_patch(p1); patches.append(p1)
        p2 = Polygon(transform(veh["chassis"]), closed=True, fc='#64748b', ec='#1e293b', lw=1.5, zorder=5)
        ax.add_patch(p2); patches.append(p2)
        p3 = Polygon(transform(veh["trailer"]), closed=True, fc='#0284c7', ec='black', lw=2, zorder=6)
        ax.add_patch(p3); patches.append(p3)

        # Chốt kéo & Mắt tài xế
        hx, hy = transform_pt(*veh["pivot"])
        p4 = ax.scatter([hx], [hy], c='yellow', edgecolor='black', s=70, zorder=7)
        patches.append(p4)

        ex, ey = transform_pt(config.EYE_X, config.EYE_Y)
        p5 = ax.scatter([ex], [ey], c='cyan', edgecolor='black', marker='*', s=140, zorder=7)
        patches.append(p5)

        # Cột A & Gương phụ
        m_rx, m_ry = transform_pt(config.MIRROR_R_X, config.MIRROR_R_Y)
        m_lx, m_ly = transform_pt(config.MIRROR_L_X, config.MIRROR_L_Y)
        p6 = ax.scatter([m_rx, m_lx], [m_ry, m_ly], c='orange', edgecolor='black', s=45, zorder=7)
        patches.append(p6)

        # Bảng thông số đo đạc chuẩn toán học
        s = res["stopping_hazard"]
        sw = res["swept_path"]
        info.set_text(
            f"  ĐỘNG HỌC THỜI GIAN THỰC\n"
            f"  ─────────────────────────\n"
            f"  v          : {v_kmh:5.1f} km/h\n"
            f"  Input Mode : {state['input_type'][:15]}\n"
            f"  Input Val  : {input_val_deg:5.1f} deg\n"
            f"  Yaw Rate ω : {math.degrees(calc.yaw_rate):5.1f} deg/s\n"
            f"  ─────────────────────────\n"
            f"  KẾT QUẢ ĐO ĐẠC HÌNH HỌC\n"
            f"  ─────────────────────────\n"
            f"  Góc gập γ  : {res['gamma_deg']:5.1f} deg\n"
            f"  Lấn lề Δy  : {sw['d_swept_val']:5.2f} m\n"
            f"  Quãng phanh: {s['d_total']:5.1f} m\n"
            f"  (Phản ứng  : {s['d_reaction']:5.1f} m)\n"
            f"  (Thắng phanh: {s['d_braking']:5.1f} m)\n"
        )

        ax.set_xlim(-28, max(28, 15 + s['d_total']))
        ax.set_ylim(-22, 22)
        fig.canvas.draw_idle()

    # Sliders & Controls
    ax_v = plt.axes([0.10, 0.12, 0.42, 0.03])
    ax_o = plt.axes([0.10, 0.06, 0.42, 0.03])
    ax_r = plt.axes([0.54, 0.06, 0.06, 0.09])

    # Radio buttons Chế độ quan sát
    ax_radio = plt.axes([0.62, 0.03, 0.17, 0.12])
    radio_view = RadioButtons(ax_radio, (
        'AI View (Đầu kéo cố định)',
        'Đầu kéo xoay (Rơ-moóc cố định)',
        'World View (Toàn cảnh)'
    ))

    # Radio buttons Chế độ Đầu vào (Yaw Rate vs Steering Angle)
    ax_input = plt.axes([0.80, 0.03, 0.17, 0.07])
    radio_input = RadioButtons(ax_input, (
        'Tốc độ góc yaw (deg/s)',
        'Góc bẻ lái vô-lăng (deg)'
    ))

    # Checkbox Bật/Tắt phân hệ toán học
    ax_chk = plt.axes([0.80, 0.11, 0.17, 0.11])
    chk = CheckButtons(ax_chk, ('1. Occlusion Shadow', '2. Swept Path', '3. Hazard Stopping'), (True, True, True))

    sl_v = Slider(ax_v, 'Vận tốc (km/h)', -10, 90, valinit=0, valfmt='%1.1f')
    sl_o = Slider(ax_o, 'Đầu vào (deg)', -45, 45, valinit=0, valfmt='%1.1f')
    btn = Button(ax_r, 'Reset', color='#cbd5e1', hovercolor='#94a3b8')

    def switch_view(label):
        state['view_mode'] = label
        draw(sl_v.val, sl_o.val)

    def switch_input(label):
        state['input_type'] = label
        draw(sl_v.val, sl_o.val)

    def toggle_layers(label):
        if 'Occlusion' in label: state['show_occlusion'] = not state['show_occlusion']
        if 'Swept' in label: state['show_swept'] = not state['show_swept']
        if 'Hazard' in label: state['show_hazard'] = not state['show_hazard']
        draw(sl_v.val, sl_o.val)

    radio_view.on_clicked(switch_view)
    radio_input.on_clicked(switch_input)
    chk.on_clicked(toggle_layers)

    sl_v.on_changed(lambda _: draw(sl_v.val, sl_o.val))
    sl_o.on_changed(lambda _: draw(sl_v.val, sl_o.val))
    btn.on_clicked(lambda _: (calc.reset(), sl_v.reset(), sl_o.reset(), draw(0, 0)))

    draw(0, 0)
    plt.show()

if __name__ == "__main__":
    main()
