const RISK_LEVEL_CONFIG = {
  1: { color: "bg-blue-100 text-blue-700 ring-blue-700/10", label: "Rủi ro thấp" },
  2: { color: "bg-yellow-100 text-yellow-800 ring-yellow-600/20", label: "Trung bình" },
  3: { color: "bg-orange-100 text-orange-800 ring-orange-600/20", label: "Rủi ro lớn" },
  4: { color: "bg-red-100 text-red-700 ring-red-600/10", label: "Rất lớn" },
  5: { color: "bg-purple-100 text-purple-700 ring-purple-600/10", label: "Thảm họa" },
};

export default function RiskBadge({ level }) {
  if (!level) return null;
  const config = RISK_LEVEL_CONFIG[level] || { color: "bg-gray-100 text-gray-600 ring-gray-500/10", label: `Cấp ${level}` };
  
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${config.color}`}>
      Cấp {level}
    </span>
  );
}
