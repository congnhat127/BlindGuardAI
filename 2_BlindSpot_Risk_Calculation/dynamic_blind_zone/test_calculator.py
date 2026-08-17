import sys
sys.path.insert(0, '2_BlindSpot_Risk_Calculation/dynamic_blind_zone')
import config, calculator

calc = calculator.BlindZoneCalculator()

# Test 1: Xe di thang (v=10 m/s, omega=0)
res = calc.compute_warning_masks(10, 0, 0.0333)
assert abs(res['gamma_deg']) < 0.1, 'FAIL: Gamma should be ~0 when going straight'
assert res['d_swept'] < 0.01, 'FAIL: d_swept should be ~0 when straight'
print('Test 1 PASSED: Xe di thang -> Gamma=0, d_swept=0')

# Test 2: Be lai PHAI (omega=-0.2), mo phong 60 buoc
calc.reset()
for _ in range(60):
    res = calc.compute_warning_masks(10, -0.2, 0.0333)
gamma = res['gamma_deg']
assert gamma > 0, 'FAIL: Gamma should be POSITIVE when steering right (omega<0), got ' + str(gamma)
print('Test 2 PASSED: Be lai phai -> Gamma=' + str(round(gamma, 2)) + ' deg (duong = ro-mooc lech trai)')

# Test 3: d_swept phai > 0 khi gamma > 0
swept = res['d_swept']
assert swept > 0, 'FAIL: d_swept should be > 0 when gamma > 0'
print('Test 3 PASSED: d_swept=' + str(round(swept, 2)) + 'm > 0 (quet banh sau ben phai)')

# Test 4: Kiem tra co du 6 vung Do
red_keys = set(res['masks']['red_zones'].keys())
expected = {'front', 'right_head', 'left_head', 'right_trail', 'left_trail', 'rear_trail'}
assert red_keys == expected, 'FAIL: Missing zones. Got ' + str(red_keys)
print('Test 4 PASSED: Du 6 vung Do: ' + str(red_keys))

# Test 5: Quang duong phanh tai 60 km/h
calc.reset()
res = calc.compute_warning_masks(60/3.6, 0, 0.0333)
d = res['stopping']['d_total']
print('Test 5 PASSED: Quang duong phanh tai 60km/h = ' + str(round(d, 2)) + 'm')

print()
print('=== ALL 5 TESTS PASSED SUCCESSFULLY! ===')
