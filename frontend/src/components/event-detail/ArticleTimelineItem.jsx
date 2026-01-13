import { Check, Trash2, ChevronRight, Tag } from "lucide-react";
import { fmtTimeAgo, fmtType, isJunkImage, toUtcDate } from "../../api.js";

const ArticleTimelineItem = ({ 
  article, 
  handleApprove, 
  handleDelete,
  onReclassify,
  isApproving, 
  isAdmin 
}) => {
  const { 
    id, title, url, is_broken, status, source, published_at, 
    disaster_type, province, agency, needs_verification, 
    full_text, summary, image_url 
  } = article;
  
  return (
    <div className="relative border-l-2 border-slate-200 pb-8 pl-6 article-item group/item">
      <div className="absolute -left-2.5 top-1 h-5 w-5 rounded-full bg-blue-500 shadow-md border-4 border-white" />
      
      <div className="flex items-start justify-between gap-3">
        <a
          className={`font-bold text-[15px] transition-all flex-1 leading-snug ${
            is_broken 
              ? 'text-slate-400 cursor-not-allowed no-underline' 
              : 'underline decoration-slate-200 hover:decoration-blue-400 text-blue-600 hover:text-blue-700'
          }`}
          href={is_broken ? '#' : url}
          onClick={(e) => is_broken && e.preventDefault()}
          target={is_broken ? '_self' : '_blank'}
          rel="noreferrer"
        >
          {title}
          {is_broken && (
            <span className="ml-2 text-[9px] font-black bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded border border-slate-200 uppercase tracking-tighter align-middle">
              Gỡ/Lưu trữ
            </span>
          )}
        </a>
        
        {isAdmin && (
          <div className="flex gap-1 no-print opacity-0 group-hover/item:opacity-100 transition-opacity">
            {status === 'pending' && (
              <button
                disabled={isApproving === id}
                onClick={(e) => handleApprove(e, id)}
                className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-md transition-colors disabled:opacity-50"
                title="Duyệt bài báo"
              >
                <Check className="w-4 h-4" />
              </button>
            )}
            <button
               onClick={(e) => handleDelete(e, id)}
               className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
               title="Xóa bài báo"
            >
               <Trash2 className="w-4 h-4" />
            </button>
            <button
               onClick={(e) => { e.preventDefault(); e.stopPropagation(); onReclassify(article); }}
               className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
               title="Phân loại lại (AI Feedback)"
            >
               <Tag className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
      
      <div className="mt-2 text-[11px] text-slate-500 flex flex-wrap gap-x-2 gap-y-1 items-center">
        <span className="text-blue-700 font-bold bg-blue-50/50 px-2 py-0.5 rounded border border-blue-100 uppercase tracking-tight">
          {source.replace(/(\.com\.vn|\.vn|\.com|https?:\/\/|www\.)/g, '').toUpperCase()}
        </span>
        <span className="flex items-center gap-1 font-mono text-[10px] text-slate-500">
          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
          {toUtcDate(published_at).toLocaleTimeString('vi-VN', {hour: '2-digit', minute:'2-digit'})} {toUtcDate(published_at).toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit', year: 'numeric'})}
        </span>
        
        <span className="flex items-center gap-1">
          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
          {fmtType(disaster_type)}
        </span>

        {province && province !== "unknown" && (
           <span className="flex items-center gap-1">
             <span className="w-1 h-1 rounded-full bg-slate-300"></span>
             {province}
           </span>
        )}

        {agency && (
           <span className="flex items-center gap-1">
             <span className="w-1 h-1 rounded-full bg-slate-300"></span>
             <span className="font-semibold text-slate-700">{agency}</span>
           </span>
        )}

        {needs_verification === 1 && (
           <span className="bg-red-600 text-white px-1.5 py-0.5 rounded-[4px] text-[9px] font-black uppercase tracking-tighter">
              Cần xác minh
           </span>
        )}

        {status === 'pending' && (
           <span className="bg-amber-500 text-white px-1.5 py-0.5 rounded-[4px] text-[9px] font-black uppercase tracking-tighter">
              Chờ duyệt
           </span>
        )}
      </div>

      {full_text ? (
        <div className="mt-4">
          <details className="group/fulltext border border-slate-100 rounded-xl overflow-hidden shadow-sm bg-slate-50/30">
            <summary className="px-3 py-2 text-[10px] font-black text-blue-600 cursor-pointer uppercase hover:bg-slate-50 transition-colors list-none flex items-center justify-between">
               <span className="flex items-center gap-2">
                 <ChevronRight className="w-3.5 h-3.5 group-open/fulltext:rotate-90 transition-transform" />
                 {is_broken ? 'Bản lưu trữ hệ thống' : 'Xem chi tiết bài báo'}
               </span>
               <span className="text-slate-400 font-bold lowercase italic">{Math.round(full_text.length / 5)} chữ</span>
            </summary>
            <div className="p-4 bg-white text-sm text-slate-800 leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap font-serif border-t border-slate-50">
               {full_text}
            </div>
          </details>
        </div>
      ) : summary ? (
        <div className={`mt-3 text-sm text-slate-600 leading-relaxed ${is_broken ? '' : 'line-clamp-3'}`}>
          {summary}
        </div>
      ) : null}

      {image_url && !isJunkImage(image_url) && (
        <div className="mt-4">
          <img 
            src={image_url} 
            alt={title} 
            className="rounded-xl h-56 w-full object-cover border border-slate-200 shadow-sm hover:opacity-95 transition-opacity"
            onError={(e) => {e.target.style.display = 'none'}}
          />
        </div>
      )}
    </div>
  );
};

export default ArticleTimelineItem;
