/**
 * Buoc 4: cang chinh camera - man hinh cot loi cua ca cong cu.
 *
 * Quy trinh tren hien truong:
 *   1. Dat 4 vat moc (chop non) o vi tri da do bang thuoc day.
 *   2. Nhap toa do met cua tung vat moc (bang ben phai).
 *   3. Cham vao chan tung vat moc tren anh, theo dung so thu tu.
 *   4. Bam "Giai goc lap" -> he thong tim pitch/yaw (va do cao) khop nhat.
 *   5. Doc sai so RMS bang MET. Dat khi <= 0.30 m.
 *   6. Bat luoi met de kiem tra bang mat: luoi phai trung vach ke va vat moc.
 *   7. Chot ket qua vao ho so.
 *
 * Co the bo qua buoc giai va chinh tay bang thanh truot - luoi met ve lai ngay
 * theo goc dang chinh, nen cang chinh bang mat cung kha thi.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type {
  CameraConfig,
  CameraId,
  GridLine,
  ReferenceCone,
  SolveResponse,
  VerifyResponse,
} from '../../lib/types'
import { CameraCanvas, type PlacedPoint } from '../../components/CameraCanvas'
import {
  Badge,
  Button,
  Callout,
  DataRow,
  Field,
  NumberInput,
  Panel,
  SegmentedControl,
  Slider,
  StatusMark,
  Toggle,
} from '../../components/ui'
import { useApp } from '../../store/app'

const ORDER: CameraId[] = ['MIRROR_R', 'MIRROR_L', 'FRONT_CAM', 'REAR_CAM']

export function StepCalibrate() {
  const { profile, patchCamera } = useApp()
  const [cameraId, setCameraId] = useState<CameraId>('MIRROR_R')
  const [cones, setCones] = useState<ReferenceCone[]>([])
  const [placed, setPlaced] = useState<PlacedPoint[]>([])
  const [gridLines, setGridLines] = useState<GridLine[]>([])
  const [showGrid, setShowGrid] = useState(true)
  const [live, setLive] = useState(false)
  const [bust, setBust] = useState(() => Date.now())
  const [solveHeight, setSolveHeight] = useState(true)
  const [solution, setSolution] = useState<SolveResponse | null>(null)
  const [verified, setVerified] = useState<VerifyResponse | null>(null)
  const [busy, setBusy] = useState<'solve' | 'verify' | 'commit' | 'upload' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string>('')
  const [hasUploadedImage, setHasUploadedImage] = useState(false)
  const [imageSize, setImageSize] = useState<[number, number] | null>(null)

  const camera = profile?.cameras[cameraId]
  const profileId: string | undefined = profile?.meta.profile_id

  function refreshImageStatus(pid: string) {
    api
      .imageStatus(pid, cameraId)
      .then((response) => {
        setHasUploadedImage(response.has_uploaded_image)
        setImageSize(response.image_size)
      })
      .catch(() => {
        setHasUploadedImage(false)
        setImageSize(null)
      })
  }

  // Doi camera -> nap lai bang vat moc, xoa diem da cham.
  useEffect(() => {
    if (!profileId) return
    setPlaced([])
    setSolution(null)
    setVerified(null)
    setError(null)
    setBust(Date.now())
    setLive(false)
    api
      .referenceCones(profileId, cameraId)
      .then((response) => {
        setCones(response.cones)
        setNote(response.note)
      })
      .catch(() => setCones([]))
    refreshImageStatus(profileId)
  }, [profileId, cameraId])

  async function uploadImage(file: File) {
    if (!profileId || !camera) return
    setBusy('upload')
    setError(null)
    try {
      const result = await api.uploadCameraImage(profileId, cameraId, file)
      // Server tu chinh width/height cua camera trong ho so theo dung anh -
      // dong bo lai o client de luoi met chieu dung ti le, khong bi lech.
      const [width, height] = result.image_size
      patchCamera(cameraId, {
        width,
        height,
        intrinsics: { ...camera.intrinsics, cx: width / 2, cy: height / 2 },
      })
      setBust(Date.now())
      setPlaced([])
      refreshImageStatus(profileId)
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Tải ảnh thất bại.')
    } finally {
      setBusy(null)
    }
  }

  async function removeImage() {
    if (!profileId) return
    setBusy('upload')
    try {
      await api.deleteCameraImage(profileId, cameraId)
      setBust(Date.now())
      refreshImageStatus(profileId)
    } finally {
      setBusy(null)
    }
  }

  // Luoi met chieu lai moi khi goc lap hoac ong kinh doi.
  const refreshGrid = useCallback(async () => {
    if (!camera) return
    try {
      const response = await api.projectGrid({
        camera,
        x_range: cameraId === 'FRONT_CAM' ? [0, 26] : [-20, 8],
        y_range: [-10, 10],
        step: 1,
      })
      setGridLines(response.lines)
    } catch {
      setGridLines([])
    }
  }, [camera, cameraId])

  useEffect(() => {
    if (showGrid) void refreshGrid()
    else setGridLines([])
  }, [showGrid, refreshGrid])

  const correspondences = useMemo(
    () =>
      placed
        .map((point) => {
          const cone = cones.find((item) => item.index === point.index)
          if (!cone) return null
          return { u: point.u, v: point.v, x: cone.x, y: cone.y, label: `${cone.index}·${cone.name}` }
        })
        .filter((item): item is NonNullable<typeof item> => item !== null),
    [placed, cones],
  )

  if (!profile || !camera || !profileId) return null

  const calibratedCount = Object.values(profile.cameras).filter((c) => c.calibrated_at).length

  async function solve() {
    if (!camera) return
    setBusy('solve')
    setError(null)
    try {
      const response = await api.solveAngles({
        camera,
        points: correspondences,
        solve_height: solveHeight,
      })
      setSolution(response)
      setVerified(null)
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Giải góc thất bại.')
    } finally {
      setBusy(null)
    }
  }

  function applySolution() {
    if (!solution || !camera) return
    const position = [...(camera.position ?? [0, 0, 0])] as [number, number, number]
    if (solveHeight) position[2] = solution.height_m
    patchCamera(cameraId, {
      pitch_deg: solution.angles.pitch_deg,
      yaw_deg: solution.angles.yaw_deg,
      position,
      auto_position: false,
    })
    setSolution(null)
  }

  async function verify() {
    if (!camera) return
    setBusy('verify')
    setError(null)
    try {
      setVerified(await api.verifyPoints({ camera, points: correspondences }))
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Kiểm tra thất bại.')
    } finally {
      setBusy(null)
    }
  }

  async function commit() {
    if (!camera || !profileId) return
    setBusy('commit')
    setError(null)
    try {
      const rms = verified?.rms_m ?? null
      const response = await api.commitCamera(profileId, cameraId, camera, rms)
      patchCamera(cameraId, response.camera)
    } catch (exception) {
      setError(exception instanceof ApiError ? exception.message : 'Chốt kết quả thất bại.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SegmentedControl
          value={cameraId}
          onChange={setCameraId}
          options={ORDER.map((id) => ({
            value: id,
            label: (
              <span className="flex items-center gap-1.5">
                {profile.cameras[id].calibrated_at && <StatusMark tone="ok" />}
                {profile.cameras[id].label}
              </span>
            ),
          }))}
        />
        <Badge tone={calibratedCount === 4 ? 'ok' : 'warn'}>
          {calibratedCount}/4 camera đã căn chỉnh
        </Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Panel
          title="Khung hình camera"
          subtitle="Chạm vào chân từng chóp nón, theo đúng số thứ tự"
          dense
          actions={
            <div className="flex items-center gap-2">
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    if (file) void uploadImage(file)
                    event.target.value = ''
                  }}
                />
                <Button size="sm" as="span" loading={busy === 'upload'}>
                  Tải ảnh camera lên
                </Button>
              </label>
              {hasUploadedImage && (
                <Button size="sm" variant="ghost" onClick={removeImage}>
                  Bỏ ảnh, dùng mô phỏng
                </Button>
              )}
              {!hasUploadedImage && (
                <>
                  <Button size="sm" variant="ghost" onClick={() => setBust(Date.now())}>
                    Chụp lại
                  </Button>
                  <Button
                    size="sm"
                    variant={live ? 'primary' : 'default'}
                    onClick={() => setLive((v) => !v)}
                  >
                    {live ? 'Dừng hình trực tiếp' : 'Xem trực tiếp'}
                  </Button>
                </>
              )}
            </div>
          }
        >
          <div className="p-3">
            {!hasUploadedImage && (
              <Callout tone="warn" title="Đang dùng ảnh mô phỏng">
                Đây là hình vẽ giả lập, không phải ảnh camera thật. Nếu camera đã lắp xong, chụp ảnh
                bằng điện thoại và bấm "Tải ảnh camera lên" để căn chỉnh trên ảnh thật.
              </Callout>
            )}
            <div className={!hasUploadedImage ? 'mt-3' : ''}>
              <CameraCanvas
                imageUrl={
                  live && !hasUploadedImage
                    ? api.streamUrl(profileId, cameraId)
                    : api.snapshotUrl(profileId, cameraId, bust)
                }
                loupeUrl={api.snapshotUrl(profileId, cameraId, bust)}
                imageSize={imageSize ?? [camera.width, camera.height]}
                cones={cones}
                placed={placed}
                onPlace={setPlaced}
                gridLines={gridLines}
                showGrid={showGrid}
                live={live && !hasUploadedImage}
              />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-4">
              <Toggle
                checked={showGrid}
                onChange={setShowGrid}
                label="Hiện lưới mét 1×1 m"
                hint="Camera nhìn chéo xuống mặt đường nên lưới sẽ méo dần theo khoảng cách (ô gần to, ô xa nhỏ) — đó là bình thường. Cách kiểm tra: 2 chóp nón cách nhau 1 m ngoài thực tế thì trên ảnh phải rơi đúng 1 ô lưới, không cần ô lưới trông vuông đều."
              />
            </div>
            {live && !hasUploadedImage && (
              <Callout tone="warn">
                Đang xem trực tiếp. Nên bấm "Dừng hình trực tiếp" trước khi chạm điểm — ảnh tĩnh cho
                độ chính xác cao hơn và kính lúp nét hơn.
              </Callout>
            )}
          </div>
        </Panel>

        <div className="space-y-4">
          <ConeTable
            cones={cones}
            placed={placed}
            note={note}
            onChange={setCones}
            camera={camera}
          />

          <Panel title="Giải góc lắp" subtitle="Từ số đo thực tế, tìm pitch / yaw khớp nhất">
            <div className="space-y-3">
              <Toggle
                checked={solveHeight}
                onChange={setSolveHeight}
                label="Giải luôn độ cao lắp camera"
                hint="Bật khi không đo chính xác được độ cao gương"
              />

              <div className="flex gap-2">
                <Button
                  variant="primary"
                  className="flex-1"
                  loading={busy === 'solve'}
                  disabled={correspondences.length < 2}
                  onClick={solve}
                >
                  Giải góc lắp
                </Button>
                <Button
                  className="flex-1"
                  loading={busy === 'verify'}
                  disabled={correspondences.length < 1}
                  onClick={verify}
                >
                  Kiểm tra sai số
                </Button>
              </div>

              {correspondences.length < 2 && (
                <p className="text-xs text-ink-500">
                  Cần ít nhất 2 điểm; nên dùng đủ 4 điểm để kết quả ổn định.
                </p>
              )}

              {error && <Callout tone="bad">{error}</Callout>}

              {solution && (
                <SolutionCard solution={solution} onApply={applySolution} onDismiss={() => setSolution(null)} />
              )}

              {verified && <VerifyCard result={verified} />}
            </div>
          </Panel>

          <ManualAngles
            camera={camera}
            rollSupported={solution?.roll_supported_by_engine}
            onChange={(patch) => patchCamera(cameraId, patch)}
          />

          <Panel title="Chốt kết quả">
            <div className="space-y-2">
              <DataRow
                label="Trạng thái camera này"
                value={
                  camera.calibrated_at
                    ? `RMS ${camera.calibration_rms_m?.toFixed(3) ?? '—'} m`
                    : 'chưa chốt'
                }
              />
              <Button
                variant="primary"
                className="w-full"
                loading={busy === 'commit'}
                disabled={!verified || verified.verdict === 'fail'}
                onClick={commit}
              >
                Chốt căn chỉnh {camera.label}
              </Button>
              {!verified && (
                <p className="text-xs text-ink-500">
                  Bấm "Kiểm tra sai số" trước khi chốt — không chốt khi chưa biết sai số bao nhiêu.
                </p>
              )}
              {verified?.verdict === 'fail' && (
                <p className="text-xs text-bad-600">
                  Sai số còn quá lớn. Đo lại vị trí 4 chóp nón bằng thước dây, kiểm tra góc nhìn ống
                  kính (HFOV) và độ cao lắp camera.
                </p>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

// --- Bang vat moc ----------------------------------------------------------
function ConeTable({
  cones,
  placed,
  note,
  onChange,
  camera,
}: {
  cones: ReferenceCone[]
  placed: PlacedPoint[]
  note: string
  onChange: (cones: ReferenceCone[]) => void
  camera: CameraConfig
}) {
  const [measured, setMeasured] = useState<Record<number, string>>({})

  /** Cham vao anh roi doc ngay toa do met - de so voi thuoc day. */
  useEffect(() => {
    const points = placed.map((point) => [point.u, point.v] as [number, number])
    if (!points.length) {
      setMeasured({})
      return
    }
    let cancelled = false
    api
      .unproject({ camera, pixels: points })
      .then((response) => {
        if (cancelled) return
        const next: Record<number, string> = {}
        response.points.forEach((row, index) => {
          const key = placed[index].index
          next[key] = row.ground
            ? `${row.ground[0].toFixed(2)} ; ${row.ground[1].toFixed(2)}`
            : 'ngoài mặt đường'
        })
        setMeasured(next)
      })
      .catch(() => setMeasured({}))
    return () => {
      cancelled = true
    }
  }, [placed, camera])

  return (
    <Panel
      title="4 chóp nón đặt trên bãi"
      subtitle="Bước 1: đo vị trí thật bằng thước dây. Bước 2: chạm vào chân từng chóp nón trong ảnh bên trái."
      dense
    >
      <div className="divide-y divide-ink-100">
        {cones.map((cone, index) => {
          const point = placed.find((item) => item.index === cone.index)
          return (
            <div key={cone.index} className="px-3 py-2">
              <div className="flex items-center gap-2">
                <span
                  className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[3px] text-[11px] font-bold text-white"
                  style={{ backgroundColor: cone.color }}
                >
                  {cone.index}
                </span>
                <span className="text-[13px] font-medium text-ink-900">
                  Chóp nón {cone.name}
                </span>
                {point ? (
                  <Badge tone="ok">Đã chạm trong ảnh</Badge>
                ) : (
                  <Badge tone="neutral">Chưa chạm trong ảnh</Badge>
                )}
              </div>
              <p className="mt-1 text-[11.5px] text-ink-500">
                Nhập đúng khoảng cách bạn đo bằng thước dây từ tâm trục sau đầu kéo đến chóp nón này.
              </p>
              <div className="mt-1.5 grid grid-cols-2 gap-2">
                <Field label="Cách trước/sau xe (m)" hint="Phía trước xe: số dương. Phía sau xe: số âm.">
                  <NumberInput
                    value={cone.x}
                    step={0.05}
                    onChange={(value) => {
                      const next = [...cones]
                      next[index] = { ...cone, x: value }
                      onChange(next)
                    }}
                  />
                </Field>
                <Field label="Cách trái/phải xe (m)" hint="Bên trái xe: số dương. Bên phải xe: số âm.">
                  <NumberInput
                    value={cone.y}
                    step={0.05}
                    onChange={(value) => {
                      const next = [...cones]
                      next[index] = { ...cone, y: value }
                      onChange(next)
                    }}
                  />
                </Field>
              </div>
              {point && (
                <p className="num mt-1 text-[11.5px] text-ink-500">
                  Theo góc camera đang lưu, chóp nón này đang được tính ở vị trí:{' '}
                  {measured[cone.index] ?? '…'} m — nếu số này lệch nhiều so với số bạn đo, góc lắp
                  camera đang sai.
                </p>
              )}
            </div>
          )
        })}
      </div>
      {note && <p className="border-t border-ink-200 px-3 py-2 text-[11.5px] text-ink-500">{note}</p>}
    </Panel>
  )
}

// --- Ket qua giai ----------------------------------------------------------
function SolutionCard({
  solution,
  onApply,
  onDismiss,
}: {
  solution: SolveResponse
  onApply: () => void
  onDismiss: () => void
}) {
  const tone = solution.verdict === 'pass' ? 'ok' : solution.verdict === 'warn' ? 'warn' : 'bad'
  return (
    <div className={`rounded-[4px] border p-3 ${tone === 'ok' ? 'border-ok-600/30 bg-ok-100' : tone === 'warn' ? 'border-warn-600/30 bg-warn-100' : 'border-bad-600/30 bg-bad-100'}`}>
      <div className="mb-2 flex items-center gap-2">
        <StatusMark tone={tone} />
        <span className="num text-sm font-semibold">
          RMS {solution.rms_m.toFixed(3)} m
          <span className="ml-1 text-[11px] font-normal opacity-70">
            / mục tiêu ≤ {solution.target_m.toFixed(2)} m
          </span>
        </span>
      </div>
      <p className="mb-2 text-[12px] opacity-90">{solution.message}</p>
      <div className="mb-2 space-y-0.5 text-[12px]">
        <DataRow label="Pitch" value={`${solution.angles.pitch_deg.toFixed(2)}°`} />
        <DataRow label="Yaw" value={`${solution.angles.yaw_deg.toFixed(2)}°`} />
        <DataRow label="Độ cao lắp" value={`${solution.height_m.toFixed(3)} m`} />
        <DataRow label="Sai số lớn nhất" value={`${solution.max_error_m.toFixed(3)} m`} />
      </div>
      <div className="mb-2 overflow-hidden rounded-[3px] border border-black/10 bg-white/70">
        <table className="w-full text-left text-[11.5px]">
          <thead>
            <tr className="border-b border-black/10">
              <th className="px-2 py-1">Điểm</th>
              <th className="px-2 py-1">Đo được</th>
              <th className="px-2 py-1">Hệ thống tính</th>
              <th className="px-2 py-1">Lệch</th>
            </tr>
          </thead>
          <tbody className="num">
            {solution.per_point.map((row) => (
              <tr key={row.label} className="border-b border-black/5 last:border-0">
                <td className="px-2 py-1">{row.label}</td>
                <td className="px-2 py-1">{row.measured.map((v) => v.toFixed(2)).join(' ; ')}</td>
                <td className="px-2 py-1">
                  {row.estimated ? row.estimated.map((v) => v.toFixed(2)).join(' ; ') : '—'}
                </td>
                <td className="px-2 py-1">{row.error_m?.toFixed(3) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2">
        <Button size="sm" variant="primary" onClick={onApply}>
          Áp dụng góc này
        </Button>
        <Button size="sm" variant="ghost" onClick={onDismiss}>
          Bỏ
        </Button>
      </div>
    </div>
  )
}

function VerifyCard({ result }: { result: VerifyResponse }) {
  const tone = result.verdict === 'pass' ? 'ok' : result.verdict === 'warn' ? 'warn' : 'bad'
  return (
    <Callout tone={tone} title={`Sai số hiện tại: ${result.rms_m?.toFixed(3) ?? '—'} m`}>
      <div className="num space-y-0.5">
        {result.per_point.map((row, index) => (
          <div key={index} className="flex justify-between gap-3">
            <span>{row.label || `Điểm ${index + 1}`}</span>
            <span>
              đo {row.measured.map((v) => v.toFixed(2)).join(' ; ')} → tính{' '}
              {row.estimated ? row.estimated.map((v) => v.toFixed(2)).join(' ; ') : '—'} (lệch{' '}
              {row.error_m?.toFixed(3) ?? '—'} m)
            </span>
          </div>
        ))}
      </div>
    </Callout>
  )
}

// --- Chinh tay -------------------------------------------------------------
function ManualAngles({
  camera,
  onChange,
}: {
  camera: CameraConfig
  rollSupported?: boolean
  onChange: (patch: Partial<CameraConfig>) => void
}) {
  return (
    <Panel
      title="Chỉnh tay (nếu không dùng giải tự động)"
      subtitle="Kéo đến khi khoảng cách giữa các chóp nón trên lưới đúng với khoảng cách bạn đo bằng thước"
    >
      <div className="space-y-3">
        <Slider
          label="Góc cúi xuống của camera"
          unit="°"
          min={-60}
          max={20}
          step={0.1}
          value={camera.pitch_deg}
          onChange={(value) => onChange({ pitch_deg: value })}
          marks={[-60, -20, 20]}
        />
        <Slider
          label="Góc quay ngang của camera"
          unit="°"
          min={-180}
          max={180}
          step={0.1}
          value={camera.yaw_deg}
          onChange={(value) => onChange({ yaw_deg: value })}
          marks={[-180, 0, 180]}
        />
      </div>
    </Panel>
  )
}
