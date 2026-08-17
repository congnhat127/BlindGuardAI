import { useEffect, useState } from 'react'
import { Badge, Button, Callout, StatusDot } from './components/ui'
import { DiagnosticsPanel } from './features/DiagnosticsPanel'
import { ProfilePicker } from './features/ProfilePicker'
import { Wizard } from './features/Wizard'
import { STEPS, useApp } from './store/app'

export function App() {
  const { boot, booted, bootError, health, profile } = useApp()
  const [showDiagnostics, setShowDiagnostics] = useState(false)

  useEffect(() => {
    void boot()
  }, [boot])

  if (!booted) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-ink-500">
        Đang kết nối thiết bị…
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <TopBar onToggleDiagnostics={() => setShowDiagnostics((value) => !value)} />

      {bootError && (
        <div className="border-b border-warn-600/25 bg-warn-100 px-4 py-2 text-[13px] text-warn-600">
          {bootError}
        </div>
      )}

      {health?.device_backend === 'mock' && (
        <div className="flex flex-wrap items-center gap-2 border-b border-ink-200 bg-ink-100 px-4 py-1.5 text-[12px] text-ink-700">
          <Badge tone="warn">Chế độ mô phỏng</Badge>
          <span>
            Chưa nối camera và GPS thật. Khung hình được dựng từ đúng mô hình camera K + [R|T], nên
            toàn bộ quy trình căn chỉnh và nghiệm thu chạy được như thật.
          </span>
        </div>
      )}

      <main className="min-h-0 flex-1 overflow-y-auto">
        {showDiagnostics ? (
          <div className="mx-auto max-w-5xl p-4">
            <DiagnosticsPanel profileId={profile?.meta.profile_id} />
          </div>
        ) : profile ? (
          <Wizard />
        ) : (
          <ProfilePicker />
        )}
      </main>

      <StatusBar />
    </div>
  )
}

function TopBar({ onToggleDiagnostics }: { onToggleDiagnostics: () => void }) {
  const { profile, closeProfile, isDirty } = useApp()
  const dirty = isDirty()

  return (
    <header className="no-print flex items-center gap-3 border-b border-ink-200 bg-ink-900 px-4 py-2 text-white">
      <div className="flex items-baseline gap-2">
        <span className="text-[13px] font-semibold tracking-tight">BlindGuard AI</span>
        <span className="text-[11px] uppercase tracking-[0.09em] text-ink-400">
          Cài đặt tại xe
        </span>
      </div>

      {profile && (
        <>
          <span className="h-4 w-px bg-ink-700" />
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate text-[13px]">
              {profile.meta.plate_number || profile.meta.display_name || profile.meta.profile_id}
            </span>
            {profile.meta.commissioned && <Badge tone="ok">Đã nghiệm thu</Badge>}
            {dirty && <Badge tone="warn">Chưa lưu</Badge>}
          </div>
        </>
      )}

      <div className="ml-auto flex items-center gap-1.5">
        <button
          onClick={onToggleDiagnostics}
          className="h-9 rounded-[4px] px-2.5 text-[13px] text-ink-200 hover:bg-ink-800"
        >
          Chẩn đoán
        </button>
        {profile && (
          <button
            onClick={() => {
              if (!dirty || confirm('Còn thay đổi chưa lưu. Vẫn thoát hồ sơ này?')) closeProfile()
            }}
            className="h-9 rounded-[4px] px-2.5 text-[13px] text-ink-200 hover:bg-ink-800"
          >
            Đổi xe
          </button>
        )}
      </div>
    </header>
  )
}

function StatusBar() {
  const { health, profile, step, lastSavedAt, draftSavedAt, saveError, saving } = useApp()
  const stepIndex = STEPS.findIndex((item) => item.id === step)

  return (
    <footer className="no-print flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-ink-200 bg-white px-4 py-1.5 text-[11.5px] text-ink-600">
      <span className="flex items-center gap-1.5">
        <StatusDot tone={health?.engine.available ? 'ok' : 'bad'} />
        Engine {health?.engine.available ? 'sẵn sàng' : 'lỗi'}
      </span>
      <span className="flex items-center gap-1.5">
        <StatusDot tone={health?.device_backend === 'jetson' ? 'ok' : 'warn'} />
        Thiết bị: {health?.device_backend === 'jetson' ? 'Jetson' : 'mô phỏng'}
      </span>
      {profile && (
        <span>
          Bước {stepIndex + 1}/{STEPS.length} · {STEPS[stepIndex]?.label}
        </span>
      )}
      {saving && <span>Đang lưu…</span>}
      {saveError && <span className="text-bad-600">{saveError}</span>}
      {!saveError && lastSavedAt && <span>Lưu lúc {formatTime(lastSavedAt)}</span>}
      {draftSavedAt && <span className="text-ink-500">Nháp đã giữ {formatTime(draftSavedAt)}</span>}
      <span className="ml-auto text-ink-400">
        Hệ toạ độ: gốc tâm trục sau đầu kéo · x hướng trước · y hướng trái · mét
      </span>
    </footer>
  )
}

export function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null
  return (
    <Callout tone="bad" title="Không thực hiện được">
      {error}
    </Callout>
  )
}

export function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <Button size="sm" onClick={onClick}>
      Thử lại
    </Button>
  )
}
