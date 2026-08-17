/** Buoc 1: dinh danh xe, loai xe, mau cau hinh, nguoi lap dat. */

import { Callout, Field, Panel, Select, TextInput, Toggle } from '../../components/ui'
import { useApp } from '../../store/app'

export function StepIdentity() {
  const { profile, patchMeta, applyTemplate, templates } = useApp()
  if (!profile) return null
  const { meta } = profile

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Hồ sơ xe" subtitle="Thông tin định danh, dùng cho báo cáo và đội xe">
        <div className="space-y-3">
          <Field label="Mã hồ sơ" hint="Không đổi được sau khi tạo">
            <TextInput value={meta.profile_id} disabled readOnly />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Biển số">
              <TextInput
                value={meta.plate_number}
                placeholder="43C-123.45"
                onChange={(event) => patchMeta({ plate_number: event.target.value })}
              />
            </Field>
            <Field label="Tên hiển thị">
              <TextInput
                value={meta.display_name}
                placeholder="Container 40ft số 3"
                onChange={(event) => patchMeta({ display_name: event.target.value })}
              />
            </Field>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Đội xe / đơn vị">
              <TextInput
                value={meta.fleet_name}
                onChange={(event) => patchMeta({ fleet_name: event.target.value })}
              />
            </Field>
            <Field label="Người lắp đặt">
              <TextInput
                value={meta.installer_name}
                onChange={(event) => patchMeta({ installer_name: event.target.value })}
              />
            </Field>
          </div>

          <Field
            label="Loại thân xe"
            hint={
              meta.vehicle_type === 'rigid'
                ? 'Thân liền: không có khớp gập, góc gập γ luôn bằng 0'
                : 'Đầu kéo + rơ-moóc: có khớp gập, sinh vùng quét lấn lề khi rẽ'
            }
          >
            <Select
              value={meta.vehicle_type}
              onChange={(value) => patchMeta({ vehicle_type: value })}
              options={[
                { value: 'articulated', label: 'Đầu kéo + sơ mi rơ-moóc' },
                { value: 'rigid', label: 'Xe thân liền (bus, thùng liền, xe bồn)' },
              ]}
            />
          </Field>

          <Field label="Ghi chú lắp đặt">
            <textarea
              value={meta.notes}
              rows={3}
              onChange={(event) => patchMeta({ notes: event.target.value })}
              placeholder="Vị trí đi dây, điểm cấp nguồn, lưu ý riêng của xe…"
              className="w-full rounded-[4px] border border-ink-300 bg-white p-2 text-sm focus:border-accent-500"
            />
          </Field>

          {profile.meta.commissioned && (
            <Toggle
              checked={meta.commissioned}
              onChange={(checked) => patchMeta({ commissioned: checked })}
              label="Khoá cấu hình sau nghiệm thu"
              hint="Bỏ chọn để mở khoá và sửa lại cấu hình xe đã bàn giao"
            />
          )}
        </div>
      </Panel>

      <div className="space-y-4">
        <Panel
          title="Mẫu cấu hình"
          subtitle="Điền sẵn kích thước điển hình rồi sửa theo sổ đăng kiểm"
          dense
        >
          <ul>
            {templates.map((template) => {
              const matches =
                profile.base.wheelbase_tractor === template.base.wheelbase_tractor &&
                profile.base.l_trail === template.base.l_trail &&
                profile.base.cab_width === template.base.cab_width
              return (
                <li key={template.template_id} className="border-b border-ink-100 last:border-0">
                  <button
                    onClick={() => applyTemplate(template.template_id)}
                    className={`flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-ink-50 ${
                      matches ? 'bg-accent-50' : ''
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="text-[13px] font-medium text-ink-900">{template.label}</div>
                      <div className="num mt-0.5 text-[11.5px] text-ink-500">
                        cơ sở {template.base.wheelbase_tractor} · cabin {template.base.cab_width} ·
                        thùng {template.base.l_trail}×{template.base.w_trail} m
                      </div>
                    </div>
                    {matches && (
                      <span className="shrink-0 text-[11px] font-semibold text-accent-600">
                        đang dùng
                      </span>
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </Panel>

        <Callout tone="accent" title="Hệ toạ độ dùng chung">
          Mọi số đo trong công cụ này dùng cùng một hệ: gốc (0,0) tại tâm trục sau đầu kéo, x hướng
          về mũi xe, y hướng sang bên trái (phía tài xế), đơn vị mét. Bên phải xe là y âm. Nhầm dấu y
          sẽ làm vùng mù lật sang bên kia xe.
        </Callout>
      </div>
    </div>
  )
}
