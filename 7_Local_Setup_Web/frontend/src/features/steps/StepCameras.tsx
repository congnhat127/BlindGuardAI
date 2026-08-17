/**
 * Buoc 3: khai bao 4 camera (phai, trai, truoc, sau).
 *
 * Da rut gon rat nhieu so voi ban truoc: an het thong so ky thuat (fx, fy, cx,
 * cy, kich thuoc pixel) vao "Cai dat nang cao", chi de lai thu ky thuat vien
 * thuc su can: nguon tin hieu va goc nhin ong kinh (do sat voi datasheet).
 */

import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { CameraId, CameraStatusRow } from '../../lib/types'
import {
  Badge,
  Button,
  Callout,
  Field,
  NumberInput,
  Panel,
  StatusMark,
  TextInput,
  Toggle,
} from '../../components/ui'
import { useApp } from '../../store/app'

const ORDER: CameraId[] = ['MIRROR_R', 'MIRROR_L', 'FRONT_CAM', 'REAR_CAM']

export function StepCameras() {
  const { profile, patchCamera } = useApp()
  const [status, setStatus] = useState<CameraStatusRow[] | null>(null)
  const [showAdvanced, setShowAdvanced] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (!profile) return
    api
      .cameraStatus(profile.meta.profile_id)
      .then((response) => setStatus(response.cameras))
      .catch(() => setStatus(null))
  }, [profile?.meta.profile_id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!profile) return null

  return (
    <div className="space-y-4">
      <Callout tone="accent" title="4 camera, mỗi camera phụ trách 1 hướng">
        Vị trí lắp được suy ra tự động từ kích thước xe đã nhập ở bước trước. Bạn chỉ cần điền nguồn
        tín hiệu (địa chỉ camera) — góc lắp chính xác sẽ căn chỉnh ở bước sau bằng ảnh thật.
      </Callout>

      {ORDER.map((cameraId) => {
        const camera = profile.cameras[cameraId]
        const row = status?.find((item) => item.camera_id === cameraId)
        const advanced = showAdvanced[cameraId] ?? false

        return (
          <Panel
            key={cameraId}
            title={camera.label}
            subtitle={
              cameraId === 'MIRROR_R'
                ? 'Giám sát vùng mù bên phải'
                : cameraId === 'MIRROR_L'
                  ? 'Giám sát vùng mù bên trái'
                  : cameraId === 'FRONT_CAM'
                    ? 'Giám sát vùng mù phía trước'
                    : 'Giám sát vùng mù phía sau'
            }
            actions={
              <div className="flex items-center gap-2">
                {row && (
                  <Badge tone={row.online ? 'ok' : 'bad'}>
                    <StatusMark tone={row.online ? 'ok' : 'bad'} />
                    {row.online ? 'Có tín hiệu' : 'Chưa có tín hiệu'}
                  </Badge>
                )}
                <Toggle
                  checked={camera.enabled}
                  onChange={(checked) => patchCamera(cameraId, { enabled: checked })}
                  label="Dùng"
                />
              </div>
            }
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Nguồn tín hiệu camera"
                hint="Địa chỉ RTSP hoặc số cổng USB. Để trống nếu đang dùng ảnh mô phỏng / ảnh tải lên."
              >
                <TextInput
                  value={camera.source}
                  placeholder="rtsp://admin:pass@192.168.1.64:554/stream1"
                  onChange={(event) => patchCamera(cameraId, { source: event.target.value })}
                />
              </Field>
              <Field
                label="Góc nhìn ngang của ống kính"
                hint="Ghi trên hộp/datasheet camera, ví dụ 120°"
              >
                <NumberInput
                  value={Number(
                    ((2 * Math.atan(camera.width / 2 / camera.intrinsics.fx) * 180) / Math.PI).toFixed(1),
                  )}
                  unit="°"
                  step={0.5}
                  min={20}
                  max={175}
                  onChange={(value) => {
                    const half = (value * Math.PI) / 360
                    if (half <= 0 || half >= Math.PI / 2) return
                    const fx = camera.width / 2 / Math.tan(half)
                    patchCamera(cameraId, { intrinsics: { ...camera.intrinsics, fx, fy: fx } })
                  }}
                />
              </Field>
            </div>

            {row && !row.online && (
              <div className="mt-3">
                <Callout tone="warn">{row.message}</Callout>
              </div>
            )}

            <button
              className="mt-3 text-[12px] text-ink-500 underline decoration-ink-300 underline-offset-2 hover:text-ink-700"
              onClick={() => setShowAdvanced((v) => ({ ...v, [cameraId]: !advanced }))}
            >
              {advanced ? 'Ẩn cài đặt nâng cao' : 'Cài đặt nâng cao (kích thước ảnh, vị trí lắp)'}
            </button>

            {advanced && (
              <div className="mt-3 grid gap-4 border-t border-ink-200 pt-3 sm:grid-cols-2">
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Rộng khung ảnh">
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
                  <Field label="Cao khung ảnh">
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
                <div className="space-y-2">
                  <Toggle
                    checked={camera.auto_position}
                    onChange={(checked) => patchCamera(cameraId, { auto_position: checked })}
                    label="Lấy vị trí lắp tự động"
                    hint="Tắt để tự nhập toạ độ khi lắp lệch vị trí chuẩn"
                  />
                  {camera.position && !camera.auto_position && (
                    <div className="grid grid-cols-3 gap-2">
                      {(['x', 'y', 'z'] as const).map((axis, index) => (
                        <Field key={axis} label={axis}>
                          <NumberInput
                            value={camera.position![index]}
                            step={0.01}
                            onChange={(value) => {
                              const next = [...camera.position!] as [number, number, number]
                              next[index] = value
                              patchCamera(cameraId, { position: next })
                            }}
                          />
                        </Field>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </Panel>
        )
      })}

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
