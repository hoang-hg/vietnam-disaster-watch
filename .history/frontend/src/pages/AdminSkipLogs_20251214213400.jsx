import React, { useEffect, useState } from "react";
import { getJson, API_BASE } from "../api";

export default function AdminSkipLogs() {
  const [items, setItems] = useState([]);
  const [pageLimit, setPageLimit] = useState(200);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
    } catch (e) {
      console.error(e);
      setError(e.message || String(e));
    } finally {
      setProcessing(null);
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-2">Admin — Skip Logs</h2>
            <div className="mt-2">
              <a className="mr-3 text-sm text-blue-600" href={it.url} target="_blank" rel="noreferrer">Open article</a>
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
        <div className="text-sm text-gray-500">
          Không có bản ghi nào. Hãy chắc backend đang chạy và crawler đã ghi
          `logs/skip_debug.jsonl`.
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
              >
                Accept
              </button>
              <button
                onClick={() => label(it, "reject")}
                className="px-2 py-1 bg-red-600 text-white text-sm"
              >
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
