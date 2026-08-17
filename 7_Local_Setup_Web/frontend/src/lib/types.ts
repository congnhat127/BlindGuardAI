/**
 * Kieu du lieu phan chieu schema Pydantic o backend.
 * Doi ben backend thi phai doi o day - khong co buoc sinh code tu dong.
 */

export type VehicleType = 'articulated' | 'rigid'
export type CameraId = 'MIRROR_R' | 'MIRROR_L' | 'FRONT_CAM'
export type Verdict = 'pass' | 'warn' | 'fail'
export type CheckStatus = 'pass' | 'warn' | 'error'

export interface Intrinsics {
  fx: number
  fy: number
  cx: number
  cy: number
}

export interface CameraConfig {
  enabled: boolean
  label: string
  source: string
  width: number
  height: number
  intrinsics: Intrinsics
  auto_position: boolean
  position: [number, number, number] | null
  pitch_deg: number
  yaw_deg: number
  roll_deg: number
  monitored_blind_zones: string[]
  calibration_rms_m: number | null
  calibrated_at: string | null
}

export interface VehicleBase {
  wheelbase_tractor: number
  cab_width: number
  l_trail: number
  w_trail: number
  driver_height: number
}

export interface Physics {
  reaction_time: number
  friction_coeff: number
  gravity: number
  steer_ratio: number
  max_gamma_deg: number
  mechanical_max_gamma_deg: number
}

export interface ZoneParams {
  front_blind_min: number
  side_blind_max: number
  rear_blind_depth: number
  front_red_ratio: number
  a_pillar_width: number
  a_pillar_blind_range: number
}

export interface SensorParams {
  gps_freq: number
  camera_freq: number
  gps_timeout_sec: number
}

export interface ProfileMeta {
  profile_id: string
  display_name: string
  plate_number: string
  vehicle_type: VehicleType
  fleet_name: string
  installer_name: string
  notes: string
  schema_version: number
  created_at: string
  updated_at: string
  commissioned: boolean
}

export interface VehicleProfile {
  meta: ProfileMeta
  base: VehicleBase
  physics: Physics
  zones: ZoneParams
  sensors: SensorParams
  cameras: Record<CameraId, CameraConfig>
}

export interface ProfileSummary {
  profile_id: string
  display_name: string
  plate_number?: string
  vehicle_type?: VehicleType
  commissioned?: boolean
  updated_at?: string
  total_length?: number
  cameras_calibrated?: number
  broken: boolean
  error?: string
}

export interface VehicleTemplate {
  template_id: string
  label: string
  description: string
  vehicle_type: VehicleType
  base: VehicleBase
}

export interface DerivedGeometry {
  cab_half_w: number
  trail_half_w: number
  chassis_half_w: number
  cab_front_x: number
  cab_rear_x: number
  d_hitch: number
  trail_overhang: number
  trail_front_x: number
  trail_rear_x: number
  eye_x: number
  eye_y: number
  eye_z: number
  mirror_r_x: number
  mirror_r_y: number
  mirror_l_x: number
  mirror_l_y: number
  a_pillar_r_x: number
  a_pillar_r_y: number
  a_pillar_l_x: number
  a_pillar_l_y: number
  b_pillar_r_x: number
  b_pillar_r_y: number
  b_pillar_l_x: number
  b_pillar_l_y: number
  total_length: number
  max_width: number
}

export interface SanityWarning {
  field: string
  message: string
}

export interface DerivationBasisEntry {
  label: string
  formula: string
  standard: string
  note: string
}

export interface DeriveResponse {
  base: VehicleBase
  geometry: DerivedGeometry
  camera_positions: Record<CameraId, [number, number, number]>
  warnings: SanityWarning[]
  basis: Record<string, DerivationBasisEntry>
}

export type Point = [number, number]

export interface ZonePreview {
  input: {
    speed_kmh: number
    speed_mps: number
    control_mode: string
    control_value_deg: number
    settle_seconds: number
  }
  state: {
    gamma_deg: number
    yaw_rate_deg_s: number
    heading_deg: number
    turn_radius_m: number | null
    d_swept_m: number
    is_rigid: boolean
  }
  stopping: { d_reaction_m: number; d_braking_m: number; d_total_m: number }
  vehicle: { cab: Point[]; chassis: Point[]; trailer: Point[]; pivot: Point }
  reference_points: Record<string, Point>
  zones: Record<string, Point[]>
}

export interface ZoneDictionaryEntry {
  label: string
  short: string
  color: string
  group: string
  note: string
}

export interface Dictionary {
  zones: Record<string, ZoneDictionaryEntry>
  vehicle_colors: Record<string, string>
  derivation_basis: Record<string, DerivationBasisEntry>
  camera_layout: Record<
    CameraId,
    {
      label: string
      default_pitch_deg: number
      default_yaw_deg: number
      default_roll_deg: number
      monitored_blind_zones: string[]
    }
  >
}

export interface ReferenceCone {
  index: number
  name: string
  color: string
  x: number
  y: number
}

export interface Correspondence {
  u: number
  v: number
  x: number
  y: number
  label?: string
}

export interface SolveResponse {
  ok: boolean
  verdict: Verdict
  message: string
  angles: { pitch_deg: number; yaw_deg: number; roll_deg: number }
  height_m: number
  rms_m: number
  max_error_m: number
  target_m: number
  per_point: {
    label: string
    measured: Point
    estimated: Point | null
    error_m: number | null
    note: string
  }[]
  iterations: number
  roll_solved: boolean
  roll_supported_by_engine: boolean
}

export interface VerifyResponse {
  rms_m: number | null
  max_error_m: number | null
  target_m: number
  verdict: Verdict
  per_point: {
    label: string
    measured: Point
    estimated: Point | null
    error_m: number | null
  }[]
}

export interface GridLine {
  axis: 'x' | 'y'
  value: number
  points: Point[]
}

export interface CameraStatusRow {
  camera_id: CameraId
  label: string
  enabled: boolean
  online: boolean
  backend: string
  resolution: [number, number]
  source: string
  fps: number
  message: string
}

export interface DiagnosticsCheck {
  key: string
  label: string
  status: CheckStatus
  detail: string
}

export interface Telemetry {
  backend: string
  timestamp: number
  gps: {
    fix: boolean
    satellites?: number
    hdop?: number
    latitude?: number
    longitude?: number
    speed_kmh?: number
    course_deg?: number
    is_lost: boolean
    quality: string
  }
  imu: {
    present: boolean
    yaw_rate_deg_s?: number
    pitch_deg?: number
    roll_deg?: number
    temperature_c?: number
  }
  note: string
}

export interface Diagnostics {
  checks: DiagnosticsCheck[]
  cameras: CameraStatusRow[]
  telemetry: Telemetry
  summary: { pass: number; warn: number; error: number }
  environment: {
    python: string
    platform: string
    device_backend: string
    data_dir: string
  }
}

export interface Health {
  status: string
  service: string
  device_backend: 'mock' | 'jetson'
  engine: { available: boolean; path: string; error: string | null }
  time: string
}

export interface CommissioningReport {
  generated_at: string
  meta: ProfileMeta
  base: VehicleBase
  physics: Physics
  zones: ZoneParams
  sensors: SensorParams
  geometry: DerivedGeometry
  cameras: {
    camera_id: CameraId
    label: string
    enabled: boolean
    position: [number, number, number]
    angles: { pitch_deg: number; yaw_deg: number; roll_deg: number }
    resolution: [number, number]
    hfov_deg: number
    calibration_rms_m: number | null
    calibrated_at: string | null
    status: 'pass' | 'warn' | 'fail' | 'not_calibrated'
  }[]
  zones_preview: ZonePreview | null
}
