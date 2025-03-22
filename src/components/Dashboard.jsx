// src/components/Dashboard.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';
import logo from '../assets/logo.jpg';

const Dashboard = () => {
  // 原始仪表板状态
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInputValue, setSearchInputValue] = useState('');
  const [exportLoading, setExportLoading] = useState(false);
  
  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  // 爬虫相关状态 - 硬编码默认值
  const crawlerType = '8A'; // 固定爬虫类型为8A
  const pageNumber = 1;    // 固定页码为1
  const pageSize = 200;    // 固定每页数量为200
  const [crawlerRunning, setCrawlerRunning] = useState(false);
  const [crawlerStatus, setCrawlerStatus] = useState('');

  // 获取数据和用户信息
  useEffect(() => {
    fetchData();
  }, [currentPage, itemsPerPage]);

  // 获取数据函数
  const fetchData = async () => {
    try {
      setLoading(true);
      
      // 获取机会数据 - 使用API获取数据库中的数据（带分页参数）
      const opportunitiesResponse = await axios.get('/api/sam-opportunities', {
        params: {
          page: currentPage,
          per_page: itemsPerPage
        }
      });
      
      if (opportunitiesResponse.data.success) {
        setOpportunities(opportunitiesResponse.data.opportunities);
        
        // 设置分页信息
        if (opportunitiesResponse.data.pagination) {
          setTotalItems(opportunitiesResponse.data.pagination.total || 0);
          setTotalPages(opportunitiesResponse.data.pagination.pages || 1);
        }
      }
      
      setLoading(false);
    } catch (err) {
      setError('Failed to retrieve data: ' + err.message);
      setLoading(false);
    }
  };

  // 修改刷新数据函数
  const refreshData = async () => {
    try {
      setCrawlerStatus('Refresh the data...');
      
      // 获取机会数据（带分页参数）
      const opportunitiesResponse = await axios.get('/api/sam-opportunities', {
        params: {
          page: currentPage,
          per_page: itemsPerPage
        }
      });
      
      if (opportunitiesResponse.data.success) {
        setOpportunities(opportunitiesResponse.data.opportunities);
        
        // 设置分页信息
        if (opportunitiesResponse.data.pagination) {
          setTotalItems(opportunitiesResponse.data.pagination.total || 0);
          setTotalPages(opportunitiesResponse.data.pagination.pages || 1);
        }
        
        setCrawlerStatus('The data has been refreshed!');
        
        // 记录刷新时间和结果
        console.log(`The data was refreshed successfully: ${new Date().toLocaleTimeString()} - Got it ${opportunitiesResponse.data.opportunities.length} records`);
        
        return true;
      }
      
      return false;
    } catch (err) {
      console.error('Failed to flush the data:', err);
      setCrawlerStatus('The data refresh failed, please try again later');
      return false;
    }
  };

  // 处理爬虫搜索提交
  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    
    if (!searchInputValue.trim()) {
      setError('Please enter a search keyword');
      return;
    }
    
    try {
      setCrawlerRunning(true);
      setCrawlerStatus('The crawler is running, please wait...');
      setError(null);
      
      // 调用爬虫API - 使用硬编码的爬虫参数
      const response = await axios.post('/api/run-crawler', {
        type: crawlerType,  // 硬编码的爬虫类型
        pageNumber,         // 硬编码的页码
        pageSize,           // 硬编码的每页数量
        params: searchInputValue
      });
      
      if (response.data.success) {
        // 显示爬虫运行的消息
        setCrawlerStatus(`The crawler is running! Search for keywords: ${searchInputValue}. The data will be automatically refreshed...`);
        
        // 重置到第一页
        setCurrentPage(1);
        
        // 在一段时间后自动刷新数据 - 首次刷新
        setTimeout(async () => {
          try {
            await refreshData();
            setSearchTerm(searchInputValue);
          } catch (refreshError) {
            console.error('First data refresh failed:', refreshError);
          }
          
          // 再等待一段时间后进行第二次刷新，确保捕获所有数据
          setTimeout(async () => {
            try {
              await refreshData();
              setCrawlerStatus('The crawler execution is complete and the data is refreshed');
            } catch (refreshError) {
              console.error('The second refresh of the data failed:', refreshError);
              setCrawlerStatus('The crawler may still be running, please wait...');
              
              // 最后一次尝试刷新
              setTimeout(async () => {
                try {
                  await refreshData();
                  setCrawlerStatus('Data refresh complete!');
                } catch (finalError) {
                  setCrawlerStatus('The crawler has completed, but the data refresh has failed');
                } finally {
                  setCrawlerRunning(false);
                }
              }, 3000); // 再等3秒后最后刷新
            } finally {
              if (crawlerRunning) {
                setCrawlerRunning(false);
              }
            }
          }, 3000); // 3秒后再次刷新
        }, 3000); // 首次3秒后刷新
      } else {
        setError('The crawler failed: ' + response.data.message);
        setCrawlerStatus('');
        setCrawlerRunning(false);
      }
    } catch (err) {
      setError('The crawler failed: ' + err.message);
      setCrawlerStatus('');
      setCrawlerRunning(false);
    }
  };

  // 处理登出
  const handleLogout = () => {
    // 清除存储
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('username');
    sessionStorage.removeItem('role');
    
    // 重定向到登录页
    window.location.href = '/';
  };

  // 导出数据到Excel
  const exportToExcel = async () => {
    try {
      setExportLoading(true);
      
      // 调用后端导出API
      const response = await axios.get('/api/export-opportunities', {
        responseType: 'blob', // 重要: 告诉axios返回的是二进制数据
      });
      
      // 创建一个用于下载的链接
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'opportunities.xlsx');
      document.body.appendChild(link);
      link.click();
      
      // 清理创建的对象和链接
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      setExportLoading(false);
    } catch (err) {
      console.error('The export failed:', err);
      alert('The export failed, please try again later');
      setExportLoading(false);
    }
  };

  // 分页函数
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
  };

  // 每页显示条数变化
  const handleItemsPerPageChange = (e) => {
    const newItemsPerPage = parseInt(e.target.value);
    setItemsPerPage(newItemsPerPage);
    setCurrentPage(1); // 重置到第一页
  };

  // 生成分页按钮 - 优化后的分页组件
  const renderPagination = () => {
    const pageButtons = [];
    const maxPagesToShow = 5; // 最多显示的页码数
    
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);
    
    // 调整startPage，确保显示足够的页码
    if (endPage - startPage + 1 < maxPagesToShow && startPage > 1) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }
    
    // 添加首页按钮
    pageButtons.push(
      <button 
        key="first" 
        className={`pagination-button ${currentPage === 1 ? 'disabled' : ''}`}
        onClick={() => handlePageChange(1)}
        disabled={currentPage === 1}
        aria-label="First page"
      >
        <span aria-hidden="true">«</span>
      </button>
    );
    
    // 添加上一页按钮
    pageButtons.push(
      <button 
        key="prev" 
        className={`pagination-button ${currentPage === 1 ? 'disabled' : ''}`}
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="Previous page"
      >
        <span aria-hidden="true">‹</span>
      </button>
    );
    
    // 添加页码按钮
    for (let i = startPage; i <= endPage; i++) {
      pageButtons.push(
        <button 
          key={i} 
          className={`pagination-button ${currentPage === i ? 'active' : ''}`}
          onClick={() => handlePageChange(i)}
          aria-label={`Page ${i}`}
          aria-current={currentPage === i ? 'page' : undefined}
        >
          {i}
        </button>
      );
    }
    
    // 添加下一页按钮
    pageButtons.push(
      <button 
        key="next" 
        className={`pagination-button ${currentPage === totalPages ? 'disabled' : ''}`}
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        aria-label="Next page"
      >
        <span aria-hidden="true">›</span>
      </button>
    );
    
    // 添加末页按钮
    pageButtons.push(
      <button 
        key="last" 
        className={`pagination-button ${currentPage === totalPages ? 'disabled' : ''}`}
        onClick={() => handlePageChange(totalPages)}
        disabled={currentPage === totalPages}
        aria-label="Last page"
      >
        <span aria-hidden="true">»</span>
      </button>
    );
    
    return (
      <div className="pagination-container">
        <div className="pagination-buttons">
          {pageButtons}
        </div>
        <div className="pagination-info">
          <span>Total <strong>{totalItems}</strong> records, <strong>{totalPages}</strong> pages</span>
          <select 
            value={itemsPerPage} 
            onChange={handleItemsPerPageChange}
            className="items-per-page-select"
            aria-label="Items per page"
          >
            <option value="10">10 items/page</option>
            <option value="20">20 items/page</option>
            <option value="50">50 items/page</option>
            <option value="100">100 items/page</option>
          </select>
        </div>
      </div>
    );
  };

  // 根据搜索词过滤机会
  const filteredOpportunities = opportunities.filter(opportunity => {
    if (!searchTerm) return true;
    return (
      (opportunity.title && opportunity.title.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (opportunity.description && opportunity.description.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  });

  // 加载状态
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading data...</p>
      </div>
    );
  }

  // 错误状态
  if (error && !crawlerRunning) {
    return (
      <div className="error-container">
        <p className="error-message">Error: {error}</p>
        <button 
          className="button button-primary"
          onClick={() => window.location.reload()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="solicitation-system">
      <header className="header">
        <div className="logo-container">
          <img src={logo} alt="TechFocus" className="logo" />
          <span className="brand-name">TechFocus</span>
        </div>
        <nav className="nav-menu">
          <ul>
            <li><a href="/news" className="nav-link">News</a></li>
            <li><a href="/business" className="nav-link">Business</a></li>
            <li><a href="/contact" className="nav-link">Contact</a></li>
            <li><a href="/career" className="nav-link">Career</a></li>
            <li><button onClick={handleLogout} className="nav-link admin-link">logout</button></li>
            <li><a href="/government" className="nav-button">Government</a></li>
          </ul>
        </nav>
      </header>

      <div className="main-content">
        {/* 导出 */}
        <div className="button-container">
          <button 
            className="export-button" 
            onClick={exportToExcel}
            disabled={exportLoading || crawlerRunning}
          >
            {exportLoading ? 'Exporting...' : 'Export Excel'}
          </button>
        </div>
        
        {/* 爬虫状态消息 */}
        {crawlerStatus && (
          <div className={`status-message ${crawlerRunning ? 'status-running' : 'status-success'}`}>
            {crawlerStatus}
          </div>
        )}
        
        {/* 数据表格区域 */}
        <div className="data-table-section">
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Title</th>
                  <th>Publish Date</th>
                  <th>Response Date</th>
                  <th>Link</th>
                  <th>Department</th>
                </tr>
              </thead>
              <tbody>
                {filteredOpportunities.length > 0 ? (
                  filteredOpportunities.map((item, index) => (
                    <tr key={item.id || index}>
                      <td>{(currentPage - 1) * itemsPerPage + index + 1}</td>
                      <td>{item.title || item.solicitation}</td>
                      <td>{item.publish_date ? new Date(item.publish_date).toLocaleDateString() : 'N/A'}</td>
                      <td>{item.response_date ? new Date(item.response_date).toLocaleDateString() : 'N/A'}</td>
                      <td>
                        {item.link ? (
                          <a href={item.link} target="_blank" rel="noopener noreferrer" className="table-link">
                            Find out more
                          </a>
                        ) : (
                          'N/A'
                        )}
                      </td>
                      <td>{item.department || 'N/A'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" className="no-data-message">
                    No matching records were found. Please try conducting a new search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
          {/* 分页控件 */}
          {filteredOpportunities.length > 0 && renderPagination()}
        </div>

        {/* 爬虫搜索区域 - 移除输入字段，只保留搜索框 */}
        <div className="search-container">
          <form onSubmit={handleSearchSubmit} className="search-form">
            <div className="search-input-container">
              <input
                type="text"
                placeholder="Enter keywords, separated by spaces,and click the serach button"
                value={searchInputValue}
                onChange={(e) => setSearchInputValue(e.target.value)}
                className="search-input"
                disabled={crawlerRunning}
              />
              <button 
                type="submit" 
                className="search-button" 
                disabled={crawlerRunning || !searchInputValue.trim()}
              >
                {crawlerRunning ? 'Searching...' : <span>🔍</span>}
              </button>
            </div>
          </form>
        </div>

        {/* 系统介绍信息 */}
        <div className="system-intro">
          <h1 className="intro-title">Introducing Solicitation information collection system</h1>
          <p className="intro-description">
            The Solicitation Information Collection System is a fast, efficient, developed by TechFocus. It is designed to
            simplify the U.S. government bid space process, thus, lightening the cognitive load on employees.
          </p>
        </div>

        {/* 使用说明 */}
        <div className="how-to-use">
          <h2 className="section-title">How to Use</h2>
          <p>
            Enter target business keywords (e.g., IT Software).
            Separate multiple keywords with commas. Click the
            button or press the Enter key to start.
          </p>
        </div>

        {/* 系统操作规则 */}
        <div className="system-rules">
          <h2 className="section-title">System Operation Rules</h2>
          <p>
            The system retrieves information from SAM.gov, the
            U.S. government's open procurement platform.
          </p>
          
          <p>It only collects data for four types of contracts:</p>
          <ul className="contract-types">
            <li>• 8A: 8A Program Contracts</li>
            <li>• RP: Request for Proposals/Pre-Announcements (Source Sought/Presolicitation)</li>
            <li>• O: Solicitation Announcements</li>
            <li>• WOSB: Women-Owned Small Business</li>
          </ul>

          <p>Only projects that match the NAICS codes of your company will be retrieved:</p>
          <ul className="naics-codes">
            <li>• 518210: Data Processing, Hosting, and Related Services</li>
            <li>• 541511: Custom Computer Programming Services</li>
            <li>• 541512: Other Computer-Related Services</li>
            <li>• 541611: Administrative Management and General Management Consulting Services</li>
            <li>• 541612: Human Resource Consulting Services</li>
            <li>• 541690: Other Scientific and Technical Consulting Services</li>
            <li>• 541715: Research and Development in Physical, Engineering, and Life Sciences (excluding Defense)</li>
            <li>• 541990: All Other Professional, Scientific, and Technical Services</li>
            <li>• 561710: Pest Control and Extermination Services</li>
            <li>• 443142: Electronics Stores</li>
          </ul>

          <div className="exclusions">
            <h3>Exclusions</h3>
            <p>
              The system excludes all contract opportunities from
              defense-related departments, including:
            </p>
            <ul className="excluded-depts">
              <li>• DEPT OF DEFENSE</li>
              <li>• DEPARTMENT OF DEFENSE</li>
              <li>• DOD</li>
              <li>• DEFENSE</li>
              <li>• ARMY</li>
              <li>• NAVY</li>
              <li>• AIR FORCE</li>
              <li>• MARINES</li>
            </ul>
          </div>
        </div>
      </div>

      <footer className="footer">
        <p className="footer-text">Are TechFocus legit? <span className="footer-circle">6</span></p>
      </footer>
    </div>
  );
};

export default Dashboard;