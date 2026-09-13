import math

def rotate_pt(x, y, angle, pivot=(0,0)):
    c, s = math.cos(angle), math.sin(angle)
    px, py = pivot
    return ((x-px)*c - (y-py)*s + px, (x-px)*s + (y-py)*c + py)

# Test ray casting side zone
def get_right_side_zone(gamma):
    cab_front_x = 3.5
    cab_rear_x = 1.5
    hw_c = 1.25
    hw_t = 1.25
    d_hitch = 0.3
    l_trail = 12.0
    pivot = (d_hitch, 0)
    
    trail_front = d_hitch + 1.0 # 1.3
    trail_rear = d_hitch - l_trail # -11.7
    
    # Trailer corners rotated
    t_fr = rotate_pt(trail_front, -hw_t, -gamma, pivot)
    t_rr = rotate_pt(trail_rear, -hw_t, -gamma, pivot)
    
    # Outer width at rear
    extra_r = l_trail * abs(math.sin(gamma)) if gamma < 0 else 0.0
    outer_width = 4.0 + extra_r
    
    # Outer rear corner
    # Direction vector of trailer rear edge
    t_rl = rotate_pt(trail_rear, hw_t, -gamma, pivot)
    # Rear vector pointing right (from left rear to right rear)
    dx = t_rr[0] - t_rl[0]
    dy = t_rr[1] - t_rl[1]
    norm = math.sqrt(dx**2 + dy**2)
    ux, uy = dx/norm, dy/norm
    
    t_outer_rear = (t_rr[0] + ux * outer_width, t_rr[1] + uy * outer_width)
    
    # Mirror position
    mirror = (cab_front_x, -hw_c)
    cab_rear = (cab_rear_x, -hw_c)
    
    # Construct clean convex polygon from mirror around the trailer to outer rear back to mirror
    if gamma < 0: # Turning right: trailer bends right towards mirror
        polygon = [
            mirror,
            cab_rear,
            t_fr,
            t_rr,
            t_outer_rear,
            (cab_front_x - 1.0, -hw_c - 2.0) # outer front near mirror
        ]
    else: # Turning left: trailer bends away to left
        polygon = [
            mirror,
            cab_rear,
            t_rr,
            t_outer_rear,
            (cab_front_x - 1.0, -hw_c - 2.0)
        ]
    return polygon

print("Right zone gamma=-0.3 rad:", get_right_side_zone(-0.3))
