// Login.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Login.css';
import logo from '../assets/logo.svg';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [autoLogin, setAutoLogin] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!username || !password) {
      setError('请输入用户名和密码');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/login', {
        username,
        password
      });

      if (response.data.success) {
        // 修复Auto Login功能
        const storage = autoLogin ? localStorage : sessionStorage;
        
        // 使用统一的存储方式
        storage.setItem('token', response.data.token);
        storage.setItem('username', response.data.username);
        storage.setItem('role', response.data.role);

        // Check if password is expired
        if (response.data.password_expired) {
          navigate('/change-password');
        } else {
          navigate('/dashboard');
        }
      }
    } catch (err) {
      if (err.response && err.response.data) {
        setError(err.response.data.message || '登录失败，请检查用户名和密码');
        
        // Handle account lockout
        if (err.response.data.locked) {
          setError(`账户已被锁定，请稍后再试`);
        }
      } else {
        setError('登录失败，请稍后再试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* 顶部导航栏 - 简化设计，匹配原型图 */}
      <header className="header">
        <div className="logo-container">
          <img src={logo} alt="TechFocus Logo" className="logo" />
          <span className="logo-text">TechFocus</span>
        </div>
        <nav className="nav-links">
          <a href="/news">News</a>
          <a href="/business">Business</a>
          <a href="/contact">Contact</a>
          <a href="/career">Career</a>
          <a href="/government" className="government-btn">Government</a>
        </nav>
      </header>

      {/* 主要内容 */}
      <main className="main-content">
        <div className="content-wrapper">
          {/* 标题 */}
          <h1 className="main-title">Solicitation information collection system</h1>
          <p className="subtitle">Company work platform.Welcome to our own world.</p>

          {/* 登录表单 */}
          <div className="login-form-wrapper">
            {/* 中央Logo */}
            <div className="center-logo">
              <img src={logo} alt="TechFocus Logo" className="form-logo" />
            </div>

            {error && <div className="error-message">{error}</div>}

            <form onSubmit={handleSubmit}>
              {/* 用户名输入 */}
              <div className="input-group">
                <input
                  type="text"
                  placeholder="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="text-input"
                />
              </div>

              {/* 密码输入 */}
              <div className="input-group">
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="text-input"
                />
              </div>

              {/* 自动登录开关 */}
              <div className="auto-login-container">
                <span className="auto-login-label">Auto Login</span>
                <div 
                  className={`toggle-switch ${autoLogin ? 'active' : ''}`}
                  onClick={() => setAutoLogin(!autoLogin)}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>

              {/* 登录按钮 */}
              <button 
                type="submit" 
                className="sign-in-button"
                disabled={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          </div>

          {/* 帮助按钮 - 放在页面底部中央 */}
          <div className="help-agent-container">
            <button className="help-agent-button">
              Ask TechFoucs agent
              <span className="arrow-icon">↑</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Login;