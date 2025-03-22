// src/components/SamCrawler.jsx
import React, { useState } from 'react';

function SamCrawler() {
  // 状态管理
  const [pageNumber, setPageNumber] = useState(1);
  const [pageSize, setPageSize] = useState(200);
  const [params, setParams] = useState('');
  const [selectedCrawlerType, setSelectedCrawlerType] = useState('8A');
  const [logs, setLogs] = useState([
    'You can change the above parameters to fit your demand.',
    'Page number should be a positive number, start from 1.',
    'Page size should be a positive number, start from 1.',
    'Results will now be saved to MySQL database.'
  ]);
  const [dbConfigOpen, setDbConfigOpen] = useState(false);
  
  // 爬虫类型选项
  const crawlerOptions = [
    { value: '8A', label: 'crawler 8A' },
    { value: 'RP', label: 'crawler Source Sought or Presolicitation' },
    { value: 'O', label: 'crawler solicitation' },
    { value: 'WOSB', label: 'crawler WOSB or EDWOSB' }
  ];
  
  // 添加日志消息
  const addLog = (message) => {
    setLogs(prevLogs => [...prevLogs, message]);
  };
  
  // 启动爬虫
  const startCrawl = () => {
    addLog(`Starting crawler: ${selectedCrawlerType} (Page: ${pageNumber}, Size: ${pageSize}, Params: ${params})`);
  };
  
  // 打开/关闭数据库配置
  const toggleDbConfig = () => {
    setDbConfigOpen(!dbConfigOpen);
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-2xl font-bold text-center text-gray-800 mb-6">SAM Crawler</h1>
      
      {/* 页码和页面大小输入字段 */}
      <div className="flex flex-wrap mb-4 gap-4">
        <div className="flex-1">
          <label className="block text-gray-700 mb-1">Page Number</label>
          <input 
            type="number" 
            value={pageNumber}
            onChange={(e) => setPageNumber(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full p-2 border rounded"
            min="1"
          />
        </div>
        <div className="flex-1">
          <label className="block text-gray-700 mb-1">Page Size</label>
          <input 
            type="number" 
            value={pageSize}
            onChange={(e) => setPageSize(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full p-2 border rounded"
            min="1"
          />
        </div>
      </div>
      
      {/* 下拉框和参数输入框 */}
      <div className="flex gap-2 mb-4">
        <div className="w-1/3">
          <label className="block text-gray-700 mb-1">Crawler Type</label>
          <select
            value={selectedCrawlerType}
            onChange={(e) => setSelectedCrawlerType(e.target.value)}
            className="w-full p-2 border rounded bg-white"
          >
            {crawlerOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="w-2/3">
          <label className="block text-gray-700 mb-1">Parameters</label>
          <input 
            type="text" 
            value={params}
            onChange={(e) => setParams(e.target.value)}
            className="w-full p-2 border rounded"
            placeholder="Enter keywords separated by space"
          />
        </div>
      </div>
      
      {/* 日志区域 */}
      <div className="h-48 bg-gray-100 p-3 mb-4 overflow-y-auto border rounded font-mono text-sm">
        {logs.map((log, index) => (
          <div key={index} className="mb-1">{log}</div>
        ))}
      </div>
      
      {/* 启动爬虫按钮 */}
      <div className="mb-4">
        <button 
          onClick={startCrawl} 
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition w-full"
        >
          Start Crawler
        </button>
      </div>
      
      {/* 数据库配置按钮 */}
      <div className="text-center">
        <button 
          onClick={toggleDbConfig}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          Database Config
        </button>
      </div>
      
      {/* 数据库配置模态框 */}
      {dbConfigOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white p-6 rounded-lg w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Database Configuration</h2>
              <button 
                onClick={toggleDbConfig}
                className="text-gray-500 hover:text-gray-800"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-gray-700 mb-1">Host</label>
                <input type="text" defaultValue="localhost" className="w-full p-2 border rounded" />
              </div>
              <div>
                <label className="block text-gray-700 mb-1">User</label>
                <input type="text" defaultValue="root" className="w-full p-2 border rounded" />
              </div>
              <div>
                <label className="block text-gray-700 mb-1">Password</label>
                <input type="password" className="w-full p-2 border rounded" />
              </div>
              <div>
                <label className="block text-gray-700 mb-1">Database</label>
                <input type="text" defaultValue="sam_gov_data" className="w-full p-2 border rounded" />
              </div>
              <div>
                <label className="block text-gray-700 mb-1">Port</label>
                <input type="number" defaultValue="3306" className="w-full p-2 border rounded" />
              </div>
            </div>
            
            <div className="flex justify-end space-x-2">
              <button 
                onClick={toggleDbConfig}
                className="px-3 py-1 border rounded"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  addLog("Database configuration saved");
                  toggleDbConfig();
                }}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SamCrawler;