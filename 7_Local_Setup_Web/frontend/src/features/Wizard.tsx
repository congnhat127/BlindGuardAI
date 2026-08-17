/** Khung wizard: thanh buoc ben trai, noi dung ben phai, thanh dieu huong duoi. */

import { Button } from '../components/ui'
import { STEPS, useApp } from '../store/app'
import { StepCalibrate } from './steps/StepCalibrate'
import { StepCameras } from './steps/StepCameras'
import { StepDimensions } from './steps/StepDimensions'
import { StepIdentity } from './steps/StepIdentity'
import { StepReview } from './steps/StepReview'
import { StepZones } from './steps/StepZones'

export function Wizard() {
  const { step, setStep, profile, save, saving, isDirty } = useApp()
  if (!profile) return null

  const index = STEPS.findIndex((item) => item.id === step)
  const calibratedCount = Object.values(profile.cameras).filter((c) => c.calibrated_at).length

  return (
    <div className="mx-auto flex max-w-[1400px] gap-4 p-4">
      <nav className="no-print hidden w-52 shrink-0 lg:block">
        <ol className="surface overflow-hidden">
          {STEPS.map((item, position) => {
            const active = item.id === step
            const done = position < index
            return (
              <li key={item.id} className="border-b border-ink-100 last:border-0">
                <button
                  onClick={() => setStep(item.id)}
                  className={`flex w-full items-start gap-2.5 px-3 py-2.5 text-left transition-colors ${
                    active ? 'bg-accent-50' : 'hover:bg-ink-50'
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[3px] border text-[11px] font-bold ${
                      active
                        ? 'border-accent-500 bg-accent-500 text-white'
                        : done
                          ? 'border-ok-600/40 bg-ok-100 text-ok-600'
                          : 'border-ink-300 bg-white text-ink-500'
                    }`}
                  >
                    {done ? '✓' : position + 1}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={`block text-[13px] ${active ? 'font-semibold text-accent-700' : 'text-ink-900'}`}
                    >
                      {item.label}
                    </span>
                    <span className="block text-[11px] text-ink-500">
                      {item.id === 'calibrate' ? `${calibratedCount}/4 camera` : item.hint}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
      </nav>

      <div className="min-w-0 flex-1 space-y-4">
        <div className="no-print flex items-baseline gap-2 lg:hidden">
          <span className="label-caps">
            Bước {index + 1}/{STEPS.length}
          </span>
          <span className="text-[13px] font-semibold">{STEPS[index]?.label}</span>
        </div>

        {step === 'identity' && <StepIdentity />}
        {step === 'dimensions' && <StepDimensions />}
        {step === 'cameras' && <StepCameras />}
        {step === 'calibrate' && <StepCalibrate />}
        {step === 'zones' && <StepZones />}
        {step === 'review' && <StepReview />}

        <div className="no-print flex items-center gap-2 pb-6">
          <Button disabled={index === 0} onClick={() => setStep(STEPS[index - 1].id)}>
            ← Bước trước
          </Button>
          <Button
            variant="ghost"
            loading={saving}
            disabled={!isDirty()}
            onClick={() => void save()}
          >
            Lưu lại
          </Button>
          <Button
            className="ml-auto"
            variant="primary"
            disabled={index === STEPS.length - 1}
            onClick={() => setStep(STEPS[index + 1].id)}
          >
            Bước tiếp →
          </Button>
        </div>
      </div>
    </div>
  )
}
