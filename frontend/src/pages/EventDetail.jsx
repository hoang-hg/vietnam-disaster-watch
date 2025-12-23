import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
} from "../api.js";
import Badge from "../components/Badge.jsx";
import { ArrowLeft } from "lucide-react";

const TYPE_TONES = {
  storm: "blue",
  flood_landslide: "cyan",
  heat_drought: "orange",
  wind_fog: "slate",
  storm_surge: "purple",
  extreme_other: "amber",
  wildfire: "red",
  quake_tsunami: "emerald",
  unknown: "slate",
};

export default function EventDetail() {
  const { id } = useParams();
  const [ev, setEv] = useState(null);
  const [error, setError] = useState(null);
  const [expandedSummary, setExpandedSummary] = useState(false);

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
        <Link to="/events" className="inline-flex items-center text-sm text-slate-500 hover:text-blue-600 mb-4 transition-colors">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Quay lại danh sách
        </Link>
        <div className="rounded-2xl border border-red-300 bg-red-50 p-4 text-red-800">
          {error}
        </div>
      </div>
    );
  }
  if (!ev)
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 text-gray-600">
         <div className="animate-pulse flex space-x-4">
            <div className="flex-1 space-y-4 py-1">
              <div className="h-4 bg-slate-200 rounded w-1/4"></div>
              <div className="space-y-3">
                <div className="h-2 bg-slate-200 rounded"></div>
                <div className="h-2 bg-slate-200 rounded"></div>
              </div>
            </div>
         </div>
      </div>
    );

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Back Button */}
      <Link to="/events" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-blue-600 mb-6 transition-colors group">
        <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
        Quay lại danh sách sự kiện
      </Link>

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
            <span>
              Cập nhật: {fmtTimeAgo(ev.last_updated_at)} (
              {fmtDate(ev.last_updated_at)})
            </span>
          </div>
        </div>
          <div className="flex flex-col items-end gap-2">

            <Badge tone={TYPE_TONES[ev.disaster_type] || "slate"}>
              {fmtType(ev.disaster_type)}
            </Badge>
            {ev.needs_verification === 1 && (
              <Badge tone="red" className="animate-pulse">
                Dữ liệu cần kiểm chứng
              </Badge>
            )}
            <div className="text-xs text-gray-600">
              Tổng hợp từ {ev.sources_count} báo
            </div>
          </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        {ev.deaths ? (
          <div className="bg-red-50 text-red-800 px-3 py-1 rounded text-sm">
            Tử vong: {ev.deaths}
          </div>
        ) : null}
        {ev.injured ? (
          <div className="bg-yellow-50 text-yellow-800 px-3 py-1 rounded text-sm">
            Bị thương: {ev.injured}
          </div>
        ) : null}
        {ev.missing ? (
          <div className="bg-orange-50 text-orange-800 px-3 py-1 rounded text-sm">
            Mất tích: {ev.missing}
          </div>
        ) : null}
        {ev.damage_billion_vnd ? (
          <div className="bg-gray-50 text-gray-900 px-3 py-1 rounded text-sm">
            Ước thiệt hại: {fmtVndBillion(ev.damage_billion_vnd)}
          </div>
        ) : null}
      </div>

      {ev.articles && ev.articles.length > 0
        ? (() => {
            const combined = ev.articles
              .map((a) =>
                a.full_text && a.full_text.length
                  ? a.full_text
                  : a.summary || ""
              )
              .filter(Boolean)
              .slice(0, 3)
              .join("<br/><br/>"); // Use line breaks for HTML
            
            const heroImage = ev.articles.find(a => a.image_url)?.image_url;
            
            if (!combined && !heroImage) return null;
            const limit = 800;
            const short =
              combined.length > limit && !expandedSummary
                ? combined.slice(0, limit).trim() + "…"
                : combined;
                
            return (
              <div className="mt-4 text-sm text-gray-700 bg-white p-4 rounded border border-gray-200">
                <div className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <span className="w-1 h-5 bg-blue-500 rounded-full"></span>
                  Tóm tắt tổng hợp
                </div>
                
                {heroImage && (
                    <div className="mb-4">
                        <img 
                            src={heroImage} 
                            alt="Ảnh hiện trường" 
                            className="rounded-lg w-full max-h-[400px] object-cover"
                            onError={(e) => {e.target.style.display = 'none'}}
                        />
                        <p className="mt-1 text-xs text-slate-500 italic text-center">Ảnh hiện trường ghi nhận từ nguồn tin</p>
                    </div>
                )}
                
                <div 
                  className="text-sm text-gray-700 leading-relaxed summary-content"
                  dangerouslySetInnerHTML={{ __html: short }}
                />
                {combined.length > limit ? (
                  <button
                    className="mt-2 text-sm text-blue-600 hover:underline font-medium"
                    onClick={() => setExpandedSummary((s) => !s)}
                  >
                    {expandedSummary ? "Thu gọn" : "Xem thêm chi tiết"}
                  </button>
                ) : null}
              </div>
            );
          })()
        : null}

      <div className="mt-6 rounded-2xl border border-gray-300 bg-white p-4">
        <div className="text-sm font-semibold text-gray-900">
          Bài báo liên quan ({ev.articles?.length || 0} báo)
        </div>
        <div className="text-xs text-gray-600 mt-1">
          Timeline cập nhật từ các nguồn. Mỗi link mở bài gốc.
        </div>
        <div className="mt-4 space-y-0">
          {ev.articles
            ?.sort(
              (a, b) => new Date(b.published_at) - new Date(a.published_at)
            )
            .map((a, idx) => (
              <div
                key={a.id}
                className="relative border-l-2 border-gray-300 pb-4 pl-6"
              >
                <div className="absolute -left-2.5 top-1 h-5 w-5 rounded-full bg-blue-500" />
                <div className="flex items-start justify-between gap-3">
                  <a
                    className="font-medium underline decoration-gray-300 hover:decoration-gray-600 text-blue-600 hover:text-blue-800 text-sm"
                    href={a.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {a.title}
                  </a>
                </div>
                <div className="mt-1 text-xs text-gray-600 flex flex-wrap gap-2">
                  <span className="text-gray-900 font-medium bg-gray-100 px-2 py-1 rounded">
                    {a.source}
                  </span>
                  <span>{fmtTimeAgo(a.published_at)}</span>
                  <span>•</span>
                  <span>{fmtType(a.disaster_type)}</span>
                  {a.province !== "unknown" ? (
                    <>
                      <span>•</span>
                      <span>{a.province}</span>
                    </>
                  ) : null}
                  {a.agency ? (
                    <>
                      <span>•</span>
                      <span className="font-medium">Xác nhận: {a.agency}</span>
                    </>
                  ) : null}
                  {a.needs_verification === 1 && (
                     <span className="bg-red-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold animate-pulse">
                        SỐ LIỆU CẦN XÁC MINH
                     </span>
                  )}
                </div>
                {a.summary ? (
                  <div className="mt-2 text-xs text-gray-700 line-clamp-2">
                    {a.summary}
                  </div>
                ) : null}
                {a.image_url ? (
                  <div className="mt-3">
                    <img 
                      src={a.image_url} 
                      alt="" 
                      className="rounded-lg h-48 w-full object-cover border border-slate-200"
                      onError={(e) => {e.target.style.display = 'none'}}
                    />
                  </div>
                ) : null}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
