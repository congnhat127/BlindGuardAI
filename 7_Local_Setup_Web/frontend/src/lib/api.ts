/** Client goi API. Mot cho duy nhat biet duong dan va cach xu ly loi. */

import type {
  CameraConfig,
  CameraId,
  CameraStatusRow,
  CommissioningReport,
  Correspondence,
  DeriveResponse,
  Diagnostics,
  Dictionary,
  GridLine,
  Health,
  Point,
  ProfileSummary,
  ReferenceCone,
  SanityWarning,
  SolveResponse,
  Telemetry,
  VehicleBase,
  VehicleProfile,
  VehicleTemplate,
  VerifyResponse,
  ZonePreview,
} from './types'

const BASE = '/api'

/** Ma PIN duoc giu trong bo nho phien, khong ghi vao localStorage. */
let setupPin = ''
export function setSetupPin(pin: string) {
  setupPin = pin
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body) headers.set('Content-Type', 'application/json')
  if (setupPin) headers.set('X-Setup-Pin', setupPin)

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers })
  } catch {
    // Tren xe, mat Wi-Fi la chuyen thuong xuyen. Noi ro de tho biet phai lam gi.
    throw new ApiError(
      'Mat ket noi tới thiết bị. Kiểm tra lại Wi-Fi của xe rồi thử lại — bản nháp đã được giữ.',
      0,
    )
  }

  if (!response.ok) {
    let detail: unknown
    let message = `Lỗi ${response.status}`
    try {
      const body = await response.json()
      detail = body?.detail ?? body
      if (typeof detail === 'string') message = detail
      else if (Array.isArray(detail)) {
        message = detail
          .map((item: { loc?: string[]; msg?: string }) =>
            `${(item.loc ?? []).slice(1).join('.')}: ${item.msg ?? ''}`.trim(),
          )
          .join('; ')
      }
    } catch {
      message = `${message} ${response.statusText}`.trim()
    }
    throw new ApiError(message, response.status, detail)
  }

  if (response.status === 204) return undefined as T
  const text = await response.text()
  return (text ? JSON.parse(text) : undefined) as T
}

const json = (body: unknown) => ({ body: JSON.stringify(body) })

export const api = {
  // --- He thong ---
  health: () => request<Health>('/health'),
  diagnostics: (profileId?: string) =>
    request<Diagnostics>(`/diagnostics${profileId ? `?profile_id=${profileId}` : ''}`),
  telemetry: () => request<Telemetry>('/telemetry'),
  dictionary: () => request<Dictionary>('/dictionary'),
  templates: () => request<{ templates: VehicleTemplate[] }>('/templates'),

  // --- Hinh hoc ---
  derive: (base: VehicleBase) =>
    request<DeriveResponse>('/derive', { method: 'POST', ...json(base) }),

  zonesPreview: (payload: {
    profile: VehicleProfile
    speed_kmh: number
    control_value_deg: number
    control_mode?: 'yaw_rate' | 'steering_angle'
    settle_seconds?: number
  }) => request<ZonePreview>('/zones/preview', { method: 'POST', ...json(payload) }),

  zonesSweep: (payload: {
    profile: VehicleProfile
    speed_kmh: number
    control_mode?: 'yaw_rate' | 'steering_angle'
    values_deg: number[]
  }) => request<{ frames: ZonePreview[] }>('/zones/sweep', { method: 'POST', ...json(payload) }),

  pointTest: (payload: {
    profile: VehicleProfile
    point: Point
    speed_kmh: number
    control_value_deg: number
  }) =>
    request<{ point: Point; inside_zones: string[]; is_dangerous: boolean }>('/zones/point-test', {
      method: 'POST',
      ...json(payload),
    }),

  // --- Ho so ---
  listProfiles: () => request<{ profiles: ProfileSummary[] }>('/profiles'),
  getProfile: (id: string) => request<VehicleProfile>(`/profiles/${id}`),
  scaffold: (payload: {
    profile_id: string
    display_name?: string
    plate_number?: string
    installer_name?: string
    template_id?: string | null
  }) => request<VehicleProfile>('/profiles/scaffold', { method: 'POST', ...json(payload) }),
  saveProfile: (profile: VehicleProfile, force = false) =>
    request<{ profile: VehicleProfile; saved_at: string; warnings: SanityWarning[] }>(
      `/profiles/${profile.meta.profile_id}?force=${force}`,
      { method: 'PUT', ...json(profile) },
    ),
  deleteProfile: (id: string) => request<{ deleted: string }>(`/profiles/${id}`, { method: 'DELETE' }),
  versions: (id: string) =>
    request<{ versions: { version: string; size_bytes: number; saved_at: string }[] }>(
      `/profiles/${id}/versions`,
    ),
  restoreVersion: (id: string, version: string) =>
    request<VehicleProfile>(`/profiles/${id}/versions/${version}/restore`, { method: 'POST' }),
  previewExport: (id: string, fmt: 'python' | 'yaml') =>
    request<{ format: string; content: string; lines: number }>(
      `/profiles/${id}/preview-export?fmt=${fmt}`,
    ),
  report: (id: string) => request<CommissioningReport>(`/profiles/${id}/report`),
  importProfile: (content: string, newProfileId?: string) =>
    request<VehicleProfile>('/profiles/import', {
      method: 'POST',
      ...json({ content, new_profile_id: newProfileId ?? null }),
    }),
  exportUrl: (id: string, fmt: 'python' | 'yaml') => `${BASE}/profiles/${id}/export?fmt=${fmt}`,

  saveDraft: (id: string, data: unknown) =>
    request<{ saved: boolean }>(`/profiles/${id}/draft`, { method: 'PUT', ...json({ data }) }),
  loadDraft: (id: string) =>
    request<{ exists: boolean; draft: { saved_at: string; data: unknown } | null }>(
      `/profiles/${id}/draft`,
    ),
  dropDraft: (id: string) => request<{ deleted: boolean }>(`/profiles/${id}/draft`, { method: 'DELETE' }),

  // --- Camera ---
  cameraStatus: (profileId: string) =>
    request<{ backend: string; cameras: CameraStatusRow[] }>(`/cameras/${profileId}/status`),
  snapshotUrl: (profileId: string, cameraId: CameraId, bust = Date.now()) =>
    `${BASE}/cameras/${profileId}/${cameraId}/snapshot?t=${bust}`,
  streamUrl: (profileId: string, cameraId: CameraId) =>
    `${BASE}/cameras/${profileId}/${cameraId}/stream`,
  imageStatus: (profileId: string, cameraId: CameraId) =>
    request<{ camera_id: CameraId; has_uploaded_image: boolean; image_size: [number, number] | null }>(
      `/cameras/${profileId}/${cameraId}/image-status`,
    ),
  uploadCameraImage: async (profileId: string, cameraId: CameraId, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const headers = new Headers()
    if (setupPin) headers.set('X-Setup-Pin', setupPin)
    const response = await fetch(`${BASE}/cameras/${profileId}/${cameraId}/image`, {
      method: 'POST',
      body: form,
      headers,
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new ApiError(body?.detail ?? 'Tải ảnh thất bại.', response.status, body)
    }
    return (await response.json()) as { uploaded: boolean; image_size: [number, number] }
  },
  deleteCameraImage: (profileId: string, cameraId: CameraId) =>
    request<{ deleted: boolean }>(`/cameras/${profileId}/${cameraId}/image`, { method: 'DELETE' }),
  referenceCones: (profileId: string, cameraId: CameraId) =>
    request<{ camera_id: CameraId; cones: ReferenceCone[]; note: string }>(
      `/cameras/${profileId}/${cameraId}/reference-cones`,
    ),
  projectGrid: (payload: {
    camera: CameraConfig
    x_range?: [number, number]
    y_range?: [number, number]
    step?: number
  }) =>
    request<{ lines: GridLine[]; image_size: [number, number] }>('/cameras/project-grid', {
      method: 'POST',
      ...json(payload),
    }),
  project: (payload: { camera: CameraConfig; ground_points: Point[]; z?: number }) =>
    request<{ pixels: (Point | null)[] }>('/cameras/project', { method: 'POST', ...json(payload) }),
  unproject: (payload: { camera: CameraConfig; pixels: Point[] }) =>
    request<{
      points: {
        pixel: Point
        ground: Point | null
        distance_from_origin_m: number | null
        side: string | null
      }[]
    }>('/cameras/unproject', { method: 'POST', ...json(payload) }),
  solveAngles: (payload: {
    camera: CameraConfig
    points: Correspondence[]
    solve_height?: boolean
  }) => request<SolveResponse>('/cameras/solve-angles', { method: 'POST', ...json(payload) }),
  verifyPoints: (payload: { camera: CameraConfig; points: Correspondence[] }) =>
    request<VerifyResponse>('/cameras/verify', { method: 'POST', ...json(payload) }),
  commitCamera: (profileId: string, cameraId: CameraId, camera: CameraConfig, rms: number | null) =>
    request<{ camera: CameraConfig; calibrated_count: number; total: number }>(
      `/cameras/${profileId}/${cameraId}`,
      { method: 'PUT', ...json({ camera, rms_m: rms }) },
    ),
}
