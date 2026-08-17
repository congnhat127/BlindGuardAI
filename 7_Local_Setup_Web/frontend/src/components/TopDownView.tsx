/**
 * So do nhin tu tren xuong, ve bang SVG trong don vi MET.
 *
 * Dung SVG chu khong dung Canvas: net o moi muc zoom, bat su kien con tro san,
 * va kiem tra duoc bang DOM. Toan bo he toa do la VCS (goc = tam truc sau dau
 * keo, x huong truoc, y huong trai), chi doi dau truc y khi ve len man hinh.
 *
 * Vai tro quan trong nhat: khi ky thuat vien dat con tro vao mot o nhap so, so
 * do to do dung khoang cach dang do kem mui ten. Tho nhin hinh la biet phai do
 * cai gi, khong phai doc chu.
 */

import { useMemo } from 'react'
import type { DerivedGeometry, Dictionary, Point, ZonePreview } from '../lib/types'

export type DimensionKey =
  | 'wheelbase_tractor'
  | 'cab_width'
  | 'l_trail'
  | 'w_trail'
  | 'driver_height'
  | null

interface Props {
  geometry: DerivedGeometry
  preview?: ZonePreview | null
  isRigid?: boolean
  dictionary?: Dictionary | null
  highlight?: DimensionKey
  visibleZones?: Record<string, boolean>
  showGrid?: boolean
  showReferencePoints?: boolean
  onPickPoint?: (point: Point) => void
  pickedPoint?: Point | null
  pickedZones?: string[]
  className?: string
}

const PAD = 3.5

export function TopDownView({
  geometry,
  preview,
  isRigid = false,
  dictionary,
  highlight = null,
  visibleZones,
  showGrid = true,
  showReferencePoints = true,
  onPickPoint,
  pickedPoint,
  pickedZones,
  className = '',
}: Props) {
  const bounds = useMemo(() => {
    const xs = [geometry.trail_rear_x, geometry.cab_front_x]
    const ys = [-geometry.max_width, geometry.max_width]
    // Neu co du lieu vung mu, phai bao het cac da giac de khong bi cat mep.
    for (const polygon of Object.values(preview?.zones ?? {})) {
      for (const [x, y] of polygon) {
        xs.push(x)
        ys.push(y)
      }
    }
    return {
      x0: Math.min(...xs) - PAD,
      x1: Math.max(...xs) + PAD,
      y0: Math.min(...ys) - PAD,
      y1: Math.max(...ys) + PAD,
    }
  }, [geometry, preview])

  const width = bounds.x1 - bounds.x0
  const height = bounds.y1 - bounds.y0

  /** VCS -> toa do SVG. Chi doi dau y: VCS y huong trai, man hinh y huong xuong. */
  const toSvg = (point: Point): Point => [point[0], -point[1]]
  const path = (polygon: Point[]) =>
    polygon.length ? `M ${polygon.map((p) => toSvg(p).join(' ')).join(' L ')} Z` : ''

  const vehicle = preview?.vehicle
  const colors = dictionary?.vehicle_colors ?? {}
  const rigidBody = isRigid
    ? (vehicle && vehicle.kind === 'rigid' ? vehicle.body : null) ??
      rect(
        geometry.trail_rear_x,
        geometry.cab_front_x,
        Math.max(geometry.cab_half_w, geometry.trail_half_w),
      )
    : null
  const cab =
    !isRigid && vehicle?.kind === 'articulated'
      ? vehicle.cab
      : rect(geometry.cab_rear_x, geometry.cab_front_x, geometry.cab_half_w)
  const chassis =
    !isRigid && vehicle?.kind === 'articulated'
      ? vehicle.chassis
      : rect(-0.3, geometry.cab_rear_x, geometry.chassis_half_w)
  const trailer =
    !isRigid && vehicle?.kind === 'articulated'
      ? vehicle.trailer
      : rect(geometry.trail_rear_x, geometry.trail_front_x, geometry.trail_half_w)
  const gridStep = width > 30 ? 2 : 1

  function handleClick(event: React.MouseEvent<SVGSVGElement>) {
    if (!onPickPoint) return
    const svg = event.currentTarget
    const rectBox = svg.getBoundingClientRect()
    const px = ((event.clientX - rectBox.left) / rectBox.width) * width + bounds.x0
    const py = ((event.clientY - rectBox.top) / rectBox.height) * height - bounds.y1
    onPickPoint([Number(px.toFixed(2)), Number((-py).toFixed(2))])
  }

  return (
    <svg
      viewBox={`${bounds.x0} ${-bounds.y1} ${width} ${height}`}
      className={`block w-full bg-white ${onPickPoint ? 'cursor-crosshair' : ''} ${className}`}
      onClick={handleClick}
      role="img"
      aria-label="Sơ đồ xe nhìn từ trên xuống kèm vùng mù"
    >
      {showGrid && (
        <g stroke="#e9ebee" strokeWidth={0.02}>
          {ticks(bounds.x0, bounds.x1, gridStep).map((x) => (
            <line key={`gx${x}`} x1={x} y1={-bounds.y1} x2={x} y2={-bounds.y0} />
          ))}
          {ticks(bounds.y0, bounds.y1, gridStep).map((y) => (
            <line key={`gy${y}`} x1={bounds.x0} y1={-y} x2={bounds.x1} y2={-y} />
          ))}
        </g>
      )}

      {/* Truc toa do: nhac lai goc (0,0) va chieu duong cua truc. */}
      <g stroke="#c7ccd2" strokeWidth={0.035}>
        <line x1={bounds.x0} y1={0} x2={bounds.x1} y2={0} strokeDasharray="0.3 0.2" />
        <line x1={0} y1={-bounds.y1} x2={0} y2={-bounds.y0} strokeDasharray="0.3 0.2" />
      </g>

      {/* Vung mu, ve truoc than xe de than xe khong bi mau phu len. */}
      <g>
        {Object.entries(preview?.zones ?? {}).map(([name, polygon]) => {
          if (!polygon.length) return null
          if (visibleZones && visibleZones[name] === false) return null
          const meta = dictionary?.zones?.[name]
          const color = meta?.color ?? '#ef4444'
          const active = pickedZones?.includes(name)
          return (
            <path
              key={name}
              d={path(polygon)}
              fill={color}
              fillOpacity={active ? 0.42 : 0.18}
              stroke={color}
              strokeWidth={active ? 0.09 : 0.05}
              strokeLinejoin="round"
            />
          )
        })}
      </g>

      {/* Than xe: xe than lien la MOT khoi nguyen, xe dau keo tach 3 phan co khop noi. */}
      {isRigid ? (
        <g strokeLinejoin="round">
          <path
            d={path(rigidBody ?? [])}
            fill={colors.cab ?? '#334155'}
            stroke="#0f172a"
            strokeWidth={0.045}
          />
          {/* 2 truc banh, khong co khop noi ma khong co duong chia than xe. */}
          <g stroke="#0f172a" strokeWidth={0.06} strokeLinecap="round" opacity={0.55}>
            <line
              x1={geometry.cab_front_x - 0.35}
              y1={-geometry.cab_half_w}
              x2={geometry.cab_front_x - 0.35}
              y2={geometry.cab_half_w}
            />
            <line
              x1={geometry.trail_rear_x + 0.6}
              y1={-geometry.cab_half_w}
              x2={geometry.trail_rear_x + 0.6}
              y2={geometry.cab_half_w}
            />
          </g>
        </g>
      ) : (
        <g strokeLinejoin="round">
          <path
            d={path(trailer)}
            fill={colors.trailer ?? '#0284c7'}
            stroke="#075985"
            strokeWidth={0.04}
          />
          <path
            d={path(chassis)}
            fill={colors.chassis ?? '#475569'}
            stroke="#1e293b"
            strokeWidth={0.03}
          />
          <path d={path(cab)} fill={colors.cab ?? '#334155'} stroke="#0f172a" strokeWidth={0.04} />
          {/* Truc banh dau keo */}
          <g stroke="#0f172a" strokeWidth={0.07} strokeLinecap="round">
            <line x1={0} y1={-geometry.cab_half_w - 0.15} x2={0} y2={geometry.cab_half_w + 0.15} />
            <line
              x1={geometry.cab_front_x - 0.4}
              y1={-geometry.cab_half_w - 0.15}
              x2={geometry.cab_front_x - 0.4}
              y2={geometry.cab_half_w + 0.15}
            />
          </g>
          {/* Chot keo - chi xe khop noi moi co */}
          <circle cx={geometry.d_hitch} cy={0} r={0.16} fill="#fff" stroke="#0f172a" strokeWidth={0.05} />
        </g>
      )}

      {showReferencePoints && (
        <g>
          <Marker x={geometry.eye_x} y={geometry.eye_y} color="#0891b2" label="Mắt TX" />
          <Marker x={geometry.mirror_r_x} y={geometry.mirror_r_y} color="#ef4444" label="Gương P" />
          <Marker x={geometry.mirror_l_x} y={geometry.mirror_l_y} color="#ef4444" label="Gương T" />
          <Marker x={geometry.a_pillar_r_x} y={geometry.a_pillar_r_y} color="#f97316" label="" />
          <Marker x={geometry.a_pillar_l_x} y={geometry.a_pillar_l_y} color="#f97316" label="" />
        </g>
      )}

      {/* Goc toa do: luon hien vi day la moc cua moi so do. */}
      <g>
        <circle cx={0} cy={0} r={0.2} fill="none" stroke="#c2410c" strokeWidth={0.06} />
        <circle cx={0} cy={0} r={0.06} fill="#c2410c" />
        <Label x={0.35} y={-0.45} text="(0,0) tâm trục sau" color="#c2410c" />
      </g>

      {pickedPoint && (
        <g>
          <circle
            cx={pickedPoint[0]}
            cy={-pickedPoint[1]}
            r={0.28}
            fill="none"
            stroke={pickedZones?.length ? '#b91c1c' : '#15803d'}
            strokeWidth={0.08}
          />
          <circle cx={pickedPoint[0]} cy={-pickedPoint[1]} r={0.09} fill="#14171a" />
          <Label
            x={pickedPoint[0] + 0.4}
            y={-pickedPoint[1] - 0.35}
            text={`${pickedPoint[0].toFixed(1)} ; ${pickedPoint[1].toFixed(1)} m`}
            color="#14171a"
          />
        </g>
      )}

      <Dimension highlight={highlight} geometry={geometry} />
    </svg>
  )
}

// --- Ghi chu kich thuoc ----------------------------------------------------
function Dimension({
  highlight,
  geometry,
}: {
  highlight: DimensionKey
  geometry: DerivedGeometry
}) {
  if (!highlight) return null
  const accent = '#c2410c'

  if (highlight === 'wheelbase_tractor') {
    const y = geometry.cab_half_w + 1.1
    return (
      <ArrowSpan
        x1={0}
        x2={geometry.cab_front_x - 0.4}
        y={y}
        color={accent}
        text={`Chiều dài cơ sở  ${(geometry.cab_front_x - 0.4).toFixed(2)} m`}
      />
    )
  }
  if (highlight === 'cab_width') {
    const x = geometry.cab_rear_x + (geometry.cab_front_x - geometry.cab_rear_x) / 2
    return (
      <ArrowSpanV
        y1={-geometry.cab_half_w}
        y2={geometry.cab_half_w}
        x={x}
        color={accent}
        text={`Rộng cabin  ${(geometry.cab_half_w * 2).toFixed(2)} m`}
      />
    )
  }
  if (highlight === 'l_trail') {
    const y = -geometry.trail_half_w - 1.1
    return (
      <ArrowSpan
        x1={geometry.trail_rear_x}
        x2={geometry.d_hitch}
        y={y}
        color={accent}
        text={`Chốt kéo → trục moóc  ${(geometry.d_hitch - geometry.trail_rear_x).toFixed(2)} m`}
      />
    )
  }
  if (highlight === 'w_trail') {
    const x = geometry.trail_rear_x + 2.0
    return (
      <ArrowSpanV
        y1={-geometry.trail_half_w}
        y2={geometry.trail_half_w}
        x={x}
        color={accent}
        text={`Rộng rơ-moóc  ${(geometry.trail_half_w * 2).toFixed(2)} m`}
      />
    )
  }
  if (highlight === 'driver_height') {
    return (
      <g>
        <circle
          cx={geometry.eye_x}
          cy={-geometry.eye_y}
          r={0.5}
          fill="none"
          stroke={accent}
          strokeWidth={0.07}
        />
        <Label
          x={geometry.eye_x + 0.7}
          y={-geometry.eye_y - 0.7}
          text={`Tầm mắt cao ${geometry.eye_z.toFixed(2)} m`}
          color={accent}
        />
      </g>
    )
  }
  return null
}

function ArrowSpan({
  x1,
  x2,
  y,
  color,
  text,
}: {
  x1: number
  x2: number
  y: number
  color: string
  text: string
}) {
  const sy = -y
  return (
    <g stroke={color} strokeWidth={0.05} fill="none">
      <line x1={x1} y1={sy} x2={x2} y2={sy} />
      <line x1={x1} y1={sy - 0.22} x2={x1} y2={sy + 0.22} />
      <line x1={x2} y1={sy - 0.22} x2={x2} y2={sy + 0.22} />
      <Label x={(x1 + x2) / 2} y={sy - 0.3} text={text} color={color} anchor="middle" />
    </g>
  )
}

function ArrowSpanV({
  y1,
  y2,
  x,
  color,
  text,
}: {
  y1: number
  y2: number
  x: number
  color: string
  text: string
}) {
  return (
    <g stroke={color} strokeWidth={0.05} fill="none">
      <line x1={x} y1={-y1} x2={x} y2={-y2} />
      <line x1={x - 0.22} y1={-y1} x2={x + 0.22} y2={-y1} />
      <line x1={x - 0.22} y1={-y2} x2={x + 0.22} y2={-y2} />
      <Label x={x + 0.35} y={0} text={text} color={color} />
    </g>
  )
}

function Marker({
  x,
  y,
  color,
  label,
}: {
  x: number
  y: number
  color: string
  label: string
}) {
  return (
    <g>
      <circle cx={x} cy={-y} r={0.13} fill={color} stroke="#fff" strokeWidth={0.04} />
      {label && <Label x={x + 0.24} y={-y - 0.22} text={label} color="#3d444d" />}
    </g>
  )
}

/** Chu trong SVG met: phai chong scale de kich co chu khong doi theo zoom. */
function Label({
  x,
  y,
  text,
  color,
  anchor = 'start',
}: {
  x: number
  y: number
  text: string
  color: string
  anchor?: 'start' | 'middle' | 'end'
}) {
  return (
    <text
      x={x}
      y={y}
      fill={color}
      textAnchor={anchor}
      // Vien trang mong ve TRUOC net chu (paintOrder) de doc duoc khi chu nam
      // tren da giac mau. Neu khong co vien nay, nhan bi lan vao mau vung mu.
      stroke="#ffffff"
      strokeWidth={0.12}
      style={{ font: '600 0.42px ui-sans-serif, system-ui', paintOrder: 'stroke' }}
    >
      {text}
    </text>
  )
}

// --- Tro giup --------------------------------------------------------------
function rect(x0: number, x1: number, halfWidth: number): Point[] {
  return [
    [x1, halfWidth],
    [x1, -halfWidth],
    [x0, -halfWidth],
    [x0, halfWidth],
  ]
}

function ticks(from: number, to: number, step: number): number[] {
  const out: number[] = []
  for (let value = Math.ceil(from / step) * step; value <= to; value += step) {
    out.push(Number(value.toFixed(2)))
  }
  return out
}
