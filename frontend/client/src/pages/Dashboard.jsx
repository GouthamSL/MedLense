
import {
  HeartPulse, LayoutDashboard, FileText, ScanLine,
  History, Settings, Bell, Search, Plus,
  ShieldCheck, AlertTriangle, Activity, ArrowUpRight,
  Menu, UserRound, ChevronDown, Clock3, Mic, X
} from "lucide-react";

import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const activities = [
  {
    name: "Prescription analysis",
    detail: "Prescription uploaded for review",
    date: "Today",
    status: "Completed",
    icon: FileText
  },
  {
    name: "Medication safety check",
    detail: "Medication interaction screening",
    date: "Yesterday",
    status: "Reviewed",
    icon: ShieldCheck
  },
  {
    name: "Prescription upload",
    detail: "New prescription received",
    date: "Yesterday",
    status: "Processing",
    icon: ScanLine
  }
];

export default function Dashboard() {
  const navigate = useNavigate();

  const [active, setActive] = useState("Dashboard");
  const [menuOpen, setMenuOpen] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const recognitionRef = useRef(null);
    const [selectedLanguage, setSelectedLanguage] = useState("en-IN");

  const languages = [
    { label: "English", value: "en-IN" },
    { label: "ಕನ್ನಡ", value: "kn-IN" },
    { label: "हिन्दी", value: "hi-IN" },
    { label: "தமிழ்", value: "ta-IN" },
    { label: "తెలుగు", value: "te-IN" }
  ];
  const filteredActivities = activities.filter((item) => {
    const searchText = searchQuery.toLowerCase();

    return (
      item.name.toLowerCase().includes(searchText) ||
      item.detail.toLowerCase().includes(searchText) ||
      item.status.toLowerCase().includes(searchText)
    );
  });

  function startVoiceSearch() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setVoiceError(
        "Voice search is not supported in this browser. Please use Chrome."
      );
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = selectedLanguage;
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListening(true);
      setVoiceError("");
    };

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join("");

      setSearchQuery(transcript);
    };

    recognition.onerror = (event) => {
      setVoiceError(
        event.error === "not-allowed"
          ? "Please allow microphone access."
          : "Voice search failed. Please try again."
      );
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }

  const navigation = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "Upload Prescription", icon: ScanLine },
    { name: "Analysis", icon: Activity },
    { name: "History", icon: History },
  ];

  return (
    <div className="dashboard-layout">

      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="dash-brand">
          <div className="dash-logo"><HeartPulse /></div>
          <span>Med<span>Lense</span></span>
        </div>

        <p className="nav-heading">MAIN MENU</p>

        
<nav className="side-navigation">
  {navigation.map((item) => {
    const Icon = item.icon;

    return (
      <button
        key={item.name}
        className={`nav-item ${active === item.name ? "active" : ""}`}
        onClick={() => {
          setActive(item.name);
          setMenuOpen(false);

          if (item.name === "Upload Prescription") {
            navigate("/prescription-upload");
          }
        }}
      >
        <Icon size={19} />
        <span>{item.name}</span>
      </button>
    );
  })}
</nav>


        <div className="sidebar-bottom">
          <button className="nav-item">
            <Settings size={19} />
            <span>Settings</span>
          </button>

          <div className="sidebar-support">
            <ShieldCheck size={24} />
            <strong>Your health, our priority.</strong>
            <p>Make informed healthcare decisions with MedLense.</p>
          </div>

          <div className="profile-mini">
            <div className="profile-avatar">K</div>
            <div>
              <strong>Krupa</strong>
              <span>Patient account</span>
            </div>
            <ChevronDown size={16} />
          </div>
        </div>
      </aside>

      <main className="dashboard-main">

        <header className="dashboard-header">
          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <Menu />
          </button>

          
<div className="search-container">
  <div className="header-search">
    <Search size={19} />

    <input
      type="text"
      placeholder="Search prescriptions, medicines..."
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
    />

    {searchQuery && (
      <button
        className="search-clear"
        onClick={() => setSearchQuery("")}
        aria-label="Clear search"
      >
        <X size={17} />
      </button>
    )}

    <select
      className="language-select"
      value={selectedLanguage}
      onChange={(e) => setSelectedLanguage(e.target.value)}
      aria-label="Select voice search language"
      title="Select voice search language"
    >
      {languages.map((language) => (
        <option key={language.value} value={language.value}>
          {language.label}
        </option>
      ))}
    </select>

    <button
      className={`voice-search-button ${isListening ? "listening" : ""}`}
      onClick={startVoiceSearch}
      title={`Voice search in ${
        languages.find((l) => l.value === selectedLanguage)?.label
      }`}
      aria-label="Start voice search"
    >
      <Mic size={19} />
    </button>
  </div>

  {isListening && (
    <p className="voice-status">
      Listening in {
        languages.find((l) => l.value === selectedLanguage)?.label
      }... Speak now
    </p>
  )}

  {voiceError && (
    <p className="voice-error">{voiceError}</p>
  )}
</div>


          <div className="header-actions">
            <button className="notification-button" aria-label="Notifications">
              <Bell size={20} />
              <span></span>
            </button>
            <div className="header-profile">
              <div className="profile-avatar">K</div>
              <div className="header-user">
                <strong>Krupa</strong>
                <span>Patient</span>
              </div>
            </div>
          </div>
        </header>

        <div className="dashboard-content">

          <section className="welcome-section">
            <div>
              <p className="welcome-date">YOUR HEALTH OVERVIEW</p>
              <h1>Welcome back, Krupa! 👋</h1>
              <p>Here's an overview of your healthcare activity.</p>
            </div>

            <button className="upload-button"
              onClick={() => navigate("/prescription-upload")}>
              <Plus size={19} /> Upload Prescription
            </button>
          </section>

          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-top">
                <span>Total Prescriptions</span>
                <div className="stat-icon teal"><FileText /></div>
              </div>
              <h2>--</h2>
              <p>Awaiting real data integration</p>
            </div>

            <div className="stat-card">
              <div className="stat-top">
                <span>Analyses Completed</span>
                <div className="stat-icon blue"><Activity /></div>
              </div>
              <h2>--</h2>
              <p>Awaiting real data integration</p>
            </div>

            <div className="stat-card">
              <div className="stat-top">
                <span>Safety Alerts</span>
                <div className="stat-icon orange"><AlertTriangle /></div>
              </div>
              <h2>--</h2>
              <p>Awaiting real data integration</p>
            </div>

            <div className="stat-card">
              <div className="stat-top">
                <span>Health Reports</span>
                <div className="stat-icon purple"><ShieldCheck /></div>
              </div>
              <h2>--</h2>
              <p>Awaiting real data integration</p>
            </div>
          </section>

          <section className="dashboard-grid">

            <div className="dashboard-panel quick-panel">
              <div className="panel-heading">
                <div>
                  <h3>Quick Actions</h3>
                  <p>Access your healthcare tools</p>
                </div>
              </div>

              <div className="quick-actions">
                <button onClick={() => setActive("Upload Prescription")}>
                  <div className="quick-icon teal"><ScanLine /></div>
                  <div>
                    <strong>Upload Prescription</strong>
                    <span>Scan a new prescription</span>
                  </div>
                  <ArrowUpRight />
                </button>

                <button onClick={() => setActive("Analysis")}>
                  <div className="quick-icon blue"><Activity /></div>
                  <div>
                    <strong>View Analysis</strong>
                    <span>Explore analysis results</span>
                  </div>
                  <ArrowUpRight />
                </button>

                <button onClick={() => setActive("History")}>
                  <div className="quick-icon purple"><History /></div>
                  <div>
                    <strong>Medical History</strong>
                    <span>Review previous records</span>
                  </div>
                  <ArrowUpRight />
                </button>
              </div>
            </div>

            <div className="dashboard-panel safety-panel">
              <div className="panel-heading">
                <div>
                  <h3>Medication Safety</h3>
                  <p>Stay informed about medicine safety</p>
                </div>
                <ShieldCheck size={23} color="#078d80" />
              </div>

              <div className="safety-content">
                <div className="safety-illustration">
                  <ShieldCheck size={38} />
                </div>
                <h4>Medication safety matters</h4>
                <p>
                  Upload a prescription to check for potential
                  medication interactions and safety concerns.
                </p>
                <button onClick={() => setActive("Upload Prescription")}>
                  Start safety check <ArrowUpRight size={16} />
                </button>
              </div>
            </div>

          </section>

          <section className="dashboard-panel activity-panel">
            <div className="panel-heading">
              <div>
                <h3>Recent Activity</h3>
                <p>Your latest healthcare activities</p>
              </div>
              <button className="view-all" onClick={() => setActive("History")}>
                View all <ArrowUpRight size={15} />
              </button>
            </div>

            <div className="activity-list">
              {filteredActivities.map((item, index) => {
                const Icon = item.icon;
                return (
                  <div className="activity-row" key={index}>
                    <div className="activity-icon"><Icon /></div>
                    <div className="activity-info">
                      <strong>{item.name}</strong>
                      <span>{item.detail}</span>
                    </div>
                    <div className="activity-date">
                      <Clock3 size={14} /> {item.date}
                    </div>
                    <span className="activity-status">{item.status}</span>
                  </div>
                );
              })}
              {searchQuery && filteredActivities.length === 0 && (
    <div className="no-results">
      <Search size={25} />
      <strong>No matching activities found</strong>
      <span>Try another keyword.</span>
    </div>
  )}
            </div>
            <p className="demo-note">
              Illustrative activity entries. Live records will appear after backend integration.
            </p>
          </section>

          <footer className="dashboard-footer">
            © 2026 MedLense · Intelligent Healthcare Platform
          </footer>

        </div>
      </main>
    </div>
  );
}
