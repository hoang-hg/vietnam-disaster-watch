import { useEffect, useState } from "react";
import { getJson, fmtType, fmtDate, fmtVndBillion } from "../api.js";
import Badge from "../components/Badge.jsx";

const TYPE_TONES = {
  storm: "blue",
  flood: "cyan",
  landslide: "red",
  earthquake: "green",
  tsunami: "purple",
  wind_hail: "amber",
  wildfire: "orange",
  extreme_weather: "slate",
  unknown: "slate",
};

export default function Events() {
  const [events, setEvents] = useState([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        const evs = await getJson(
          `/api/events?limit=200${q ? `&q=${encodeURIComponent(q)}` : ""}`
        );
        setEvents(evs);
      } catch (e) {
        setError(e.message || "Load failed");
      }
    })();
  }, [q]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold text-gray-900">
            Danh sách sự kiện
          </div>
          <div className="text-sm text-gray-600 mt-1">
            Nhóm theo loại + tỉnh + ngày • Ưu tiên sự kiện đa nguồn
          </div>
        </div>
        <div className="w-full max-w-sm">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Tìm kiếm tiêu đề sự kiện…"
            className="w-full bg-white border border-gray-300 rounded-xl px-3 py-2 text-sm text-gray-900 placeholder-gray-500"
          />
        </div>
      </div>

      {error ? <div className="mt-6 text-red-700">{error}</div> : null}

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        {events.map((e) => (
          <a
            key={e.id}
            href={`/events/${e.id}`}
            className="block rounded-2xl border border-gray-300 bg-white hover:bg-gray-50 p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="font-semibold leading-snug text-gray-900">
                {e.title}
              </div>
              <Badge tone={TYPE_TONES[e.disaster_type] || "slate"}>
                {fmtType(e.disaster_type)}
              </Badge>
            </div>
            <div className="mt-2 text-xs text-gray-600 flex flex-wrap gap-2">
              <span>{e.province}</span>
              <span>•</span>
              <span>Nguồn: {e.sources_count}</span>
              <span>•</span>
              <span>Tin cậy: {Math.round(e.confidence * 100)}%</span>
              <span>•</span>
              <span>Cập nhật: {fmtDate(e.last_updated_at)}</span>
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2 text-xs">
              <div className="rounded-xl border border-gray-300 bg-gray-50 p-2">
                <div className="text-gray-600 font-medium">Chết</div>
                <div className="font-semibold text-gray-900">
                  {e.deaths ?? "—"}
                </div>
              </div>
              <div className="rounded-xl border border-gray-300 bg-gray-50 p-2">
                <div className="text-gray-600 font-medium">Mất tích</div>
                <div className="font-semibold text-gray-900">
                  {e.missing ?? "—"}
                </div>
              </div>
              <div className="rounded-xl border border-gray-300 bg-gray-50 p-2">
                <div className="text-gray-600 font-medium">Bị thương</div>
                <div className="font-semibold text-gray-900">
                  {e.injured ?? "—"}
                </div>
              </div>
              <div className="rounded-xl border border-gray-300 bg-gray-50 p-2">
                <div className="text-gray-600 font-medium">Thiệt hại</div>
                <div className="font-semibold text-gray-900">
                  {fmtVndBillion(e.damage_billion_vnd)}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>

      {events.length === 0 ? (
        <div className="mt-6 text-slate-500">Chưa có sự kiện.</div>
      ) : null}
    </div>
  );
}
