import React, { useState, useEffect } from 'react';
import { Bell, Check, ExternalLink, Inbox, Loader2, Trash2 } from 'lucide-react';
import { getJson, patchJson, fmtTimeAgo } from '../api';
import { Link } from 'react-router-dom';

export default function NotificationDropdown({ isOpen, setIsOpen, user }) {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(false);
    const [unreadCount, setUnreadCount] = useState(0);

    const fetchNotifications = async () => {
        if (!user) return;
        setLoading(true);
        try {
            const data = await getJson("/api/user/notifications");
            setNotifications(data);
            const countRes = await getJson("/api/user/notifications/unread-count");
            setUnreadCount(countRes.count);
        } catch (err) {
            console.error("Failed to fetch notifications", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) fetchNotifications();
    }, [isOpen]);

    useEffect(() => {
        const interval = setInterval(() => {
            if (user && !isOpen) {
                getJson("/api/user/notifications/unread-count")
                    .then(res => setUnreadCount(res.count))
                    .catch(() => {});
            }
        }, 30000); // Polling every 30s for bells
        return () => clearInterval(interval);
    }, [user, isOpen]);

    const markRead = async (id) => {
        try {
            await patchJson(`/api/user/notifications/${id}/read`);
            setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
            setUnreadCount(prev => Math.max(0, prev - 1));
        } catch (err) {
            console.error(err);
        }
    };

    const markAllRead = async () => {
        try {
            await patchJson("/api/user/notifications/read-all");
            setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
            setUnreadCount(0);
        } catch (err) {
            console.error(err);
        }
    };

    if (!isOpen) return (
        <button 
            onClick={() => setIsOpen(true)}
            className="relative p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors group"
        >
            <Bell className="w-5 h-5 text-slate-600 dark:text-slate-400 group-hover:text-blue-600" />
            {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-red-600 text-white text-[9px] font-black rounded-full flex items-center justify-center border-2 border-white dark:border-slate-900">
                    {unreadCount > 9 ? "9+" : unreadCount}
                </span>
            )}
        </button>
    );

    return (
        <div className="absolute right-0 top-full mt-2 w-80 sm:w-96 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-100 dark:border-slate-800 overflow-hidden z-[100] animate-in slide-in-from-top-2 duration-200">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-800/50">
                <h4 className="font-black text-slate-900 dark:text-white uppercase tracking-tight text-xs flex items-center gap-2">
                    <Bell className="w-4 h-4 text-blue-600" /> Thông báo
                </h4>
                <div className="flex items-center gap-1">
                    <button 
                        onClick={markAllRead}
                        className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors text-slate-500 hover:text-blue-600"
                        title="Đánh dấu tất cả đã đọc"
                    >
                        <Check className="w-4 h-4" />
                    </button>
                    <button 
                        onClick={() => setIsOpen(false)}
                        className="px-2 py-1 text-[10px] font-black hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg text-slate-400"
                    >
                        ĐÓNG
                    </button>
                </div>
            </div>

            <div className="max-h-[400px] overflow-y-auto custom-scrollbar">
                {loading && notifications.length === 0 ? (
                    <div className="p-12 text-center flex flex-col items-center">
                        <Loader2 className="w-8 h-8 text-blue-600 animate-spin mb-2" />
                        <span className="text-xs font-bold text-slate-400 uppercase">Đang tải...</span>
                    </div>
                ) : notifications.length === 0 ? (
                    <div className="p-12 text-center flex flex-col items-center">
                        <Inbox className="w-12 h-12 text-slate-100 dark:text-slate-800 mb-2" />
                        <span className="text-xs font-bold text-slate-400 uppercase">Không có thông báo mới</span>
                    </div>
                ) : (
                    <div className="divide-y divide-slate-50 dark:divide-slate-800/50">
                        {notifications.map((notif) => (
                            <div 
                                key={notif.id} 
                                className={`p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors relative group ${!notif.is_read ? 'bg-blue-50/30' : ''}`}
                            >
                                {!notif.is_read && <div className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-blue-600 rounded-full animate-pulse"></div>}
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex-1">
                                        <div className={`text-xs font-black mb-0.5 ${!notif.is_read ? 'text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'}`}>
                                            {notif.title}
                                        </div>
                                        <p className="text-[11px] font-medium text-slate-500 dark:text-slate-500 leading-normal line-clamp-2">
                                            {notif.message}
                                        </p>
                                        <div className="mt-2 flex items-center justify-between">
                                            <span className="text-[9px] font-black text-slate-400 dark:text-slate-600 uppercase tracking-tighter">
                                                {fmtTimeAgo(notif.created_at)}
                                            </span>
                                            {notif.link && (
                                                <Link 
                                                    to={notif.link} 
                                                    onClick={() => {
                                                        markRead(notif.id);
                                                        setIsOpen(false);
                                                    }}
                                                    className="inline-flex items-center gap-1 text-[10px] font-black text-blue-600 hover:text-blue-700 uppercase"
                                                >
                                                    Xem chi tiết <ExternalLink className="w-2.5 h-2.5" />
                                                </Link>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            
            <div className="p-3 bg-slate-50 dark:bg-slate-800/50 text-center border-t border-slate-100 dark:border-slate-800">
                <Link to="/profile?tab=notifications" className="text-[10px] font-black text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 uppercase tracking-widest transition-colors">Xem tất cả thông báo</Link>
            </div>
        </div>
    );
}
