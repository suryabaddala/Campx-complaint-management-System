import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import {
  Activity, ArrowDownLeft, ArrowRight, ArrowUpRight, Bell, Building2, Check,
  CheckCheck, ChevronDown, ChevronRight, CircleHelp, Clock3, CloudUpload,
  FileText, Filter, GraduationCap, LayoutDashboard, LifeBuoy, LogOut, Menu,
  MessageCircle, Plus, Search, Send, ShieldCheck, Sparkles, Users, Wrench, X, Zap,
} from "lucide-react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, messageFromError } from "./api";

const AdminVisualizations = lazy(() => import("./AdminVisualizations.jsx"));

const CATEGORIES = [
  "Electrical", "Plumbing", "Cleaning and Sanitation", "Internet and Networking",
  "Classroom Equipment", "Laboratory Equipment", "Hostel Facilities", "Security", "Other",
];
const PRIORITIES = ["Low", "Medium", "High"];
const STATUSES = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Reopened", "Closed"];
const DEPARTMENTS = [
  "Electrical Maintenance", "Plumbing", "Housekeeping", "IT Services", "Classroom Support",
  "Laboratory Support", "Hostel Administration", "Campus Security", "Student Services",
];
function PageLoader() {
  return <div className="loading-screen"><div className="loader-ring" /><span>Getting things ready…</span></div>;
}

function Brand({ light = false }) {
  return <div className={`brand ${light ? "brand-light" : ""}`}>
    <span className="brand-mark"><LifeBuoy size={20} strokeWidth={2.5} /></span>
    <span>campus<span className="brand-accent">fix</span><span className="brand-ai"> AI</span></span>
  </div>;
}

function StatusBadge({ status }) {
  const tone = status?.toLowerCase().replaceAll(" ", "-") || "submitted";
  return <span className={`status-badge tone-${tone}`}><span className="status-dot" />{status}</span>;
}

function PriorityTag({ priority }) {
  return <span className={`priority-tag priority-${(priority || "medium").toLowerCase()}`}>
    <span className="priority-dot" />{priority || "Medium"}
  </span>;
}

function EmptyState({ icon: Icon = FileText, title, text, action }) {
  return <div className="empty-state">
    <div className="empty-icon"><Icon size={22} /></div>
    <h3>{title}</h3><p>{text}</p>{action}
  </div>;
}

function Toast({ toast, onClose }) {
  if (!toast) return null;
  return <div className={`toast toast-${toast.type}`} role="status">
    {toast.type === "error" ? <CircleHelp size={18} /> : <Check size={18} />}
    <span>{toast.message}</span><button className="icon-button" onClick={onClose} aria-label="Dismiss"><X size={16} /></button>
  </div>;
}

function AuthPage({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { data } = await api.post(`/auth/${mode === "login" ? "login" : "register"}`, form);
      onLogin(data.data);
      navigate("/app");
    } catch (err) {
      setError(messageFromError(err));
    } finally {
      setBusy(false);
    }
  };

  return <main className="auth-layout">
    <section className="auth-visual">
      <div className="auth-visual-top"><Brand light /><span className="online-indicator">A better campus starts here</span></div>
      <div className="auth-story">
        <div className="eyebrow eyebrow-light"><span className="eyebrow-spark"><Sparkles size={13} /></span> YOUR CAMPUS. YOUR VOICE.</div>
        <h1>Small fixes.<br />Better <em>campus</em>.</h1>
        <p>A simpler way to report what needs attention and follow it all the way to resolution.</p>
        <div className="auth-art" aria-hidden="true">
          <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
          <div className="art-spark art-spark-one">✳</div><div className="art-spark art-spark-two">✦</div>
          <div className="art-main-icon"><LifeBuoy size={58} strokeWidth={1.25} /></div>
          <div className="art-card art-card-one"><span className="art-card-icon green"><Check size={13} /></span><span>Issue resolved</span><small>Just now</small></div>
          <div className="art-card art-card-two"><span className="art-card-icon purple"><Sparkles size={13} /></span><span>Smartly routed</span><small>To the right team</small></div>
          <div className="art-pill"><span className="status-dot" /> Making campus better</div>
        </div>
      </div>
      <div className="auth-footer"><span>Thoughtful campus care, one report at a time.</span><span>© 2026 CampusFix AI</span></div>
    </section>

    <section className="auth-form-side">
      <div className="auth-mobile-brand"><Brand /></div>
      <div className="auth-form-wrap">
        <div className="auth-heading">
          <div className="auth-icon"><GraduationCap size={25} /></div>
          <span className="section-kicker">WELCOME {mode === "login" ? "BACK" : "ABOARD"}</span>
          <h2>{mode === "login" ? "Sign in to CampusFix" : "Create your account"}</h2>
          <p>{mode === "login" ? "Your campus, a little better. Pick up where you left off." : "Join your campus community and make your voice heard."}</p>
        </div>
        <div className="auth-tabs" role="tablist">
          <button className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setError(""); }}>Sign in</button>
          <button className={mode === "register" ? "selected" : ""} onClick={() => { setMode("register"); setError(""); }}>Create account</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === "register" && <label>Your name<div className="input-shell"><Users size={16} /><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Alex Morgan" autoComplete="name" required /></div></label>}
          <label>College email<div className="input-shell"><span className="input-at">@</span><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@college.edu" autoComplete="email" required /></div></label>
          <label>Password<div className="input-shell"><ShieldCheck size={16} /><input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={mode === "register" ? "At least 10 characters" : "Enter your password"} autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={mode === "register" ? 10 : 1} required /></div></label>
          {error && <div className="form-error"><CircleHelp size={15} />{error}</div>}
          <button className="button button-primary auth-submit" disabled={busy}>{busy ? <span className="button-spinner" /> : <>{mode === "login" ? "Sign in" : "Create student account"}<ArrowRight size={16} /></>}</button>
        </form>
        <div className="auth-safe"><ShieldCheck size={15} /><span>Your account and complaint details are protected.</span></div>
      </div>
    </section>
  </main>;
}

function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const signOut = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch { /* The local session is still cleared. */ }
    localStorage.removeItem("campusfix_token");
    setUser(null);
  }, []);

  useEffect(() => {
    if (!localStorage.getItem("campusfix_token")) {
      setLoading(false);
      return;
    }
    api.get("/auth/me")
      .then(({ data }) => setUser(data.data.user))
      .catch(() => localStorage.removeItem("campusfix_token"))
      .finally(() => setLoading(false));
  }, []);

  const signIn = (result) => {
    localStorage.setItem("campusfix_token", result.token);
    setUser(result.user);
  };
  return { user, loading, signIn, signOut };
}

function useToast() {
  const [toast, setToast] = useState(null);
  const showToast = (message, type = "success") => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 4200);
  };
  return { toast, showToast, clearToast: () => setToast(null) };
}

function Shell({ user, onLogout, children, toast, clearToast }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [notificationError, setNotificationError] = useState(false);
  const role = user.role;
  const studentLinks = [
    { to: "/app", label: "Overview", icon: LayoutDashboard },
    { to: "/app/complaints", label: "My complaints", icon: FileText },
    { to: "/app/notifications", label: "Notifications", icon: Bell },
  ];
  const staffLinks = [
    { to: "/app", label: "My work", icon: Wrench },
    { to: "/app/notifications", label: "Notifications", icon: Bell },
  ];
  const adminLinks = [
    { to: "/app", label: "Overview", icon: LayoutDashboard },
    { to: "/app/complaints", label: "All complaints", icon: FileText },
    { to: "/app/notifications", label: "Notifications", icon: Bell },
  ];
  const links = role === "admin" ? adminLinks : role === "staff" ? staffLinks : studentLinks;

  useEffect(() => {
    api.get("/notifications")
      .then(({ data }) => {
        setUnread(data.data.items.filter((item) => !item.is_read).length);
        setNotificationError(false);
      })
      .catch(() => setNotificationError(true));
  }, [location.pathname]);

  return <div className="app-layout">
    <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-brand"><Brand /><button className="mobile-close icon-button" onClick={() => setMenuOpen(false)} aria-label="Close menu"><X size={18} /></button></div>
      <div className="workspace-chip"><span className="campus-avatar"><Building2 size={16} /></span><span><b>Campus portal</b><small>Student services</small></span><ChevronDown size={14} /></div>
      <div className="nav-caption">WORKSPACE</div>
      <nav className="side-nav">
        {links.map(({ to, label, icon: Icon }) => {
          const active = to === "/app" ? location.pathname === "/app" : location.pathname.startsWith(to);
          return <Link key={to} to={to} title={label === "Notifications" && notificationError ? "Notification count could not be refreshed" : undefined} onClick={() => setMenuOpen(false)} className={`nav-link ${active ? "nav-active" : ""}`}><Icon size={18} /><span>{label}</span>{label === "Notifications" && unread > 0 && <span className="nav-count">{unread}</span>}{label === "Notifications" && notificationError && <span className="nav-count nav-count-error">!</span>}</Link>;
        })}
      </nav>
      <div className="sidebar-lower">
        <div className="help-card"><div className="help-icon"><CircleHelp size={17} /></div><strong>Need a hand?</strong><p>We’re here to help your campus feel like home.</p><a href="mailto:campus-support@college.edu">Contact support <ArrowRight size={13} /></a></div>
        <div className="sidebar-rule" />
        <div className="user-profile">
          <div className="profile-avatar">{user.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</div>
          <div className="profile-copy"><strong>{user.name}</strong><span>{role === "admin" ? "Administrator" : role === "staff" ? "Maintenance staff" : "Student"}</span></div>
          <button className="icon-button logout-button" aria-label="Sign out" title="Sign out" onClick={async () => { await onLogout(); navigate("/"); }}><LogOut size={17} /></button>
        </div>
      </div>
    </aside>
    {menuOpen && <button className="mobile-scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
    <main className="main-column">
      <header className="topbar">
        <div className="topbar-start"><button className="mobile-menu icon-button" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div className="breadcrumbs"><span>CampusFix</span><ChevronRight size={13} /><strong>{location.pathname.includes("notifications") ? "Notifications" : location.pathname.includes("complaints") ? "Complaints" : role === "staff" ? "My work" : "Overview"}</strong></div></div>
        <div className="topbar-end"><span className="today-label">{new Intl.DateTimeFormat("en", { weekday: "short", month: "short", day: "numeric" }).format(new Date())}</span><button className="topbar-bell icon-button" aria-label="Notifications" onClick={() => navigate("/app/notifications")}><Bell size={18} />{unread > 0 && <span className="bell-pip" />}</button><div className="topbar-divider" /><div className="topbar-user">{user.name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase()}</div></div>
      </header>
      <div className="content-wrap">{children}</div>
      <footer className="page-footer"><span>Made with care for a better campus.</span><span>CampusFix AI <span className="footer-dot">·</span> Student-first campus care</span></footer>
    </main>
    <Toast toast={toast} onClose={clearToast} />
  </div>;
}

function StatCard({ icon: Icon, label, value, hint, tone = "blue", trend }) {
  return <article className={`stat-card stat-${tone}`}><div className="stat-top"><span className={`stat-icon stat-icon-${tone}`}><Icon size={18} /></span>{trend && <span className="stat-trend">{trend}</span>}</div><div className="stat-value">{value}</div><div className="stat-label">{label}</div>{hint && <div className="stat-hint">{hint}</div>}</article>;
}

function PageHeading({ eyebrow, title, description, action }) {
  return <div className="page-heading"><div><div className="section-kicker">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action && <div className="heading-action">{action}</div>}</div>;
}

function ComplaintRow({ item, onClick }) {
  return <button className="complaint-row" onClick={() => onClick(item)}>
    <span className="row-ticket">{item.public_id}</span>
    <span className="row-main"><strong>{item.title}</strong><small><span>{item.category}</span><span className="tiny-sep">·</span><span>{item.location || "Location not provided"}</span></small></span>
    <PriorityTag priority={item.priority} />
    <StatusBadge status={item.status} />
    <span className="row-date">{new Date(item.created_at).toLocaleDateString("en", { month: "short", day: "numeric" })}</span>
    <ArrowRight className="row-arrow" size={16} />
  </button>;
}

function SectionHeader({ title, action, onAction }) {
  return <div className="section-header"><h2>{title}</h2>{action && <button className="text-button" onClick={onAction}>{action}<ArrowRight size={14} /></button>}</div>;
}

function StudentDashboard({ user, onCreate, onOpen }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(() => api.get("/complaints/my?per_page=100").then(({ data }) => setItems(data.data.items)).catch((err) => setError(messageFromError(err))).finally(() => setBusy(false)), []);
  useEffect(() => { load(); }, [load]);
  const openCount = items.filter((item) => !["Resolved", "Closed"].includes(item.status)).length;
  const resolvedCount = items.filter((item) => ["Resolved", "Closed"].includes(item.status)).length;
  const recent = items.slice(0, 4);
  const firstName = user.name.split(/\s+/)[0];
  return <div className="dashboard-page">
    <div className="welcome-banner">
      <div className="welcome-copy"><div className="eyebrow"><span className="eyebrow-spark"><Sparkles size={13} /></span> YOUR CAMPUS, IN THE LOOP</div><h1>Hey, {firstName}<span className="wave">✳</span></h1><p>When something needs fixing, you know where to find us.</p><button className="button button-dark" onClick={onCreate}><Plus size={16} /> Report an issue <ArrowRight size={15} /></button></div>
      <div className="welcome-art" aria-hidden="true"><div className="welcome-sun" /><div className="welcome-building building-one" /><div className="welcome-building building-two" /><div className="welcome-building building-three" /><div className="welcome-plant plant-one">✦</div><div className="welcome-plant plant-two">✳</div><div className="welcome-cloud cloud-one" /><div className="welcome-cloud cloud-two" /><div className="welcome-road" /></div>
      <div className="banner-caption"><span className="caption-line" /> Better campus, together</div>
    </div>
    {error && <div className="inline-error"><CircleHelp size={16} />{error}</div>}
    <div className="stats-grid student-stats">
      <StatCard icon={FileText} label="Total reports" value={busy ? "—" : items.length} hint="Issues you’ve raised" tone="blue" />
      <StatCard icon={Clock3} label="Being worked on" value={busy ? "—" : openCount} hint="We’re on it" tone="amber" />
      <StatCard icon={CheckCheck} label="Resolved" value={busy ? "—" : resolvedCount} hint="Campus, a little better" tone="green" />
      <StatCard icon={Activity} label="Latest update" value={busy ? "—" : items[0]?.status || "All clear"} hint={items[0] ? items[0].public_id : "Nothing waiting on you"} tone="purple" />
    </div>
    <div className="dashboard-grid">
      <section className="panel recent-panel"><SectionHeader title="Recent reports" action="See all reports" onAction={() => window.dispatchEvent(new CustomEvent("campusfix:navigate", { detail: "/app/complaints" }))} />
        {busy ? <div className="skeleton-list"><div /><div /><div /></div> : recent.length ? <div className="complaint-list">{recent.map((item) => <ComplaintRow key={item.id} item={item} onClick={onOpen} />)}</div> : <EmptyState icon={FileText} title="A clear campus starts here" text="No reports yet. When something needs attention, send your first report." action={<button className="button button-secondary" onClick={onCreate}><Plus size={15} /> Report an issue</button>} />}
      </section>
      <aside className="panel impact-panel"><div className="impact-top"><div><div className="section-kicker">YOUR IMPACT</div><h2>Every report<br />helps us improve.</h2></div><span className="impact-icon"><Zap size={19} /></span></div><p>Letting the right team know is the first step toward a campus that works better for everyone.</p><div className="impact-divider" /><div className="impact-mini"><div className="mini-avatars"><span>{firstName[0]?.toUpperCase()}</span><span>✦</span><span>+</span></div><span>You’re part of the fix.</span></div></aside>
    </div>
    <div className="emergency-note"><span className="emergency-icon"><ShieldCheck size={16} /></span><span><strong>Something urgent or unsafe?</strong> CampusFix isn’t an emergency service. Contact campus security or local emergency services directly.</span></div>
  </div>;
}

function NewComplaintModal({ onClose, onSubmitted, showToast }) {
  const [form, setForm] = useState({ title: "", description: "", location: "", category: "Other" });
  const [attachment, setAttachment] = useState(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, value));
    if (attachment) data.append("attachment", attachment);
    data.append("ai_consent", consent ? "true" : "false");
    try {
      const { data: response } = await api.post("/complaints", data);
      onSubmitted(response.data.complaint);
    } catch (err) {
      setError(messageFromError(err));
      showToast(messageFromError(err), "error");
    } finally {
      setBusy(false);
    }
  };
  return <div className="modal-scrim" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card complaint-modal" role="dialog" aria-modal="true" aria-labelledby="new-complaint-title">
      <div className="modal-top"><div><div className="section-kicker">LET’S GET IT SORTED</div><h2 id="new-complaint-title">Report an issue</h2><p>Give us the details and we’ll get it to the right people.</p></div><button className="icon-button modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      <form className="modal-form" onSubmit={submit}>
        <label>What needs attention?<span className="field-hint">A short, specific title makes it easier to find.</span><input maxLength={140} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g. Projector isn’t working in Room 204" required /></label>
        <div className="form-two-columns"><label>Where is it?<span className="field-hint">Building, floor, and room</span><input maxLength={180} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="e.g. Science block, Lab 2" /></label><label>Closest match<span className="field-hint">A starting point for our team</span><select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>{CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></label></div>
        <label>Tell us a little more<span className="field-hint">What happened? When did you notice it?</span><textarea minLength={15} maxLength={5000} rows={4} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Add details that could help the team understand the issue…" required /><span className="char-count">{form.description.length}/5,000</span></label>
        <label className="upload-label"><span>Add a photo <span className="optional-label">OPTIONAL · PNG, JPG, WEBP · UP TO 5 MB</span></span><span className={`upload-box ${attachment ? "upload-selected" : ""}`}><span className="upload-icon"><CloudUpload size={18} /></span><span><strong>{attachment ? attachment.name : "Click to add a photo"}</strong><small>{attachment ? "Photo attached to your report" : "A picture can help us see what you see"}</small></span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setAttachment(e.target.files?.[0] || null)} /></span></label>
        <label className="consent-row"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /><span><strong>Get an AI-assisted summary and suggested route.</strong><small>Only your report title, description, and location are shared with Google Gemini. AI suggestions are reviewed by campus staff. Leave unchecked to keep the report on campus only.</small></span></label>
        <div className="emergency-modal-note"><ShieldCheck size={15} /><span>CampusFix is not an emergency response service. For urgent safety concerns, contact campus security directly.</span></div>
        {error && <div className="form-error"><CircleHelp size={15} />{error}</div>}
        <div className="modal-actions"><button type="button" className="button button-quiet" onClick={onClose}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? <span className="button-spinner" /> : <>Send report <ArrowRight size={15} /></>}</button></div>
      </form>
    </section>
  </div>;
}

function CreateStaffModal({ onClose, onCreated, showToast }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", department: DEPARTMENTS[0] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      await api.post("/admin/staff", form);
      showToast("Staff account created. They can sign in with their email and password.");
      onCreated();
    } catch (err) { setError(messageFromError(err)); }
    finally { setBusy(false); }
  };
  return <div className="modal-scrim" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card complaint-modal staff-modal" role="dialog" aria-modal="true" aria-labelledby="create-staff-title">
      <div className="modal-top"><div><div className="section-kicker">CAMPUS SUPPORT TEAM</div><h2 id="create-staff-title">Add a staff member</h2><p>Staff can only view work assigned to their account.</p></div><button className="icon-button modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      <form className="modal-form" onSubmit={submit}>
        <label>Name<input maxLength={100} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Jamie Lee" required /></label>
        <label>College email<input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="jamie@college.edu" required /></label>
        <label>Department<select value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>{DEPARTMENTS.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>Temporary sign-in password<span className="field-hint">At least 10 characters. Share it securely.</span><input type="password" minLength={10} maxLength={128} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></label>
        {error && <div className="form-error"><CircleHelp size={15} />{error}</div>}
        <div className="modal-actions"><button type="button" className="button button-quiet" onClick={onClose}>Cancel</button><button className="button button-primary" disabled={busy}>{busy ? <span className="button-spinner" /> : <>Create staff account <ArrowRight size={15} /></>}</button></div>
      </form>
    </section>
  </div>;
}

function ComplaintDetailModal({ complaint, user, onClose, onRefresh, showToast }) {
  const [comment, setComment] = useState("");
  const [resolutionComment, setResolutionComment] = useState("");
  const [department, setDepartment] = useState(complaint.department || DEPARTMENTS[8]);
  const [aiConsent, setAiConsent] = useState(false);
  const [staff, setStaff] = useState([]);
  const [staffId, setStaffId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (user.role === "admin") api.get("/admin/staff").then(({ data }) => setStaff(data.data.items)).catch(() => {});
  }, [user.role]);

  const act = async (fn, doneText) => {
    setBusy(true); setError("");
    try { await fn(); showToast(doneText); await onRefresh(); }
    catch (err) { setError(messageFromError(err)); }
    finally { setBusy(false); }
  };
  const addComment = (event) => {
    event.preventDefault();
    if (!comment.trim()) return;
    act(() => api.post(`/complaints/${complaint.public_id}/comments`, { comment }), "Your update was added.");
    setComment("");
  };
  const updateStatus = (status) => act(
    () => api.post(`/admin/complaints/${complaint.public_id}/status`, { status, comment: resolutionComment }),
    `Status updated to ${status}.`,
  );
  const assign = () => act(
    () => api.post(`/admin/complaints/${complaint.public_id}/assign`, {
      department,
      staff_id: staffId ? Number(staffId) : null,
    }),
    "The complaint has been assigned.",
  );
  const adminEdit = (field, value) => act(
    () => api.patch(`/admin/complaints/${complaint.public_id}`, { [field]: value }),
    `${field === "category" ? "Category" : "Priority"} updated.`,
  );
  const addWorkNote = () => act(
    () => api.post(`/staff/complaints/${complaint.public_id}/resolution`, { comment: resolutionComment }),
    "Your work update was sent for administrative review.",
  );
  const reopen = () => act(
    () => api.post(`/complaints/${complaint.public_id}/reopen`, { comment: resolutionComment }),
    "Your complaint has been reopened.",
  );
  const optInToAI = () => act(
    () => api.post(`/complaints/${complaint.public_id}/analyze`, { consent: true }),
    "AI suggestions are ready for staff review.",
  );
  const retryAI = () => act(
    () => api.post(`/admin/complaints/${complaint.public_id}/analyze`),
    "AI analysis has been retried.",
  );
  const openAttachment = async (attachmentId) => {
    try {
      const { data } = await api.get(`/attachments/${attachmentId}`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) { showToast(messageFromError(err), "error"); }
  };
  const refresh = async () => {
    if (user.role === "admin") await api.get("/admin/complaints?per_page=100");
    else if (user.role === "staff") await api.get("/staff/complaints");
    else await api.get("/complaints/my?per_page=100");
    onRefresh();
  };
  const entries = complaint.history || [];
  return <div className="modal-scrim" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="modal-card detail-modal" role="dialog" aria-modal="true" aria-labelledby="detail-title">
      <div className="detail-header"><div><div className="detail-id"><span className="row-ticket">{complaint.public_id}</span><span className="detail-created">Opened {new Date(complaint.created_at).toLocaleDateString("en", { month: "long", day: "numeric", year: "numeric" })}</span></div><h2 id="detail-title">{complaint.title}</h2><div className="detail-badges"><StatusBadge status={complaint.status} /><PriorityTag priority={complaint.priority} /><span className="category-chip">{complaint.category}</span></div></div><button className="icon-button modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
      <div className="detail-scroll">
        <div className="detail-main-grid"><div className="detail-description"><h3>What’s going on</h3><p>{complaint.description}</p><div className="detail-location"><Building2 size={15} /><span>{complaint.location || "Location not provided"}</span><span className="detail-department">{complaint.department}</span></div>
          {complaint.student && <div className="admin-student"><div className="profile-avatar">{complaint.student.name[0]}</div><span><strong>{complaint.student.name}</strong><small>{complaint.student.email}</small></span></div>}
          {complaint.attachments?.map((file) => <button className="attachment-link attachment-button" key={file.id} onClick={() => openAttachment(file.id)}><CloudUpload size={15} />{file.name}<ArrowUpRight size={13} /></button>)}
        </div>
        <aside className="ai-insight"><div className="ai-insight-title"><span className="ai-spark"><Sparkles size={14} /></span> AI-ASSISTED REVIEW</div>{complaint.ai_processing_status === "Completed" ? <><p>{complaint.ai_summary || "No summary available."}</p><div className="ai-detail-pills"><span>{complaint.ai_suggested_category || "—"}</span><span>{complaint.ai_suggested_priority || "—"} priority</span></div>{complaint.ai_explanation && <small>{complaint.ai_explanation}</small>}{complaint.ai_review_flag && <div className="review-flag"><Zap size={13} />Please review promptly</div>}</> : <><p>{complaint.ai_explanation || "AI suggestions are pending. A staff member will review the report."}</p><span className="ai-processing">Analysis: {complaint.ai_processing_status}</span>{user.role === "student" && !complaint.ai_consent && <label className="detail-consent"><input type="checkbox" checked={aiConsent} onChange={(e) => setAiConsent(e.target.checked)} /><span>I agree to send this report to Google Gemini for AI analysis.</span></label>}{user.role === "student" && !complaint.ai_consent && <button className="button button-secondary ai-action" onClick={optInToAI} disabled={busy || !aiConsent}><Sparkles size={14} /> Analyze my report</button>}{user.role === "admin" && complaint.ai_consent && complaint.ai_processing_status !== "Completed" && <button className="button button-secondary ai-action" onClick={retryAI} disabled={busy}><Sparkles size={14} /> Retry AI analysis</button>}</>}</aside></div>
        <div className="detail-timeline"><div className="section-header"><h3>Updates & history</h3><span className="event-count">{entries.length} updates</span></div>{entries.length ? <div className="timeline">{entries.map((entry, index) => <div className={`timeline-event ${index === 0 ? "timeline-latest" : ""}`} key={`${entry.event_type}-${entry.created_at}-${index}`}><div className="timeline-rail"><span className="timeline-point" /></div><div className="timeline-copy"><div className="timeline-event-head"><strong>{eventLabel(entry)}</strong><time>{new Date(entry.created_at).toLocaleString("en", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</time></div>{entry.comment && <p>{entry.comment}</p>}{entry.actor && <small>by {entry.actor}</small>}</div></div>)}</div> : <p className="quiet-copy">Updates will appear here as your report moves along.</p>}</div>
        <div className="detail-actions">
          {user.role === "admin" && <div className="admin-actions">
            <div className="admin-control-row"><label>Category<select value={complaint.category} onChange={(e) => adminEdit("category", e.target.value)}>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select></label><label>Priority<select value={complaint.priority} onChange={(e) => adminEdit("priority", e.target.value)}>{PRIORITIES.map((item) => <option key={item}>{item}</option>)}</select></label></div>
            {complaint.status === "Submitted" && <button className="button button-secondary" onClick={() => updateStatus("Under Review")} disabled={busy}>Start review <ArrowRight size={15} /></button>}
            {["Under Review", "Reopened", "Assigned"].includes(complaint.status) && <><div className="admin-control-row"><label>Department<select value={department} onChange={(e) => setDepartment(e.target.value)}>{DEPARTMENTS.map((item) => <option key={item}>{item}</option>)}</select></label><label>Assign to staff<select value={staffId} onChange={(e) => setStaffId(e.target.value)}><option value="">Unassigned</option>{staff.map((person) => <option key={person.id} value={person.id}>{person.name} · {person.department}</option>)}</select></label></div><button className="button button-secondary" onClick={assign} disabled={busy}><Users size={15} /> Assign & route</button></>}
            {complaint.status === "Assigned" && <button className="button button-secondary" onClick={() => updateStatus("In Progress")} disabled={busy}>Move to in progress <ArrowRight size={15} /></button>}
            {complaint.status === "In Progress" && <><label className="resolution-field">Verification note<textarea value={resolutionComment} onChange={(e) => setResolutionComment(e.target.value)} placeholder="Add what was checked before resolving…" minLength={8} /></label><button className="button button-primary" onClick={() => updateStatus("Resolved")} disabled={busy || resolutionComment.trim().length < 8}><CheckCheck size={15} /> Verify & resolve</button></>}
            {complaint.status === "Resolved" && <button className="button button-secondary" onClick={() => updateStatus("Closed")} disabled={busy}>Close verified complaint <Check size={15} /></button>}
            {complaint.status === "Resolved" && <button className="button button-quiet" onClick={() => updateStatus("Reopened")} disabled={busy}>Reopen for more work <Activity size={15} /></button>}
            <form className="comment-form" onSubmit={(e) => { e.preventDefault(); act(() => api.patch(`/admin/complaints/${complaint.public_id}`, { comment, internal: false }), "Student update shared."); setComment(""); }}><label>Student-visible update<textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Share progress with the student…" /></label><button className="button button-quiet" disabled={busy || !comment.trim()}>Post update <Send size={14} /></button></form>
            <form className="comment-form internal-comment" onSubmit={(e) => { e.preventDefault(); act(() => api.patch(`/admin/complaints/${complaint.public_id}`, { comment, internal: true }), "Internal note saved."); setComment(""); }}><label>Internal staff note<textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Only administrators can view this note…" /></label><button className="button button-quiet" disabled={busy || !comment.trim()}>Save internal note <Send size={14} /></button></form>
          </div>}
          {user.role === "staff" && complaint.status === "Assigned" && <button className="button button-primary" onClick={() => act(() => api.post(`/staff/complaints/${complaint.public_id}/accept`), "Work accepted.")}><Wrench size={15} /> Accept this work</button>}
          {user.role === "staff" && complaint.status === "In Progress" && <div className="staff-update"><label>Progress update for the student<textarea value={resolutionComment} onChange={(e) => setResolutionComment(e.target.value)} placeholder="What have you checked or fixed so far?" /></label><button className="button button-primary" onClick={addWorkNote} disabled={busy || resolutionComment.trim().length < 8}><Send size={15} /> Send progress update</button><p className="field-hint">An administrator verifies work before marking the complaint resolved.</p></div>}
          {user.role === "student" && <form className="comment-form" onSubmit={addComment}><label>Add a clarification<textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Have more detail to share? Add it here…" /></label><button className="button button-primary" disabled={busy || !comment.trim()}><Send size={15} /> Send update</button>{complaint.status === "Resolved" && <><label>Why does the issue persist?<textarea value={resolutionComment} onChange={(e) => setResolutionComment(e.target.value)} placeholder="Let the campus team know…" /></label><button type="button" className="button button-secondary" disabled={busy || resolutionComment.trim().length < 8} onClick={reopen}><Activity size={15} /> Reopen this issue</button><small className="field-hint">Available for 30 days after the issue is resolved.</small></>}</form>}
        </div>
        {error && <div className="form-error detail-error"><CircleHelp size={15} />{error}</div>}
      </div>
      <div className="detail-footer"><span><ShieldCheck size={14} /> Your report is only shown to authorized campus users.</span><button className="button button-quiet" onClick={onClose}>Done</button></div>
    </section>
  </div>;
}

function eventLabel(entry) {
  const labels = {
    submitted: "Report received", ai_analysis: "AI suggestions ready for review",
    ai_analysis_failed: "Manual review requested", status_changed: `Status: ${entry.old_value} → ${entry.new_value}`,
    assignment_changed: "Work assignment updated", department_changed: "Department updated",
    category_corrected: "Category reviewed by staff", priority_corrected: "Priority reviewed by staff",
    comment: "Update shared", work_completed: "Maintenance progress submitted",
  };
  return labels[entry.event_type] || entry.event_type.replaceAll("_", " ");
}

function ComplaintsPage({ user, onOpen, onCreate }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All statuses");
  const [priority, setPriority] = useState("All priorities");
  const [category, setCategory] = useState("All categories");
  const [department, setDepartment] = useState("All departments");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setBusy(true); setError("");
    try {
      const params = new URLSearchParams({ per_page: "100" });
      if (user.role === "student") {
        if (status !== "All statuses") params.set("status", status);
        const { data } = await api.get(`/complaints/my?${params}`);
        setItems(data.data.items);
      } else if (user.role === "staff") {
        const { data } = await api.get(`/staff/complaints?${params}`);
        setItems(data.data.items);
      } else {
        if (status !== "All statuses") params.set("status", status);
        if (priority !== "All priorities") params.set("priority", priority);
        if (category !== "All categories") params.set("category", category);
        if (department !== "All departments") params.set("department", department);
        if (fromDate) params.set("from_date", fromDate);
        if (toDate) params.set("to_date", toDate);
        if (query.trim()) params.set("q", query.trim());
        const { data } = await api.get(`/admin/complaints?${params}`);
        setItems(data.data.items);
      }
    } catch (err) { setError(messageFromError(err)); }
    finally { setBusy(false); }
  }, [user.role, status, priority, category, department, fromDate, toDate, query]);
  useEffect(() => { load(); }, [load]);
  const heading = user.role === "admin" ? "Complaint inbox" : user.role === "staff" ? "Assigned to you" : "My complaints";
  return <div className="dashboard-page"><PageHeading eyebrow="THE ISSUE TRACKER" title={heading} description={user.role === "admin" ? "A clear view of the things your campus is working to fix." : user.role === "staff" ? "Your assigned work and the campus issues you're helping solve." : "Follow each report from the first note to the final fix."} action={user.role === "student" && <button className="button button-primary" onClick={onCreate}><Plus size={16} /> New report</button>} />
    <section className="panel table-panel"><div className="table-toolbar"><div className="table-results">{items.length} {items.length === 1 ? "report" : "reports"}<span>·</span> Latest first</div><div className="table-controls">{user.role === "admin" && <label className="search-shell"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search issue, ID or student" /></label>}<label className="filter-shell"><Filter size={14} /><select value={status} onChange={(e) => setStatus(e.target.value)}><option>All statuses</option>{STATUSES.map((item) => <option key={item}>{item}</option>)}</select></label>{user.role === "admin" && <><select className="priority-filter" value={priority} onChange={(e) => setPriority(e.target.value)}><option>All priorities</option>{PRIORITIES.map((item) => <option key={item}>{item}</option>)}</select><select className="priority-filter" value={category} onChange={(e) => setCategory(e.target.value)}><option>All categories</option>{CATEGORIES.map((item) => <option key={item}>{item}</option>)}</select><select className="priority-filter" value={department} onChange={(e) => setDepartment(e.target.value)}><option>All departments</option>{DEPARTMENTS.map((item) => <option key={item}>{item}</option>)}</select><input className="date-filter" type="date" aria-label="From date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /><input className="date-filter" type="date" aria-label="To date" value={toDate} onChange={(e) => setToDate(e.target.value)} /></>}</div></div>
      {error && <div className="inline-error"><CircleHelp size={16} />{error}</div>}
      {busy ? <div className="skeleton-list"><div /><div /><div /><div /></div> : items.length ? <div className="complaint-list">{items.map((item) => <ComplaintRow item={item} key={item.id} onClick={onOpen} />)}</div> : <EmptyState icon={FileText} title="Nothing to see just yet" text={user.role === "student" ? "Your reports will show up here. Have a campus issue? Let the right people know." : "No reports match those filters right now."} action={user.role === "student" && <button className="button button-secondary" onClick={onCreate}><Plus size={15} /> Report an issue</button>} />}
    </section>
  </div>;
}

function AdminDashboard({ onOpen, showToast, onAddStaff }) {
  const [analytics, setAnalytics] = useState(null);
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [filter, setFilter] = useState("All");
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [statsResponse, complaintsResponse] = await Promise.all([
        api.get("/admin/analytics"),
        api.get(`/admin/complaints?per_page=100${filter !== "All" ? `&status=${encodeURIComponent(filter)}` : ""}`),
      ]);
      setAnalytics(statsResponse.data.data);
      setItems(complaintsResponse.data.data.items);
      setError("");
    } catch (err) { setError(messageFromError(err)); }
    finally { setBusy(false); }
  }, [filter]);
  useEffect(() => { load(); }, [load]);
  const exportReport = async () => {
    try {
      const response = await api.get("/admin/reports", { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url; link.download = "campusfix-report.csv"; link.click();
      URL.revokeObjectURL(url);
      showToast("Your report has been downloaded.");
    } catch (err) { showToast(messageFromError(err), "error"); }
  };
  return <div className="dashboard-page"><PageHeading eyebrow="CAMPUS OPERATIONS" title="Good morning, team" description="Here’s what’s happening across your campus today." action={<div className="header-actions"><button className="button button-secondary export-button" onClick={onAddStaff}><Plus size={14} /> Add staff</button><button className="button button-secondary export-button" onClick={exportReport}><ArrowDownLeft size={15} /> Export report</button></div>} />
    {error && <div className="inline-error"><CircleHelp size={16} />{error}</div>}
    <div className="stats-grid admin-stats"><StatCard icon={FileText} label="Total reports" value={analytics?.total ?? "—"} hint="Across your campus" tone="blue" /><StatCard icon={Activity} label="Active right now" value={analytics?.active ?? "—"} hint="Needs follow-through" tone="amber" /><StatCard icon={Zap} label="High priority" value={analytics?.high_priority ?? "—"} hint="Needs a closer look" tone="rose" /><StatCard icon={CheckCheck} label="Resolved" value={analytics?.resolved ?? "—"} hint={analytics?.average_resolution_hours == null ? "No completed reports yet" : `${analytics.average_resolution_hours}h average resolution`} tone="green" /></div>
    <Suspense fallback={<div className="chart-skeleton" />}><AdminVisualizations analytics={analytics} busy={busy} /></Suspense>
    <section className="panel inbox-panel"><div className="inbox-heading"><div><div className="section-kicker">KEEP THINGS MOVING</div><h2>Needs your attention</h2></div><div className="inbox-filters">{["All", "Submitted", "Under Review", "Assigned", "In Progress"].map((item) => <button key={item} className={filter === item ? "filter-active" : ""} onClick={() => setFilter(item)}>{item}</button>)}</div></div>{busy ? <div className="skeleton-list"><div /><div /><div /></div> : items.length ? <div className="complaint-list">{items.slice(0, 6).map((item) => <ComplaintRow key={item.id} item={item} onClick={onOpen} />)}</div> : <EmptyState icon={CheckCheck} title="All caught up" text="There are no reports in this view. Nice work." />}</section>
    <div className="admin-footnote"><ShieldCheck size={15} /> AI classifications are recommendations—not decisions. Review every assignment and resolution.</div>
  </div>;
}

function StaffDashboard({ user, onOpen }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(() => api.get("/staff/complaints?per_page=100").then(({ data }) => setItems(data.data.items)).catch((err) => setError(messageFromError(err))).finally(() => setBusy(false)), []);
  useEffect(() => { load(); }, [load]);
  const active = items.filter((item) => item.status === "In Progress").length;
  const queued = items.filter((item) => item.status === "Assigned").length;
  return <div className="dashboard-page"><div className="staff-welcome"><div><div className="eyebrow"><span className="eyebrow-spark"><Wrench size={13} /></span> THE HANDS-ON TEAM</div><h1>Good work, {user.name.split(/\s+/)[0]}.</h1><p>Your skills make a difference to everyone on campus.</p></div><div className="staff-emblem"><Wrench size={30} /></div></div>{error && <div className="inline-error">{error}</div>}
    <div className="stats-grid"><StatCard icon={FileText} label="On your list" value={items.length} hint="Assigned to you" tone="blue" /><StatCard icon={Clock3} label="Ready to begin" value={queued} hint="Pick one up to get started" tone="amber" /><StatCard icon={Wrench} label="In progress" value={active} hint="Keep up the great work" tone="purple" /><StatCard icon={CheckCheck} label="Completed" value={items.filter((item) => item.status === "Resolved").length} hint="Verified by an administrator" tone="green" /></div>
    <section className="panel staff-work-panel"><SectionHeader title="Your assigned work" />{busy ? <div className="skeleton-list"><div /><div /><div /></div> : items.length ? <div className="complaint-list">{items.map((item) => <ComplaintRow key={item.id} item={item} onClick={onOpen} />)}</div> : <EmptyState icon={Wrench} title="No work assigned yet" text="New assignments will appear here as soon as your team routes them to you." />}</section>
  </div>;
}

function NotificationsPage({ onOpen, showToast }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(() => api.get("/notifications?per_page=50").then(({ data }) => setItems(data.data.items)).catch((err) => setError(messageFromError(err))).finally(() => setBusy(false)), []);
  useEffect(() => { load(); }, [load]);
  const markRead = async (item) => {
    try {
      await api.patch(`/notifications/${item.id}/read`);
      setItems((current) => current.map((entry) => entry.id === item.id ? { ...entry, is_read: true } : entry));
    } catch (err) { showToast(messageFromError(err), "error"); }
  };
  const openItem = async (item) => {
    if (!item.is_read) await markRead(item);
    try {
      const { data } = await api.get(`/complaints/${item.public_id}`);
      onOpen(data.data.complaint);
    } catch (err) { showToast(messageFromError(err), "error"); }
  };
  return <div className="dashboard-page"><PageHeading eyebrow="STAY IN THE LOOP" title="Notifications" description="Updates from the campus team, all in one place." action={items.some((item) => !item.is_read) && <button className="button button-secondary" onClick={async () => { for (const item of items.filter((entry) => !entry.is_read)) await markRead(item); showToast("You’re all caught up."); }}><CheckCheck size={15} /> Mark all read</button>} />
    <section className="panel notifications-panel">{error && <div className="inline-error">{error}</div>}{busy ? <div className="skeleton-list"><div /><div /><div /></div> : items.length ? items.map((item) => <button className={`notification-row ${item.is_read ? "" : "notification-unread"}`} key={item.id} onClick={() => openItem(item)}><span className="notification-icon">{item.is_read ? <MessageCircle size={17} /> : <Bell size={17} />}</span><span className="notification-text"><strong>{item.message}</strong><small>Complaint {item.public_id} <span>·</span> {new Date(item.created_at).toLocaleString("en", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}</small></span>{!item.is_read && <span className="notification-new">NEW</span>}<ArrowRight size={15} /></button>) : <EmptyState icon={Bell} title="Nothing new, for now" text="When your campus team has an update, you’ll find it here." />}</section>
  </div>;
}

function ProtectedApp({ auth }) {
  const { toast, showToast, clearToast } = useToast();
  const navigate = useNavigate();
  const [newOpen, setNewOpen] = useState(false);
  const [staffOpen, setStaffOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  useEffect(() => {
    const handleNavigation = (event) => navigate(event.detail);
    window.addEventListener("campusfix:navigate", handleNavigation);
    return () => window.removeEventListener("campusfix:navigate", handleNavigation);
  }, [navigate]);
  if (auth.loading) return <PageLoader />;
  if (!auth.user) return <Navigate to="/" replace />;
  const refreshSelected = async () => {
    setRefreshKey((value) => value + 1);
    if (!selected) return;
    try {
      const endpoint = auth.user.role === "admin" ? "/admin/complaints?per_page=100" : auth.user.role === "staff" ? "/staff/complaints?per_page=100" : "/complaints/my?per_page=100";
      const { data } = await api.get(endpoint);
      const item = data.data.items.find((row) => row.public_id === selected.public_id);
      if (item) setSelected(item);
    } catch { /* The current detail remains visible if a list refresh fails. */ }
  };
  const handleSubmitted = (complaint) => {
    setNewOpen(false);
    showToast(`Report received · ${complaint.public_id}`);
    setRefreshKey((value) => value + 1);
    navigate("/app/complaints");
    setSelected(complaint);
  };
  const openComplaint = async (item) => {
    try {
      const { data } = await api.get(`/complaints/${item.public_id}`);
      setSelected(data.data.complaint);
    } catch (err) { showToast(messageFromError(err), "error"); }
  };
  return <Shell user={auth.user} onLogout={auth.signOut} toast={toast} clearToast={clearToast}>
    <div key={refreshKey}>
      <Routes>
        <Route path="/" element={auth.user.role === "student" ? <StudentDashboard user={auth.user} onCreate={() => setNewOpen(true)} onOpen={openComplaint} /> : auth.user.role === "admin" ? <AdminDashboard onOpen={openComplaint} showToast={showToast} onAddStaff={() => setStaffOpen(true)} /> : <StaffDashboard user={auth.user} onOpen={openComplaint} />} />
        <Route path="/complaints" element={<ComplaintsPage user={auth.user} onOpen={openComplaint} onCreate={() => setNewOpen(true)} />} />
        <Route path="/notifications" element={<NotificationsPage onOpen={setSelected} showToast={showToast} />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </div>
    {newOpen && <NewComplaintModal onClose={() => setNewOpen(false)} onSubmitted={handleSubmitted} showToast={showToast} />}
    {staffOpen && <CreateStaffModal onClose={() => setStaffOpen(false)} onCreated={() => { setStaffOpen(false); setRefreshKey((value) => value + 1); }} showToast={showToast} />}
    {selected && <ComplaintDetailModal complaint={selected} user={auth.user} onClose={() => setSelected(null)} onRefresh={refreshSelected} showToast={showToast} />}
  </Shell>;
}

export default function App() {
  const auth = useAuth();
  if (auth.loading) return <PageLoader />;
  return <Routes><Route path="/" element={auth.user ? <Navigate to="/app" replace /> : <AuthPage onLogin={auth.signIn} />} /><Route path="/app/*" element={<ProtectedApp auth={auth} />} /><Route path="*" element={<Navigate to={auth.user ? "/app" : "/"} replace />} /></Routes>;
}
