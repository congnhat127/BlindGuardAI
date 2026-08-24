# ==============================================================================
# OCCLUSION_VISUALIZER.PY - MÔ PHỎNG VÙNG NGUY HIỂM XUNG QUANH (SURROUND HAZARD)
# ==============================================================================
import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
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

def translate_poly(poly, dx, dy):
    return [(x + dx, y + dy) for x, y in poly]

def main():
    calc = occ_module.PureOcclusionCalculator()
    fig, ax = plt.subplots(figsize=(15, 9.5))
    plt.subplots_adjust(bottom=0.25, right=0.74)

    ax.set_title("DYNAMIC HAZARD DRIVING SIMULATOR", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("X (m)", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)
    
    # ---------------------------------------------------------
    # VẼ SA BÀN GIAO THÔNG (MÔ PHỎNG NGÃ TƯ & LÀN ĐƯỜNG)
    # ---------------------------------------------------------
    ax.set_facecolor('#d1d5db')  # Màu nền lề đường (xám nhạt)
    
    # Đường ngang (Rộng 14m, mỗi bên 2 làn 3.5m)
    road_h = Polygon([(-200, -7), (200, -7), (200, 7), (-200, 7)], fc='#475569', ec='none', zorder=1)
    # Đường dọc (Rộng 14m)
    road_v = Polygon([(-7, -200), (-7, 200), (7, 200), (7, -200)], fc='#475569', ec='none', zorder=1)
    ax.add_patch(road_h)
    ax.add_patch(road_v)
    
    # Vẽ vạch kẻ đường (Vạch liền phân cách 2 chiều)
    ax.plot([-200, -7], [0, 0], color='#fbbf24', lw=2, zorder=1)
    ax.plot([7, 200], [0, 0], color='#fbbf24', lw=2, zorder=1)
    ax.plot([0, 0], [-200, -7], color='#fbbf24', lw=2, zorder=1)
    ax.plot([0, 0], [7, 200], color='#fbbf24', lw=2, zorder=1)
    
    # Vẽ vạch đứt phân làn
    ax.plot([-200, -7], [3.5, 3.5], color='white', lw=1, ls='--', zorder=1)
    ax.plot([-200, -7], [-3.5, -3.5], color='white', lw=1, ls='--', zorder=1)
    ax.plot([7, 200], [3.5, 3.5], color='white', lw=1, ls='--', zorder=1)
    ax.plot([7, 200], [-3.5, -3.5], color='white', lw=1, ls='--', zorder=1)
    
    ax.plot([3.5, 3.5], [-200, -7], color='white', lw=1, ls='--', zorder=1)
    ax.plot([-3.5, -3.5], [-200, -7], color='white', lw=1, ls='--', zorder=1)
    ax.plot([3.5, 3.5], [7, 200], color='white', lw=1, ls='--', zorder=1)
    ax.plot([-3.5, -3.5], [7, 200], color='white', lw=1, ls='--', zorder=1)
    
    ax.grid(True, linestyle=':', color='black', alpha=0.2)
    # ---------------------------------------------------------

    info = fig.text(0.76, 0.95, '', fontsize=8.5, va='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.6', facecolor='#0f172a', alpha=0.95), color='#f8fafc')

    legend_items = [
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#334155', ms=10, label='Cabin đầu kéo'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#0284c7', ms=10, label='Thùng Rơ-moóc'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#ec4899', ms=10, label='[LỚP 1] Giáp Cận Chiến (Surround Hazard)', alpha=0.25),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#fef08a', ms=10, label='[LỚP 2] Nguy Hiểm Phanh (Stopping Hazard)', alpha=0.3),
        Line2D([0],[0], marker='*', color='w', markerfacecolor='yellow', ms=12, label='Chốt Kéo (Pivot)'),
    ]
    ax.legend(handles=legend_items, loc='lower right', fontsize=9, framealpha=0.9)

    patches = []

    state = {
        'view_mode': 'World View (Camera fly)',
        'input_type': 'Góc bẻ lái vô-lăng (deg)',
        'show_surround': True,
        'show_stopping': True,
        'world_x': 0.0,
        'world_y': 0.0,
        'world_theta': 0.0
    }

    # Sliders & Controls
    ax_v = plt.axes([0.10, 0.12, 0.42, 0.03])
    ax_o = plt.axes([0.10, 0.06, 0.42, 0.03])
    ax_r = plt.axes([0.54, 0.06, 0.06, 0.09])

    ax_radio = plt.axes([0.62, 0.03, 0.17, 0.12])
    radio_view = RadioButtons(ax_radio, (
        'World View (Camera fly)',
        'AI View (Fixed Center)'
    ))

    ax_input = plt.axes([0.80, 0.03, 0.17, 0.07])
    radio_input = RadioButtons(ax_input, (
        'Góc bẻ lái vô-lăng (deg)',
        'Tốc độ góc yaw (deg/s)'
    ))

    ax_chk = plt.axes([0.80, 0.12, 0.17, 0.08])
    chk = CheckButtons(ax_chk, ('1. Surround Hazard', '2. Stopping Hazard'), (True, True))

    sl_v = Slider(ax_v, 'Vận tốc (km/h)', -20, 90, valinit=30, valfmt='%1.1f')
    sl_o = Slider(ax_o, 'Vô-lăng (deg)', -180, 180, valinit=0, valfmt='%1.1f')
    btn = Button(ax_r, 'Reset', color='#cbd5e1', hovercolor='#94a3b8')

    def switch_view(label):
        state['view_mode'] = label

    def switch_input(label):
        state['input_type'] = label
        if 'vô-lăng' in label:
            sl_o.valmin = -720
            sl_o.valmax = 720
            sl_o.ax.set_xlim(-720, 720)
        else:
            sl_o.valmin = -45
            sl_o.valmax = 45
            sl_o.ax.set_xlim(-45, 45)

    def toggle_layers(label):
        if 'Surround' in label: state['show_surround'] = not state['show_surround']
        if 'Stopping' in label: state['show_stopping'] = not state['show_stopping']

    radio_view.on_clicked(switch_view)
    radio_input.on_clicked(switch_input)
    chk.on_clicked(toggle_layers)

    def reset(event):
        calc.reset()
        sl_v.reset()
        sl_o.reset()
        state['world_x'] = 0.0
        state['world_y'] = 0.0
        state['world_theta'] = 0.0
    btn.on_clicked(reset)

    # Vòng lặp Animation (30 FPS)
    def update(frame):
        v = sl_v.val / 3.6
        val_rad = math.radians(sl_o.val)
        is_steer = (state['input_type'] == 'Góc bẻ lái vô-lăng (deg)')
        
        dt = 0.05 # 20 FPS Physics
        
        # 1. Update Physics Kinematics
        res = calc.compute_all(v, val_rad, dt, is_steering_angle=is_steer)
        
        # 2. Update World Position
        state['world_x'] += v * math.cos(state['world_theta']) * dt
        state['world_y'] += v * math.sin(state['world_theta']) * dt
        state['world_theta'] += calc.yaw_rate * dt
        
        # 3. Clear old patches
        for p in patches:
            p.remove()
        patches.clear()

        # Transformation Helper
        def transform(pts):
            if state['view_mode'] == 'World View (Camera fly)':
                rotated = rotate_poly(pts, state['world_theta'], pivot=(0,0))
                return translate_poly(rotated, state['world_x'], state['world_y'])
            return pts

        # 1. VÙNG NGUY HIỂM PHANH (Stopping Hazard Zone)
        if state['show_stopping']:
            hazard_pts = res["stopping_hazard"]["front_hazard_polygon"]
            p = Polygon(transform(hazard_pts), closed=True, fc='#fef08a', ec='#ca8a04', lw=1.5, ls='--', alpha=0.3, zorder=2)
            ax.add_patch(p); patches.append(p)

        # 2. VÙNG BẢO VỆ XUNG QUANH (Surround Hazard Zone - Predictive Swept Path)
        if state['show_surround']:
            p_sh = Polygon(transform(res["surround_hazard"]), closed=True, fc='#ec4899', ec='#be185d', lw=2, linestyle='--', alpha=0.35, zorder=3)
            ax.add_patch(p_sh); patches.append(p_sh)

        # 3. HÌNH HỌC THÂN XE
        veh = res["vehicle"]
        p1 = Polygon(transform(veh["cab"]), closed=True, fc='#334155', ec='black', lw=2, zorder=6)
        ax.add_patch(p1); patches.append(p1)
        p2 = Polygon(transform(veh["chassis"]), closed=True, fc='#64748b', ec='#1e293b', lw=1.5, zorder=5)
        ax.add_patch(p2); patches.append(p2)
        p3 = Polygon(transform(veh["trailer"]), closed=True, fc='#0284c7', ec='black', lw=2, zorder=6)
        ax.add_patch(p3); patches.append(p3)

        hx, hy = veh["pivot"]
        if state['view_mode'] == 'World View (Camera fly)':
            hx, hy = rotate_pt(hx, hy, state['world_theta'], pivot=(0,0))
            hx += state['world_x']
            hy += state['world_y']
        
        p4 = ax.scatter([hx], [hy], c='yellow', edgecolor='black', s=70, zorder=7)
        patches.append(p4)

        # Camera follow
        if state['view_mode'] == 'World View (Camera fly)':
            ax.set_xlim(state['world_x'] - 25, state['world_x'] + 25)
            ax.set_ylim(state['world_y'] - 25, state['world_y'] + 25)
        else:
            ax.set_xlim(-28, 28)
            ax.set_ylim(-22, 22)

        # Update Text
        s = res["stopping_hazard"]
        info.set_text(
            f"  ĐỘNG HỌC THỜI GIAN THỰC\n"
            f"  ─────────────────────────\n"
            f"  v          : {sl_v.val:5.1f} km/h\n"
            f"  Vô-lăng    : {sl_o.val:5.1f} deg\n"
            f"  Yaw Rate ω : {math.degrees(calc.yaw_rate):5.1f} deg/s\n"
            f"  World X,Y  : {state['world_x']:.1f}, {state['world_y']:.1f}\n"
            f"  ─────────────────────────\n"
            f"  KẾT QUẢ ĐO ĐẠC HÌNH HỌC\n"
            f"  ─────────────────────────\n"
            f"  Góc gập γ  : {res['gamma_deg']:5.1f} deg\n"
            f"  Quãng phanh: {s['d_total']:5.1f} m\n"
            f"  (Phản ứng  : {s['d_reaction']:5.1f} m)\n"
            f"  (Thắng phanh: {s['d_braking']:5.1f} m)\n"
        )
        
        return patches

    ani = animation.FuncAnimation(fig, update, interval=50, blit=False, cache_frame_data=False)
    plt.show()

if __name__ == "__main__":
    main()
