// smart-spend-frontend/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './providers/ThemeProvider.tsx';
import App from './App.tsx';
import './index.css';

// Initialize the Query Client for state management
const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* 1. Set up routing */}
    <BrowserRouter>
      {/* 2. Set up theme switching */}
      <ThemeProvider>
        {/* 3. Set up data fetching/caching */}
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);