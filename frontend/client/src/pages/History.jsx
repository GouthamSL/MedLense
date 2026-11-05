
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  History as HistoryIcon,
  Search,
  FileText,
  Pill,
  CalendarDays,
  ChevronRight,
  Activity,
  ShieldCheck,
  Clock,
  Filter,
  Upload,
  Info,
} from "lucide-react";
import "./History.css";

export default function History() {
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState("");
  const [filter, setFilter] = useState("All");

  // Real history records will be loaded from the backend later.
  const historyRecords = [];

  const filteredRecords = historyRecords.filter((record) => {
    const matchesSearch =
      record.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      record.prescriptionId?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesFilter =
      filter === "All" || record.status === filter;

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="history-page">
      <header className="history-header">
        <button
          className="history-back"
          onClick={() => navigate("/dashboard")}
        >
          <ArrowLeft size={18} />
          Dashboard
        </button>

        <div className="history-brand">
          <Activity size={22} />
          <span>MedLense</span>
        </div>
      </header>

      <main className="history-container">
        <section className="history-welcome">
          <div>
            <span className="history-eyebrow">
              PATIENT RECORDS
            </span>
            <h1>Medical History</h1>
            <p>
              Access your previous prescriptions and medication
              analysis records in one place.
            </p>
          </div>

          <div className="history-heading-icon">
            <HistoryIcon size={32} />
          </div>
        </section>

        <section className="history-overview">
          <div className="history-overview-card">
            <div className="history-card-icon teal">
              <FileText size={21} />
            </div>
            <div>
              <strong>{historyRecords.length}</strong>
              <span>Total Prescriptions</span>
            </div>
          </div>

          <div className="history-overview-card">
            <div className="history-card-icon blue">
              <Activity size={21} />
            </div>
            <div>
              <strong>—</strong>
              <span>Analyses Completed</span>
            </div>
          </div>

          <div className="history-overview-card">
            <div className="history-card-icon purple">
              <Pill size={21} />
            </div>
            <div>
              <strong>—</strong>
              <span>Medicines Recorded</span>
            </div>
          </div>
        </section>

        <section className="history-record-section">
          <div className="history-section-heading">
            <div>
              <h2>Prescription Records</h2>
              <p>View and manage your previous medical records.</p>
            </div>

            <button
              className="history-upload-button"
              onClick={() => navigate("/prescription-upload")}
            >
              <Upload size={17} />
              New Prescription
            </button>
          </div>

          <div className="history-toolbar">
            <div className="history-search">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search prescriptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <div className="history-filter">
              <Filter size={17} />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="All">All Records</option>
                <option value="Completed">Completed</option>
                <option value="Processing">Processing</option>
              </select>
            </div>
          </div>

          {filteredRecords.length > 0 ? (
            <div className="history-record-list">
              {filteredRecords.map((record) => (
                <article
                  className="history-record-card"
                  key={record.prescriptionId}
                >
                  <div className="history-record-icon">
                    <FileText size={23} />
                  </div>

                  <div className="history-record-info">
                    <h3>{record.title}</h3>
                    <span>
                      Prescription ID: {record.prescriptionId}
                    </span>

                    <div className="history-record-meta">
                      <span>
                        <CalendarDays size={14} />
                        {record.date}
                      </span>
                      <span>
                        <Pill size={14} />
                        {record.medicineCount} medicines
                      </span>
                    </div>
                  </div>

                  <span
                    className={`history-status ${
                      record.status === "Completed"
                        ? "history-status-completed"
                        : "history-status-processing"
                    }`}
                  >
                    {record.status}
                  </span>

                  <button
                    className="history-view-button"
                    onClick={() =>
                      navigate("/prescription-analysis", {
                        state: {
                          analysisData: record.analysisData,
                        },
                      })
                    }
                    aria-label="View prescription analysis"
                  >
                    <ChevronRight size={21} />
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <div className="history-empty">
              <div className="history-empty-icon">
                <HistoryIcon size={34} />
              </div>

              <h3>
                {searchQuery || filter !== "All"
                  ? "No matching records"
                  : "No medical history yet"}
              </h3>

              <p>
                {searchQuery || filter !== "All"
                  ? "Try changing your search or filter."
                  : "Your prescription uploads and analysis records will appear here once they are saved to your account."}
              </p>

              {!searchQuery && filter === "All" && (
                <button
                  onClick={() => navigate("/prescription-upload")}
                >
                  <Upload size={17} />
                  Upload Your First Prescription
                </button>
              )}
            </div>
          )}
        </section>

        <section className="history-information">
          <Info size={19} />
          <p>
            Your medical history is intended to help you review
            previous records. Actual records will be displayed
            after database integration. Always consult a qualified
            healthcare professional for medical decisions.
          </p>
        </section>

        <footer className="history-footer">
          <ShieldCheck size={16} />
          MedLense · Intelligent Healthcare Platform
        </footer>
      </main>
    </div>
  );
}
