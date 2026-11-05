
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  UserRound,
  Mail,
  Phone,
  CalendarDays,
  MapPin,
  ShieldCheck,
  Edit3,
  Activity,
} from "lucide-react";
import "./PatientProfile.css";

export default function PatientProfile() {
  const navigate = useNavigate();

  return (
    <div className="patient-profile-page">
      <header className="patient-profile-header">
        <button onClick={() => navigate("/dashboard")}>
          <ArrowLeft size={18} />
          Back to Dashboard
        </button>
        <strong>MedLense</strong>
      </header>

      <main className="patient-profile-container">
        <div className="patient-profile-heading">
          <div>
            <span>PATIENT ACCOUNT</span>
            <h1>My Profile</h1>
            <p>View and manage your personal information.</p>
          </div>
          <ShieldCheck size={34} />
        </div>

        <section className="patient-profile-card">
          <div className="patient-profile-avatar">K</div>
          <div>
            <h2>Krupa</h2>
            <p>Patient Account</p>
            <span className="patient-profile-status">
              <Activity size={14} />
              Active Account
            </span>
          </div>
        </section>

        <section className="patient-details-card">
          <div className="patient-details-heading">
            <h3>Personal Information</h3>
            <span><UserRound size={18} /> Patient Details</span>
          </div>

          <div className="patient-details-grid">
            <div>
              <Mail />
              <span>Email Address</span>
              <strong>Not provided</strong>
            </div>

            <div>
              <Phone />
              <span>Phone Number</span>
              <strong>Not provided</strong>
            </div>

            <div>
              <CalendarDays />
              <span>Date of Birth</span>
              <strong>Not provided</strong>
            </div>

            <div>
              <MapPin />
              <span>Address</span>
              <strong>Not provided</strong>
            </div>
          </div>
        </section>

        <div className="patient-profile-note">
          <ShieldCheck size={19} />
          <p>
            Your personal and medical information should be kept
            private and secure. Profile editing and saved patient
            information will be connected to the backend later.
          </p>
        </div>
      </main>
    </div>
  );
}
