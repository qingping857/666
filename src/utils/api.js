// src/utils/api.js
import axios from 'axios';

// Set base URL for API requests
axios.defaults.baseURL = 'http://localhost:8888'; // Update this to match your backend URL

// Add request interceptor to include auth token
axios.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle auth errors
axios.interceptors.response.use(
  response => response,
  error => {
    // Handle 401 errors (token expired or invalid)
    if (error.response && error.response.status === 401) {
      // Clear auth data
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      localStorage.removeItem('role');
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('username');
      sessionStorage.removeItem('role');
      
      // Redirect to login page
      window.location.href = '/';
    }
    
    return Promise.reject(error);
  }
);

export default axios;