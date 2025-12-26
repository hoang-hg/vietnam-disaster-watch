import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getJson,
  deleteJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
} from "../api.js";
import Badge from "../components/Badge.jsx";
import { ArrowLeft, Trash2 } from "lucide-react";

const TYPE_TONES = {
  storm: "blue",
  flood_landslide: "cyan",
  heat_drought: "orange",
  wind_fog: "slate",
  storm_surge: "purple",
  extreme_other: "yellow",
  wildfire: "red",
  quake_tsunami: "green",
  recovery: "indigo",
  relief_aid: "pink",
  unknown: "slate",
};

const isJunkImage = (url) => {
  if (!url) return true;
  const junkPatterns = [
      'googleusercontent.com', 
      'gstatic.com', 
      'news_logo', 
      'default_image',
      'placeholder',
      'tabler-icons',
      'triangle.svg',
      'droplet.svg'
  ];
  return junkPatterns.some(p => url.toLowerCase().includes(p));
};

export default function EventDetail() {
  const { id } = useParams();
  const [ev, setEv] = useState(null);
  const [error, setError] = useState(null);
  const [expandedSummary, setExpandedSummary] = useState(false);
  const [isAdmin, setIsAdmin] = useState(!!localStorage.getItem("access_token"));

  const handleDeleteArticle = async (e, articleId) => {
    e.preventDefault();
    if (!window.confirm("Bạn có chắc chắn muốn xóa bài báo này? Bài báo sẽ bị đánh dấu 'rejected' và loại khỏi sự kiện.")) return;

    try {
        await deleteJson(`/api/articles/${articleId}`);
        // Update local state
        setEv(prev => ({
            ...prev,
            articles: prev.articles.filter(a => a.id !== articleId),
            sources_count: Math.max(0, prev.sources_count - 1)
        }));
    } catch (err) {
        alert("Xóa thất bại: " + err.message);
    }
  };

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
              <Badge tone="red">
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
          <div className="bg-red-50 text-red-700 border border-red-200 font-bold px-3 py-1.5 rounded-lg text-sm shadow-sm">
            Tử vong: {ev.deaths}
          </div>
        ) : null}
        {ev.injured ? (
          <div className="bg-yellow-50 text-yellow-700 border border-yellow-200 font-bold px-3 py-1.5 rounded-lg text-sm shadow-sm">
            Bị thương: {ev.injured}
          </div>
        ) : null}
        {ev.missing ? (
          <div className="bg-orange-50 text-orange-700 border border-orange-200 font-bold px-3 py-1.5 rounded-lg text-sm shadow-sm">
            Mất tích: {ev.missing}
          </div>
        ) : null}
        {ev.damage_billion_vnd ? (
          <div className="bg-blue-50 text-blue-700 border border-blue-200 font-bold px-3 py-1.5 rounded-lg text-sm shadow-sm">
            Ước thiệt hại: {fmtVndBillion(ev.damage_billion_vnd)}
          </div>
        ) : null}
      </div>

      {/* Detailed Impact Breakdown (homes, agriculture, etc.) */}
      {ev.details && Object.keys(ev.details).length > 0 && (
          <div className="mt-8 space-y-4">
              <div className="flex items-center gap-2 text-slate-800 font-bold">
                  <span className="w-1.5 h-5 bg-red-500 rounded-full"></span>
                  Chi tiết thiệt hại trích xuất
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Housing Details */}
                  {ev.details.homes?.length > 0 && (
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                          <div className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                               <div className="w-2 h-2 rounded-full bg-indigo-500"></div>
                               Nhà cửa & Công trình
                          </div>
                          <div className="space-y-2">
                              {ev.details.homes.map((h, i) => (
                                  <div key={i} className="flex justify-between items-center text-sm">
                                      <span className="text-slate-600 truncate mr-2">{h.status || 'Hư hại'}</span>
                                      <span className="font-bold text-slate-900 whitespace-nowrap">{h.num} {h.unit || 'căn'}</span>
                                  </div>
                              ))}
                          </div>
                      </div>
                  )}

                  {/* Agriculture Details */}
                  {ev.details.agriculture?.length > 0 && (
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                          <div className="text-xs font-bold text-emerald-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                               <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                               Nông nghiệp & Chăn nuôi
                          </div>
                          <div className="space-y-2">
                              {ev.details.agriculture.map((a, i) => (
                                  <div key={i} className="flex justify-between items-center text-sm">
                                      <span className="text-slate-600 truncate mr-2">{a.crop || a.livestock || 'Diện tích'} {a.status ? `(${a.status})` : ''}</span>
                                      <span className="font-bold text-slate-900 whitespace-nowrap">{a.num} {a.unit}</span>
                                  </div>
                              ))}
                          </div>
                      </div>
                  )}

                  {/* Marine Details */}
                  {ev.details.marine?.length > 0 && (
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                          <div className="text-xs font-bold text-blue-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                               <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                               Tàu thuyền & Thủy sản
                          </div>
                          <div className="space-y-2">
                              {ev.details.marine.map((m, i) => (
                                  <div key={i} className="flex justify-between items-center text-sm">
                                      <span className="text-slate-600 truncate mr-2">{m.vessel || 'Phương tiện'}</span>
                                      <span className="font-bold text-slate-900 whitespace-nowrap">{m.num} {m.unit}</span>
                                  </div>
                              ))}
                          </div>
                      </div>
                  )}

                  {/* Disruption Details */}
                  {ev.details.disruption?.length > 0 && (
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                          <div className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                               <div className="w-2 h-2 rounded-full bg-slate-500"></div>
                               Giao thông & Đời sống
                          </div>
                          <div className="space-y-2">
                              {ev.details.disruption.map((d, i) => (
                                  <div key={i} className="flex justify-between items-center text-sm">
                                      <span className="text-slate-600 truncate mr-2">{d.obj || 'Số lượng'}</span>
                                      <span className="font-bold text-slate-900 whitespace-nowrap">{d.num || ''} {d.unit || 'lần'}</span>
                                  </div>
                              ))}
                          </div>
                      </div>
                  )}
              </div>
          </div>
      )}

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
            
            const heroImage = ev.articles.find(a => a.image_url && !isJunkImage(a.image_url))?.image_url;
            
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
                <div className="flex items-start justify-between gap-3 group/item">
                  <a
                    className={`font-medium text-sm transition-all flex-1 ${a.is_broken ? 'text-slate-400 cursor-not-allowed no-underline' : 'underline decoration-gray-300 hover:decoration-gray-600 text-blue-600 hover:text-blue-800'}`}
                    href={a.is_broken ? '#' : a.url}
                    onClick={(e) => a.is_broken && e.preventDefault()}
                    target={a.is_broken ? '_self' : '_blank'}
                    rel="noreferrer"
                  >
                    {a.title}
                    {a.is_broken && <span className="ml-2 text-[10px] font-bold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded border border-slate-200">BÀI GỐC ĐÃ GỠ</span>}
                  </a>
                  {isAdmin && (
                      <button
                          onClick={(e) => handleDeleteArticle(e, a.id)}
                          className="p-2 ml-2 flex-shrink-0 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                          title="Xóa bài báo (Admin)"
                      >
                          <Trash2 className="w-4 h-4" />
                      </button>
                  )}
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
                     <span className="bg-red-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">
                        SỐ LIỆU CẦN XÁC MINH
                     </span>
                  )}
                  {a.status === 'pending' && (
                     <span className="bg-yellow-500 text-white px-1.5 py-0.5 rounded text-[10px] font-bold shadow-sm">
                        ĐANG CHỜ DUYỆT
                     </span>
                  )}
                  {a.is_broken && (
                     <span className="bg-blue-50 text-blue-600 border border-blue-200 px-1.5 py-0.5 rounded text-[10px] font-bold">
                        ĐÃ LƯU TRỮ TẠI HỆ THỐNG
                     </span>
                  )}
                </div>
                {a.is_broken && a.full_text ? (
                  <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800 leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap">
                    <div className="font-bold text-[10px] text-slate-400 uppercase mb-2">Nội dung đã lưu trữ</div>
                    {a.full_text}
                  </div>
                ) : a.summary ? (
                  <div className={`mt-2 text-xs text-gray-700 ${a.is_broken ? '' : 'line-clamp-2'}`}>
                    {a.summary}
                  </div>
                ) : null}
                {a.image_url && !isJunkImage(a.image_url) ? (
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
