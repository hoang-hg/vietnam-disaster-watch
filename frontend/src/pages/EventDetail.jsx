import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getJson,
  deleteJson,
  putJson,
  postJson,
  fmtType,
  fmtDate,
  fmtTimeAgo,
  fmtVndBillion,
} from "../api.js";
import { ArrowLeft, Trash2, Printer, FileText, Edit2, Check, X, Share2, Facebook, Send, Bell, BellOff, Download, RefreshCw, MapPin, Calendar, Zap, AlertTriangle, ChevronRight } from "lucide-react";
import { Helmet } from "react-helmet-async";
import { API_BASE } from "../api.js";
import ConfirmModal from "../components/ConfirmModal.jsx";
import Toast from "../components/Toast.jsx";
import { useNavigate } from "react-router-dom";

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
  "Tuyên Quang", "Cao Bằng", "Lai Châu", "Lào Cai", "Thái Nguyên", "Điện Biên", "Lạng Sơn", "Sơn La", "Phú Thọ", "Bắc Ninh", "Quảng Ninh", "TP. Hà Nội", "TP. Hải Phòng", "Hưng Yên", "Ninh Bình", "Thanh Hóa", "Nghệ An", "Hà Tĩnh", "Quảng Trị", "TP. Huế", "TP. Đà Nẵng", "Quảng Ngãi", "Gia Lai", "Đắk Lắk", "Khánh Hòa", "Lâm Đồng", "Đồng Nai", "Tây Ninh", "TP. Hồ Chí Minh", "Đồng Tháp", "An Giang", "Vĩnh Long", "TP. Cần Thơ", "Cà Mau"
].sort();

const HAZARD_TYPES = [
  { id: "storm", label: "Bão, ATNĐ" },
  { id: "flood", label: "Lũ lụt" },
  { id: "flash_flood", label: "Lũ quét, Lũ ống" },
  { id: "landslide", label: "Sạt lở đất, đá" },
  { id: "subsidence", label: "Sụt lún đất" },
  { id: "drought", label: "Hạn hán" },
  { id: "salinity", label: "Xâm nhập mặn" },
  { id: "extreme_weather", label: "Mưa lớn, Lốc, Sét, Mưa Đá" },
  { id: "heatwave", label: "Nắng nóng" },
  { id: "cold_surge", label: "Rét hại, Sương muối" },
  { id: "earthquake", label: "Động đất" },
  { id: "tsunami", label: "Sóng thần" },
  { id: "storm_surge", label: "Nước dâng" },
  { id: "wildfire", label: "Cháy rừng" },
  { id: "warning_forecast", label: "Cảnh báo, dự báo" },
  { id: "recovery", label: "Khắc phục hậu quả" }
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
  const navigate = useNavigate();

  // Modal states
  const [deleteModal, setDeleteModal] = useState({ open: false, type: null, id: null });
  
  // Toast state
  const [toast, setToast] = useState({ isVisible: false, message: '', type: 'success' });

  const handleDeleteArticle = (e, articleId) => {
    e.preventDefault();
    setDeleteModal({ open: true, type: 'article', id: articleId });
  };

  const confirmDeleteArticle = async () => {
    const articleId = deleteModal.id;
    try {
        await deleteJson(`/api/articles/${articleId}`);
        setEv(prev => ({
            ...prev,
            articles: prev.articles.filter(a => a.id !== articleId),
            sources_count: Math.max(0, prev.sources_count - 1)
        }));
        setToast({ isVisible: true, message: 'Đã xóa bài báo thành công!', type: 'success' });
    } catch (err) {
        if (err.message.includes("404")) {
            setEv(prev => ({
                ...prev,
                articles: prev.articles.filter(a => a.id !== articleId)
            }));
            setToast({ isVisible: true, message: 'Bài báo đã được gỡ trước đó.', type: 'info' });
        } else {
            setToast({ isVisible: true, message: "Xóa thất bại: " + err.message, type: 'error' });
        }
    }
  };

  const handleApproveArticle = async (e, articleId) => {
    e.preventDefault();
    try {
        await postJson(`/api/admin/approve-article/${articleId}`);
        // Update local state to reflect approved status
        setEv(prev => ({
            ...prev,
            articles: prev.articles.map(a => a.id === articleId ? {...a, status: 'approved'} : a)
        }));
        setToast({ isVisible: true, message: 'Đã duyệt bài báo thành công!', type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Duyệt bài thất bại: " + err.message, type: 'error' });
    }
  };

  const handleApproveEvent = async () => {
    try {
        await postJson(`/api/admin/events/${ev.id}/approve`);
        setEv(prev => ({
            ...prev,
            needs_verification: 0,
            articles: prev.articles.map(a => ({...a, status: 'approved'}))
        }));
        setToast({ isVisible: true, message: 'Đã duyệt toàn bộ sự kiện thành công!', type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Duyệt sự kiện thất bại: " + err.message, type: 'error' });
    }
  };

  const [isReclassifying, setIsReclassifying] = useState(null);

  const handleStartEdit = () => {
    setEditForm({ ...ev });
    setIsEditing(true);
  };

  const submitReclassification = async (correctedType) => {
    if (!isReclassifying) return;
    try {
        await postJson("/api/admin/ai-feedback", {
            article_id: isReclassifying.id,
            corrected_type: correctedType,
            comment: "Manual reclassification from Event Detail"
        });
        // Update local article list
        setEv(prev => ({
            ...prev,
            articles: prev.articles.map(a => a.id === isReclassifying.id ? {...a, disaster_type: correctedType} : a)
        }));
        setToast({ isVisible: true, message: 'Đã cập nhật phân loại thành công!', type: 'success' });
        setIsReclassifying(null);
    } catch (err) {
        setToast({ isVisible: true, message: "Phân loại lại thất bại: " + err.message, type: 'error' });
    }
  };

  const handleDeleteEvent = () => {
    setDeleteModal({ open: true, type: 'event', id: ev.id });
  };

  const confirmDeleteEvent = async () => {
    try {
        await deleteJson(`/api/events/${ev.id}`);
        // Redirect with success parameter
        window.location.href = "/events?deleted=true";
    } catch (err) {
        if (err.message.includes("404") || err.status === 404) {
            window.location.href = "/events?deleted=true";
        } else {
            setToast({ isVisible: true, message: "Xóa sự kiện thất bại: " + err.message, type: 'error' });
        }
    }
  };

  const handleExportExcel = () => {
    const token = localStorage.getItem("access_token");
    window.open(`${API_BASE}/api/admin/export/event/${ev.id}?format=excel&token_query=${token}`, '_blank');
  };

  const [isFollowing, setIsFollowing] = useState(false);

  useEffect(() => {
    if (user && ev?.id) {
      getJson(`/api/user/events/${ev.id}/is-following`)
        .then(data => setIsFollowing(data.is_following))
        .catch(console.error);
    }
  }, [user, ev?.id]);

  const toggleFollow = async () => {
    if (!user) {
      alert("Vui lòng đăng nhập để theo dõi sự kiện.");
      return;
    }
    try {
      const res = await postJson(`/api/user/events/${ev.id}/follow`);
      setIsFollowing(res.status === "followed");
    } catch (err) {
      alert("Lỗi: " + err.message);
    }
  };

  const handleSaveEdit = async () => {
    try {
        const updated = await putJson(`/api/events/${ev.id}`, editForm);
        setEv({ ...ev, ...updated });
        setIsEditing(false);
        setToast({ isVisible: true, message: 'Cập nhật sự kiện thành công!', type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Lỗi cập nhật: " + err.message, type: 'error' });
    }
  };

  useEffect(() => {
    if (!id || id === 'undefined' || id === '[object Object]') {
       setError("Mã sự kiện không hợp lệ.");
       return;
    }
    
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
      <Helmet>
        <title>{`${fmtType(ev.disaster_type)} tại ${ev.province || "Việt Nam"} | BÁO TỔNG HỢP RỦI RO THIÊN TAI`}</title>
        <meta name="description" content={ev.summary?.substring(0, 160) || "Cập nhật diễn biến thiên tai mới nhất."} />
        
        {/* OpenGraph / Facebook */}
        <meta property="og:type" content="article" />
        <meta property="og:title" content={`${fmtType(ev.disaster_type)} tại ${ev.province || "Việt Nam"}`} />
        <meta property="og:description" content={ev.summary?.substring(0, 200) || "Cập nhật diễn biến thiên tai."} />
        {ev.articles?.[0]?.image_url && !isJunkImage(ev.articles[0].image_url) && (
             <meta property="og:image" content={ev.articles[0].image_url} />
        )}
        <meta property="og:url" content={window.location.href} />

        {/* Twitter */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={`${fmtType(ev.disaster_type)} tại ${ev.province || "Việt Nam"}`} />
        <meta name="twitter:description" content={ev.summary?.substring(0, 200) || "Cập nhật diễn biến thiên tai."} />
      </Helmet>
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
              <>
                <button 
                  onClick={handleExportExcel}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md"
                >
                  <Download className="w-4 h-4" />
                  <span>Xuất Excel</span>
                </button>
                <button 
                  onClick={() => window.print()}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md group"
                >
                  <FileText className="w-4 h-4" />
                  <span>Xuất PDF</span>
                </button>
                <button 
                  onClick={handleStartEdit}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md group"
                >
                  <Edit2 className="w-4 h-4" />
                  <span>Chỉnh sửa</span>
                </button>
                <button 
                  onClick={handleDeleteEvent}
                  className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-red-50 text-red-600 border border-red-200 rounded-lg text-sm font-semibold transition-all shadow-md group"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Xóa sự kiện</span>
                </button>
                {(ev.needs_verification === 1 || ev.articles.some(a => a.status === 'pending')) && (
                  <button 
                    onClick={handleApproveEvent}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md animate-pulse hover:animate-none"
                    title="Duyệt nhanh toàn bộ sự kiện và bài báo"
                  >
                    <Check className="w-4 h-4" />
                    <span>Duyệt nhanh</span>
                  </button>
                )}
              </>
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
          </div>
        )}
      </div>

      {/* Professional Report Header */}
      <div className="mb-6 flex items-center justify-between border-b-4 border-red-600 pb-4">
        <div className="flex items-center gap-4">
          <div className="bg-red-600 text-white px-4 py-2 rounded-lg font-black text-[10px] tracking-tighter text-center leading-tight w-24">
            BÁO TỔNG HỢP RỦI RO THIÊN TAI
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

      <div className="flex flex-col lg:flex-row items-start justify-between gap-6 mb-8 pb-6 border-b border-slate-100">
        <div className="flex-1 space-y-4">
          <div className="text-3xl font-black leading-tight text-slate-900 tracking-tight">
            {isEditing ? (
              <input 
                value={editForm.title}
                onChange={e => setEditForm({...editForm, title: e.target.value})}
                className="w-full border-b-2 border-blue-500 focus:outline-none bg-blue-50/50 px-1"
              />
            ) : ev.title}
          </div>

          <div className="text-sm font-medium text-slate-500 flex flex-wrap gap-x-4 gap-y-2 items-center">
            <div className="flex items-center gap-1.5 bg-slate-100 px-2 py-1 rounded-md text-slate-700">
               <MapPin className="w-3.5 h-3.5 text-slate-400" />
               {isEditing ? (
                <>
                  <select 
                    value={editForm.province}
                    onChange={e => setEditForm({...editForm, province: e.target.value})}
                    className="bg-transparent focus:outline-none cursor-pointer text-xs font-bold"
                  >
                    {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                  <input 
                    placeholder="Địa chỉ cụ thể..."
                    value={editForm.location_description || ""} 
                    onChange={e => setEditForm({...editForm, location_description: e.target.value})}
                    className="w-32 border-b border-slate-300 focus:border-blue-500 focus:outline-none bg-transparent text-xs px-1"
                  />
                </>
              ) : <span>{ev.province || "Cả nước"} {ev.location_description ? `- ${ev.location_description}` : ''}</span>}
            </div>
            <span className="flex items-center gap-1.5">
               <Calendar className="w-3.5 h-3.5 text-slate-400" />
               Bắt đầu: {fmtDate(ev.started_at)}
            </span>
            <span className="text-slate-300">|</span>
            <span className="flex items-center gap-1.5 italic text-xs">
              Cập nhật {fmtTimeAgo(ev.last_updated_at)} ({fmtDate(ev.last_updated_at)})
            </span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row lg:flex-col items-end gap-4 min-w-fit">
          {/* Status Badges */}
          <div className="flex flex-col items-end gap-2">
            {isEditing ? (
              <select 
                value={editForm.disaster_type}
                onChange={e => setEditForm({...editForm, disaster_type: e.target.value})}
                className="border rounded px-2 py-1 bg-white text-sm font-bold shadow-sm"
              >
                {HAZARD_TYPES.map(h => <option key={h.id} value={h.id}>{h.label}</option>)}
              </select>
            ) : (
              <span className={`px-3 py-1 font-black uppercase text-[10px] tracking-widest rounded-lg border shadow-sm flex items-center gap-1.5 ${
                ev.disaster_type === 'storm' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                ev.disaster_type === 'flood' ? 'bg-cyan-50 text-cyan-700 border-cyan-200' :
                ev.disaster_type === 'landslide' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                ev.disaster_type === 'wildfire' ? 'bg-red-50 text-red-700 border-red-200' :
                'bg-slate-50 text-slate-700 border-slate-200'
              }`}>
                {fmtType(ev.disaster_type)}
              </span>
            )}
            
            {isEditing ? (
                <label className="flex items-center gap-2 text-[10px] font-black text-red-600 uppercase">
                  <input 
                    type="checkbox" 
                    checked={editForm.needs_verification === 1}
                    onChange={e => setEditForm({...editForm, needs_verification: e.target.checked ? 1 : 0})}
                  />
                  Cần kiểm chứng
                </label>
            ) : ev.needs_verification === 1 && (
              <span className="bg-red-50 text-red-700 border border-red-200 text-[9px] font-bold px-2 py-0.5 rounded-lg flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Dữ liệu cần kiểm chứng
              </span>
            )}
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">
              Tổng hợp từ {ev.sources_count} báo
            </div>
          </div>

          {/* Quick Share Buttons */}
          <div className="no-print flex items-center gap-2 bg-slate-50 p-1.5 rounded-2xl border border-slate-100 shadow-sm">
            <button
               onClick={toggleFollow}
               className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-black transition-all shadow-sm hover:shadow-md ${
                 isFollowing 
                   ? "bg-slate-800 text-yellow-400" 
                   : "bg-white text-slate-700 hover:bg-slate-50"
               }`}
            >
               {isFollowing ? <BellOff className="w-3.5 h-3.5" /> : <Bell className="w-3.5 h-3.5 text-blue-600" />}
               <span>{isFollowing ? "ĐANG THEO DÕI" : "THEO DÕI"}</span>
            </button>
            <div className="w-px h-6 bg-slate-200 mx-1"></div>
            <a 
              href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(window.location.href)}`}
              target="_blank" rel="noopener noreferrer"
              className="p-2 bg-white text-[#1877F2] rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all group/fb flex items-center gap-2 px-4 py-2"
              title="Chia sẻ Facebook"
            >
                <Facebook className="w-4 h-4 group-hover/fb:scale-110 transition-transform" />
                <span className="text-[10px] font-black uppercase">Chia sẻ Facebook</span>
            </a>
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
                
                {combined.length > limit ? (
                  <button
                    className="mt-3 text-sm text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1 group/more"
                    onClick={() => setExpandedSummary((s) => !s)}
                  >
                    <span>{expandedSummary ? "RÚT GỌN" : "XEM TOÀN BỘ NỘI DUNG TỔNG HỢP"}</span>
                    <ChevronRight className={`w-3 h-3 transition-transform ${expandedSummary ? '-rotate-90' : 'rotate-90'}`} />
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
                   {isAdmin && a.status === 'pending' && (
                       <div className="flex gap-1 no-print">
                          <button
                              onClick={(e) => handleApproveArticle(e, a.id)}
                              className="p-2 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-md transition-colors"
                              title="Duyệt bài báo (Admin)"
                          >
                              <Check className="w-3.5 h-3.5" />
                          </button>
                       </div>
                   )}
                </div>
                <div className="mt-1 text-xs text-gray-500 flex flex-wrap gap-2 items-center">
                     <span className="text-blue-600 hover:underline font-semibold bg-gray-50 px-2 py-1 rounded border border-gray-100 uppercase">
                     {a.source.replace(/(\.com\.vn|\.vn|\.com|https?:\/\/|www\.)/g, '').toUpperCase()}
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
                   {a.needs_verification === 1 ? (
                     <span className="bg-red-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">
                        SỐ LIỆU CẦN XÁC MINH
                     </span>
                  ) : null}
                  {a.status === 'pending' ? (
                     <span className="bg-yellow-500 text-white px-1.5 py-0.5 rounded text-[10px] font-bold shadow-sm">
                        ĐANG CHỜ DUYỆT
                     </span>
                  ) : null}
                  {a.is_broken ? (
                     <span className="bg-blue-50 text-blue-600 border border-blue-200 px-1.5 py-0.5 rounded text-[10px] font-bold">
                        ĐÃ LƯU TRỮ TẠI HỆ THỐNG
                     </span>
                  ) : null}
                </div>
                {a.full_text ? (
                   <div className="mt-3">
                     <details className="group/fulltext border border-slate-100 rounded-lg overflow-hidden">
                       <summary className="bg-slate-50 px-3 py-2 text-[10px] font-bold text-blue-600 cursor-pointer uppercase hover:text-blue-800 transition-colors list-none flex items-center justify-between">
                          <span className="flex items-center gap-1.5">
                            <ChevronRight className="w-3 h-3 group-open/fulltext:rotate-90 transition-transform" />
                            {a.is_broken ? 'Nội dung đã lưu trữ tại hệ thống' : 'Xem nội dung chi tiết bài báo'}
                          </span>
                          <span className="text-slate-400 font-medium lowercase italic">{Math.round(a.full_text.length / 5)} chữ</span>
                       </summary>
                       <div className="p-4 bg-white text-xs text-slate-800 leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap font-serif">
                          {a.full_text}
                       </div>
                     </details>
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

      {/* Reclassification Modal */}
      {isReclassifying && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[110] p-4 no-print">
            <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                    <h3 className="text-xl font-black text-slate-800 uppercase tracking-tighter">Phân loại lại AI</h3>
                    <button onClick={() => setIsReclassifying(null)} className="p-2 text-slate-400 hover:text-slate-600">
                        <X className="w-6 h-6" />
                    </button>
                </div>
                <div className="p-6">
                    <p className="text-xs font-bold text-slate-400 uppercase mb-4 tracking-widest">Chọn loại thiên tai chính xác:</p>
                    <div className="grid grid-cols-2 gap-2">
                        {HAZARD_TYPES.map(type => (
                            <button
                                key={type.id}
                                onClick={() => submitReclassification(type.id)}
                                className={`px-4 py-3 rounded-xl border-2 transition-all font-bold text-sm text-left ${
                                    isReclassifying.currentType === type.id 
                                    ? "bg-slate-800 text-white border-slate-800 shadow-lg" 
                                    : "border-slate-100 text-slate-600 hover:border-blue-300 hover:bg-blue-50"
                                }`}
                            >
                                {type.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="p-4 bg-slate-50 text-center">
                    <p className="text-[10px] font-bold text-slate-400 uppercase">Hệ thống sẽ ghi nhận Feedback để tự huấn luyện</p>
                </div>
            </div>
        </div>
      )}

      {/* Modern Confirm Modal */}
      <ConfirmModal 
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, type: null, id: null })}
        onConfirm={deleteModal.type === 'event' ? confirmDeleteEvent : confirmDeleteArticle}
        title={deleteModal.type === 'event' ? "Xóa sự kiện" : "Xóa bài báo"}
        message={deleteModal.type === 'event' 
            ? "Bạn có chắc chắn muốn xóa TOÀN BỘ sự kiện này? Các bài báo liên quan sẽ bị loại khỏi hệ thống và không thể khôi phục."
            : "Bạn có chắc chắn muốn xóa bài báo này? Bài báo sẽ bị gỡ khỏi sự kiện và chuyển vào danh sách đen."
        }
        confirmLabel="Xác nhận xóa"
        variant="danger"
      />

      <Toast 
        isVisible={toast.isVisible}
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ ...toast, isVisible: false })}
      />
    </div>
  );
}
