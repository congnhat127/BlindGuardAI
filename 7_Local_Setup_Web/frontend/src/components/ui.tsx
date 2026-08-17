/**
 * Cac thanh phan giao dien co ban.
 *
 * Co y khong dung thu vien component (MUI / Ant / shadcn): chung mang theo
 * ngon ngu thi giac rieng, va do la thu lam giao dien nhin "chung chung, do AI
 * sinh ra". O day moi thanh phan deu bam sat design token trong styles.css.
 */

import type { ReactNode } from 'react'
import { useEffect, useId, useRef, useState } from 'react'

type Tone = 'ok' | 'warn' | 'bad' | 'neutral' | 'accent'

const TONE_CLASS: Record<Tone, string> = {
  ok: 'bg-ok-100 text-ok-600 border-ok-600/25',
  warn: 'bg-warn-100 text-warn-600 border-warn-600/25',
  bad: 'bg-bad-100 text-bad-600 border-bad-600/25',
  neutral: 'bg-ink-100 text-ink-700 border-ink-300',
  accent: 'bg-accent-50 text-accent-600 border-accent-500/25',
}

// --- Nut -------------------------------------------------------------------
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'default' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
  loading?: boolean
  as?: 'button' | 'span'
}

export function Button({
  variant = 'default',
  size = 'md',
  loading,
  className = '',
  children,
  disabled,
  as = 'button',
  ...rest
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-[4px] border font-medium ' +
    'transition-colors disabled:opacity-45 disabled:cursor-not-allowed select-none whitespace-nowrap'
  // 44px la nguong vung cham toi thieu tren tablet - thiet bi chinh cua tho lap dat.
  const sizes = { sm: 'h-8 px-2.5 text-[13px]', md: 'h-11 px-4 text-sm' }
  const variants = {
    primary: 'bg-accent-500 border-accent-600 text-white hover:bg-accent-600 active:bg-accent-700',
    default: 'bg-white border-ink-300 text-ink-900 hover:bg-ink-50 active:bg-ink-100',
    ghost: 'bg-transparent border-transparent text-ink-700 hover:bg-ink-100',
    danger: 'bg-white border-bad-600/40 text-bad-600 hover:bg-bad-100',
  }
  const classes = `${base} ${sizes[size]} ${variants[variant]} ${disabled || loading ? 'opacity-45 cursor-not-allowed' : ''} ${className}`

  if (as === 'span') {
    return (
      <span className={classes} {...(rest as React.HTMLAttributes<HTMLSpanElement>)}>
        {loading && <Spinner />}
        {children}
      </span>
    )
  }

  return (
    <button className={classes} disabled={disabled || loading} {...rest}>
      {loading && <Spinner />}
      {children}
    </button>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-current border-t-transparent"
    />
  )
}

// --- Khoi noi dung ---------------------------------------------------------
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = '',
  dense,
}: {
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
  dense?: boolean
}) {
  return (
    <section className={`surface ${className}`}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-ink-200 px-4 py-2.5">
          <div className="min-w-0">
            {title && <h2 className="text-[13px] font-semibold text-ink-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-600">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={dense ? '' : 'p-4'}>{children}</div>
    </section>
  )
}

export function Badge({
  tone = 'neutral',
  children,
  className = '',
}: {
  tone?: Tone
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-[3px] border px-1.5 py-0.5 text-[11px] font-medium ${TONE_CLASS[tone]} ${className}`}
    >
      {children}
    </span>
  )
}

export function StatusDot({ tone }: { tone: Tone }) {
  const color = {
    ok: 'bg-ok-600',
    warn: 'bg-warn-600',
    bad: 'bg-bad-600',
    neutral: 'bg-ink-400',
    accent: 'bg-accent-500',
  }[tone]
  return <span aria-hidden className={`inline-block h-2 w-2 shrink-0 rounded-full ${color}`} />
}

/** Khong dung mau don doc de bao trang thai: co ky hieu chu kem theo. */
export function StatusMark({ tone }: { tone: Tone }) {
  const glyph = { ok: '✓', warn: '!', bad: '×', neutral: '–', accent: '•' }[tone]
  return (
    <span
      className={`inline-flex h-4 w-4 items-center justify-center rounded-[3px] border text-[10px] font-bold leading-none ${TONE_CLASS[tone]}`}
    >
      {glyph}
    </span>
  )
}

// --- Truong nhap lieu ------------------------------------------------------
export function Field({
  label,
  hint,
  error,
  children,
  htmlFor,
  className = '',
}: {
  label: ReactNode
  hint?: ReactNode
  error?: ReactNode
  children: ReactNode
  htmlFor?: string
  className?: string
}) {
  return (
    <div className={className}>
      <label htmlFor={htmlFor} className="label-caps mb-1 block">
        {label}
      </label>
      {children}
      {error ? (
        <p className="mt-1 text-xs text-bad-600">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-ink-500">{hint}</p>
      ) : null}
    </div>
  )
}

export function TextInput({
  className = '',
  ...rest
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-11 w-full rounded-[4px] border border-ink-300 bg-white px-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-accent-500 ${className}`}
      {...rest}
    />
  )
}

/**
 * O nhap so do.
 *
 * Quyet dinh thiet ke: don vi in mo ben trong o, khong nam trong nhan. Tho doc
 * lai so vua nhap thi thay ngay "3.60 m" chu khong phai doi mat len nhan de
 * kiem tra don vi. Nhap sai don vi (cm thay m) la loi pho bien nhat.
 */
export function NumberInput({
  value,
  onChange,
  unit = 'm',
  step = 0.01,
  min,
  max,
  id,
  invalid,
  onFocus,
  onBlur,
  disabled,
}: {
  value: number
  onChange: (value: number) => void
  unit?: string
  step?: number
  min?: number
  max?: number
  id?: string
  invalid?: boolean
  onFocus?: () => void
  onBlur?: () => void
  disabled?: boolean
}) {
  const [text, setText] = useState(String(value))
  const focused = useRef(false)

  useEffect(() => {
    if (!focused.current) setText(String(value))
  }, [value])

  return (
    <div
      className={`flex h-11 items-center rounded-[4px] border bg-white pr-2.5 ${
        invalid ? 'border-bad-600' : 'border-ink-300 focus-within:border-accent-500'
      } ${disabled ? 'opacity-50' : ''}`}
    >
      <input
        id={id}
        type="number"
        inputMode="decimal"
        className="h-full w-full bg-transparent px-2.5 text-sm outline-none"
        value={text}
        step={step}
        min={min}
        max={max}
        disabled={disabled}
        onFocus={() => {
          focused.current = true
          onFocus?.()
        }}
        onBlur={() => {
          focused.current = false
          const parsed = Number(text)
          if (Number.isFinite(parsed)) onChange(parsed)
          else setText(String(value))
          onBlur?.()
        }}
        onChange={(event) => {
          setText(event.target.value)
          const parsed = Number(event.target.value)
          if (Number.isFinite(parsed) && event.target.value.trim() !== '') onChange(parsed)
        }}
      />
      {unit && <span className="shrink-0 text-xs text-ink-500">{unit}</span>}
    </div>
  )
}

export function Slider({
  value,
  onChange,
  min,
  max,
  step = 1,
  label,
  unit = '',
  marks,
}: {
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step?: number
  label: ReactNode
  unit?: string
  marks?: number[]
}) {
  const id = useId()
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <label htmlFor={id} className="label-caps">
          {label}
        </label>
        <span className="num text-[13px] font-semibold text-ink-900">
          {value.toFixed(step < 1 ? 2 : 0)}
          {unit && <span className="ml-0.5 text-xs font-normal text-ink-500">{unit}</span>}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-11 w-full accent-[var(--color-accent-500)]"
      />
      {marks && (
        <div className="mt-0.5 flex justify-between text-[10px] text-ink-400">
          {marks.map((mark) => (
            <span key={mark} className="num">
              {mark}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function Toggle({
  checked,
  onChange,
  label,
  hint,
  disabled,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  label: ReactNode
  hint?: ReactNode
  disabled?: boolean
}) {
  return (
    <label
      className={`flex min-h-11 cursor-pointer items-start gap-2.5 ${disabled ? 'opacity-50' : ''}`}
    >
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 accent-[var(--color-accent-500)]"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="min-w-0">
        <span className="block text-sm text-ink-900">{label}</span>
        {hint && <span className="block text-xs text-ink-500">{hint}</span>}
      </span>
    </label>
  )
}

export function Select<T extends string>({
  value,
  onChange,
  options,
  id,
}: {
  value: T
  onChange: (value: T) => void
  options: { value: T; label: string }[]
  id?: string
}) {
  return (
    <select
      id={id}
      value={value}
      onChange={(event) => onChange(event.target.value as T)}
      className="h-11 w-full rounded-[4px] border border-ink-300 bg-white px-2 text-sm text-ink-900 focus:border-accent-500"
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

// --- Trinh bay du lieu -----------------------------------------------------
export function DataRow({
  label,
  value,
  note,
  highlight,
}: {
  label: ReactNode
  value: ReactNode
  note?: ReactNode
  highlight?: boolean
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-3 border-b border-ink-100 py-1.5 last:border-0 ${
        highlight ? 'bg-accent-50 -mx-2 px-2' : ''
      }`}
    >
      <div className="min-w-0">
        <div className="truncate text-[13px] text-ink-700">{label}</div>
        {note && <div className="truncate text-[11px] text-ink-500">{note}</div>}
      </div>
      <div className="num shrink-0 text-[13px] font-semibold text-ink-900">{value}</div>
    </div>
  )
}

export function Callout({
  tone = 'neutral',
  title,
  children,
}: {
  tone?: Tone
  title?: ReactNode
  children: ReactNode
}) {
  return (
    <div className={`rounded-[4px] border px-3 py-2 text-[13px] ${TONE_CLASS[tone]}`}>
      {title && <div className="mb-0.5 font-semibold">{title}</div>}
      <div className="opacity-90">{children}</div>
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1.5 px-6 py-12 text-center">
      <p className="text-sm font-medium text-ink-700">{title}</p>
      {children && <div className="max-w-sm text-[13px] text-ink-500">{children}</div>}
    </div>
  )
}

export function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T
  onChange: (value: T) => void
  options: { value: T; label: ReactNode }[]
}) {
  return (
    <div role="tablist" className="inline-flex rounded-[4px] border border-ink-300 bg-white p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          role="tab"
          aria-selected={value === option.value}
          onClick={() => onChange(option.value)}
          className={`h-9 rounded-[3px] px-3 text-[13px] font-medium transition-colors ${
            value === option.value
              ? 'bg-ink-900 text-white'
              : 'text-ink-600 hover:bg-ink-100'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
