/** Man hinh dau: chon xe da co hoac tao ho so moi tu mau. */

import { useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import type { ProfileSummary } from '../lib/types'
import { Badge, Button, Callout, Field, Panel, Select, TextInput } from '../components/ui'
import { useApp } from '../store/app'

export function ProfilePicker() {
  const { templates, openProfile, createProfile } = useApp()
  const [profiles, setProfiles] = useState<ProfileSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [form, setForm] = useState({
    profile_id: '',
    plate_number: '',
    display_name: '',
    installer_name: '',
    template_id: templates[0]?.template_id ?? '',
  })

  useEffect(() => {
    api
      .listProfiles()
      .then((response) => setProfiles(response.profiles))
      .catch((exception) =>
        setError(exception instanceof ApiError ? exception.message : 'Không đọc được danh sách xe.'),
      )
  }, [])

  useEffect(() => {
    if (!form.template_id && templates.length) {
      setForm((value) => ({ ...value, template_id: templates[0].template_id }))
    }
  }, [templates, form.template_id])

  /**
   * Bien so -> profile_id. Bien so la thu ky thuat vien co san trong tay, con
   * profile_id la thu may can. Tu sinh de tho khong phai nghi ra dinh danh.
   */
  function onPlateChange(plate: string) {
    const slug = plate
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48)
    setForm((value) => ({
      ...value,
      plate_number: plate,
      profile_id: slug.length >= 2 ? slug : value.profile_id,
    }))
  }

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      await createProfile({
        profile_id: form.profile_id.trim(),
        plate_number: form.plate_number.trim(),
        display_name: form.display_name.trim(),
        installer_name: form.installer_name.trim(),
        template_id: form.template_id || null,
      })
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Không tạo được hồ sơ.')
    } finally {
      setBusy(false)
    }
  }

  const template = templates.find((item) => item.template_id === form.template_id)
  const canSubmit = form.profile_id.trim().length >= 2 && !busy

  return (
    <div className="mx-auto grid max-w-5xl gap-4 p-4 lg:grid-cols-[1fr_360px]">
      <Panel
        title="Xe đã cấu hình trên thiết bị này"
        subtitle="Chọn một xe để xem lại hoặc căn chỉnh lại"
        dense
      >
        {error && (
          <div className="p-4">
            <Callout tone="bad">{error}</Callout>
          </div>
        )}
        {profiles === null ? (
          <p className="px-4 py-6 text-[13px] text-ink-500">Đang tải…</p>
        ) : profiles.length === 0 ? (
          <div className="px-4 py-10 text-center">
            <p className="text-sm font-medium text-ink-700">Thiết bị chưa có hồ sơ xe nào</p>
            <p className="mt-1 text-[13px] text-ink-500">
              Đây là lần lắp đặt đầu tiên. Tạo hồ sơ ở khung bên phải để bắt đầu.
            </p>
          </div>
        ) : (
          <ul>
            {profiles.map((item) => (
              <li key={item.profile_id} className="border-b border-ink-100 last:border-0">
                <button
                  onClick={() => void openProfile(item.profile_id)}
                  disabled={item.broken}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-ink-50 disabled:opacity-50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-ink-900">
                        {item.plate_number || item.display_name || item.profile_id}
                      </span>
                      {item.commissioned && <Badge tone="ok">Đã nghiệm thu</Badge>}
                      {item.broken && <Badge tone="bad">Hồ sơ lỗi</Badge>}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-ink-500">
                      {item.broken
                        ? item.error
                        : [
                            item.vehicle_type === 'rigid' ? 'Xe thân liền' : 'Đầu kéo + rơ-moóc',
                            item.total_length ? `dài ${item.total_length} m` : null,
                            `${item.cameras_calibrated ?? 0}/4 camera đã căn chỉnh`,
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                    </div>
                  </div>
                  <span className="num shrink-0 text-xs text-ink-400">{item.profile_id}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Lắp đặt xe mới" subtitle="Chọn mẫu xe rồi sửa lại theo số đo thực tế">
        <div className="space-y-3">
          <Field
            label="Biển số xe"
            hint="Nhập biển số, mã hồ sơ sẽ tự sinh theo"
            htmlFor="plate"
          >
            <TextInput
              id="plate"
              value={form.plate_number}
              placeholder="43C-123.45"
              onChange={(event) => onPlateChange(event.target.value)}
            />
          </Field>

          <Field label="Mã hồ sơ" hint="Chữ thường, số, gạch ngang" htmlFor="pid">
            <TextInput
              id="pid"
              value={form.profile_id}
              placeholder="43c-123-45"
              onChange={(event) =>
                setForm((value) => ({ ...value, profile_id: event.target.value }))
              }
            />
          </Field>

          <Field label="Mẫu xe" htmlFor="tpl">
            <Select
              id="tpl"
              value={form.template_id}
              onChange={(value) => setForm((form) => ({ ...form, template_id: value }))}
              options={templates.map((item) => ({ value: item.template_id, label: item.label }))}
            />
          </Field>

          {template && (
            <div className="rounded-[4px] border border-ink-200 bg-ink-50 px-3 py-2 text-[12px] text-ink-600">
              <p>{template.description}</p>
              <p className="num mt-1">
                Cơ sở {template.base.wheelbase_tractor} m · rộng cabin {template.base.cab_width} m ·
                thùng {template.base.l_trail} × {template.base.w_trail} m
              </p>
              <p className="mt-1 text-ink-500">
                Đây là số điển hình. Bước sau bắt buộc đối chiếu sổ đăng kiểm.
              </p>
            </div>
          )}

          <Field label="Người lắp đặt" htmlFor="installer">
            <TextInput
              id="installer"
              value={form.installer_name}
              placeholder="Họ tên kỹ thuật viên"
              onChange={(event) =>
                setForm((value) => ({ ...value, installer_name: event.target.value }))
              }
            />
          </Field>

          <Button variant="primary" className="w-full" onClick={submit} disabled={!canSubmit} loading={busy}>
            Bắt đầu lắp đặt
          </Button>

          <ImportBox />
        </div>
      </Panel>
    </div>
  )
}

/** Nhan ban cau hinh sang xe khac cung loai - chi phai can chinh lai camera. */
function ImportBox() {
  const { openProfile } = useApp()
  const [open, setOpen] = useState(false)
  const [content, setContent] = useState('')
  const [newId, setNewId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full pt-1 text-left text-[12px] text-ink-500 underline decoration-ink-300 underline-offset-2 hover:text-ink-700"
      >
        Nhân bản từ file cấu hình xe khác
      </button>
    )
  }

  return (
    <div className="space-y-2 border-t border-ink-200 pt-3">
      <p className="text-[12px] text-ink-600">
        Dán nội dung file YAML đã xuất từ xe cùng loại. Kích thước được giữ nguyên, kết quả căn chỉnh
        camera bị xoá vì góc lắp trên xe mới chắc chắn khác.
      </p>
      <Field label="Mã hồ sơ mới">
        <TextInput value={newId} onChange={(event) => setNewId(event.target.value)} />
      </Field>
      <textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        rows={5}
        placeholder="meta:&#10;  profile_id: ..."
        className="w-full rounded-[4px] border border-ink-300 bg-white p-2 font-mono text-[11px]"
      />
      {error && <Callout tone="bad">{error}</Callout>}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="primary"
          loading={busy}
          onClick={async () => {
            setBusy(true)
            setError(null)
            try {
              const created = await api.importProfile(content, newId.trim() || undefined)
              await openProfile(created.meta.profile_id)
            } catch (exception) {
              setError(exception instanceof ApiError ? exception.message : 'Nhập thất bại.')
            } finally {
              setBusy(false)
            }
          }}
        >
          Nhân bản
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Đóng
        </Button>
      </div>
    </div>
  )
}
