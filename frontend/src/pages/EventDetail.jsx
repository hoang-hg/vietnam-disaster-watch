import { useEffect, useState, useMemo, useCallback } from "react";
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
  isJunkImage,
  getDisasterMeta,
  API_BASE
} from "../api.js";
import { DISASTER_METADATA } from "../theme.js";
import { ArrowLeft, Trash2, Printer, FileText, Edit2, Check, X, Share2, Facebook, Send, Bell, BellOff, Download, RefreshCw, MapPin, Calendar, Zap, AlertTriangle, ChevronRight, Loader2 } from "lucide-react";
import { Helmet } from "react-helmet-async";
import Badge from "../components/Badge.jsx";
import ConfirmModal from "../components/ConfirmModal.jsx";
import Toast from "../components/Toast.jsx";
import { VALID_PROVINCES } from "../provinces.js";
import { useNavigate } from "react-router-dom";
import ImpactBreakdown from "../components/event-detail/ImpactBreakdown.jsx";
import FieldInfoTable from "../components/event-detail/FieldInfoTable.jsx";
import ArticleTimelineItem from "../components/event-detail/ArticleTimelineItem.jsx";

const HAZARD_TYPES = Object.entries(DISASTER_METADATA).map(([id, meta]) => ({
  id,
  label: meta.label,
  tone: meta.tone
}));

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
          // Session errors are expected when logged out
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
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  
  // Toast state
  const [toast, setToast] = useState({ isVisible: false, message: '', type: 'success' });

  const handleDeleteArticle = (e, articleId) => {
    e.preventDefault();
    setDeleteModal({ open: true, type: 'article', id: articleId });
  };

  const confirmDeleteArticle = async () => {
    const articleId = deleteModal.id;
    setIsDeleting(true);
    try {
        await deleteJson(`/api/articles/${articleId}`);
        setEv(prev => ({
            ...prev,
            articles: prev.articles.filter(a => a.id !== articleId),
            sources_count: Math.max(0, (prev.sources_count || 0) - 1),
            articles_count: Math.max(0, (prev.articles_count || 0) - 1)
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
    } finally {
        setIsDeleting(false);
        setDeleteModal({ open: false, type: null, id: null });
    }
  };

  const handleApproveArticle = async (e, articleId) => {
    e.preventDefault();
    setIsApproving(articleId);
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
    } finally {
        setIsApproving(null);
    }
  };

  const handleApproveEvent = async () => {
    setIsApproving('all');
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
    } finally {
        setIsApproving(null);
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
    setIsDeleting(true);
    try {
        await deleteJson(`/api/events/${ev.id}`);
        // Redirect with success parameter
        navigate("/events?deleted=true");
    } catch (err) {
        if (err.message.includes("404") || err.status === 404) {
            navigate("/events?deleted=true");
        } else {
            setToast({ isVisible: true, message: "Xóa sự kiện thất bại: " + err.message, type: 'error' });
        }
    } finally {
        setIsDeleting(false);
        setDeleteModal({ open: false, type: null, id: null });
    }
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    const token = localStorage.getItem("access_token");
    try {
        const response = await fetch(`${API_BASE}/api/admin/export/event/${ev.id}?format=excel`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `su_kien_${ev.id}.xlsx`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setToast({ isVisible: true, message: 'Đã xuất dữ liệu thành công!', type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Lỗi tải xuống: " + err.message, type: 'error' });
    } finally {
        setIsExporting(false);
    }
  };

  const [isFollowing, setIsFollowing] = useState(false);

  useEffect(() => {
    if (!user || !ev?.id) return;
    
    const controller = new AbortController();
    
    getJson(`/api/user/events/${ev.id}/is-following`, { signal: controller.signal })
      .then(data => {
        if (!controller.signal.aborted) {
          setIsFollowing(data.is_following);
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          showToast(`Không thể tải dữ liệu: ${err.message}`, "error");
        }
      });
    
    return () => controller.abort();
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
    setIsSaving(true);
    try {
        const updated = await putJson(`/api/events/${ev.id}`, editForm);
        setEv({ ...ev, ...updated });
        setIsEditing(false);
        setToast({ isVisible: true, message: 'Cập nhật sự kiện thành công!', type: 'success' });
    } catch (err) {
        setToast({ isVisible: true, message: "Lỗi cập nhật: " + err.message, type: 'error' });
    } finally {
        setIsSaving(false);
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

  const sortedArticles = useMemo(() => {
    return [...(ev?.articles || [])].sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
  }, [ev?.articles]);

  const { combinedSummary, heroImage } = useMemo(() => {
    if (!ev?.articles?.length) return { combinedSummary: "", heroImage: null };
    
    const combined = ev.articles
      .map((a) => a.summary || "")
      .filter(Boolean)
      .slice(0, 3)
      .join("<br/><br/>");
    
    const hero = ev.articles.find(a => a.image_url && !isJunkImage(a.image_url))?.image_url;
    
    return { combinedSummary: combined, heroImage: hero };
  }, [ev?.articles]);

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
                  disabled={isExporting}
                  onClick={handleExportExcel}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md disabled:opacity-50"
                >
                  {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  <span>{isExporting ? "Đang xuất..." : "Xuất Excel"}</span>
                </button>
                <button 
                  onClick={() => window.print()}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md group no-print"
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
                  <span>Xóa</span>
                </button>
                {(ev.needs_verification === 1 || ev.articles.some(a => a.status === 'pending')) && (
                  <button 
                    disabled={isApproving === 'all'}
                    onClick={handleApproveEvent}
                    className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md animate-pulse hover:animate-none disabled:opacity-50"
                    title="Duyệt nhanh toàn bộ sự kiện và bài báo"
                  >
                    {isApproving === 'all' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    <span>{isApproving === 'all' ? "Đang duyệt..." : "Duyệt nhanh"}</span>
                  </button>
                )}
              </>
            ) : (
                <>
                <button 
                  disabled={isSaving}
                  onClick={handleSaveEdit}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold transition-all shadow-md group disabled:opacity-50"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  <span>{isSaving ? "Đang lưu..." : "Lưu"}</span>
                </button>
                <button 
                  disabled={isSaving}
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
                    {VALID_PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
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
                {Object.entries(DISASTER_METADATA).map(([id, meta]) => <option key={id} value={id}>{meta.label}</option>)}
              </select>
            ) : (
              <Badge tone={getDisasterMeta(ev.disaster_type).tone} className="px-3 py-1 font-black uppercase text-[10px] tracking-widest shadow-sm">
                {fmtType(ev.disaster_type)}
              </Badge>
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
                <input type="number" value={editForm.deaths || 0} onChange={e => setEditForm({...editForm, deaths: parseInt(e.target.value) || 0})} className="w-16 border rounded px-2 py-1 text-sm font-bold text-red-700" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Mất tích</span>
                <input type="number" value={editForm.missing || 0} onChange={e => setEditForm({...editForm, missing: parseInt(e.target.value) || 0})} className="w-16 border rounded px-2 py-1 text-sm font-bold text-orange-700" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Bị thương</span>
                <input type="number" value={editForm.injured || 0} onChange={e => setEditForm({...editForm, injured: parseInt(e.target.value) || 0})} className="w-16 border rounded px-2 py-1 text-sm font-bold text-yellow-700" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] uppercase font-bold text-slate-400">Thiệt hại (Tỷ)</span>
                <input type="number" step="0.1" value={editForm.damage_billion_vnd || 0} onChange={e => setEditForm({...editForm, damage_billion_vnd: parseFloat(e.target.value) || 0})} className="w-24 border rounded px-2 py-1 text-sm font-bold text-blue-700" />
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
      <FieldInfoTable 
        isEditing={isEditing} 
        ev={ev} 
        editForm={editForm} 
        setEditForm={setEditForm} 
      />

      {/* Detailed Impact Breakdown (homes, agriculture, etc.) */}
      <ImpactBreakdown details={ev.details} />

      {combinedSummary || heroImage ? (
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
                  dangerouslySetInnerHTML={{ __html: !expandedSummary && combinedSummary.length > 800 ? combinedSummary.slice(0, 800) + "..." : combinedSummary }}
                />
                
                {combinedSummary.length > 800 ? (
                  <button
                    className="mt-3 text-sm text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1 group/more"
                    onClick={() => setExpandedSummary((s) => !s)}
                  >
                    <span>{expandedSummary ? "RÚT GỌN" : "XEM TOÀN BỘ NỘI DUNG TỔNG HỢP"}</span>
                    <ChevronRight className={`w-3 h-3 transition-transform ${expandedSummary ? '-rotate-90' : 'rotate-90'}`} />
                  </button>
                ) : null}
              </div>
            ) : null}

      <div className="mt-6 rounded-2xl border border-gray-300 bg-white p-4">
        <div className="text-sm font-semibold text-gray-900">
          Bài báo liên quan ({ev.articles?.length || 0} báo)
        </div>
        <div className="text-xs text-gray-600 mt-1">
          Timeline cập nhật từ các nguồn. Mỗi link mở bài gốc.
        </div>
        <div className="mt-4 space-y-0">
          {sortedArticles
            .map((a) => (
              <ArticleTimelineItem 
                key={a.id} 
                article={a} 
                isAdmin={isAdmin} 
                handleApprove={handleApproveArticle}
                handleDelete={handleDeleteArticle}
                isApproving={isApproving}
              />
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
