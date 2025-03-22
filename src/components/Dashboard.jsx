import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';

const Dashboard = () => {
  // 状态管理
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchInputValue, setSearchInputValue] = useState('');
  const [username, setUsername] = useState('');
  const [exportLoading, setExportLoading] = useState(false);

  // 获取数据和用户信息
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // 从存储中获取用户信息
        const storedUsername = localStorage.getItem('username') || sessionStorage.getItem('username');
        if (storedUsername) {
          setUsername(storedUsername);
        }
        
        // 获取机会数据 - 使用API获取数据库中的数据
        const opportunitiesResponse = await axios.get('/api/sam-opportunities');
        if (opportunitiesResponse.data.success) {
          setOpportunities(opportunitiesResponse.data.opportunities);
        }
        
        setLoading(false);
      } catch (err) {
        setError('获取数据失败: ' + err.message);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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
      console.error('导出失败:', err);
      alert('导出失败，请稍后再试');
      setExportLoading(false);
    }
  };

  // 根据搜索词过滤机会
  const filteredOpportunities = opportunities.filter(opportunity => {
    if (!searchTerm) return true;
    return (
      (opportunity.title && opportunity.title.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (opportunity.description && opportunity.description.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  });

  // 处理搜索提交
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSearchTerm(searchInputValue);
  };

  // 加载状态
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>正在加载数据...</p>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className="error-container">
        <p className="error-message">错误: {error}</p>
        <button 
          className="button button-primary"
          onClick={() => window.location.reload()}
        >
          重试
        </button>
      </div>
    );
  }

  return (
    <div className="solicitation-system">
      <header className="header">
        <div className="logo-container">
          <img src="/techfocus-logo.png" alt="TechFocus" className="logo" />
          <span className="brand-name">TechFocus</span>
        </div>
        <nav className="nav-menu">
          <ul>
            <li><a href="#" className="nav-link">News</a></li>
            <li><a href="#" className="nav-link">Business</a></li>
            <li><a href="#" className="nav-link">Contact</a></li>
            <li><a href="#" className="nav-link">Career</a></li>
            <li><a href="#" className="nav-link admin-link">admin 登出</a></li>
            <li><a href="#" className="nav-button">SUBSCRIBE</a></li>
          </ul>
        </nav>
      </header>

      <main className="main-content">
        {/* 数据表格区域 */}
        <div className="data-table-section">
          {/* 导出按钮 */}
          <div className="export-button-container">
            <button 
              className="export-button" 
              onClick={exportToExcel}
              disabled={exportLoading}
            >
              {exportLoading ? '导出中...' : '导出Excel'}
            </button>
          </div>
          
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>编号</th>
                  <th>方案名称</th>
                  <th>价格</th>
                  <th>刊登天数</th>
                  <th>刊登人数</th>
                  <th>刊登周期</th>
                </tr>
              </thead>
              <tbody>
                {filteredOpportunities.map((item, index) => (
                  <tr key={item.id || index}>
                    <td>{index + 1}</td>
                    <td>{item.title || item.solicitation}</td>
                    <td>{item.price || 'N/A'}</td>
                    <td>{item.duration || 'N/A'}</td>
                    <td>{item.count || 'N/A'}</td>
                    <td>{item.cycle || 'N/A'}</td>
                  </tr>
                ))}
                {/* 如果没有记录则显示示例数据 */}
                {filteredOpportunities.length === 0 && (
                  <>
                    <tr>
                      <td>1</td>
                      <td>Sources Sought - Digital Incentives</td>
                      <td>N/A</td>
                      <td>N/A</td>
                      <td>N/A</td>
                      <td>N/A</td>
                    </tr>
                    <tr>
                      <td>2</td>
                      <td>Final Innovative Solutions Opening (ISO) ARPA-H Rare Disease AI/ML for Precision Integrated Diagnostics (RAPID)</td>
                      <td>N/A</td>
                      <td>N/A</td>
                      <td>N/A</td>
                      <td>N/A</td>
                    </tr>
                  </>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* 搜索区域 */}
        <div className="search-container">
          <form onSubmit={handleSearchSubmit} className="search-form">
            <input
              type="text"
              placeholder="keywords"
              value={searchInputValue}
              onChange={(e) => setSearchInputValue(e.target.value)}
              className="search-input"
            />
            <button type="submit" className="search-button">
              <span>🔍</span>
            </button>
          </form>
        </div>

        {/* 系统信息区域 */}
        <div className="system-intro">
          <h1 className="intro-title">Introducing Solicitation information collection system</h1>
          <p className="intro-description">
            The Solicitation Information Collection System is a fast, efficient, developed by TechFocus. It is designed to
            simplify the U.S. government bid space process, thus, lightening the cognitive load on employees.
          </p>
        </div>

        <div className="how-to-use">
          <h2 className="section-title">How to Use</h2>
          <p>
            Enter target business keywords (e.g., IT Software).
            Separate multiple keywords with commas. Click the
            button or press the Enter key to start.
          </p>
        </div>

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
      </main>

      <footer className="footer">
        <p className="footer-text">Are TechFocus legit? <span className="footer-circle">6</span></p>
      </footer>
    </div>
  );
};

export default Dashboard;