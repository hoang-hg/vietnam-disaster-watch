import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getJson, fmtType, fmtDate, fmtTimeAgo, fmtVndBillion } from "../api.js";
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

export default function EventDetail() {
  const { id } = useParams();
  const [ev, setEv] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        const data = await getJson(`/api/events/${id}`);
        setEv(data);
      } catch (e) {
        setError(e.message || "Load failed");
      }
    })();
  }, [id]);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-2xl border border-red-300 bg-red-50 p-4 text-red-800">
          {error}
        </div>
      </div>
    );
  }
  if (!ev)
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 text-gray-600">Đang tải…</div>
    );

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold leading-snug text-gray-900">
            {ev.title}
          </div>
          <div className="mt-2 text-sm text-gray-600 flex flex-wrap gap-2">
            <span>{ev.province}</span>
            <span>•</span>
            <span>Bắt đầu: {fmtDate(ev.started_at)}</span>
            <span>•</span>
            <span>Cập nhật: {fmtDate(ev.last_updated_at)}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge tone={TYPE_TONES[ev.disaster_type] || "slate"}>
            {fmtType(ev.disaster_type)}
          </Badge>
          <div className="text-xs text-gray-600">
            Tin cậy: {Math.round(ev.confidence * 100)}% • Nguồn:{" "}
            {ev.sources_count}
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-gray-300 bg-white p-4">
        <div className="text-sm font-semibold text-gray-900">
          Nguồn bài báo (đối chiếu)
        </div>
        <div className="text-xs text-gray-600 mt-1">
          Mỗi link mở bài gốc. Hệ thống chỉ lưu metadata.
        </div>
        <div className="mt-4 space-y-3">
          {ev.articles
            ?.sort(
              (a, b) => new Date(b.published_at) - new Date(a.published_at)
            )
            .map((a) => (
              <div
                key={a.id}
                className="rounded-xl border border-gray-300 bg-gray-50 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <a
                    className="font-medium underline decoration-gray-300 hover:decoration-gray-600 text-blue-600 hover:text-blue-800"
                    href={a.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {a.title}
                  </a>
                  <div className="text-xs text-gray-600 whitespace-nowrap">
                    {fmtDate(a.published_at)}
                  </div>
                </div>
                <div className="mt-2 text-xs text-gray-600 flex flex-wrap gap-2">
                  <span className="text-gray-900 font-medium">{a.source}</span>
                  <span>•</span>
                  <span>{a.province}</span>
                  <span>•</span>
                  <span>{fmtType(a.disaster_type)}</span>
                  {a.agency ? (
                    <>
                      <span>•</span>
                      <span>Xác nhận: {a.agency}</span>
                    </>
                  ) : null}
                </div>
                {a.summary ? (
                  <div className="mt-2 text-xs text-gray-700">{a.summary}</div>
                ) : null}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
