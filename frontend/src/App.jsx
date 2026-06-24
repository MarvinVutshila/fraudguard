import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ApprovalQueue from './pages/ApprovalQueue';
import History from './pages/History';
import Predict from './pages/Predict';
import BatchAnalysis from './pages/BatchAnalysis';
import ModelInfo from './pages/ModelInfo';
import AdminPanel from './pages/AdminPanel';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import './App.css';

function PrivateRoute({ children }) {
  const token = localStorage.getItem('fg_token');
  return token ? children : <Navigate to="/login" />;
}

function MainLayout({ children }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const pathMap = {
    '/': 'Live Feed',
    '/approval': 'Approval Queue',
    '/history': 'History',
    '/predict': 'Predict',
    '/batch': 'Batch Analysis',
    '/model': 'Model Info',
    '/admin': 'Admin Panel',
  };
  const title = pathMap[location.pathname] || 'Dashboard';

  const handleRefresh = () => {
    window.dispatchEvent(new Event('refresh'));
  };

  return (
    <div className="app-layout">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <div className="main-content">
        <Navbar title={title} onRefresh={handleRefresh} />
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <PrivateRoute>
                <MainLayout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/approval" element={<ApprovalQueue />} />
                    <Route path="/history" element={<History />} />
                    <Route path="/predict" element={<Predict />} />
                    <Route path="/batch" element={<BatchAnalysis />} />
                    <Route path="/model" element={<ModelInfo />} />
                    <Route path="/admin" element={<AdminPanel />} />
                  </Routes>
                </MainLayout>
              </PrivateRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
