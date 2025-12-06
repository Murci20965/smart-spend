// smart-spend-frontend/src/App.tsx
import { Routes, Route } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import AuthLayout from './layouts/AuthLayout';
import LoginPage from './pages/auth/LoginPage'; // Will create these soon
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import TransactionsPage from './pages/TransactionsPage';

function App() {
  // NOTE: This is where we will add Auth Guards later, 
  // but for now, we set up the basic routes.

  return (
    <Routes>
      {/* PROTECTED ROUTES (Requires Login) */}
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        {/* Add /upload and /coach routes here later */}
      </Route>

      {/* PUBLIC/AUTH ROUTES (No Login Required) */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      
      {/* Fallback 404 Page (Optional) */}
      <Route path="*" element={<>404 Not Found</>} />
    </Routes>
  );
}

export default App;