import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, MessageSquare, History, BarChart3, Settings, Moon, Sun } from 'lucide-react';
import { useState } from 'react';

export default function AppLayout() {
  const [dark, setDark] = useState(false);
  const toggleDark = () => {
    setDark(!dark);
    document.documentElement.classList.toggle('dark');
  };

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center gap-0.5 text-[10px] font-medium transition-colors px-2 py-1 min-w-[56px] min-h-[48px] justify-center ${
      isActive ? 'text-[#0D9488]' : 'text-gray-400 dark:text-gray-500'
    }`;

  return (
    <div className={`min-h-screen bg-[#F8FAFC] ${dark ? 'dark bg-gray-950' : ''}`}>
      {/* Top Bar */}
      <header className="sticky top-0 z-20 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🦉</span>
            <h1 className="font-bold text-lg text-gray-900 dark:text-white">Ozzy for Business</h1>
          </div>
          <button onClick={toggleDark} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            {dark ? <Sun size={20} className="text-yellow-400" /> : <Moon size={20} className="text-gray-500" />}
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 pb-24">
        <Outlet />
      </main>

      {/* Bottom Nav — Figma 5-tab: Home, Chat, History, Reports, Settings */}
      <nav className="fixed bottom-0 left-0 right-0 z-20 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
        <div className="max-w-6xl mx-auto flex justify-around py-1">
          <NavLink to="/dashboard" className={linkClass}>
            <LayoutDashboard size={20} /><span>Home</span>
          </NavLink>
          <NavLink to="/chat" className={linkClass}>
            <MessageSquare size={20} /><span>Chat</span>
          </NavLink>
          <NavLink to="/transactions" className={linkClass}>
            <History size={20} /><span>History</span>
          </NavLink>
          <NavLink to="/reports" className={linkClass}>
            <BarChart3 size={20} /><span>Reports</span>
          </NavLink>
          <NavLink to="/settings" className={linkClass}>
            <Settings size={20} /><span>Settings</span>
          </NavLink>
        </div>
      </nav>
    </div>
  );
}