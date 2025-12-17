import React, {useEffect, useState} from 'react'

export default function AdminSkipLogs(){
  const [items, setItems] = useState([])
  const [pageLimit, setPageLimit] = useState(200)

  useEffect(()=>{ fetchLogs() }, [pageLimit])

  async function fetchLogs(){
    try{
      const res = await fetch(`/api/admin/skip-logs?limit=${pageLimit}`)
      const data = await res.json()
      setItems(data.reverse())
    }catch(e){
      console.error(e)
    }
  }

  async function label(item, label){
    try{
      await fetch('/api/admin/label',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({id:item.id,label})})
      fetchLogs()
    }catch(e){console.error(e)}
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-2">Admin — Skip Logs</h2>
      <div className="mb-2">
        <label>Limit: </label>
        <input type="number" value={pageLimit} onChange={e=>setPageLimit(Number(e.target.value))} className="border px-2" />
        <button className="ml-2 px-3 py-1 bg-blue-600 text-white" onClick={fetchLogs}>Refresh</button>
      </div>
      <div className="space-y-2">
        {items.map((it, idx)=> (
          <div key={idx} className="p-2 border rounded">
            <div className="text-sm text-gray-600">{it.timestamp} — {it.source} — {it.action}</div>
            <div className="font-medium">{it.title}</div>
            <div className="text-xs text-gray-700">{it.url}</div>
            <div className="mt-2">
              <button onClick={()=>label(it, 'accept')} className="mr-2 px-2 py-1 bg-green-600 text-white">Accept</button>
              <button onClick={()=>label(it, 'reject')} className="px-2 py-1 bg-red-600 text-white">Reject</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
