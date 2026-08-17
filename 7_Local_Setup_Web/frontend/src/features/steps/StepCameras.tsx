/**
 * Buoc 3: khai bao 3 camera.
 *
 * Vi tri lap mac dinh duoc suy ra tu hinh hoc xe (guong, mui xe) nen thuong
 * khong phai nhap. Cho phep ghi de bang tay khi lap lech thuc te.
 *
 * O nhap tieu cu (fx) co the thay bang FOV ngang ghi tren datasheet ong kinh -
 * do la con so ky thuat vien co trong tay, con fx thi khong.
 */

import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { CameraId, CameraStatusRow } from '../../lib/types'
import {
  Badge,
  Button,
  Callout,
  DataRow,
  Field,
  NumberInput,
  Panel,
  StatusMark,
  TextInput,
  Toggle,
} from '../../components/ui'
import { useApp } from '../../store/app'

const ORDER: CameraId[] = ['MIRROR_R', 'MIRROR_L', 'FRONT_CAM']

export function StepCameras() {
  const { profile, patchCamera } = useApp()
  const [status, setStatus] = useState<CameraStatusRow[] | null>(null)

  useEffect(() => {
    if (!profile) return
    api
      .cameraStatus(profile.meta.profile_id)
      .then((response) => setStatus(response.cameras))
      .catch(() => setStatus(null))
  }, [profile?.meta.profile_id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!profile) return null
  const geometry = profile.base

  return (
    <div className="space-y-4">
      <Callout tone="accent" title="Vị trí lắp được suy ra tự động">
        Camera gương lấy đúng toạ độ gương chiếu hậu, camera mũi xe lấy toạ độ cản trước — đều suy từ
        4 thông số đã nhập ở bước trước. Chỉ nhập tay khi thực tế lắp lệch so với vị trí này.
      </Callout>

      {ORDER.map((cameraId) => {
        const camera = profile.cameras[cameraId]
        const row = status?.find((item) => item.camera_id === cameraId)
        const hfov = (2 * Math.atan(camera.width / 2 / camera.intrinsics.fx) * 180) / Math.PI

        return (
          <Panel
            key={cameraId}
            title={
              <span className="flex items-center gap-2">
                {camera.label}
                <span className="num text-[11px] font-normal text-ink-500">{cameraId}</span>
              </span>
            }
            subtitle={`Giám sát: ${camera.monitored_blind_zones.join(', ')}`}
            actions={
              row ? (
                <Badge tone={row.online ? 'ok' : 'bad'}>
                  <StatusMark tone={row.online ? 'ok' : 'bad'} />
                  {row.online ? 'Có tín hiệu' : 'Không tín hiệu'}
                </Badge>
              ) : null
            }
          >
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-3">
                <div className="label-caps">Nguồn tín hiệu</div>
                <Field
                  label="Địa chỉ RTSP hoặc số thứ tự USB"
                  hint="Để trống khi chạy chế độ mô phỏng"
                >
                  <TextInput
                    value={camera.source}
                    placeholder="rtsp://admin:pass@192.168.1.64:554/stream1"
                    onChange={(event) => patchCamera(cameraId, { source: event.target.value })}
                  />
                </Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Rộng khung">
                    <NumberInput
                      value={camera.width}
                      unit="px"
                      step={1}
                      onChange={(value) =>
                        patchCamera(cameraId, {
                          width: Math.round(value),
                          intrinsics: { ...camera.intrinsics, cx: Math.round(value) / 2 },
                        })
                      }
                    />
                  </Field>
                  <Field label="Cao khung">
                    <NumberInput
                      value={camera.height}
                      unit="px"
                      step={1}
                      onChange={(value) =>
                        patchCamera(cameraId, {
                          height: Math.round(value),
                          intrinsics: { ...camera.intrinsics, cy: Math.round(value) / 2 },
                        })
                      }
                    />
                  </Field>
                </div>
                <Toggle
                  checked={camera.enabled}
                  onChange={(checked) => patchCamera(cameraId, { enabled: checked })}
                  label="Bật camera này"
                  hint="Tắt nếu chưa lắp đủ, hệ thống sẽ bỏ qua vùng tương ứng"
                />
              </div>

              <div className="space-y-3">
                <div className="label-caps">Ống kính (ma trận nội tại K)</div>
                <Field
                  label="Góc nhìn ngang (HFOV)"
                  hint="Số ghi trên datasheet ống kính. Đổi số này sẽ tính lại tiêu cự fx, fy."
                >
                  <NumberInput
                    value={Number(hfov.toFixed(1))}
                    unit="°"
                    step={0.5}
                    min={20}
                    max={175}
                    onChange={(value) => {
                      const half = (value * Math.PI) / 360
                      if (half <= 0 || half >= Math.PI / 2) return
                      const fx = camera.width / 2 / Math.tan(half)
                      patchCamera(cameraId, {
                        intrinsics: { ...camera.intrinsics, fx, fy: fx },
                      })
                    }}
                  />
                </Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="fx">
                    <NumberInput
                      value={Number(camera.intrinsics.fx.toFixed(2))}
                      unit="px"
                      step={1}
                      onChange={(value) =>
                        patchCamera(cameraId, { intrinsics: { ...camera.intrinsics, fx: value } })
                      }
                    />
                  </Field>
                  <Field label="fy">
                    <NumberInput
                      value={Number(camera.intrinsics.fy.toFixed(2))}
                      unit="px"
                      step={1}
                      onChange={(value) =>
                        patchCamera(cameraId, { intrinsics: { ...camera.intrinsics, fy: value } })
                      }
                    />
                  </Field>
                  <Field label="cx">
                    <NumberInput
                      value={camera.intrinsics.cx}
                      unit="px"
                      step={1}
                      onChange={(value) =>
                        patchCamera(cameraId, { intrinsics: { ...camera.intrinsics, cx: value } })
                      }
                    />
                  </Field>
                  <Field label="cy">
                    <NumberInput
                      value={camera.intrinsics.cy}
                      unit="px"
                      step={1}
                      onChange={(value) =>
                        patchCamera(cameraId, { intrinsics: { ...camera.intrinsics, cy: value } })
                      }
                    />
                  </Field>
                </div>
              </div>

              <div className="space-y-3">
                <div className="label-caps">Vị trí lắp (hệ toạ độ xe)</div>
                <Toggle
                  checked={camera.auto_position}
                  onChange={(checked) => patchCamera(cameraId, { auto_position: checked })}
                  label="Lấy vị trí suy ra tự động"
                  hint={
                    cameraId === 'FRONT_CAM'
                      ? 'Toạ độ cản trước, cao hơn tầm mắt 0.30 m'
                      : 'Toạ độ chân gương chiếu hậu'
                  }
                />
                {camera.position && (
                  <div className="grid grid-cols-3 gap-2">
                    {(['x', 'y', 'z'] as const).map((axis, index) => (
                      <Field key={axis} label={axis}>
                        <NumberInput
                          value={camera.position![index]}
                          disabled={camera.auto_position}
                          step={0.01}
                          onChange={(value) => {
                            const next = [...camera.position!] as [number, number, number]
                            next[index] = value
                            patchCamera(cameraId, { position: next, auto_position: false })
                          }}
                        />
                      </Field>
                    ))}
                  </div>
                )}
                <div className="rounded-[4px] border border-ink-200 bg-ink-50 px-3 py-2">
                  <DataRow
                    label="Góc chúc (pitch)"
                    value={`${camera.pitch_deg.toFixed(1)}°`}
                    note="Căn chỉnh ở bước sau"
                  />
                  <DataRow label="Góc dạt (yaw)" value={`${camera.yaw_deg.toFixed(1)}°`} />
                  <DataRow
                    label="Đã căn chỉnh"
                    value={
                      camera.calibrated_at
                        ? `RMS ${camera.calibration_rms_m?.toFixed(3) ?? '—'} m`
                        : 'chưa'
                    }
                  />
                </div>
              </div>
            </div>

            {row && !row.online && (
              <div className="mt-3">
                <Callout tone="warn" title="Chưa nhận được hình">
                  {row.message}
                </Callout>
              </div>
            )}
          </Panel>
        )
      })}

      <Panel dense className="px-4 py-3">
        <DataRow
          label="Nhắc lại kích thước đã nhập"
          value={`cơ sở ${geometry.wheelbase_tractor} m · cabin ${geometry.cab_width} m · moóc ${geometry.l_trail}×${geometry.w_trail} m`}
        />
      </Panel>

      <div className="flex justify-end">
        <Button
          size="sm"
          onClick={() => {
            if (!profile) return
            api
              .cameraStatus(profile.meta.profile_id)
              .then((response) => setStatus(response.cameras))
              .catch(() => setStatus(null))
          }}
        >
          Kiểm tra lại tín hiệu
        </Button>
      </div>
    </div>
  )
}
