/**
 * Trang chan doan truoc khi lap.
 *
 * Muc dich: ky thuat vien biet ngay dang thieu gi, truoc khi bo 30 phut cang
 * chinh roi moi phat hien camera chua co tin hieu hoac chua co IMU.
 */

import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import type { Diagnostics } from '../lib/types'
import { Badge, Button, Callout, DataRow, Panel, StatusMark } from '../components/ui'

export function DiagnosticsPanel({ profileId }: { profileId?: string }) {
  const [data, setData] = useState<Diagnostics | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)

  const load = useCallback(async () => {
    setBusy(true)
    try {
      setData(await api.diagnostics(profileId))
      setError(null)
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Không đọc được chẩn đoán.')
    } finally {
      setBusy(false)
    }
  }, [profileId])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!autoRefresh) return
    const timer = setInterval(() => void load(), 2000)
    return () => clearInterval(timer)
  }, [autoRefresh, load])

  const telemetry = data?.telemetry

  return (
    <div className="space-y-4">
      <Panel
        title="Kiểm tra thiết bị"
        subtitle={
          data
            ? `${data.summary.pass} đạt · ${data.summary.warn} cảnh báo · ${data.summary.error} lỗi`
            : 'Đang kiểm tra…'
        }
        dense
        actions={
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-[12px] text-ink-600">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(event) => setAutoRefresh(event.target.checked)}
              />
              Tự làm mới
            </label>
            <Button size="sm" loading={busy} onClick={() => void load()}>
              Kiểm tra lại
            </Button>
          </div>
        }
      >
        {error && (
          <div className="p-4">
            <Callout tone="bad">{error}</Callout>
          </div>
        )}
        <ul className="divide-y divide-ink-100">
          {(data?.checks ?? []).map((check) => (
            <li key={check.key} className="flex items-start gap-2.5 px-4 py-2.5">
              <span className="mt-0.5">
                <StatusMark tone={check.status === 'pass' ? 'ok' : check.status === 'warn' ? 'warn' : 'bad'} />
              </span>
              <span className="min-w-0">
                <span className="block text-[13px] text-ink-900">{check.label}</span>
                <span className="block text-[11.5px] text-ink-500">{check.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      {data && data.cameras.length > 0 && (
        <Panel title="Camera" dense>
          <ul className="divide-y divide-ink-100">
            {data.cameras.map((camera) => (
              <li key={camera.camera_id} className="flex items-center gap-3 px-4 py-2.5">
                <StatusMark tone={camera.online ? 'ok' : 'bad'} />
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] text-ink-900">
                    {camera.label}{' '}
                    <span className="num text-[11px] text-ink-500">{camera.camera_id}</span>
                  </div>
                  <div className="truncate text-[11.5px] text-ink-500">{camera.message}</div>
                </div>
                <span className="num shrink-0 text-[11.5px] text-ink-500">
                  {camera.resolution.join('×')} · {camera.fps} fps
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {telemetry && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Panel
            title="GPS"
            actions={
              <Badge tone={telemetry.gps.fix ? (telemetry.gps.is_lost ? 'warn' : 'ok') : 'bad'}>
                {telemetry.gps.fix ? (telemetry.gps.is_lost ? 'Tín hiệu yếu' : 'Có fix') : 'Không fix'}
              </Badge>
            }
          >
            <DataRow label="Số vệ tinh" value={telemetry.gps.satellites ?? '—'} />
            <DataRow label="HDOP" value={telemetry.gps.hdop ?? '—'} note="Càng nhỏ càng chính xác" />
            <DataRow label="Tốc độ" value={`${telemetry.gps.speed_kmh?.toFixed(1) ?? '—'} km/h`} />
            <DataRow label="Hướng (COG)" value={`${telemetry.gps.course_deg?.toFixed(0) ?? '—'}°`} />
            <DataRow
              label="Toạ độ"
              value={
                telemetry.gps.latitude
                  ? `${telemetry.gps.latitude.toFixed(5)} ; ${telemetry.gps.longitude?.toFixed(5)}`
                  : '—'
              }
            />
          </Panel>

          <Panel
            title="IMU"
            actions={
              <Badge tone={telemetry.imu.present ? 'ok' : 'bad'}>
                {telemetry.imu.present ? 'Có phản hồi' : 'Không thấy'}
              </Badge>
            }
          >
            <DataRow
              label="Tốc độ góc yaw"
              value={`${telemetry.imu.yaw_rate_deg_s?.toFixed(2) ?? '—'} °/s`}
              note="Nguồn tin cậy nhất khi xe rẽ chậm"
            />
            <DataRow label="Pitch" value={`${telemetry.imu.pitch_deg?.toFixed(2) ?? '—'}°`} />
            <DataRow label="Roll" value={`${telemetry.imu.roll_deg?.toFixed(2) ?? '—'}°`} />
            <DataRow label="Nhiệt độ" value={`${telemetry.imu.temperature_c ?? '—'} °C`} />
          </Panel>
        </div>
      )}

      {telemetry?.note && <Callout tone="neutral">{telemetry.note}</Callout>}

      {data && (
        <Panel title="Môi trường chạy" dense>
          <div className="px-4 py-2">
            <DataRow label="Python" value={data.environment.python} />
            <DataRow label="Hệ điều hành" value={data.environment.platform} />
            <DataRow label="Chế độ thiết bị" value={data.environment.device_backend} />
            <DataRow label="Thư mục dữ liệu" value={data.environment.data_dir} />
          </div>
        </Panel>
      )}
    </div>
  )
}
