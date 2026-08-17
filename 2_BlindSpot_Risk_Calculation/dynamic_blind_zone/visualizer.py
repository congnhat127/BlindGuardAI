# ==============================================================================
# VISUALIZER.PY - MÔ PHỎNG TƯƠNG TÁC VÙNG MÙ ĐỘNG BLINDGUARD AI
# ==============================================================================
import math
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
import calculator as calc_module
import config

def rotate_pt(x, y, angle_rad, pivot=(0,0)):
    """Xoay một điểm quanh gốc pivot"""
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    px, py = pivot
    return ((x - px) * c - (y - py) * s + px, (x - px) * s + (y - py) * c + py)

def rotate_poly(poly, angle_rad, pivot=(0,0)):
    """Xoay toàn bộ đa giác quanh gốc pivot"""
    return [rotate_pt(x, y, angle_rad, pivot) for x, y in poly]

def main():
    calc = calc_module.BlindZoneCalculator()
    fig, ax = plt.subplots(figsize=(14, 9))
    plt.subplots_adjust(bottom=0.22, right=0.76)
    ax.set_title("BLINDGUARD AI - DYNAMIC BLIND ZONE", fontsize=13, fontweight='bold')
    ax.set_xlabel("X (m) [Goc 0,0 = Truc sau dau keo]", fontsize=10)
    ax.set_ylabel("Y (m)", fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.4)

    info = fig.text(0.78, 0.95, '', fontsize=8.5, va='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a2e', alpha=0.95), color='#e0e0e0')

    legend_items = [
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#455a64', ms=10, label='Cabin'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#78909c', ms=10, label='Khung gam'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#0277bd', ms=10, label='Ro-mooc'),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#e53935', ms=10, label='Vung mu Do', alpha=0.5),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#ff6f00', ms=10, label='Cot A', alpha=0.5),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#7b1fa2', ms=10, label='Khe gap', alpha=0.5),
        Line2D([0],[0], marker='s', color='w', markerfacecolor='#fff176', ms=10, label='Vung Vang', alpha=0.4),
        Line2D([0],[0], marker='*', color='w', markerfacecolor='cyan', ms=10, label='Mat tai xe'),
    ]
    ax.legend(handles=legend_items, loc='lower right', fontsize=7.5, framealpha=0.9)

    patches = []

    # View mode state
    view_mode = {'mode': 'AI View (Đầu kéo cố định)'}

    def draw(v_kmh, omega_deg):
        v = v_kmh / 3.6
        omega = math.radians(omega_deg)

        calc.reset()
        theta_world = 0.0
        dt = 0.0333
        
        # Mô phỏng quá trình quay (2 giây)
        for _ in range(60):
            res = calc.compute(v, omega, dt)
            theta_world += omega * dt

        for p in patches:
            p.remove()
        patches.clear()

        # Hàm trợ giúp áp dụng góc quay theo chế độ xem
        def transform(pts):
            if view_mode['mode'] == 'Đầu kéo xoay (Rơ-moóc cố định)':
                # Xoay toàn bộ khung hình quanh chốt kéo một góc +gamma
                return rotate_poly(pts, res['gamma'], pivot=(config.D_HITCH, 0))
            elif view_mode['mode'] == 'World View (Toàn cảnh)':
                return rotate_poly(pts, theta_world, pivot=(0,0))
            return pts

        def transform_pt(x, y):
            if view_mode['mode'] == 'Đầu kéo xoay (Rơ-moóc cố định)':
                return rotate_pt(x, y, res['gamma'], pivot=(config.D_HITCH, 0))
            elif view_mode['mode'] == 'World View (Toàn cảnh)':
                return rotate_pt(x, y, theta_world, pivot=(0,0))
            return (x, y)

        # Vung Vang
        for pts in res["yellow_zones"].values():
            p = Polygon(transform(pts), closed=True, fc='#fff176', ec='#f9a825', lw=1.2, ls='--', alpha=0.25, zorder=2)
            ax.add_patch(p); patches.append(p)

        # Vung Do
        zone_style = {
            "front":       ('#e53935', 0.35),
            "a_pillar_right": ('#ff6f00', 0.50),
            "a_pillar_left":  ('#ff6f00', 0.35),
            "right_side":  ('#c62828', 0.35),
            "left_side":   ('#ef9a9a', 0.30),
            "rear":        ('#7b1fa2', 0.35),
        }
        for key, pts in res["red_zones"].items():
            c, a = zone_style.get(key, ('#e53935', 0.35))
            p = Polygon(transform(pts), closed=True, fc=c, ec='#b71c1c', lw=1.2, alpha=a, zorder=3)
            ax.add_patch(p); patches.append(p)

        # Khe gap (Articulation gap)
        if res["gap_zone"]:
            p = Polygon(transform(res["gap_zone"]), closed=True, fc='#7b1fa2', ec='purple', lw=1.5, alpha=0.45, zorder=3)
            ax.add_patch(p); patches.append(p)

        # Than xe - 3 phan tach biet
        veh = res["vehicle"]
        p1 = Polygon(transform(veh["cab"]), closed=True, fc='#455a64', ec='black', lw=2, zorder=5)
        ax.add_patch(p1); patches.append(p1)
        p2 = Polygon(transform(veh["chassis"]), closed=True, fc='#78909c', ec='#37474f', lw=1.5, zorder=4)
        ax.add_patch(p2); patches.append(p2)
        p3 = Polygon(transform(veh["trailer"]), closed=True, fc='#0277bd', ec='black', lw=2, zorder=5)
        ax.add_patch(p3); patches.append(p3)

        # Chot keo
        hx, hy = transform_pt(*veh["hitch"])
        p4 = ax.scatter([hx], [hy], c='yellow', edgecolor='black', s=60, zorder=6)
        patches.append(p4)

        # Mat tai xe
        ex, ey = transform_pt(config.EYE_X, config.EYE_Y)
        p5 = ax.scatter([ex], [ey], c='cyan', edgecolor='black',
                         marker='*', s=120, zorder=6)
        patches.append(p5)

        # Goc toa do
        p6 = ax.scatter([0], [0], c='lime', edgecolor='black', marker='+', s=80, lw=2, zorder=6)
        patches.append(p6)

        # Thong so
        s = res["stopping"]
        info.set_text(
            f" THONG SO VAN HANH\n"
            f" ─────────────────\n"
            f" v      : {v_kmh:5.1f} km/h\n"
            f" omega  : {omega_deg:5.1f} deg/s\n"
            f" ─────────────────\n"
            f" KET QUA\n"
            f" ─────────────────\n"
            f" gamma  : {res['gamma_deg']:5.1f} deg\n"
            f" d_react: {s['d_reaction']:5.1f} m\n"
            f" d_brake: {s['d_braking']:5.1f} m\n"
            f" d_total: {s['d_total']:5.1f} m\n"
            f" d_swept: {res['d_swept']:5.1f} m\n"
        )

        ax.set_xlim(-25, max(25, 12 + s['d_total']))
        ax.set_ylim(-20, 20)
        fig.canvas.draw_idle()

    # Sliders
    ax_v = plt.axes([0.12, 0.10, 0.45, 0.03])
    ax_o = plt.axes([0.12, 0.05, 0.45, 0.03])
    ax_r = plt.axes([0.60, 0.05, 0.07, 0.08])
    
    # Radio buttons cho các chế độ góc nhìn
    ax_radio = plt.axes([0.65, 0.03, 0.32, 0.12])
    radio = RadioButtons(ax_radio, (
        'AI View (Đầu kéo cố định)',
        'Đầu kéo xoay (Rơ-moóc cố định)',
        'World View (Toàn cảnh)'
    ))

    sl_v = Slider(ax_v, 'v (km/h)', -10, 90, valinit=0, valfmt='%1.1f')
    sl_o = Slider(ax_o, 'omega (deg/s)', -25, 25, valinit=0, valfmt='%1.1f')
    btn = Button(ax_r, 'Reset', color='lightgray', hovercolor='0.9')

    def switch_view(label):
        view_mode['mode'] = label
        draw(sl_v.val, sl_o.val)

    radio.on_clicked(switch_view)
    sl_v.on_changed(lambda _: draw(sl_v.val, sl_o.val))
    sl_o.on_changed(lambda _: draw(sl_v.val, sl_o.val))
    btn.on_clicked(lambda _: (calc.reset(), sl_v.reset(), sl_o.reset(), draw(0, 0)))

    draw(0, 0)
    plt.show()

if __name__ == "__main__":
    main()
