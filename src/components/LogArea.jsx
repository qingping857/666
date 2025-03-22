// src/components/LogArea.jsx
import React, { useRef, useEffect } from 'react';

function LogArea({ logs }) {
  const logRef = useRef(null);

  // 当logs更新时，自动滚动到底部
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div 
      ref={logRef}
      className="h-48 bg-gray-100 p-3 mb-4 overflow-y-auto border rounded font-mono text-sm"
    >
      {logs.map((log, index) => (
        <div key={index} className="mb-1">{log}</div>
      ))}
    </div>
  );
}

export default LogArea;