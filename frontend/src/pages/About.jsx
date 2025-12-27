export default function About() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="text-2xl font-semibold text-gray-900">Giới thiệu</div>
      <div className="mt-3 text-gray-700 leading-relaxed">
        BÁO TỔNG HỢP RỦI RO THIÊN TAI là hệ thống tổng hợp tin thiên tai từ các nguồn báo
        chính thống, tự động phân loại và nhóm thành Sự kiện.
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-2xl border border-gray-300 bg-white p-4">
          <div className="font-semibold text-gray-900">Dữ liệu</div>
          <ul className="mt-2 text-sm text-gray-700 list-disc pl-5 space-y-1">
            <li>
              Ưu tiên RSS; fallback Google News RSS theo domain (site:... + từ
              khóa).
            </li>
            <li>Chỉ lưu metadata/tóm tắt trích xuất, kèm link về bài gốc.</li>
            <li>Nhóm sự kiện và tính điểm tin cậy dựa trên số nguồn.</li>
          </ul>
        </div>
        <div className="rounded-2xl border border-gray-300 bg-white p-4">
          <div className="font-semibold text-gray-900">Nâng cấp đề xuất</div>
          <ul className="mt-2 text-sm text-gray-700 list-disc pl-5 space-y-1">
            <li>
              NLP nâng cao (PhoBERT/VnCoreNLP) cho trích xuất chính xác hơn.
            </li>
            <li>Admin dashboard để duyệt/điều chỉnh sự kiện.</li>
            <li>
              Push notification (web push / Zalo OA) theo khu vực người dùng.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
