import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ozzyLogo from '../assets/ozzy-icon-logo.png';

function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span className={`material-symbols-outlined ${className}`}>{name}</span>;
}

export default function AppLayout() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const nav = [
    { to: '/chat', icon: 'chat', label: 'Chat' },
    { to: '/transactions', icon: 'history', label: 'Activities' },
    { to: '/reports', icon: 'analytics', label: 'Reports' },
    { to: '/settings', icon: 'settings', label: 'Settings' },
  ];

  const sideLink = ({ isActive }: { isActive: boolean }) =>
    `w-full flex items-center gap-3 px-4 py-3 rounded-lg font-bold ease-out-expo duration-200 ${
      isActive ? 'bg-primary-container text-white' : 'text-on-surface-variant hover:bg-surface-container-high transition-colors font-normal'
    }`;

  const mobLink = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center justify-center rounded-xl p-2 w-16 h-16 transition-transform ${
      isActive ? 'bg-primary-container text-white' : 'text-on-surface-variant'
    }`;

  const handleSignOut = () => { logout(); navigate('/login'); };

  return (
    <div className="bg-surface font-body-md text-on-surface min-h-screen">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col h-screen w-64 fixed left-0 top-0 bg-surface border-r border-outline-variant z-50">
        <div className="p-md flex flex-col gap-xs">
          <div className="flex items-center gap-sm">
            <img src={ozzyLogo} alt="Ozzy" className="w-10 h-10 rounded-lg object-cover" />
            <div>
              <h1 className="font-headline-md text-headline-md font-bold text-primary">Ozzy</h1>
              <p className="font-label-md text-label-md text-outline">Business Suite</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-sm py-md space-y-sm">
          {nav.map(n => (
            <NavLink key={n.to} to={n.to} className={sideLink}>
              <Icon name={n.icon} />
              <span className="font-label-md text-label-md">{n.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-md mt-auto space-y-md">
          <button onClick={() => navigate('/chat')} className="w-full py-4 bg-primary text-on-primary font-bold rounded-xl flex items-center justify-center gap-2 active:scale-95 transition-transform duration-200 ease-out-expo">
            <Icon name="add_circle" /> New Request
          </button>
          <div className="border-t border-outline-variant pt-md">
            <button className="w-full flex items-center gap-3 px-4 py-2 text-on-surface-variant hover:text-primary transition-colors">
              <Icon name="help" />
              <span className="font-label-md text-label-md">Help Center</span>
            </button>
            <button onClick={handleSignOut} className="w-full flex items-center gap-3 px-4 py-2 text-on-surface-variant hover:text-error transition-colors">
              <Icon name="logout" />
              <span className="font-label-md text-label-md">Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Top App Bar */}
      <header className="flex md:hidden justify-between items-center w-full px-margin-mobile py-sm bg-surface-bright border-b border-outline-variant sticky top-0 z-40 shadow-sm">
        <h1 className="font-headline-md text-headline-md font-bold text-primary">Ozzy</h1>
        <div className="flex items-center gap-md">
          <Icon name="notifications" className="text-primary" />
          <Icon name="account_circle" className="text-primary" />
        </div>
      </header>

      {/* Page content */}
      <main className="md:ml-64 relative">
        <Outlet />
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-around items-center px-4 py-2 bg-surface border-t border-outline-variant shadow-lg z-50 rounded-t-xl">
        {nav.map(n => (
          <NavLink key={n.to} to={n.to} className={mobLink}>
            <Icon name={n.icon} />
            <span className="font-label-md text-label-md">{n.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
