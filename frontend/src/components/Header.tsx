import { Database, Plus, Menu, Sun, Moon } from 'lucide-react';
import '../styles/Header.css';

interface HeaderProps {
  onNewQuery: () => void;
  onToggleSidebar: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

export function Header({ onNewQuery, onToggleSidebar, theme, onToggleTheme }: HeaderProps) {
  return (
    <header className="header" role="banner">
      <div className="header__brand">
        <button
          className="header__menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle session history"
        >
          <Menu size={18} />
        </button>
        <Database className="header__icon" aria-hidden="true" />
        <h1 className="header__title">
          Query<span className="header__accent">Lens</span>
        </h1>
        <span className="header__subtitle">Natural-Language Database Explorer</span>
      </div>
      <div className="header__actions">
        <button 
          className="header__btn header__theme-btn" 
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>
        <button className="header__btn" onClick={onNewQuery}>
          <Plus className="header__btn-icon" aria-hidden="true" />
          New Query
        </button>
      </div>
    </header>
  );
}
