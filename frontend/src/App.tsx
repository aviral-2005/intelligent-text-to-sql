import { useState, useEffect } from 'react';
import { useQuery } from './hooks/useQuery';
import { Header } from './components/Header';
import { SessionHistory } from './components/SessionHistory';
import { EmptyState } from './components/EmptyState';
import { QueryInput } from './components/QueryInput';
import { ResultCard } from './components/ResultCard';
import './App.css';

function App() {
  const { state, history, askQuestion, submitClarification, loadFromHistory, reset } = useQuery();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') return saved;
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const isInputDisabled = state.status === 'submitting' || state.status === 'clarification_needed';
  const showEmptyState = state.status === 'idle';

  return (
    <>
      <Header 
        onNewQuery={reset}
        onToggleSidebar={() => setSidebarOpen(prev => !prev)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      
      <div className="app-layout">
        {/* Sidebar Overlay (Mobile/Tablet) */}
        <div 
          className={`app-sidebar-overlay ${sidebarOpen ? 'app-sidebar-overlay--open' : ''}`}
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />

        {/* Left Sidebar */}
        <div className={`app-sidebar ${sidebarOpen ? 'app-sidebar--open' : ''} ${isSidebarCollapsed ? 'app-sidebar--collapsed' : ''}`}>
          <SessionHistory 
            history={history}
            currentId={state.conversationId}
            onSelect={(entry) => {
              loadFromHistory(entry);
              setSidebarOpen(false);
            }}
            isCollapsed={isSidebarCollapsed}
            onToggleCollapse={() => setIsSidebarCollapsed(prev => !prev)}
          />
        </div>

        {/* Main Workspace */}
        <main className="app-main">
          <div className="app-workspace">
            <div className="app-workspace__inner">
              {showEmptyState ? (
                <EmptyState onSuggestionClick={askQuestion} />
              ) : (
                <ResultCard 
                  state={state}
                  onSubmitClarification={submitClarification}
                  onRetryError={() => askQuestion(state.question)}
                />
              )}
            </div>
          </div>

          {/* Sticky Footer Input */}
          <div className="app-footer-input">
            <div className="app-footer-input__inner">
              <QueryInput 
                onSubmit={askQuestion}
                disabled={isInputDisabled}
                placeholder={showEmptyState ? "Ask a question about your database…" : "Ask a follow-up question…"}
              />
            </div>
          </div>
        </main>
      </div>
    </>
  );
}

export default App;
