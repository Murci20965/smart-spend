// smart-spend-frontend/src/layouts/DashboardLayout.tsx
import React from 'react';
import { Outlet } from 'react-router-dom';
import ThemeSwitcher from '../components/ThemeSwitcher';

const DashboardLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-bg-light dark:bg-bg-dark text-text-light dark:text-text-dark">
      {/* Placeholder Sidebar */}
      <aside className="w-64 p-4 border-r border-gray-200 dark:border-gray-800 flex flex-col justify-between">
        <nav className="space-y-2">
          <h1 className="text-xl font-bold text-accent-primary">Smart Spend</h1>
          {/* Nav Links will go here */}
        </nav>
        {/* Theme Switcher placed at the bottom of the sidebar/layout */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
            <ThemeSwitcher />
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet /> 
      </main>
    </div>
  );
};

export default DashboardLayout;