import { useEffect, useMemo, useState } from 'react'
import { getJson, fmtType, fmtDate } from '../api.js'
import StatCard from '../components/StatCard.jsx'
import Badge from '../components/Badge.jsx'
import VietnamMap from '../components/VietnamMap.jsx'

const TYPE_TONES = { 
  storm: 'blue', 
  flood: 'cyan', 
  landslide: 'red', 
  earthquake: 'green', 
  tsunami: 'purple',
  wind_hail: 'amber',
  wildfire: 'orange',
  extreme_weather: 'slate', 
  unknown: 'slate' 
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [events, setEvents] = useState([])
  const [articles, setArticles] = useState([])
  const [type, setType] = useState('')
  const [province, setProvince] = useState('')
  const [error, setError] = useState(null)

  async function load() {
    try {
      setError(null)
      const [s, evs, arts] = await Promise.all([
        getJson('/api/stats/summary'),
        getJson(`/api/events?limit=50${type ? `&type=${encodeURIComponent(type)}` : ''}${province ? `&province=${encodeURIComponent(province)}` : ''}`),
        getJson(`/api/articles/latest?limit=50${type ? `&type=${encodeURIComponent(type)}` : ''}${province ? `&province=${encodeURIComponent(province)}` : ''}`),
      ])
      setStats(s); setEvents(evs); setArticles(arts)
    } catch (e) {
      setError(e.message || 'Load failed')
    }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 60_000)
    return () => clearInterval(t)
  }, [type, province])

  const provinces = useMemo(() => {
    const set = new Set(events.map(e => e.province).filter(p => p && p !== 'unknown'))
    return Array.from(set).sort((a,b) => a.localeCompare(b, 'vi'))
  }, [events])

  const mapPoints = useMemo(() => events.map(e => ({
    id: e.id,
    title: e.title,
    province: e.province,
    typeLabel: fmtType(e.disaster_type),
    confidence: e.confidence,
    lat: (window.__PROVINCE_CENTROIDS__?.[e.province]?.[0]) || 16.0,
    lng: (window.__PROVINCE_CENTROIDS__?.[e.province]?.[1]) || 107.5,
  })), [events])

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-2xl font-semibold text-gray-900">Dashboard thời gian thực</div>
          <div className="text-sm text-gray-600 mt-1">Tổng hợp đa nguồn • phân loại • nhóm sự kiện • cập nhật tự động</div>
        </div>
        <div className="flex flex-col gap-2 md:flex-row md:items-center">
          <select className="bg-white border border-gray-300 rounded-xl px-3 py-2 text-sm text-gray-900 font-medium" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">Tất cả loại thiên tai</option>
            <option value="storm">Bão/ATNĐ</option>
            <option value="flood">Mưa lũ/Ngập</option>
            <option value="landslide">Sạt lở/Lũ quét</option>
            <option value="earthquake">Động đất</option>
            <option value="tsunami">Sóng thần</option>
            <option value="wind_hail">Gió mạnh/Dông lốc</option>
            <option value="wildfire">Cháy rừng</option>
            <option value="extreme_weather">Khí hậu cực đoan</option>
            <option value="unknown">Khác</option>
          </select>
          <select className="bg-white border border-gray-300 rounded-xl px-3 py-2 text-sm text-gray-900 font-medium" value={province} onChange={(e) => setProvince(e.target.value)}>
            <option value="">Tất cả tỉnh/thành</option>
            {provinces.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
      </div>

      {error ? (
        <div className="mt-6 rounded-2xl border border-red-300 bg-red-50 p-4 text-red-800">
          Không tải được dữ liệu: {error}. Hãy chắc backend đang chạy ở cổng 8000.
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <StatCard title="Bài viết (24h)" value={stats?.articles_24h ?? '—'} sub="Tổng bài liên quan thiên tai" />
        <StatCard title="Sự kiện (24h)" value={stats?.events_24h ?? '—'} sub="Nhóm theo loại + tỉnh + ngày" />
        <StatCard title="Bão/ATNĐ (24h)" value={stats?.by_type?.storm ?? '—'} sub="Tin bão mới" />
        <StatCard title="Mưa lũ (24h)" value={stats?.by_type?.flood ?? '—'} sub="Tin lũ/ngập mới" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
        <VietnamMap points={mapPoints} />
        <div className="rounded-2xl border border-gray-300 bg-white p-4">
          <div className="text-sm font-semibold text-gray-900">Sự kiện mới nhất</div>
          <div className="text-xs text-gray-600 mt-1">Click để xem chi tiết + đối chiếu nguồn</div>
          <div className="mt-4 space-y-3 max-h-[420px] overflow-auto pr-1">
            {events.slice(0, 30).map(e => (
              <a key={e.id} href={`/events/${e.id}`} className="block rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="font-medium leading-snug text-gray-900">{e.title}</div>
                  <Badge tone={TYPE_TONES[e.disaster_type] || 'slate'}>{fmtType(e.disaster_type)}</Badge>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
                  <span>{e.province}</span><span>•</span>
                  <span>Tin cậy: {Math.round(e.confidence * 100)}%</span><span>•</span>
                  <span>Nguồn: {e.sources_count}</span><span>•</span>
                  <span>Cập nhật: {fmtDate(e.last_updated_at)}</span>
                </div>
              </a>
            ))}
            {events.length === 0 ? <div className="text-sm text-gray-500">Chưa có dữ liệu. Hãy chạy crawler hoặc chờ lịch.</div> : null}
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-gray-300 bg-white p-4">
        <div className="text-sm font-semibold text-gray-900">Tin mới (bài báo)</div>
        <div className="mt-4 overflow-auto">
          <table className="w-full text-sm">
            <thead className="text-gray-700">
              <tr className="text-left border-b border-gray-300">
                <th className="py-2 pr-3 font-semibold">Thời gian</th>
                <th className="py-2 pr-3 font-semibold">Tiêu đề</th>
                <th className="py-2 pr-3 font-semibold">Nguồn</th>
                <th className="py-2 pr-3 font-semibold">Loại</th>
                <th className="py-2 pr-3 font-semibold">Tỉnh</th>
              </tr>
            </thead>
            <tbody>
              {articles.slice(0, 50).map(a => (
                <tr key={a.id} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="py-2 pr-3 whitespace-nowrap text-gray-600">{fmtDate(a.published_at)}</td>
                  <td className="py-2 pr-3">
                    <a className="underline decoration-gray-300 hover:decoration-gray-600 text-blue-600 hover:text-blue-800" href={a.url} target="_blank" rel="noreferrer">{a.title}</a>
                    {a.summary ? <div className="text-xs text-gray-600 mt-1">{a.summary}</div> : null}
                  </td>
                  <td className="py-2 pr-3 text-gray-700">{a.source}</td>
                  <td className="py-2 pr-3"><Badge tone={TYPE_TONES[a.disaster_type] || 'slate'}>{fmtType(a.disaster_type)}</Badge></td>
                  <td className="py-2 pr-3 text-gray-700">{a.province}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {articles.length === 0 ? <div className="text-sm text-slate-500 py-4">Chưa có bài nào.</div> : null}
        </div>
      </div>
    </div>
  )
}
