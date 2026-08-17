/**
 * Buoc 2: 4 thong so co ban tu so dang kiem.
 *
 * Diem manh nhat cua man hinh nay: so do top-down ve lai theo tung ky tu vua
 * nhap, va khi con tro dat vao mot o thi so do TO DO dung khoang cach dang do
 * kem mui ten. Ky thuat vien nhin hinh la biet phai do cai gi.
 *
 * Duoi cung la bang 25 thong so tu suy ra kem CAN CU TIEU CHUAN cua tung so.
 * Neu chi hien con so ma khong noi tu dau ra thi khong ai tin va se doi tay.
 */

import { useEffect, useMemo, useState } from 'react'
import { api } from '../../lib/api'
import type { DeriveResponse } from '../../lib/types'
import { Callout, DataRow, Field, NumberInput, Panel } from '../../components/ui'
import { TopDownView, type DimensionKey } from '../../components/TopDownView'
import { useApp } from '../../store/app'

const FIELDS: {
  key: keyof DeriveResponse['base']
  dim: DimensionKey
  label: string
  hint: string
  min: number
  max: number
}[] = [
  {
    key: 'wheelbase_tractor',
    dim: 'wheelbase_tractor',
    label: 'Chiều dài cơ sở đầu kéo (L_f)',
    hint: 'Tâm trục bánh trước → tâm trục bánh sau',
    min: 2.5,
    max: 7,
  },
  {
    key: 'cab_width',
    dim: 'cab_width',
    label: 'Chiều rộng cabin (W_cab)',
    hint: 'Rộng tổng thể, không tính gương',
    min: 1.8,
    max: 2.8,
  },
  {
    key: 'l_trail',
    dim: 'l_trail',
    label: 'Chiều dài rơ-moóc (L_trail)',
    hint: 'Chốt kéo → tâm cụm trục bánh sau moóc',
    min: 3,
    max: 16,
  },
  {
    key: 'w_trail',
    dim: 'w_trail',
    label: 'Chiều rộng rơ-moóc (W_trail)',
    hint: 'Rộng tổng thể thùng',
    min: 1.8,
    max: 3,
  },
  {
    key: 'driver_height',
    dim: 'driver_height',
    label: 'Chiều cao tài xế',
    hint: 'Dùng để suy ra độ cao tầm mắt, ảnh hưởng trực tiếp vùng mù mũi xe',
    min: 1.4,
    max: 2.1,
  },
]

export function StepDimensions() {
  const { profile, patchBase, dictionary } = useApp()
  const [derived, setDerived] = useState<DeriveResponse | null>(null)
  const [focused, setFocused] = useState<DimensionKey>(null)
  const [error, setError] = useState<string | null>(null)

  const base = profile?.base

  useEffect(() => {
    if (!base) return
    let cancelled = false
    const timer = setTimeout(() => {
      api
        .derive(base)
        .then((response) => {
          if (!cancelled) {
            setDerived(response)
            setError(null)
          }
        })
        .catch((exception) => {
          if (!cancelled) setError(exception?.message ?? 'Không suy được hình học.')
        })
    }, 180)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [base])

  const warningsByField = useMemo(() => {
    const map: Record<string, string[]> = {}
    for (const warning of derived?.warnings ?? []) {
      map[warning.field] = [...(map[warning.field] ?? []), warning.message]
    }
    return map
  }, [derived])

  if (!profile || !base) return null

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[380px_1fr]">
        <Panel
          title="4 thông số từ sổ đăng kiểm"
          subtitle="Chỉ cần 4 số này, 25 thông số còn lại tự suy ra"
        >
          <div className="space-y-3">
            {FIELDS.map((field) => (
              <Field
                key={field.key}
                label={field.label}
                hint={field.hint}
                error={warningsByField[field.key]?.join(' ')}
              >
                <NumberInput
                  value={base[field.key]}
                  min={field.min}
                  max={field.max}
                  step={0.01}
                  invalid={Boolean(warningsByField[field.key])}
                  onChange={(value) => patchBase({ [field.key]: value })}
                  onFocus={() => setFocused(field.dim)}
                  onBlur={() => setFocused(null)}
                />
              </Field>
            ))}
          </div>

          {error && (
            <div className="mt-3">
              <Callout tone="bad">{error}</Callout>
            </div>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel
            title="Sơ đồ nhìn từ trên xuống"
            subtitle="Đặt con trỏ vào một ô số để thấy đúng khoảng cách cần đo"
            dense
          >
            {derived ? (
              <TopDownView
                geometry={derived.geometry}
                dictionary={dictionary}
                highlight={focused}
                className="max-h-[420px]"
              />
            ) : (
              <div className="h-64 animate-pulse bg-ink-50" />
            )}
          </Panel>

          {derived && (
            <div className="grid gap-3 sm:grid-cols-3">
              <Panel dense className="px-4 py-3">
                <div className="label-caps">Tổng chiều dài</div>
                <div className="num text-xl font-semibold">
                  {derived.geometry.total_length.toFixed(2)}
                  <span className="ml-1 text-sm font-normal text-ink-500">m</span>
                </div>
              </Panel>
              <Panel dense className="px-4 py-3">
                <div className="label-caps">Chiều rộng lớn nhất</div>
                <div className="num text-xl font-semibold">
                  {derived.geometry.max_width.toFixed(2)}
                  <span className="ml-1 text-sm font-normal text-ink-500">m</span>
                </div>
              </Panel>
              <Panel dense className="px-4 py-3">
                <div className="label-caps">Độ cao tầm mắt</div>
                <div className="num text-xl font-semibold">
                  {derived.geometry.eye_z.toFixed(2)}
                  <span className="ml-1 text-sm font-normal text-ink-500">m</span>
                </div>
              </Panel>
            </div>
          )}
        </div>
      </div>

      {derived && <DerivedTable derived={derived} />}
    </div>
  )
}

function DerivedTable({ derived }: { derived: DeriveResponse }) {
  const { geometry, basis } = derived
  const rows: { key: string; label: string; value: string }[] = [
    { key: 'CAB_FRONT_X', label: 'Mũi xe', value: `${geometry.cab_front_x.toFixed(2)} m` },
    { key: 'CAB_REAR_X', label: 'Vách sau cabin', value: `${geometry.cab_rear_x.toFixed(2)} m` },
    { key: 'D_HITCH', label: 'Chốt kéo', value: `${geometry.d_hitch.toFixed(2)} m` },
    {
      key: 'TRAIL_OVERHANG',
      label: 'Nhô rơ-moóc trước chốt kéo',
      value: `${geometry.trail_overhang.toFixed(2)} m`,
    },
    {
      key: 'CHASSIS_HALF_W',
      label: 'Nửa rộng khung gầm',
      value: `${geometry.chassis_half_w.toFixed(2)} m`,
    },
    {
      key: 'EYE_X',
      label: 'Mắt tài xế (dọc)',
      value: `${geometry.eye_x.toFixed(2)} m`,
    },
    { key: 'EYE_Y', label: 'Mắt tài xế (ngang)', value: `${geometry.eye_y.toFixed(2)} m` },
    { key: 'EYE_Z', label: 'Độ cao tầm mắt', value: `${geometry.eye_z.toFixed(2)} m` },
    {
      key: 'MIRROR_X',
      label: 'Gương (dọc)',
      value: `${geometry.mirror_r_x.toFixed(2)} m`,
    },
    {
      key: 'MIRROR_Y',
      label: 'Gương (ngang)',
      value: `±${Math.abs(geometry.mirror_r_y).toFixed(2)} m`,
    },
    {
      key: 'A_PILLAR',
      label: 'Cột A',
      value: `${geometry.a_pillar_r_x.toFixed(2)} ; ±${Math.abs(geometry.a_pillar_r_y).toFixed(2)} m`,
    },
    {
      key: 'B_PILLAR',
      label: 'Cột B',
      value: `${geometry.b_pillar_r_x.toFixed(2)} ; ±${Math.abs(geometry.b_pillar_r_y).toFixed(2)} m`,
    },
  ]

  return (
    <Panel
      title="Thông số tự suy ra"
      subtitle="Mỗi con số đều có căn cứ tiêu chuẩn, không phải hệ số tuỳ ý"
      dense
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-[13px]">
          <thead>
            <tr className="border-b border-ink-200 bg-ink-50">
              <th className="px-4 py-2 font-semibold text-ink-700">Đại lượng</th>
              <th className="px-4 py-2 font-semibold text-ink-700">Giá trị</th>
              <th className="px-4 py-2 font-semibold text-ink-700">Công thức</th>
              <th className="px-4 py-2 font-semibold text-ink-700">Căn cứ</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const meta = basis[row.key]
              return (
                <tr key={row.key} className="border-b border-ink-100 last:border-0">
                  <td className="px-4 py-1.5 text-ink-900">{meta?.label ?? row.label}</td>
                  <td className="num px-4 py-1.5 font-semibold text-ink-900">{row.value}</td>
                  <td className="num px-4 py-1.5 text-ink-600">{meta?.formula ?? '—'}</td>
                  <td className="px-4 py-1.5 text-ink-500">{meta?.standard ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className="border-t border-ink-200 px-4 py-2">
        <DataRow
          label="Vị trí lắp 3 camera (suy ra từ gương và mũi xe)"
          value={Object.entries(derived.camera_positions)
            .map(([id, position]) => `${id} (${position.map((v) => v.toFixed(2)).join(', ')})`)
            .join('   ')}
        />
      </div>
    </Panel>
  )
}
