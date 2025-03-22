// src/index.jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App';
import './utils/api'; // Import API configuration

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);