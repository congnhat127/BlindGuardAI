/**
 * Khung hinh camera + lop phu SVG de cham diem moc.
 *
 * Nhung diem da can nhac ky vi anh huong truc tiep den do chinh xac hieu chuan:
 *
 *  1. KINH LUP. Ngon tay che dung cai chop non can cham. Kinh lup hien lech len
 *     phia tren diem cham, phong to 3.5 lan, co dau thap chinh giua.
 *  2. CHE DO TACH BIET (cham diem / keo anh). Doan cu chi bang heuristic hay
 *     doan sai va lam lech diem da dat. Tach thanh 2 che do ro rang an toan hon.
 *  3. SO THU TU + MAU. Ky thuat vien mu mau van lam duoc; va so thu tu la thu
 *     rang buoc thu tu cham dung voi bang so do.
 *  4. NHICH BANG BAN PHIM. Mui ten nhich 1 px - dat lai bang tay khong bao gio
 *     chinh xac bang.
 *  5. image-rendering: pixelated khi zoom > 2 - tho phai thay dung pixel.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { GridLine, Point, ReferenceCone } from '../lib/types'
import { Button, SegmentedControl } from './ui'

export interface PlacedPoint {
  index: number
  u: number
  v: number
}

interface Props {
  imageUrl: string
  loupeUrl: string
  imageSize: [number, number]
  cones: ReferenceCone[]
  placed: PlacedPoint[]
  onPlace: (points: PlacedPoint[]) => void
  gridLines?: GridLine[]
  zonePolygons?: { name: string; color: string; points: Point[] }[]
  showGrid: boolean
  live: boolean
}

type Mode = 'point' | 'pan'
const LOUPE_ZOOM = 3.5
const LOUPE_SIZE = 132

export function CameraCanvas({
  imageUrl,
  loupeUrl,
  imageSize,
  cones,
  placed,
  onPlace,
  gridLines = [],
  zonePolygons = [],
  showGrid,
  live,
}: Props) {
  const [imageWidth, imageHeight] = imageSize
  const [mode, setMode] = useState<Mode>('point')
  const [scale, setScale] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [selected, setSelected] = useState<number | null>(null)
  const [loupe, setLoupe] = useState<{ u: number; v: number; cx: number; cy: number } | null>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  const dragging = useRef<{ kind: 'pan' | 'point'; index?: number; startX: number; startY: number } | null>(
    null,
  )

  const nextIndex = useMemo(() => {
    const used = new Set(placed.map((point) => point.index))
    for (let index = 1; index <= cones.length; index += 1) if (!used.has(index)) return index
    return null
  }, [placed, cones.length])

  /** Toa do con tro -> toa do pixel trong anh goc. */
  const toImage = useCallback(
    (clientX: number, clientY: number): Point | null => {
      const frame = frameRef.current
      if (!frame) return null
      const box = frame.getBoundingClientRect()
      const u = ((clientX - box.left) / box.width) * imageWidth
      const v = ((clientY - box.top) / box.height) * imageHeight
      if (u < 0 || v < 0 || u > imageWidth || v > imageHeight) return null
      return [u, v]
    },
    [imageWidth, imageHeight],
  )

  function setPoint(index: number, u: number, v: number) {
    const clampedU = Math.min(imageWidth, Math.max(0, u))
    const clampedV = Math.min(imageHeight, Math.max(0, v))
    const rest = placed.filter((point) => point.index !== index)
    onPlace(
      [...rest, { index, u: Number(clampedU.toFixed(1)), v: Number(clampedV.toFixed(1)) }].sort(
        (a, b) => a.index - b.index,
      ),
    )
  }

  function handlePointerDown(event: React.PointerEvent) {
    const target = event.target as SVGElement
    const hitIndex = target.dataset?.pointIndex
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)

    if (hitIndex) {
      const index = Number(hitIndex)
      setSelected(index)
      dragging.current = { kind: 'point', index, startX: event.clientX, startY: event.clientY }
      const image = toImage(event.clientX, event.clientY)
      if (image) setLoupe({ u: image[0], v: image[1], cx: event.clientX, cy: event.clientY })
      return
    }

    if (mode === 'pan') {
      dragging.current = { kind: 'pan', startX: event.clientX - pan.x, startY: event.clientY - pan.y }
      return
    }

    if (nextIndex === null) return
    const image = toImage(event.clientX, event.clientY)
    if (!image) return
    setPoint(nextIndex, image[0], image[1])
    setSelected(nextIndex)
    dragging.current = { kind: 'point', index: nextIndex, startX: event.clientX, startY: event.clientY }
    setLoupe({ u: image[0], v: image[1], cx: event.clientX, cy: event.clientY })
  }

  function handlePointerMove(event: React.PointerEvent) {
    const drag = dragging.current
    if (!drag) return
    if (drag.kind === 'pan') {
      setPan({ x: event.clientX - drag.startX, y: event.clientY - drag.startY })
      return
    }
    const image = toImage(event.clientX, event.clientY)
    if (!image || drag.index === undefined) return
    setPoint(drag.index, image[0], image[1])
    setLoupe({ u: image[0], v: image[1], cx: event.clientX, cy: event.clientY })
  }

  function handlePointerUp() {
    dragging.current = null
    setLoupe(null)
  }

  // Nhich diem dang chon bang mui ten - do chinh xac tot hon dat lai bang tay.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (selected === null) return
      const deltas: Record<string, [number, number]> = {
        ArrowLeft: [-1, 0],
        ArrowRight: [1, 0],
        ArrowUp: [0, -1],
        ArrowDown: [0, 1],
      }
      const delta = deltas[event.key]
      if (!delta) return
      const point = placed.find((item) => item.index === selected)
      if (!point) return
      event.preventDefault()
      const step = event.shiftKey ? 10 : 1
      setPoint(selected, point.u + delta[0] * step, point.v + delta[1] * step)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, placed]) // eslint-disable-line react-hooks/exhaustive-deps

  const aspect = `${imageWidth} / ${imageHeight}`
  const markerScale = imageWidth / 900 / scale

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <SegmentedControl
          value={mode}
          onChange={setMode}
          options={[
            { value: 'point', label: 'Chạm để đặt điểm' },
            { value: 'pan', label: 'Kéo để di chuyển' },
          ]}
        />
        <div className="flex items-center gap-1.5">
          <Button size="sm" onClick={() => setScale((s) => Math.max(1, Number((s - 0.5).toFixed(1))))}>
            −
          </Button>
          <span className="num w-12 text-center text-[13px] text-ink-600">{scale.toFixed(1)}×</span>
          <Button size="sm" onClick={() => setScale((s) => Math.min(6, Number((s + 0.5).toFixed(1))))}>
            +
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setScale(1)
              setPan({ x: 0, y: 0 })
            }}
          >
            Vừa khung
          </Button>
        </div>
      </div>

      <div
        className="no-select relative overflow-hidden rounded-[4px] border border-ink-300 bg-ink-900"
        style={{ aspectRatio: aspect, touchAction: 'none' }}
      >
        <div
          ref={frameRef}
          className="absolute inset-0 origin-center"
          style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})` }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <img
            src={imageUrl}
            alt="Khung hình camera"
            draggable={false}
            className={`absolute inset-0 h-full w-full object-fill ${scale > 2 ? 'pixelated' : ''}`}
          />

          <svg
            viewBox={`0 0 ${imageWidth} ${imageHeight}`}
            className="absolute inset-0 h-full w-full"
            style={{ cursor: mode === 'pan' ? 'grab' : 'crosshair' }}
          >
            {showGrid && (
              <g fill="none">
                {gridLines.map((line, index) => (
                  <polyline
                    key={`${line.axis}${line.value}-${index}`}
                    points={line.points.map((point) => point.join(',')).join(' ')}
                    stroke={line.value === 0 ? '#22d3ee' : '#38bdf8'}
                    strokeOpacity={line.value === 0 ? 0.95 : 0.5}
                    strokeWidth={(line.value === 0 ? 3 : 1.6) * markerScale * 2}
                  />
                ))}
              </g>
            )}

            {zonePolygons.map((zone) => (
              <polygon
                key={zone.name}
                points={zone.points.map((point) => point.join(',')).join(' ')}
                fill={zone.color}
                fillOpacity={0.22}
                stroke={zone.color}
                strokeWidth={3 * markerScale * 2}
              />
            ))}

            {placed.map((point) => {
              const cone = cones.find((item) => item.index === point.index)
              const color = cone?.color ?? '#c2410c'
              const isSelected = selected === point.index
              const radius = 13 * markerScale * 2
              return (
                <g key={point.index} data-point-index={point.index}>
                  {/* Vong bat su kien rong hon vong ve: ngon tay khong chinh xac. */}
                  <circle
                    data-point-index={point.index}
                    cx={point.u}
                    cy={point.v}
                    r={radius * 2.6}
                    fill="transparent"
                  />
                  <line
                    data-point-index={point.index}
                    x1={point.u - radius * 1.9}
                    y1={point.v}
                    x2={point.u + radius * 1.9}
                    y2={point.v}
                    stroke="#fff"
                    strokeWidth={1.6 * markerScale * 2}
                  />
                  <line
                    data-point-index={point.index}
                    x1={point.u}
                    y1={point.v - radius * 1.9}
                    x2={point.u}
                    y2={point.v + radius * 1.9}
                    stroke="#fff"
                    strokeWidth={1.6 * markerScale * 2}
                  />
                  <circle
                    data-point-index={point.index}
                    cx={point.u}
                    cy={point.v}
                    r={radius}
                    fill={color}
                    stroke={isSelected ? '#fff' : 'rgba(255,255,255,0.75)'}
                    strokeWidth={(isSelected ? 3.5 : 2) * markerScale * 2}
                  />
                  <text
                    data-point-index={point.index}
                    x={point.u}
                    y={point.v + radius * 0.62}
                    textAnchor="middle"
                    fill="#fff"
                    style={{
                      font: `700 ${radius * 1.5}px ui-sans-serif, system-ui`,
                      pointerEvents: 'none',
                    }}
                  >
                    {point.index}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {live && (
          <span className="pointer-events-none absolute right-2 top-2 rounded-[3px] bg-bad-600 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-white">
            LIVE
          </span>
        )}

        {loupe && (
          <div
            className="pointer-events-none absolute z-10 overflow-hidden rounded-full border-2 border-white shadow-[0_2px_10px_rgba(0,0,0,0.45)]"
            style={{
              width: LOUPE_SIZE,
              height: LOUPE_SIZE,
              // Lech len tren de ngon tay khong che chinh cai kinh lup.
              left: loupeLeft(loupe.cx, frameRef.current),
              top: loupeTop(loupe.cy, frameRef.current),
              backgroundImage: `url(${loupeUrl})`,
              backgroundRepeat: 'no-repeat',
              backgroundSize: `${imageWidth * LOUPE_ZOOM}px ${imageHeight * LOUPE_ZOOM}px`,
              backgroundPosition: `${LOUPE_SIZE / 2 - loupe.u * LOUPE_ZOOM}px ${
                LOUPE_SIZE / 2 - loupe.v * LOUPE_ZOOM
              }px`,
            }}
          >
            <svg viewBox={`0 0 ${LOUPE_SIZE} ${LOUPE_SIZE}`} className="h-full w-full">
              <line
                x1={LOUPE_SIZE / 2 - 14}
                y1={LOUPE_SIZE / 2}
                x2={LOUPE_SIZE / 2 + 14}
                y2={LOUPE_SIZE / 2}
                stroke="#fff"
                strokeWidth={1.5}
              />
              <line
                x1={LOUPE_SIZE / 2}
                y1={LOUPE_SIZE / 2 - 14}
                x2={LOUPE_SIZE / 2}
                y2={LOUPE_SIZE / 2 + 14}
                stroke="#fff"
                strokeWidth={1.5}
              />
              <circle
                cx={LOUPE_SIZE / 2}
                cy={LOUPE_SIZE / 2}
                r={5}
                fill="none"
                stroke="#c2410c"
                strokeWidth={2}
              />
            </svg>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-ink-600">
        <span>
          {nextIndex
            ? `Tiếp theo: chạm vào chóp nón số ${nextIndex}`
            : 'Đã đủ 4 điểm — kéo để tinh chỉnh'}
        </span>
        <span className="text-ink-300">·</span>
        <span>Chọn 1 điểm rồi dùng mũi tên để nhích 1 px (Shift = 10 px)</span>
        {placed.length > 0 && (
          <Button size="sm" variant="ghost" onClick={() => onPlace(placed.slice(0, -1))}>
            Hoàn tác
          </Button>
        )}
        {placed.length > 0 && (
          <Button size="sm" variant="ghost" onClick={() => onPlace([])}>
            Xoá hết
          </Button>
        )}
      </div>
    </div>
  )
}

function loupeLeft(clientX: number, frame: HTMLDivElement | null): number {
  if (!frame) return 0
  const box = frame.parentElement!.getBoundingClientRect()
  const raw = clientX - box.left - LOUPE_SIZE / 2
  return Math.max(4, Math.min(box.width - LOUPE_SIZE - 4, raw))
}

function loupeTop(clientY: number, frame: HTMLDivElement | null): number {
  if (!frame) return 0
  const box = frame.parentElement!.getBoundingClientRect()
  // Uu tien dat phia tren diem cham; neu sat mep tren thi lat xuong duoi.
  const above = clientY - box.top - LOUPE_SIZE - 28
  if (above > 4) return above
  return Math.min(box.height - LOUPE_SIZE - 4, clientY - box.top + 28)
}
