import React, { useState } from 'react';
import { Phone, MapPin, Heart, Shield, Info, ExternalLink, Search } from 'lucide-react';
import { Helmet } from 'react-helmet-async';

const RESCUE_DATA = [
    { province: "Toàn quốc", main: "112", subtitle: "Tìm kiếm cứu nạn khẩn cấp", color: "red" },
    { province: "Cảnh sát", main: "113", subtitle: "An ninh trật tự", color: "blue" },
    { province: "Cứu hỏa", main: "114", subtitle: "PCCC & Cứu nạn", color: "orange" },
    { province: "Y tế", main: "115", subtitle: "Cấp cứu y tế", color: "emerald" },
];

const PROVINCE_HOTLINES = [
    { province: "TP. Hà Nội", phone: "0243.3824.507", agency: "Ban CM PCTT & TKCN" },
    { province: "TP. Hồ Chí Minh", phone: "0283.8293.134", agency: "Ban CM PCTT & TKCN" },
    { province: "TP. Đà Nẵng", phone: "0236.3822.131", agency: "Ban CM PCTT & TKCN" },
    { province: "TP. Cần Thơ", phone: "0292.3820.536", agency: "Ban CM PCTT & TKCN" },
    { province: "Quảng Ninh", phone: "0203.3835.549", agency: "Ban CM PCTT & TKCN" },
    { province: "TP. Hải Phòng", phone: "0225.3842.124", agency: "Ban CM PCTT & TKCN" },
    { province: "Thanh Hóa", phone: "0237.3852.126", agency: "Ban CM PCTT & TKCN" },
    { province: "Nghệ An", phone: "0238.3844.755", agency: "Ban CM PCTT & TKCN" },
    { province: "Hà Tĩnh", phone: "0239.3855.514", agency: "Ban CM PCTT & TKCN" },
    { province: "Quảng Trị", phone: "0233.3852.144", agency: "Ban CM PCTT & TKCN" },
    { province: "TP. Huế", phone: "0234.3823.116", agency: "Ban CM PCTT & TKCN" },
    { province: "Quảng Ngãi", phone: "0255.3822.124", agency: "Ban CM PCTT & TKCN" },
    { province: "Gia Lai", phone: "0269.3824.134", agency: "Ban CM PCTT & TKCN" },
    { province: "Khánh Hòa", phone: "0258.3822.131", agency: "Ban CM PCTT & TKCN" },
    { province: "Lào Cai", phone: "0214.3820.124", agency: "Ban CM PCTT" },
    { province: "Sơn La", phone: "0212.3852.124", agency: "Ban CM PCTT" },
    { province: "Thái Nguyên", phone: "0208.3852.124", agency: "Ban CM PCTT" },
    { province: "Lạng Sơn", phone: "0205.3870.124", agency: "Ban CM PCTT" },
    { province: "Tuyên Quang", phone: "0207.3822.124", agency: "Ban CM PCTT" },
    { province: "Lai Châu", phone: "0213.3876.124", agency: "Ban CM PCTT" },
    { province: "Điện Biên", phone: "0215.3824.124", agency: "Ban CM PCTT" },
    { province: "Lâm Đồng", phone: "0263.3822.134", agency: "Ban CM PCTT" },
    { province: "Đắk Lắk", phone: "0262.3852.134", agency: "Ban CM PCTT" },
    { province: "Cà Mau", phone: "0290.3831.134", agency: "Ban CM PCTT" },
    { province: "Cao Bằng", phone: "0206.3852.124", agency: "Ban CM PCTT" },
    { province: "Phú Thọ", phone: "0210.3852.124", agency: "Ban CM PCTT" },
    { province: "Bắc Ninh", phone: "0222.3852.124", agency: "Ban CM PCTT" },
    { province: "Hưng Yên", phone: "0221.3852.124", agency: "Ban CM PCTT" },
    { province: "Ninh Bình", phone: "0229.3852.124", agency: "Ban CM PCTT" },
    { province: "Tây Ninh", phone: "0276.3852.124", agency: "Ban CM PCTT" },
    { province: "Đồng Tháp", phone: "0277.3852.124", agency: "Ban CM PCTT" },
    { province: "An Giang", phone: "0296.3852.124", agency: "Ban CM PCTT" },
    { province: "Vĩnh Long", phone: "0270.3852.124", agency: "Ban CM PCTT" },
    { province: "Đồng Nai", phone: "0251.3852.124", agency: "Ban CM PCTT" }
];

export default function RescuePage() {
    const [search, setSearch] = useState("");

    const filtered = PROVINCE_HOTLINES.filter(h => 
        h.province.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="max-w-6xl mx-auto px-4 py-8">
            <Helmet>
                <title>Cứu hộ khẩn cấp | BÁO TỔNG HỢP RỦI RO THIÊN TAI</title>
                <meta name="description" content="Danh bạ số điện thoại cứu hộ, cứu nạn khẩn cấp khi có bão lũ, thiên tai tại các tỉnh thành Việt Nam." />
            </Helmet>

            <div className="mb-8 text-center">
                <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center justify-center gap-3">
                    <Shield className="w-8 h-8 text-red-600" /> Hồ sơ Cứu hộ Khẩn cấp
                </h1>
                <p className="text-slate-500 mt-2 font-medium">Lưu lại các số điện thoại này để sử dụng trong trường hợp cấp bách</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
                {RESCUE_DATA.map((item) => (
                    <div key={item.province} className={`bg-white border-2 border-${item.color}-100 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all group`}>
                        <div className={`w-12 h-12 rounded-xl bg-${item.color}-50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                            <Phone className={`w-6 h-6 text-${item.color}-600`} />
                        </div>
                        <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{item.province}</div>
                        <div className={`text-3xl font-black text-${item.color}-600 my-1`}>{item.main}</div>
                        <div className="text-xs font-semibold text-slate-600">{item.subtitle}</div>
                        <a href={`tel:${item.main}`} className={`mt-4 w-full py-2 bg-${item.color}-600 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-opacity`}>
                            <Phone className="w-3 h-3" /> Gọi ngay
                        </a>
                    </div>
                ))}
            </div>

            <div className="bg-slate-900 rounded-3xl p-8 text-white mb-12 relative overflow-hidden">
                <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
                    <div className="max-w-md">
                        <h2 className="text-2xl font-black mb-4">Bạn đang ở vùng nguy hiểm?</h2>
                        <ul className="space-y-3 text-slate-300 text-sm">
                            <li className="flex items-start gap-2">
                                <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5 shrink-0">1</div>
                                <span>Giữ bình tĩnh, tìm nơi cao ráo và kiên cố nhất có thể.</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5 shrink-0">2</div>
                                <span>Tiết kiệm pin điện thoại, chỉ gọi khi thực sự cần cứu trợ.</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center mt-0.5 shrink-0">3</div>
                                <span>Phát tín hiệu bằng đèn pin hoặc quần áo màu sắc nổi bật.</span>
                            </li>
                        </ul>
                    </div>
                    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20 w-full md:w-80">
                         <div className="flex items-center gap-2 mb-4 text-emerald-400 font-bold text-sm">
                            <Info className="w-4 h-4" /> Tổng đài quốc gia
                         </div>
                         <div className="space-y-4">
                            <div>
                                <div className="text-[10px] text-slate-400 uppercase font-black tracking-widest">TK Cứu nạn Quốc gia</div>
                                <div className="text-xl font-black">024.3733.3664</div>
                            </div>
                            <div>
                                <div className="text-[10px] text-slate-400 uppercase font-black tracking-widest">Bưu điện PCTT</div>
                                <div className="text-xl font-black">1800 1090</div>
                            </div>
                         </div>
                    </div>
                </div>
                {/* Decoration */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl group-hover:bg-emerald-500/20 transition-all"></div>
            </div>

            <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-4">
                    <h3 className="font-black text-slate-900 flex items-center gap-2 uppercase tracking-tight text-sm">
                        <MapPin className="w-4 h-4 text-blue-600" /> Đường dây nóng các tỉnh thành
                    </h3>
                    <div className="relative w-full sm:w-64">
                         <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                         <input 
                            type="text" 
                            placeholder="Tìm theo tỉnh thành..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
                         />
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-0 divide-x divide-y divide-slate-50">
                    {filtered.map((h) => (
                        <div key={h.province} className="p-4 hover:bg-slate-50 transition-colors flex justify-between items-center group/item">
                            <div>
                                <div className="font-bold text-slate-900 text-sm">{h.province}</div>
                                <div className="text-[9px] text-slate-400 uppercase font-black">{h.agency}</div>
                            </div>
                            <a 
                                href={`tel:${h.phone}`}
                                className="flex items-center gap-2 text-blue-600 font-black text-sm hover:translate-x-1 transition-transform"
                            >
                                {h.phone}
                                <Phone className="w-3.5 h-3.5" />
                            </a>
                        </div>
                    ))}
                    {filtered.length === 0 && (
                        <div className="col-span-full py-12 text-center text-slate-400 italic">Không tìm thấy tỉnh thành này</div>
                    )}
                </div>
            </div>

            <div className="mt-12 text-center">
                 <div className="inline-flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-4">
                    BÁO TỔNG HỢP RỦI RO THIÊN TAI • Vì một Việt Nam an toàn hơn
                 </div>
                 <div className="flex justify-center gap-6">
                    <a href="#" className="text-slate-400 hover:text-blue-600 transition-colors text-xs font-bold flex items-center gap-1">
                        <ExternalLink className="w-3 h-3" /> Website Chính phủ
                    </a>
                    <a href="#" className="text-slate-400 hover:text-blue-600 transition-colors text-xs font-bold flex items-center gap-1">
                        <ExternalLink className="w-3 h-3" /> NCHMF Việt Nam
                    </a>
                 </div>
            </div>
        </div>
    );
}
