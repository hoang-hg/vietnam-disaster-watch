const RISK_LEVEL_CONFIG = {
  1: { color: "rgb(175, 225, 255)", textColor: "rgb(23, 37, 84)", label: "Rủi ro nhỏ" },       // Light Blue -> Dark Blue Text
  2: { color: "rgb(250, 245, 140)", textColor: "rgb(113, 63, 18)", label: "Rủi ro trung bình" }, // Light Yellow -> Brown Text
  3: { color: "rgb(255, 155, 0)",   textColor: "rgb(0, 0, 0)",     label: "Rủi ro lớn" },        // Orange -> Black Text (Contrast)
  4: { color: "rgb(255, 10, 0)",    textColor: "rgb(255, 255, 255)", label: "Rủi ro rất lớn" },  // Red -> White Text
  5: { color: "rgb(160, 40, 160)",  textColor: "rgb(255, 255, 255)", label: "Rủi ro đặc biệt lớn" }, // Purple -> White Text
};

export default function RiskBadge({ level }) {
  if (!level) return null;
  const config = RISK_LEVEL_CONFIG[level] || { color: "rgb(241, 245, 249)", textColor: "rgb(71, 85, 105)", label: `Cấp ${level}` };
  
  return (
    <span 
      className="inline-flex items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-bold ring-1 ring-inset ring-black/10 shadow-sm"
      style={{ backgroundColor: config.color, color: config.textColor }}
      title={config.label}
    >
      Cấp {level}
    </span>
  );
}
