"""Realtime GPS/IMU-driven Dynamic Hazard Zone demo."""
import math

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from matplotlib.widgets import Button, Slider

import config
from dhz_calculator import DynamicHazardZoneCalculator

X_MIN, X_MAX = -25.0, 20.0
Y_MIN, Y_MAX = -16.0, 16.0


def main():
    print("Starting GPS/IMU DHZ demo (object-independent, no stopping cone)")
    calculator = DynamicHazardZoneCalculator()
    fig, ax = plt.subplots(figsize=(13, 9))
    plt.subplots_adjust(left=0.08, right=0.98, bottom=0.27, top=0.92)
    ax.set_title("BLINDGUARD AI — GPS/IMU DYNAMIC HAZARD ZONE",
                 fontsize=14, fontweight="bold")
    ax.text(0.5, 1.01, "DHZ = vùng chiếm dụng quét + khoảng đệm động (không dùng đối tượng)",
            transform=ax.transAxes, ha="center", fontsize=9, color="#475569")
    ax.set_aspect("equal")
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_xticks(range(-24, 21, 2))
    ax.set_yticks(range(-16, 17, 2))
    ax.grid(True, ls="--", lw=0.5, color="#cbd5e1")
    ax.axhline(0, color="#64748b", lw=1.1)
    ax.axvline(0, color="#64748b", lw=1.1)
    ax.set_xlabel("X (m) — hướng tiến (+)")
    ax.set_ylabel("Y (m) — trái (+) / phải (−)")
    ax.annotate("X+", xy=(18, 0), xytext=(16, 0.8),
                arrowprops=dict(arrowstyle="-|>", color="#16a34a", lw=2),
                color="#15803d")
    ax.annotate("Y+", xy=(0, 14), xytext=(0.7, 12),
                arrowprops=dict(arrowstyle="-|>", color="#16a34a", lw=2),
                color="#15803d")

    dhz = Polygon([(0, 0)] * 4, fc="#fb923c", ec="#ea580c",
                  lw=2.0, alpha=0.28, zorder=2)
    swept = Polygon([(0, 0)] * 4, fc="#38bdf8", ec="#0284c7",
                    lw=1.8, alpha=0.30, zorder=3)
    current = Polygon([(0, 0)] * 4, fc="none", ec="#db2777",
                      lw=1.7, ls="--", zorder=4)
    chassis = Polygon([(0, 0)] * 4, fc="#64748b", ec="#1e293b", lw=1.2, zorder=6)
    trailer = Polygon([(0, 0)] * 4, fc="#0284c7", ec="black", lw=1.8, zorder=7)
    cab = Polygon([(0, 0)] * 4, fc="#334155", ec="black", lw=1.8, zorder=8)
    for patch in (dhz, swept, current, chassis, trailer, cab):
        ax.add_patch(patch)
    steer_path_line, = ax.plot([], [], color="#16a34a", lw=1.4, ls="--", zorder=5)
    trailer_axle_line, = ax.plot([], [], color="#7c3aed", lw=1.5, ls=":", zorder=5)

    ax.scatter([0], [0], c="#22c55e", marker="+", s=120, lw=2.5, zorder=10)
    hitch = ax.scatter([config.D_HITCH], [0], c="#facc15",
                       edgecolor="black", s=70, zorder=10)
    handles = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#fb923c",
               ms=12, alpha=0.55, label="DHZ: vùng quét + clearance động"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#38bdf8",
               ms=12, alpha=0.60, label="Swept occupancy của chính xe"),
        Line2D([0], [0], color="#db2777", lw=1.7, ls="--",
               label="Thân xe hiện tại + clearance cơ sở"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#0284c7",
               ms=11, label="Rơ-moóc"),
        Line2D([0], [0], color="#16a34a", lw=1.4, ls="--",
               label="Vệt tâm trục lái đầu kéo"),
        Line2D([0], [0], color="#7c3aed", lw=1.5, ls=":",
               label="Vệt tâm trục rơ-moóc"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8.3, framealpha=0.94)
    info = ax.text(0.985, 0.98, "", transform=ax.transAxes, ha="right", va="top",
                   fontsize=8.8, fontfamily="monospace", color="white",
                   bbox=dict(boxstyle="round,pad=0.45",
                             facecolor="#0f172a", alpha=0.9))

    speed_ax = plt.axes([0.14, 0.175, 0.66, 0.022])
    yaw_ax = plt.axes([0.14, 0.130, 0.66, 0.022])
    ax_ax = plt.axes([0.14, 0.085, 0.66, 0.022])
    ay_ax = plt.axes([0.14, 0.040, 0.66, 0.022])
    reset_ax = plt.axes([0.86, 0.065, 0.08, 0.10])
    speed = Slider(speed_ax, "Vận tốc dọc có dấu vₓ (km/h): âm = lùi",
                   -30, 90, valinit=30, valstep=1)
    yaw = Slider(yaw_ax, "IMU r — yaw-rate đầu kéo (°/s, không phải γ)",
                 -30, 30, valinit=0, valstep=0.5)
    accel_x = Slider(ax_ax, "IMU aₓ (m/s²)", -5, 3, valinit=0, valstep=0.1)
    accel_y = Slider(ay_ax, "IMU aᵧ (m/s²)", -5, 5, valinit=0, valstep=0.1)
    reset = Button(reset_ax, "Reset", color="#e2e8f0", hovercolor="#cbd5e1")

    def redraw(_event=None):
        speed_mps = speed.val / 3.6
        yaw_rad_s = math.radians(yaw.val)
        # Khi tiến, dùng nghiệm quay xác lập để tạo một ảnh chụp minh họa.
        # Khi lùi, nghiệm này không ổn định nên giả định xe bắt đầu thẳng hàng
        # (gamma0=0). Hệ thống thật phải tích phân gamma từ lịch sử cảm biến.
        gamma_est = (0.0 if speed_mps < 0.0 else
                     calculator.estimate_steady_state_gamma(speed_mps, yaw_rad_s))
        result = calculator.compute(
            speed_mps=speed_mps,
            yaw_rate_rad_s=yaw_rad_s,
            longitudinal_accel_mps2=accel_x.val,
            lateral_accel_mps2=accel_y.val,
            gamma_rad=gamma_est,
        )
        vehicle = result["vehicle"]
        cab.set_xy(vehicle["cab"])
        chassis.set_xy(vehicle["chassis"])
        trailer.set_xy(vehicle["trailer"])
        hitch.set_offsets([vehicle["pivot"]])
        current.set_xy(result["current_safety_envelope"])
        swept.set_xy(result["raw_swept_path"])
        dhz.set_xy(result["dynamic_hazard_zone"])
        paths = result["reference_paths"]
        steer_path_line.set_data(*zip(*paths["tractor_steer_axle"]))
        trailer_axle_line.set_data(*zip(*paths["trailer_axle"]))

        metrics = result["metrics"]
        curvature = metrics["curvature_1pm"]
        turn = "TRÁI" if curvature > 1e-5 else (
            "PHẢI" if curvature < -1e-5 else "THẲNG")
        radius = metrics["turning_radius_m"]
        radius_text = "∞" if math.isinf(radius) else f"{radius:.1f} m"
        motion = {"forward": "TIẾN", "reverse": "LÙI",
                  "stationary": "ĐỨNG YÊN"}[metrics["motion_direction"]]
        offtracking = metrics["steady_state_offtracking_reference_m"]
        offtracking_text = "N/A" if offtracking is None else f"{offtracking:.2f} m"
        reverse_note = " / LÙI KHÔNG ỔN ĐỊNH" if speed.val < 0 else ""
        plausible = "OK" if metrics["state_is_plausible"] else "KHÔNG HỢP LÝ"
        info.set_text(
            f"v_x có dấu  = {speed.val:+5.1f} km/h ({motion})\n"
            f"IMU yaw     = {yaw.val:+5.1f} deg/s\n"
            f"IMU a_x     = {accel_x.val:+5.1f} m/s²\n"
            f"IMU a_y     = {accel_y.val:+5.1f} m/s²\n"
            f"quỹ đạo     = {turn}; R = {radius_text}\n"
            f"gamma đầu   = {math.degrees(gamma_est):+5.1f} deg{reverse_note}\n"
            f"gamma cuối  = {metrics['predicted_gamma_deg']:+5.1f} deg\n"
            f"quãng quét  = {metrics['preview_distance_m']:5.2f} m\n"
            f"offtrack ref= {offtracking_text}\n"
            f"tail swing  = {metrics['tail_swing_rotation_reference_m']:.2f} m\n"
            f"a_y expected= {metrics['expected_lateral_accel_mps2']:+5.2f}\n"
            f"a_y residual= {metrics['lateral_residual_mps2']:+5.2f}\n"
            f"clearance   = {metrics['dynamic_clearance_m']:5.2f} m\n"
            f"state       = {plausible}"
        )
        fig.canvas.draw_idle()

    for slider in (speed, yaw, accel_x, accel_y):
        slider.on_changed(redraw)

    def reset_all(_event):
        for slider in (speed, yaw, accel_x, accel_y):
            slider.reset()

    reset.on_clicked(reset_all)
    redraw()
    plt.show()


if __name__ == "__main__":
    main()
