import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getJson,
  deleteJson,
  putJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
} from "../api.js";
import Badge from "../components/Badge.jsx";
import { ArrowLeft, Trash2, Printer, FileText, Edit2, Check, X } from "lucide-react";

const TYPE_TONES = {
  storm: "blue",
  flood: "cyan",
  flash_flood: "cyan",
  landslide: "orange",
  subsidence: "slate",
  drought: "orange",
  salinity: "blue",
  extreme_weather: "yellow",
  heatwave: "red",
  cold_surge: "indigo",
  earthquake: "slate",
  tsunami: "blue",
  storm_surge: "purple",
  wildfire: "red",
  warning_forecast: "yellow",
  recovery: "emerald",
  unknown: "slate",
};

const PROVINCES = [
  "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu", "Bắc Ninh", "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước", "Bình Thuận", "Cà Mau", "Cần Thơ", "Cao Bằng", "Đà Nẵng", "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang", "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "TP. Hồ Chí Minh", "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái"
].sort();

const HAZARD_TYPES = [
  { id: "storm", label: "Bão, ATNĐ" },
  { id: "flood", label: "Lũ lụt" },
  { id: "flash_flood", label: "Lũ quét, Lũ ống" },
  { id: "landslide", label: "Sạt lở đất, đá" },
  { id: "subsidence", label: "Sụt lún đất" },
  { id: "drought", label: "Hạn hán" },
  { id: "salinity", label: "Xâm nhập mặn" },
  { id: "extreme_weather", label: "Mưa lớn, Lốc, Sét, Đá" },
  { id: "heatwave", label: "Nắng nóng" },
  { id: "cold_surge", label: "Rét hại, Sương muối" },
  { id: "earthquake", label: "Động đất" },
  { id: "tsunami", label: "Sóng thần" },
  { id: "storm_surge", label: "Nước dâng" },
  { id: "wildfire", label: "Cháy rừng" },
  { id: "warning_forecast", label: "Tin cảnh báo, dự báo" },
  { id: "recovery", label: "Tin khắc phục hậu quả" }
];

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
  const [isAdmin, setIsAdmin] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const checkRole = () => {
      const storedUser = localStorage.getItem("user");
      if (storedUser) {
        try {
          const u = JSON.parse(storedUser);
          setUser(u);
          setIsAdmin(u?.role === 'admin');
        } catch (e) {
          console.error("Role check error:", e);
        }
      } else {
        setUser(null);
        setIsAdmin(false);
      }
    };
    checkRole();
    window.addEventListener("storage", checkRole);
    return () => window.removeEventListener("storage", checkRole);
  }, []);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

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

  const handleStartEdit = () => {
    setEditForm({ ...ev });
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    try {
        const updated = await putJson(`/api/events/${ev.id}`, editForm);
        setEv({ ...ev, ...updated });
        setIsEditing(false);
        alert("Cập nhật thành công!");
    } catch (err) {
        alert("Lỗi cập nhật: " + err.message);
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
    <div className="mx-auto max-w-4xl px-4 py-8 report-container">
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .report-container { max-width: 100% !important; padding: 0 !important; margin: 0 !important; }
          body { background: white !important; }
          .shadow-sm { shadow: none !important; border: 1px solid #eee !important; }
          .bg-white { background: white !important; }
          .summary-content { font-size: 14pt !important; line-height: 1.6 !important; }
          .article-item { page-break-inside: avoid; }
        }
      `}</style>
      {/* Header Actions */}
      <div className="flex justify-between items-center no-print mb-6">
        <Link to="/events" className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-blue-600 transition-colors group">
          <ArrowLeft className="w-4 h-4 mr-1 group-hover:-translate-x-1 transition-transform" />
          Quay lại danh sách sự kiện
        </Link>
        
        {isAdmin && (
          <div className="flex gap-2">
            {!isEditing ? (
              <button 
                onClick={handleStartEdit}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md group"
              >
                <Edit2 className="w-4 h-4" />
                <span>Chỉnh sửa</span>
              </button>
            ) : (
                <>
                <button 
                  onClick={handleSaveEdit}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md group"
                >
                  <Check className="w-4 h-4" />
                  <span>Lưu</span>
                </button>
                <button 
                  onClick={() => setIsEditing(false)}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-sm font-semibold transition-all shadow-md group"
                >
                  <X className="w-4 h-4" />
                  <span>Hủy</span>
                </button>
              </>
            )}
            <button 
                onClick={() => window.print()}
                className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-sm font-semibold transition-all shadow-md group"
            >
                <Printer className="w-4 h-4" />
                <span>In (PDF)</span>
            </button>
          </div>
        )}
      </div>

      {/* Professional Report Header */}
      <div className="mb-6 flex items-center justify-between border-b-4 border-red-600 pb-4">
        <div className="flex items-center gap-4">
          <div className="bg-red-600 text-white px-4 py-2 rounded-lg font-black text-xl tracking-tighter">
            VDW
          </div>
          <div>
            <h1 className="text-xl font-black text-slate-900 uppercase tracking-tight">Phiếu Tin Thiên Tai</h1>
            <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase">
              <span className="flex h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
              ID: {ev.id.toString().padStart(6, '0')} • Hệ thống giám sát rủi ro thiên tai
            </div>
          </div>
        </div>
        
        {/* Print-only QR Code Placeholder */}
        <div className="hidden print:block text-right">
           <div className="w-16 h-16 border-2 border-slate-900 ml-auto flex items-center justify-center text-[8px] font-bold text-center leading-none">
              MÃ QR<br/>TRUY XUẤT
           </div>
           <div className="text-[10px] font-bold mt-1 uppercase">viet-disaster.gov.vn</div>
        </div>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold leading-snug text-gray-900">
            {isEditing ? (
              <input 
                value={editForm.title}
                onChange={e => setEditForm({...editForm, title: e.target.value})}
                className="w-full border-b-2 border-blue-500 focus:outline-none bg-blue-50/50 px-1"
              />
            ) : ev.title}
          </div>
          <div className="mt-2 text-sm text-gray-600 flex flex-wrap gap-2 items-center">
            {isEditing ? (
              <select 
                value={editForm.province}
                onChange={e => setEditForm({...editForm, province: e.target.value})}
                className="border rounded px-1 py-0.5 bg-white"
              >
                {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            ) : <span>{ev.province}</span>}
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
            {isEditing ? (
              <select 
                value={editForm.disaster_type}
                onChange={e => setEditForm({...editForm, disaster_type: e.target.value})}
                className="border rounded px-2 py-1 bg-white text-sm font-bold"
              >
                {HAZARD_TYPES.map(h => <option key={h.id} value={h.id}>{h.label}</option>)}
              </select>
            ) : (
              <Badge tone={TYPE_TONES[ev.disaster_type] || "slate"}>
                {fmtType(ev.disaster_type)}
              </Badge>
            )}
            
            {isEditing ? (
               <label className="flex items-center gap-2 text-xs font-bold text-red-600">
                 <input 
                   type="checkbox" 
                   checked={editForm.needs_verification === 1}
                   onChange={e => setEditForm({...editForm, needs_verification: e.target.checked ? 1 : 0})}
                 />
                 Cần kiểm chứng
               </label>
            ) : ev.needs_verification === 1 && (
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
        {isEditing ? (
           <>
            <div className="flex flex-wrap gap-2 items-center bg-slate-50 p-3 rounded-xl border border-slate-200 w-full">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Tử vong</span>
                <input type="number" value={editForm.deaths || 0} onChange={e => setEditForm({...editForm, deaths: parseInt(e.target.value)})} className="w-16 border rounded px-2 py-1 text-sm font-bold text-red-700" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Mất tích</span>
                <input type="number" value={editForm.missing || 0} onChange={e => setEditForm({...editForm, missing: parseInt(e.target.value)})} className="w-16 border rounded px-2 py-1 text-sm font-bold text-orange-700" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Bị thương</span>
                <input type="number" value={editForm.injured || 0} onChange={e => setEditForm({...editForm, injured: parseInt(e.target.value)})} className="w-16 border rounded px-2 py-1 text-sm font-bold text-yellow-700" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Thiệt hại (Tỷ)</span>
                <input type="number" step="0.1" value={editForm.damage_billion_vnd || 0} onChange={e => setEditForm({...editForm, damage_billion_vnd: parseFloat(e.target.value)})} className="w-24 border rounded px-2 py-1 text-sm font-bold text-blue-700" />
              </div>
            </div>
           </>
        ) : (
          <>
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
          </>
        )}
      </div>
      
      {/* Field Information Table - Matches the professional report format */}
      {(isEditing || ev.commune || ev.village || ev.route || ev.cause || ev.characteristics) && (
        <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 flex items-center gap-2">
             <div className="w-1.5 h-4 bg-blue-600 rounded-full"></div>
             <span className="text-sm font-bold text-slate-800 uppercase tracking-tight">Thông tin thực địa (Trích xuất)</span>
          </div>
          <table className="min-w-full divide-y divide-slate-100">
             <tbody className="divide-y divide-slate-50 text-sm">
                {(isEditing || ev.commune) && (
                  <tr>
                    <td className="px-4 py-3 font-medium text-slate-500 w-1/3 bg-slate-50/50 text-xs uppercase tracking-wider">Xã/Phường</td>
                    <td className="px-4 py-3 text-slate-900 font-semibold">
                      {isEditing ? (
                        <input value={editForm.commune || ""} onChange={e => setEditForm({...editForm, commune: e.target.value})} className="w-full border rounded px-2 py-1" />
                      ) : ev.commune}
                    </td>
                  </tr>
                )}
                {(isEditing || ev.village) && (
                  <tr>
                    <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Thôn/Bản/Xóm</td>
                    <td className="px-4 py-3 text-slate-900">
                      {isEditing ? (
                        <input value={editForm.village || ""} onChange={e => setEditForm({...editForm, village: e.target.value})} className="w-full border rounded px-2 py-1" />
                      ) : ev.village}
                    </td>
                  </tr>
                )}
                {(isEditing || ev.route) && (
                  <tr>
                    <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Tuyến đường</td>
                    <td className="px-4 py-3 text-slate-900 font-mono text-xs">
                      {isEditing ? (
                        <input value={editForm.route || ""} onChange={e => setEditForm({...editForm, route: e.target.value})} className="w-full border rounded px-2 py-1" />
                      ) : ev.route}
                    </td>
                  </tr>
                )}
                {(isEditing || ev.cause) && (
                  <tr>
                    <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Nguyên nhân</td>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <input value={editForm.cause || ""} onChange={e => setEditForm({...editForm, cause: e.target.value})} className="w-full border rounded px-2 py-1" />
                      ) : (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${ev.cause.includes('Mưa') ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                          {ev.cause}
                        </span>
                      )}
                    </td>
                  </tr>
                )}
                {(isEditing || ev.characteristics) && (
                  <tr>
                    <td className="px-4 py-3 font-medium text-slate-500 bg-slate-50/50 text-xs uppercase tracking-wider">Đặc điểm / Quy mô</td>
                    <td className="px-4 py-3 text-slate-800 leading-relaxed italic">
                      {isEditing ? (
                        <textarea value={editForm.characteristics || ""} onChange={e => setEditForm({...editForm, characteristics: e.target.value})} className="w-full border rounded px-2 py-1" rows={3} />
                      ) : `"${ev.characteristics}"`}
                    </td>
                  </tr>
                )}
             </tbody>
          </table>
        </div>
      )}

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
                {/* Professional Report Header */}
                <div className="mb-6 flex items-center justify-between border-b-4 border-slate-900 pb-4">
                  <div className="flex items-center gap-4">
                    <div className="bg-slate-900 text-white px-4 py-2 rounded-lg font-black text-xl tracking-tighter">
                      VDW
                    </div>
                    <div>
                      <h1 className="text-xl font-black text-slate-900 uppercase tracking-tight">Phiếu Tin Thiên Tai</h1>
                      <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase">
                        <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                        ID: {ev.id.toString().padStart(6, '0')} • Hệ thống giám sát thời gian thực
                      </div>
                    </div>
                  </div>
                  
                  {/* Print-only QR Code Placeholder */}
                  <div className="hidden print:block text-right">
                    <div className="w-16 h-16 border-2 border-slate-900 ml-auto flex items-center justify-center text-[8px] font-bold text-center leading-none">
                        MÃ QR<br/>TRUY XUẤT
                    </div>
                    <div className="text-[10px] font-bold mt-1 uppercase">viet-disaster.gov.vn</div>
                  </div>
                </div>
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
                          className="p-2 ml-2 flex-shrink-0 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors no-print"
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
