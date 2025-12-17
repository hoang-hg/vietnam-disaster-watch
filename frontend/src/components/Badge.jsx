export default function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-gray-100 text-gray-800 border-gray-300",
    blue: "bg-blue-100 text-blue-800 border-blue-300",
    cyan: "bg-cyan-100 text-cyan-800 border-cyan-300",
    red: "bg-red-100 text-red-800 border-red-300",
    green: "bg-green-100 text-green-800 border-green-300",
    amber: "bg-amber-100 text-amber-800 border-amber-300",
    purple: "bg-purple-100 text-purple-800 border-purple-300",
    orange: "bg-orange-100 text-orange-800 border-orange-300",
  };
  return (
    <span
      className={
        "inline-flex items-center gap-1 px-2 py-1 rounded-lg border text-xs font-medium " +
        (tones[tone] || tones.slate)
      }
    >
      {children}
    </span>
  );
}
