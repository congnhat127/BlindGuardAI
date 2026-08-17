/**
 * Buoc 5: tham so vung mu + mo phong.
 *
 * Hai vai tro:
 *   - Ky thuat vien kiem tra bang mat vung mu co hop ly voi chiec xe cu the.
 *   - Truoc hoi dong: keo thanh truot toc do / goc be lai va thay vung nguy hiem
 *     bien dang theo - day la vat lieu trinh dien manh nhat cua de tai, chay
 *     truc tiep tren engine that chu khong phai hoat hinh dung san.
 *
 * Cham vao ban do se cho biet diem do co nam trong vung nao (Point-in-Polygon),
 * dung de tu kiem chung: dat vat o vi tri X, he thong co bao khong.
 */

import { useEffect, useMemo, useState } from 'react'
import { api } from '../../lib/api'
import type { Point, ZonePreview } from '../../lib/types'
import { TopDownView } from '../../components/TopDownView'
import {
  Badge,
  Button,
  Callout,
  DataRow,
  Field,
  NumberInput,
  Panel,
  SegmentedControl,
  Slider,
  Toggle,
} from '../../components/ui'
import { useApp } from '../../store/app'

type ControlMode = 'yaw_rate' | 'steering_angle'

export function StepZones() {
  const { profile, patchZones, patchPhysics, dictionary } = useApp()
  const [speed, setSpeed] = useState(12)
  const [control, setControl] = useState(10)
  const [mode, setMode] = useState<ControlMode>('yaw_rate')
  const [preview, setPreview] = useState<ZonePreview | null>(null)
  const [hidden, setHidden] = useState<Record<string, boolean>>({})
  const [picked, setPicked] = useState<Point | null>(null)
  const [pickedZones, setPickedZones] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!profile) return
    let cancelled = false
    const timer = setTimeout(() => {
      api
        .zonesPreview({
          profile,
          speed_kmh: speed,
          control_value_deg: control,
          control_mode: mode,
        })
        .then((response) => {
          if (!cancelled) {
            setPreview(response)
            setError(null)
          }
        })
        .catch((exception) => {
          if (!cancelled) setError(exception?.message ?? 'Không tính được vùng mù.')
        })
    }, 140)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [profile, speed, control, mode])

  const geometry = useMemo(() => {
    if (!profile) return null
    // Suy hinh hoc tu 4 so co ban, khong doi backend: chi dung de dat khung nhin.
    const lf = profile.base.wheelbase_tractor
    const wc = profile.base.cab_width
    const halfCab = wc / 2
    const dHitch = lf * 0.08
    return {
      cab_half_w: halfCab,
      trail_half_w: profile.base.w_trail / 2,
      chassis_half_w: wc * 0.18,
      cab_front_x: lf + 0.4,
      cab_rear_x: lf * 0.61,
      d_hitch: dHitch,
      trail_overhang: lf * 0.25,
      trail_front_x: dHitch + lf * 0.25,
      trail_rear_x: dHitch - profile.base.l_trail,
      eye_x: lf * 0.78,
      eye_y: wc * 0.2,
      eye_z: 2.2 + (profile.base.driver_height - 1.7) * 0.5,
      mirror_r_x: lf * 0.97,
      mirror_r_y: -(halfCab + 0.1),
      mirror_l_x: lf * 0.97,
      mirror_l_y: halfCab + 0.1,
      a_pillar_r_x: lf * 0.97 - 0.1,
      a_pillar_r_y: -(halfCab - 0.05),
      a_pillar_l_x: lf * 0.97 - 0.1,
      a_pillar_l_y: halfCab - 0.05,
      b_pillar_r_x: lf * 0.61,
      b_pillar_r_y: -halfCab,
      b_pillar_l_x: lf * 0.61,
      b_pillar_l_y: halfCab,
      total_length: lf + 0.4 - (dHitch - profile.base.l_trail),
      max_width: Math.max(wc, profile.base.w_trail),
    }
  }, [profile])

  if (!profile || !geometry) return null
  const isRigid = profile.meta.vehicle_type === 'rigid'

  async function pick(point: Point) {
    setPicked(point)
    try {
      const response = await api.pointTest({
        profile: profile!,
        point,
        speed_kmh: speed,
        control_value_deg: control,
      })
      setPickedZones(response.inside_zones)
    } catch {
      setPickedZones([])
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <Panel
          title="Mô phỏng vùng mù động"
          subtitle="Chạm vào bản đồ để kiểm tra một điểm có bị coi là nguy hiểm không"
          dense
          actions={
            preview && (
              <div className="flex items-center gap-2 text-[11.5px]">
                <Badge tone={Math.abs(preview.state.gamma_deg) > 1 ? 'warn' : 'neutral'}>
                  γ = {preview.state.gamma_deg.toFixed(1)}°
                </Badge>
                {preview.state.turn_radius_m && (
                  <Badge tone="neutral">R = {preview.state.turn_radius_m.toFixed(1)} m</Badge>
                )}
              </div>
            )
          }
        >
          <TopDownView
            geometry={geometry}
            preview={preview}
            dictionary={dictionary}
            visibleZones={Object.fromEntries(
              Object.entries(hidden).map(([key, value]) => [key, !value]),
            )}
            onPickPoint={pick}
            pickedPoint={picked}
            pickedZones={pickedZones}
            className="max-h-[560px]"
          />
          {picked && (
            <div className="border-t border-ink-200 px-4 py-2">
              <Callout tone={pickedZones.length ? 'bad' : 'ok'}>
                Điểm ({picked[0].toFixed(2)} ; {picked[1].toFixed(2)}) m —{' '}
                {pickedZones.length
                  ? `NGUY HIỂM, nằm trong: ${pickedZones
                      .map((name) => dictionary?.zones[name]?.label ?? name)
                      .join(', ')}`
                  : 'an toàn, không nằm trong vùng mù nào'}
              </Callout>
            </div>
          )}
          {error && (
            <div className="border-t border-ink-200 px-4 py-2">
              <Callout tone="bad">{error}</Callout>
            </div>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel title="Điểm làm việc">
            <div className="space-y-3">
              <SegmentedControl
                value={mode}
                onChange={setMode}
                options={[
                  { value: 'yaw_rate', label: 'Tốc độ góc' },
                  { value: 'steering_angle', label: 'Góc vô-lăng' },
                ]}
              />
              <Slider
                label="Tốc độ xe"
                unit=" km/h"
                min={0}
                max={60}
                step={1}
                value={speed}
                onChange={setSpeed}
                marks={[0, 30, 60]}
              />
              <Slider
                label={mode === 'yaw_rate' ? 'Tốc độ góc yaw (ω)' : 'Góc bẻ lái vô-lăng (δ)'}
                unit="°"
                min={mode === 'yaw_rate' ? -25 : -540}
                max={mode === 'yaw_rate' ? 25 : 540}
                step={mode === 'yaw_rate' ? 0.5 : 5}
                value={control}
                onChange={setControl}
                marks={mode === 'yaw_rate' ? [-25, 0, 25] : [-540, 0, 540]}
              />
              <div className="flex gap-1.5">
                <Button size="sm" onClick={() => { setSpeed(0); setControl(0) }}>
                  Đứng yên
                </Button>
                <Button size="sm" onClick={() => { setSpeed(10); setControl(mode === 'yaw_rate' ? -12 : -420) }}>
                  Rẽ phải chậm
                </Button>
                <Button size="sm" onClick={() => { setSpeed(45); setControl(0) }}>
                  Đường trường
                </Button>
              </div>

              {preview && (
                <div className="rounded-[4px] border border-ink-200 bg-ink-50 px-3 py-2">
                  <DataRow
                    label="Góc gập rơ-moóc γ"
                    value={isRigid ? 'thân liền — không có' : `${preview.state.gamma_deg.toFixed(2)}°`}
                  />
                  <DataRow
                    label="Lệch ngang bánh quét"
                    value={`${preview.state.d_swept_m.toFixed(2)} m`}
                    note="L_trail × |sin γ|"
                  />
                  <DataRow
                    label="Quãng đường phản ứng"
                    value={`${preview.stopping.d_reaction_m.toFixed(2)} m`}
                  />
                  <DataRow
                    label="Quãng đường phanh"
                    value={`${preview.stopping.d_braking_m.toFixed(2)} m`}
                    note="v² / (2·μ·g)"
                  />
                  <DataRow
                    label="Tổng cự ly dừng"
                    value={`${preview.stopping.d_total_m.toFixed(2)} m`}
                    highlight
                  />
                </div>
              )}
            </div>
          </Panel>

          <Panel title="Lớp hiển thị" dense>
            <div className="divide-y divide-ink-100">
              {Object.entries(dictionary?.zones ?? {}).map(([name, meta]) => {
                const polygon = preview?.zones[name]
                const empty = !polygon || polygon.length === 0
                return (
                  <label
                    key={name}
                    className={`flex min-h-10 cursor-pointer items-center gap-2.5 px-3 py-1.5 ${empty ? 'opacity-45' : ''}`}
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      checked={!hidden[name]}
                      onChange={(event) =>
                        setHidden((value) => ({ ...value, [name]: !event.target.checked }))
                      }
                    />
                    <span
                      className="h-3 w-3 shrink-0 rounded-[2px] border border-black/15"
                      style={{ backgroundColor: meta.color }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px]">{meta.label}</span>
                      <span className="block truncate text-[11px] text-ink-500">{meta.note}</span>
                    </span>
                    {empty && <span className="shrink-0 text-[10px] text-ink-400">rỗng</span>}
                  </label>
                )
              })}
            </div>
          </Panel>
        </div>
      </div>

      <details className="surface">
        <summary className="cursor-pointer px-4 py-2.5 text-[13px] font-semibold">
          Tham số nâng cao — bình thường không cần sửa
        </summary>
        <div className="grid gap-4 border-t border-ink-200 p-4 sm:grid-cols-2 lg:grid-cols-3">
          <Field label="Độ sâu vùng mù mũi xe" hint="FRONT_BLIND_MIN">
            <NumberInput
              value={profile.zones.front_blind_min}
              onChange={(value) => patchZones({ front_blind_min: value })}
            />
          </Field>
          <Field label="Bề rộng vùng mù hông phải" hint="SIDE_BLIND_MAX">
            <NumberInput
              value={profile.zones.side_blind_max}
              onChange={(value) => patchZones({ side_blind_max: value })}
            />
          </Field>
          <Field label="Độ sâu vùng mù đuôi" hint="REAR_BLIND_DEPTH">
            <NumberInput
              value={profile.zones.rear_blind_depth}
              onChange={(value) => patchZones({ rear_blind_depth: value })}
            />
          </Field>
          <Field label="Bề rộng hiệu dụng cột A" hint="Cột A + khung cửa + chân gương">
            <NumberInput
              value={profile.zones.a_pillar_width}
              onChange={(value) => patchZones({ a_pillar_width: value })}
            />
          </Field>
          <Field label="Tầm chiếu vùng mù cột A" hint="A_PILLAR_BLIND_RANGE">
            <NumberInput
              value={profile.zones.a_pillar_blind_range}
              onChange={(value) => patchZones({ a_pillar_blind_range: value })}
            />
          </Field>
          <Field label="Thời gian phản ứng phanh" hint="Mặc định 1.5 s">
            <NumberInput
              value={profile.physics.reaction_time}
              unit="s"
              onChange={(value) => patchPhysics({ reaction_time: value })}
            />
          </Field>
          <Field label="Hệ số ma sát mặt đường" hint="0.7 đường khô · 0.4 đường ướt">
            <NumberInput
              value={profile.physics.friction_coeff}
              unit=""
              onChange={(value) => patchPhysics({ friction_coeff: value })}
            />
          </Field>
          <Field label="Tỷ số truyền hệ thống lái" hint="STEER_RATIO">
            <NumberInput
              value={profile.physics.steer_ratio}
              unit=":1"
              step={0.5}
              onChange={(value) => patchPhysics({ steer_ratio: value })}
            />
          </Field>
          <Field label="Giới hạn góc gập cơ khí" hint="Ngưỡng va chạm cabin (cab-strike)">
            <NumberInput
              value={profile.physics.mechanical_max_gamma_deg}
              unit="°"
              step={1}
              disabled={isRigid}
              onChange={(value) => patchPhysics({ mechanical_max_gamma_deg: value })}
            />
          </Field>
        </div>
        <div className="border-t border-ink-200 p-4">
          <Toggle
            checked={profile.physics.friction_coeff <= 0.5}
            onChange={(checked) => patchPhysics({ friction_coeff: checked ? 0.4 : 0.7 })}
            label="Cấu hình cho tuyến đường thường xuyên ẩm ướt"
            hint="Hạ hệ số ma sát về 0.4 — vùng nguy hiểm phanh sẽ dài ra đáng kể"
          />
        </div>
      </details>
    </div>
  )
}
