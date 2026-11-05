import Dashboard from "./pages/Dashboard";
import PrescriptionUpload from "./pages/PrescriptionUpload";
import { useState } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import {
  HeartPulse, ShieldCheck, Activity, Eye, EyeOff,
  Mail, LockKeyhole, UserRound, ArrowRight, ScanLine
} from "lucide-react";
import "./App.css";


function BrandPanel() {
  return (
    <section className="brand-panel">
      <div className="brand-logo">
        <div className="logo-icon"><HeartPulse size={27} /></div>
        <span>Med<span>Lense</span></span>
      </div>

      <div className="brand-content">
        <div className="brand-tag"><Activity size={15} /> INTELLIGENT HEALTHCARE</div>
        <h1>Better insights.<br />Safer healthcare.</h1>
        <p>
          Understand prescriptions, identify potential medication risks
          and make more informed healthcare decisions.
        </p>

        <div className="feature-list">
          <div><ShieldCheck /> Intelligent medication safety</div>
          <div><ScanLine /> Smart prescription analysis</div>
          <div><HeartPulse /> Patient-focused healthcare</div>
        </div>
      </div>

      <div className="brand-footer">
        © 2026 MedLense. Healthcare intelligence platform.
      </div>
    </section>
  );
}

function AuthLayout({ children }) {
  return (
    <main className="auth-layout">
      <BrandPanel />
      <section className="auth-side">{children}</section>
    </main>
  );
}

function Login() {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  function handleSubmit(e) {
  e.preventDefault();
  navigate("/dashboard");
}
  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="mobile-logo">
          <HeartPulse /> MedLense
        </div>

        <div className="welcome-label">WELCOME BACK</div>
        <h2>Sign in to your account</h2>
        <p className="auth-description">
          Access your healthcare dashboard securely.
        </p>

        <form onSubmit={handleSubmit}>
          <label>Email address</label>
          <div className="input-wrapper">
            <Mail size={19} />
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="label-row">
            <label>Password</label>
          </div>
          <div className="input-wrapper">
            <LockKeyhole size={19} />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="eye-button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label="Toggle password visibility"
            >
              {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
            </button>
          </div>

          <button className="primary-button" type="submit">
            Sign in <ArrowRight size={18} />
          </button>
        </form>

        {message && <p className="form-message">{message}</p>}

        <div className="auth-switch">
          Don't have an account? <Link to="/signup">Create account</Link>
        </div>

        <div className="secure-note">
          <ShieldCheck size={16} /> Your healthcare data deserves privacy.
        </div>
      </div>
    </AuthLayout>
  );
}

function Signup() {
  const [showPassword, setShowPassword] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");

  function handleSubmit(e) {
    e.preventDefault();

    if (password.length < 8) {
      setMessage("Password must contain at least 8 characters.");
      return;
    }

    if (password !== confirm) {
      setMessage("Passwords do not match.");
      return;
    }

    setMessage("Registration interface ready. Backend integration is next.");
  }

  return (
    <AuthLayout>
      <div className="auth-card signup-card">
        <div className="mobile-logo">
          <HeartPulse /> MedLense
        </div>

        <div className="welcome-label">GET STARTED</div>
        <h2>Create your account</h2>
        <p className="auth-description">
          Join MedLense for smarter healthcare insights.
        </p>

        <form onSubmit={handleSubmit}>
          <label>Full name</label>
          <div className="input-wrapper">
            <UserRound size={19} />
            <input
              type="text"
              placeholder="Enter your full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <label>Email address</label>
          <div className="input-wrapper">
            <Mail size={19} />
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <label>Password</label>
          <div className="input-wrapper">
            <LockKeyhole size={19} />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Minimum 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <button
              type="button"
              className="eye-button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label="Toggle password visibility"
            >
              {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
            </button>
          </div>

          <label>Confirm password</label>
          <div className="input-wrapper">
            <LockKeyhole size={19} />
            <input
              type="password"
              placeholder="Re-enter your password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>

          <button className="primary-button" type="submit">
            Create account <ArrowRight size={18} />
          </button>
        </form>

        {message && <p className="form-message">{message}</p>}

        <div className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>

        <div className="secure-note">
          <ShieldCheck size={16} /> Secure and privacy-conscious healthcare.
        </div>
      </div>
    </AuthLayout>
  );
}

function App() {
  return (
    <BrowserRouter>
  <Routes>
    <Route path="/" element={<Login />} />
    <Route path="/login" element={<Login />} />
    <Route path="/signup" element={<Signup />} />
    <Route path="/dashboard" element={<Dashboard />} />

    <Route
      path="/prescription-upload"
      element={<PrescriptionUpload />}
    />
  </Routes>
    </BrowserRouter>
  );
}

export default App;
