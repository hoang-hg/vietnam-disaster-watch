import React, { useEffect, useState } from "react";
import { getJson, API_BASE } from "../api";

export default function AdminSkipLogs() {
  const [items, setItems] = useState([]);
  const [pageLimit, setPageLimit] = useState(200);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [snack, setSnack] = useState(null);

  useEffect(() => {
    fetchLogs();
  }, [pageLimit]);

  async function fetchLogs() {
    setLoading(true);
    setError(null);
    try {
      const data = await getJson(`/api/admin/skip-logs?limit=${pageLimit}`);
      setItems(Array.isArray(data) ? data.reverse() : []);
    } catch (e) {
      console.error(e);
      setError(e.message || String(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function label(item, lab) {
    setError(null);
    setProcessing(item.id);
    try {
      const res = await fetch(API_BASE + "/api/admin/label", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id: item.id, label: lab }),
      });
      if (!res.ok) throw new Error(`label request failed ${res.status}`);
      // Optimistically remove labeled item from UI
      setItems((prev) => prev.filter((it) => it.id !== item.id));
      setSnack({ message: `Đã gán nhãn: ${lab}`, item });
    } catch (e) {
      console.error(e);
      setError(e.message || String(e));
    } finally {
      setProcessing(null);
    }
  }

  useEffect(() => {
    if (!snack) return;
    const t = setTimeout(() => setSnack(null), 3000);
    return () => clearTimeout(t);
  }, [snack]);

  async function undoLabel(item) {
    setError(null);
    setProcessing(item.id);
    try {
      const res = await fetch(API_BASE + "/api/admin/label/revert", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id: item.id }),
      });
      if (!res.ok) throw new Error(`undo failed ${res.status}`);
      const data = await res.json();
      // put item back at top of list
      setItems((prev) => [item, ...prev]);
      setSnack({
        message: `Hoàn tác: ${data.reverted_label || "n/a"}`,
        item: null,
      });
    } catch (e) {
      console.error(e);
      setError(e.message || String(e));
    } finally {
      setProcessing(null);
    }
  }

  return (
    <div className="p-4 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Xác minh tin tức tiềm năng</h2>
      <p className="text-sm text-gray-600 mb-6">
        Đây là các tin tức bị NLP từ chối tự động nhưng có chứa từ khóa thiên tai. 
        Bạn có thể duyệt thủ công để đưa vào hệ thống hoặc loại bỏ.
      </p>

      <div className="mb-2">
        <label>Limit: </label>
        <input
          type="number"
          value={pageLimit}
          onChange={(e) => setPageLimit(Number(e.target.value))}
          className="border px-2"
        />
        <button
          className="ml-2 px-3 py-1 bg-blue-600 text-white"
          onClick={fetchLogs}
        >
          Refresh
        </button>
      </div>

      {loading && <div className="text-sm text-gray-600">Loading…</div>}
      {error && <div className="text-sm text-red-600">Error: {error}</div>}

      {!loading && items.length === 0 && !error && (
        <div className="text-sm text-gray-500 bg-gray-50 p-8 border rounded-lg text-center">
          Không có bản ghi nào cần xử lý. Hệ thống đang hoạt động tốt.
        </div>
      )}

      <div className="space-y-2 mt-3">
        {items.map((it, idx) => (
          <div key={idx} className="p-3 border rounded bg-white">
            <div className="text-sm text-gray-600">
              {it.timestamp} — <span className="font-medium">{it.source}</span>{" "}
              — <span className="italic">{it.action}</span>
            </div>
            <div className="font-semibold mt-1">{it.title}</div>
            <div className="text-xs text-gray-700 break-words">{it.url}</div>
            {it.diagnose && (
              <div className="text-xs text-gray-500 mt-1">
                Diag: {it.diagnose.reason} (score {it.diagnose.score})
              </div>
            )}
            <div className="mt-2">
              <a
                className="mr-3 text-sm text-blue-600"
                href={it.url}
                target="_blank"
                rel="noreferrer"
              >
                Open article
              </a>
              <button
                onClick={() => label(it, "accept")}
                className="mr-2 px-2 py-1 bg-green-600 text-white text-sm"
                disabled={processing === it.id}
              >
                {processing === it.id ? "…" : "Accept"}
              </button>
              <button
                onClick={() => label(it, "reject")}
                className="px-2 py-1 bg-red-600 text-white text-sm"
                disabled={processing === it.id}
              >
                {processing === it.id ? "…" : "Reject"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {snack && (
        <div className="fixed bottom-6 right-6 bg-gray-900 text-white px-4 py-2 rounded shadow">
          {snack}
        </div>
      )}
    </div>
  );
}
