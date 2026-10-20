import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Activity, ChevronRight, CircleHelp, History, Menu, MessageSquare, Radio, ScanLine, Settings2, Shield, ShieldAlert, X } from 'lucide-react';

export type AppPage = 'overview' | 'scan' | 'live' | 'results' | 'history' | 'assistant' | 'profile';

interface ApplicationShellProps {
  page: AppPage;
  onNavigate: (page: AppPage) => void;
  hasActiveScan: boolean;
  profileName: string;
  engineOnline: boolean | null;
  ollamaOnline: boolean | null;
  onRefresh: () => Promise<void>;
  children: ReactNode;
}

const pageTitles: Record<AppPage, string> = {
  overview: 'Overview', scan: 'New assessment', live: 'Live scan', results: 'Results & findings',
  history: 'Scan history', assistant: 'Aegis assistant', profile: 'Profile & preferences',
};

/** Present existing views without owning scan state or changing their lifecycle. */
export default function ApplicationShell({ page, onNavigate, hasActiveScan, profileName, engineOnline, ollamaOnline, onRefresh, children }: ApplicationShellProps) {
  const drawer = useRef<HTMLDialogElement>(null);
  const main = useRef<HTMLElement>(null);
  const previousPage = useRef(page);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const engineLabel = engineOnline === null ? 'Checking engine' : engineOnline ? 'Engine online' : 'Engine offline';
  const engineClass = engineOnline === null ? '' : engineOnline ? 'online' : 'offline';
  const initial = profileName.slice(0, 1).toUpperCase();
  const items = [
    { id: 'overview' as const, icon: Activity },
    { id: 'scan' as const, icon: ScanLine },
    ...(hasActiveScan ? [{ id: 'live' as const, icon: Activity }] : []),
    { id: 'results' as const, icon: ShieldAlert },
    { id: 'history' as const, icon: History },
    { id: 'assistant' as const, icon: MessageSquare },
    { id: 'profile' as const, icon: Settings2 },
  ];

  useEffect(() => {
    if (previousPage.current !== page) {
      drawer.current?.close();
      main.current?.focus({ preventScroll: true });
      previousPage.current = page;
    }
  }, [page]);

  useEffect(() => {
    if (!navigationOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previousOverflow; };
  }, [navigationOpen]);

  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 1024px)');
    const closeOnDesktop = () => {
      if (desktop.matches && drawer.current?.open) {
        drawer.current.close();
        main.current?.focus({ preventScroll: true });
      }
    };
    desktop.addEventListener('change', closeOnDesktop);
    return () => desktop.removeEventListener('change', closeOnDesktop);
  }, []);

  /** Reuse identical destinations in the desktop rail and modal drawer. */
  function navigationContents(compact = false) {
    return <>
      <div className="shell-brand-row">
        <div className="brand"><span className="brand-mark"><Shield size={21} aria-hidden="true" /></span><span>AEGIS<small>AI SECURITY WORKBENCH</small></span></div>
        {compact && <button className="icon-button" aria-label="Close navigation" onClick={() => drawer.current?.close()}><X size={20} aria-hidden="true" /></button>}
      </div>
      <nav className="nav-list" aria-label="Main navigation">
        <p className="nav-label">Workspace</p>
        {items.map(({ id, icon: Icon }) => <button key={id} type="button"
          className={`nav-item${page === id ? ' active' : ''}`} aria-current={page === id ? 'page' : undefined}
          onClick={() => { drawer.current?.close(); onNavigate(id); }}>
          <Icon size={18} aria-hidden="true" /><span>{id === 'profile' ? 'Settings' : pageTitles[id]}</span>
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <section className="engine-card" aria-label="Local services">
          <div className="engine-card-title"><span className={`status-dot ${engineClass}`} aria-hidden="true" /><strong>{engineLabel}</strong>
            <button className="icon-button tiny" aria-label="Refresh connection" onClick={() => void onRefresh()}><Radio size={16} aria-hidden="true" /></button></div>
          <div className="engine-row"><span>Ollama</span><span className={ollamaOnline ? 'service-connected' : ''}>{ollamaOnline === null ? 'Checking' : ollamaOnline ? 'Connected' : 'Offline'}</span></div>
          <div className="engine-row"><span>Playwright</span><span>Not checked</span></div>
        </section>
        <div className="workspace-identity"><span className="profile-avatar" aria-hidden="true">{initial}</span><span><strong>Personal workspace</strong><small>Local environment</small></span></div>
        <div className="sidebar-footer"><span>AEGIS</span><span>v0.1.0</span></div>
      </div>
    </>;
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="sidebar">{navigationContents()}</aside>
    <dialog ref={drawer} id="mobile-navigation" className="navigation-drawer" aria-label="Workspace navigation"
      onClose={() => setNavigationOpen(false)}
      onClick={event => {
        const bounds = event.currentTarget.getBoundingClientRect();
        if (event.target === event.currentTarget && (event.clientX > bounds.right || event.clientX < bounds.left || event.clientY > bounds.bottom || event.clientY < bounds.top)) drawer.current?.close();
      }}>
      <div className="drawer-content">{navigationContents(true)}</div>
    </dialog>
    <div className="main-area">
      <header className="topbar">
        <div className="header-context"><button type="button" className="icon-button navigation-toggle" aria-label="Open navigation"
          aria-controls="mobile-navigation" aria-expanded={navigationOpen}
          onClick={() => { drawer.current?.showModal(); setNavigationOpen(true); }}><Menu size={20} aria-hidden="true" /></button>
          <nav className="breadcrumbs" aria-label="Breadcrumb"><span className="breadcrumb-root">Workspace</span><ChevronRight className="breadcrumb-root" size={14} aria-hidden="true" /><strong aria-current="page">{pageTitles[page]}</strong></nav>
        </div>
        <div className="top-actions">
          <span className={`connection-chip ${engineClass}`} role="status"><span className={`status-dot ${engineClass}`} aria-hidden="true" /><span>{engineLabel}</span></span>
          <button className="icon-button" aria-label="Open setup guidance" onClick={() => onNavigate('assistant')}><CircleHelp size={20} aria-hidden="true" /></button>
          <button className="header-avatar" aria-label={`Open profile for ${profileName}`} onClick={() => onNavigate('profile')}>{initial}</button>
        </div>
      </header>
      <main id="main-content" ref={main} tabIndex={-1}>{children}</main>
    </div>
  </div>;
}
