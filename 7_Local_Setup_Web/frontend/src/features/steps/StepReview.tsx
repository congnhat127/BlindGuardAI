/**
 * Buoc 6: nghiem thu.
 *
 * Ba viec:
 *   - Danh sach kiem tra: con thieu gi truoc khi ban giao xe.
 *   - Xem truoc file cau hinh se sinh ra, va tai ve.
 *   - Bien ban nghiem thu in duoc + khoa cau hinh.
 *
 * File `config_<ho_so>.py` sinh ra dung y ten hang so ma engine dang doc, nen
 * chi can copy vao thay config.py la chay - khong phai sua mot dong code nao.
 */

import { useEffect, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { CommissioningReport } from '../../lib/types'
import {
  Badge,
  Button,
  Callout,
  DataRow,
  Panel,
  SegmentedControl,
  StatusMark,
  Toggle,
} from '../../components/ui'
import { useApp } from '../../store/app'

export function StepReview() {
  const { profile, patchMeta, save, saving, isDirty, warnings } = useApp()
  const [report, setReport] = useState<CommissioningReport | null>(null)
  const [format, setFormat] = useState<'python' | 'yaml'>('python')
  const [preview, setPreview] = useState<string>('')
  const [versions, setVersions] = useState<{ version: string; saved_at: string }[]>([])
  const [error, setError] = useState<string | null>(null)

  const profileId = profile?.meta.profile_id
  const dirty = isDirty()

  useEffect(() => {
    if (!profileId || dirty) return
    api.report(profileId).then(setReport).catch(() => setReport(null))
    api
      .previewExport(profileId, format)
      .then((response) => setPreview(response.content))
      .catch(() => setPreview(''))
    api
      .versions(profileId)
      .then((response) => setVersions(response.versions))
      .catch(() => setVersions([]))
  }, [profileId, format, dirty])

  if (!profile || !profileId) return null

  const calibrated = Object.values(profile.cameras).filter((c) => c.calibrated_at)
  const failing = report?.cameras.filter((c) => c.status === 'fail' || c.status === 'not_calibrated')

  const checklist = [
    {
      ok: Boolean(profile.meta.plate_number),
      label: 'Đã nhập biển số xe',
      detail: 'Cần cho biên bản bàn giao và quản lý đội xe',
    },
    {
      ok: Boolean(profile.meta.installer_name),
      label: 'Đã ghi tên người lắp đặt',
      detail: 'Truy được người chịu trách nhiệm khi cần kiểm tra lại',
    },
    {
      ok: warnings.length === 0,
      label: 'Kích thước xe không có cảnh báo',
      detail: warnings.length ? warnings.map((w) => w.message).join(' ') : 'Nằm trong dải hợp lý',
    },
    {
      ok: calibrated.length === 4,
      label: 'Cả 4 camera đã căn chỉnh',
      detail: `${calibrated.length}/4 camera đã chốt kết quả`,
    },
    {
      ok: (failing?.length ?? 1) === 0,
      label: 'Sai số căn chỉnh đạt ngưỡng ≤ 0.30 m',
      detail: failing?.length
        ? `Chưa đạt: ${failing.map((c) => c.label).join(', ')}`
        : 'Toàn bộ camera trong ngưỡng',
    },
    {
      ok: !dirty,
      label: 'Đã lưu mọi thay đổi',
      detail: dirty ? 'Còn thay đổi chưa lưu — lưu trước khi nghiệm thu' : 'Không còn thay đổi treo',
    },
  ]

  const readyToCommission = checklist.every((item) => item.ok)

  return (
    <div className="space-y-4">
      {dirty && (
        <Callout tone="warn" title="Còn thay đổi chưa lưu">
          Biên bản và file cấu hình chỉ sinh từ dữ liệu đã lưu.{' '}
          <Button size="sm" variant="primary" loading={saving} onClick={() => void save()}>
            Lưu ngay
          </Button>
        </Callout>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Danh sách kiểm tra trước bàn giao" dense>
          <ul className="divide-y divide-ink-100">
            {checklist.map((item) => (
              <li key={item.label} className="flex items-start gap-2.5 px-4 py-2.5">
                <span className="mt-0.5">
                  <StatusMark tone={item.ok ? 'ok' : 'warn'} />
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] text-ink-900">{item.label}</span>
                  <span className="block text-[11.5px] text-ink-500">{item.detail}</span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          title="Xuất cấu hình cho engine"
          subtitle="File Python sinh ra dùng đúng tên hằng số mà engine đang đọc"
          actions={
            <SegmentedControl
              value={format}
              onChange={setFormat}
              options={[
                { value: 'python', label: 'config.py' },
                { value: 'yaml', label: 'YAML' },
              ]}
            />
          }
        >
          <pre className="max-h-72 overflow-auto rounded-[4px] border border-ink-200 bg-ink-50 p-2.5 font-mono text-[11px] leading-relaxed text-ink-800">
            {preview || 'Lưu hồ sơ để xem trước nội dung file.'}
          </pre>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="primary"
              onClick={() => window.open(api.exportUrl(profileId, 'python'), '_blank')}
            >
              Tải config_{profileId}.py
            </Button>
            <Button onClick={() => window.open(api.exportUrl(profileId, 'yaml'), '_blank')}>
              Tải {profileId}.yaml
            </Button>
            <Button variant="ghost" onClick={() => window.print()}>
              In biên bản
            </Button>
          </div>
          <p className="mt-2 text-[11.5px] text-ink-500">
            Cách dùng: copy file .py vào{' '}
            <span className="font-mono">2_BlindSpot_Risk_Calculation/dynamic_blind_zone/config.py</span>{' '}
            trên Jetson. File YAML dùng để lưu trữ và nhân bản sang xe khác cùng loại.
          </p>
        </Panel>
      </div>

      {report && <ReportView report={report} />}

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Khoá cấu hình" subtitle="Sau khi khoá, cần mở khoá mới sửa được">
          <div className="space-y-3">
            <Toggle
              checked={profile.meta.commissioned}
              disabled={!readyToCommission && !profile.meta.commissioned}
              onChange={(checked) => patchMeta({ commissioned: checked })}
              label="Đánh dấu đã nghiệm thu và khoá cấu hình"
              hint={
                readyToCommission
                  ? 'Ngăn sửa cấu hình ngoài ý muốn sau khi giao xe'
                  : 'Còn hạng mục chưa đạt trong danh sách kiểm tra'
              }
            />
            <Callout tone="warn" title="Bảo mật cần làm trước khi giao xe">
              Web này chạy trên mạng Wi-Fi của xe. Nếu chưa đặt mã PIN, bất kỳ ai trong tầm phủ sóng
              đều sửa được cấu hình an toàn của xe đang chạy. Đặt biến{' '}
              <span className="font-mono">BLINDGUARD_SETUP_PIN</span> trên Jetson, bật WPA2 cho điểm
              truy cập, và bind server vào đúng interface AP.
            </Callout>
            {error && <Callout tone="bad">{error}</Callout>}
            <Button
              variant="primary"
              className="w-full"
              loading={saving}
              disabled={!dirty}
              onClick={async () => {
                setError(null)
                const ok = await save()
                if (!ok) setError('Lưu thất bại. Nếu hồ sơ đang khoá, mở khoá trước rồi thử lại.')
              }}
            >
              Lưu hồ sơ
            </Button>
          </div>
        </Panel>

        <Panel title="Lịch sử phiên bản" subtitle="Mỗi lần lưu tạo một bản sao lưu" dense>
          {versions.length === 0 ? (
            <p className="px-4 py-6 text-[13px] text-ink-500">Chưa có phiên bản nào được lưu.</p>
          ) : (
            <ul className="divide-y divide-ink-100">
              {versions.slice(0, 12).map((item) => (
                <li key={item.version} className="flex items-center gap-3 px-4 py-2">
                  <span className="num min-w-0 flex-1 truncate text-[12px] text-ink-700">
                    {item.version}
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={async () => {
                      if (!confirm('Phục hồi phiên bản này? Bản hiện tại sẽ được lưu lại trước.')) return
                      try {
                        await api.restoreVersion(profileId, item.version)
                        window.location.reload()
                      } catch (exception) {
                        setError(
                          exception instanceof ApiError ? exception.message : 'Phục hồi thất bại.',
                        )
                      }
                    }}
                  >
                    Phục hồi
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  )
}

function ReportView({ report }: { report: CommissioningReport }) {
  return (
    <Panel
      title="Biên bản nghiệm thu"
      subtitle={`Sinh lúc ${new Date(report.generated_at).toLocaleString('vi-VN')}`}
    >
      <div className="grid gap-6 lg:grid-cols-3">
        <div>
          <div className="label-caps mb-1">Hồ sơ xe</div>
          <DataRow label="Mã hồ sơ" value={report.meta.profile_id} />
          <DataRow label="Biển số" value={report.meta.plate_number || '—'} />
          <DataRow
            label="Loại thân xe"
            value={report.meta.vehicle_type === 'rigid' ? 'Thân liền' : 'Đầu kéo + rơ-moóc'}
          />
          <DataRow label="Đội xe" value={report.meta.fleet_name || '—'} />
          <DataRow label="Người lắp đặt" value={report.meta.installer_name || '—'} />
        </div>

        <div>
          <div className="label-caps mb-1">Kích thước</div>
          <DataRow label="Chiều dài cơ sở" value={`${report.base.wheelbase_tractor} m`} />
          <DataRow label="Rộng cabin" value={`${report.base.cab_width} m`} />
          <DataRow label="Rơ-moóc" value={`${report.base.l_trail} × ${report.base.w_trail} m`} />
          <DataRow label="Tổng chiều dài" value={`${report.geometry.total_length.toFixed(2)} m`} />
          <DataRow label="Độ cao tầm mắt" value={`${report.geometry.eye_z.toFixed(2)} m`} />
        </div>

        <div>
          <div className="label-caps mb-1">Vật lý</div>
          <DataRow label="Thời gian phản ứng" value={`${report.physics.reaction_time} s`} />
          <DataRow label="Hệ số ma sát" value={String(report.physics.friction_coeff)} />
          <DataRow label="Tỷ số truyền lái" value={`${report.physics.steer_ratio}:1`} />
          <DataRow
            label="Giới hạn góc gập"
            value={`${report.physics.mechanical_max_gamma_deg}°`}
          />
        </div>
      </div>

      <div className="mt-5 overflow-x-auto">
        <div className="label-caps mb-1">Kết quả căn chỉnh camera</div>
        <table className="w-full min-w-[720px] text-left text-[12.5px]">
          <thead>
            <tr className="border-b border-ink-200 bg-ink-50">
              <th className="px-3 py-2 font-semibold">Camera</th>
              <th className="px-3 py-2 font-semibold">Vị trí (x, y, z) m</th>
              <th className="px-3 py-2 font-semibold">Pitch / Yaw</th>
              <th className="px-3 py-2 font-semibold">HFOV</th>
              <th className="px-3 py-2 font-semibold">Sai số RMS</th>
              <th className="px-3 py-2 font-semibold">Kết luận</th>
            </tr>
          </thead>
          <tbody className="num">
            {report.cameras.map((camera) => (
              <tr key={camera.camera_id} className="border-b border-ink-100 last:border-0">
                <td className="px-3 py-1.5">
                  <span className="font-medium">{camera.label}</span>
                  <span className="ml-1.5 text-[11px] text-ink-500">{camera.camera_id}</span>
                </td>
                <td className="px-3 py-1.5">
                  {camera.position.map((value) => value.toFixed(2)).join(' ; ')}
                </td>
                <td className="px-3 py-1.5">
                  {camera.angles.pitch_deg.toFixed(1)}° / {camera.angles.yaw_deg.toFixed(1)}°
                </td>
                <td className="px-3 py-1.5">{camera.hfov_deg.toFixed(0)}°</td>
                <td className="px-3 py-1.5">
                  {camera.calibration_rms_m !== null
                    ? `${camera.calibration_rms_m.toFixed(3)} m`
                    : '—'}
                </td>
                <td className="px-3 py-1.5">
                  <Badge
                    tone={
                      camera.status === 'pass'
                        ? 'ok'
                        : camera.status === 'warn'
                          ? 'warn'
                          : camera.status === 'fail'
                            ? 'bad'
                            : 'neutral'
                    }
                  >
                    {
                      {
                        pass: 'Đạt',
                        warn: 'Tạm được',
                        fail: 'Chưa đạt',
                        not_calibrated: 'Chưa căn chỉnh',
                      }[camera.status]
                    }
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {report.meta.notes && (
        <div className="mt-4">
          <div className="label-caps mb-1">Ghi chú lắp đặt</div>
          <p className="whitespace-pre-wrap text-[13px] text-ink-700">{report.meta.notes}</p>
        </div>
      )}

      <div className="mt-6 grid gap-8 border-t border-ink-200 pt-6 sm:grid-cols-2">
        <div>
          <div className="h-12 border-b border-ink-400" />
          <p className="mt-1 text-[12px] text-ink-600">Kỹ thuật viên lắp đặt</p>
        </div>
        <div>
          <div className="h-12 border-b border-ink-400" />
          <p className="mt-1 text-[12px] text-ink-600">Đại diện đơn vị nhận xe</p>
        </div>
      </div>
    </Panel>
  )
}
