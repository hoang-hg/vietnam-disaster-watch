export default function StatCard({ title, value, sub }) {
  return (
    <div className="rounded-2xl border border-gray-300 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium text-gray-600">{title}</div>
      <div className="mt-2 text-2xl font-bold text-gray-900">{value}</div>
      {sub ? <div className="mt-1 text-xs text-gray-600">{sub}</div> : null}
    </div>
  )
}
