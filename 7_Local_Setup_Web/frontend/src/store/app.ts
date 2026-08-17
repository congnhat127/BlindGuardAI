/**
 * Trang thai ung dung.
 *
 * Nguyen tac: ho so dang sua luon nam trong bo nho, va duoc ghi ban nhap sang
 * server sau moi thay doi (co giam tan). Wi-Fi cua xe hay rot giua buoi lap dat;
 * mat 30 phut cong nhap lieu la khong the chap nhan.
 */

import { create } from 'zustand'
import { api, ApiError } from '../lib/api'
import type {
  CameraConfig,
  CameraId,
  Dictionary,
  Health,
  Physics,
  ProfileMeta,
  SanityWarning,
  VehicleBase,
  VehicleProfile,
  VehicleTemplate,
  ZoneParams,
} from '../lib/types'

export type StepId = 'identity' | 'dimensions' | 'cameras' | 'calibrate' | 'zones' | 'review'

export const STEPS: { id: StepId; label: string; hint: string }[] = [
  { id: 'identity', label: 'Hồ sơ xe', hint: 'Biển số, loại xe, mẫu cấu hình' },
  { id: 'dimensions', label: 'Kích thước', hint: '4 số từ sổ đăng kiểm' },
  { id: 'cameras', label: 'Lắp camera', hint: 'Vị trí, ống kính, nguồn tín hiệu' },
  { id: 'calibrate', label: 'Căn chỉnh', hint: 'Chạm vật mốc, giải góc lắp' },
  { id: 'zones', label: 'Vùng mù', hint: 'Tham số và mô phỏng' },
  { id: 'review', label: 'Nghiệm thu', hint: 'Kiểm tra, xuất cấu hình' },
]

const DRAFT_DEBOUNCE_MS = 1200

interface AppState {
  // Du lieu tham chieu, nap mot lan
  health: Health | null
  dictionary: Dictionary | null
  templates: VehicleTemplate[]
  bootError: string | null
  booted: boolean

  // Ho so dang sua
  profile: VehicleProfile | null
  savedSnapshot: string | null
  warnings: SanityWarning[]
  saving: boolean
  saveError: string | null
  lastSavedAt: string | null
  draftSavedAt: string | null

  step: StepId

  boot: () => Promise<void>
  setStep: (step: StepId) => void
  openProfile: (id: string) => Promise<void>
  createProfile: (payload: {
    profile_id: string
    display_name?: string
    plate_number?: string
    installer_name?: string
    template_id?: string | null
  }) => Promise<void>
  closeProfile: () => void

  patchMeta: (patch: Partial<ProfileMeta>) => void
  patchBase: (patch: Partial<VehicleBase>) => void
  patchPhysics: (patch: Partial<Physics>) => void
  patchZones: (patch: Partial<ZoneParams>) => void
  patchCamera: (cameraId: CameraId, patch: Partial<CameraConfig>) => void
  applyTemplate: (templateId: string) => void

  save: (force?: boolean) => Promise<boolean>
  isDirty: () => boolean
}

let draftTimer: ReturnType<typeof setTimeout> | undefined

function fingerprint(profile: VehicleProfile | null): string | null {
  if (!profile) return null
  // Bo qua updated_at: no doi moi lan luu nen se lam co dirty bao sai.
  const { meta, ...rest } = profile
  const { updated_at: _ignored, ...metaRest } = meta
  return JSON.stringify({ meta: metaRest, ...rest })
}

export const useApp = create<AppState>((set, get) => {
  /**
   * Cap nhat ho so + hen gio ghi ban nhap.
   * Vi tri cac truong `auto_position` cua camera duoc tinh lai o backend khi luu,
   * nen o day khong tu suy - tranh hai nguon su that.
   */
  function mutate(updater: (profile: VehicleProfile) => VehicleProfile) {
    const current = get().profile
    if (!current) return
    const next = updater(structuredClone(current))
    set({ profile: next })

    clearTimeout(draftTimer)
    draftTimer = setTimeout(() => {
      api
        .saveDraft(next.meta.profile_id, next)
        .then(() => set({ draftSavedAt: new Date().toISOString() }))
        .catch(() => {
          /* Mat mang thi im lang: lan sua tiep theo se thu lai. */
        })
    }, DRAFT_DEBOUNCE_MS)
  }

  return {
    health: null,
    dictionary: null,
    templates: [],
    bootError: null,
    booted: false,
    profile: null,
    savedSnapshot: null,
    warnings: [],
    saving: false,
    saveError: null,
    lastSavedAt: null,
    draftSavedAt: null,
    step: 'identity',

    boot: async () => {
      try {
        const [health, dictionary, templates] = await Promise.all([
          api.health(),
          api.dictionary(),
          api.templates(),
        ])
        set({
          health,
          dictionary,
          templates: templates.templates,
          booted: true,
          bootError: health.engine.available
            ? null
            : `Không nạp được engine vùng mù: ${health.engine.error ?? 'không rõ nguyên nhân'}`,
        })
      } catch (error) {
        set({
          booted: true,
          bootError:
            error instanceof ApiError
              ? error.message
              : 'Không kết nối được backend. Kiểm tra lại server đang chạy chưa.',
        })
      }
    },

    setStep: (step) => set({ step }),

    openProfile: async (id) => {
      const profile = await api.getProfile(id)
      // Uu tien ban nhap neu no moi hon ban da luu.
      let restored = profile
      try {
        const draft = await api.loadDraft(id)
        if (draft.exists && draft.draft) {
          const candidate = draft.draft.data as VehicleProfile
          if (
            candidate?.meta?.profile_id === id &&
            new Date(draft.draft.saved_at) > new Date(profile.meta.updated_at)
          ) {
            restored = candidate
          }
        }
      } catch {
        /* Khong co ban nhap thi thoi. */
      }
      set({
        profile: restored,
        savedSnapshot: fingerprint(profile),
        step: 'identity',
        warnings: [],
        saveError: null,
        lastSavedAt: profile.meta.updated_at,
      })
    },

    createProfile: async (payload) => {
      const profile = await api.scaffold(payload)
      set({
        profile,
        savedSnapshot: null,
        step: 'dimensions',
        warnings: [],
        saveError: null,
        lastSavedAt: null,
      })
    },

    closeProfile: () => {
      clearTimeout(draftTimer)
      set({ profile: null, savedSnapshot: null, warnings: [], step: 'identity' })
    },

    patchMeta: (patch) => mutate((profile) => ({ ...profile, meta: { ...profile.meta, ...patch } })),
    patchBase: (patch) => mutate((profile) => ({ ...profile, base: { ...profile.base, ...patch } })),
    patchPhysics: (patch) =>
      mutate((profile) => ({ ...profile, physics: { ...profile.physics, ...patch } })),
    patchZones: (patch) =>
      mutate((profile) => ({ ...profile, zones: { ...profile.zones, ...patch } })),
    patchCamera: (cameraId, patch) =>
      mutate((profile) => ({
        ...profile,
        cameras: {
          ...profile.cameras,
          [cameraId]: { ...profile.cameras[cameraId], ...patch },
        },
      })),

    applyTemplate: (templateId) => {
      const template = get().templates.find((item) => item.template_id === templateId)
      if (!template) return
      mutate((profile) => ({
        ...profile,
        base: { ...template.base },
        meta: { ...profile.meta, vehicle_type: template.vehicle_type },
      }))
    },

    save: async (force = false) => {
      const profile = get().profile
      if (!profile) return false
      set({ saving: true, saveError: null })
      try {
        const result = await api.saveProfile(profile, force)
        set({
          profile: result.profile,
          savedSnapshot: fingerprint(result.profile),
          warnings: result.warnings,
          saving: false,
          lastSavedAt: result.saved_at,
          draftSavedAt: null,
        })
        return true
      } catch (error) {
        set({
          saving: false,
          saveError: error instanceof ApiError ? error.message : 'Lưu thất bại.',
        })
        return false
      }
    },

    isDirty: () => {
      const { profile, savedSnapshot } = get()
      if (!profile) return false
      return fingerprint(profile) !== savedSnapshot
    },
  }
})
