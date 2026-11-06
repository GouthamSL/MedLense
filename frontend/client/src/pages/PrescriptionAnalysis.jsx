
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Activity,
  Pill,
  FileText,
  Clock,
  CheckCircle,
  AlertTriangle,
  Info,
  RotateCcw,
} from "lucide-react";
import "./PrescriptionAnalysis.css";

function PrescriptionAnalysis() {
  const location = useLocation();
  const navigate = useNavigate();

  // Results will be passed from the prescription upload page.
  const response =
    location.state?.analysisData ||
    location.state?.result ||
    location.state ||
    {};

  const data = response.result || response;

  const medicines = Array.isArray(data.medicines)
    ? data.medicines
    : [];

  const prescriptionId = data.prescription_id || "Not available";
  const rawOcrText = data.raw_ocr_text || "";

  const getStatus = (medicine) => {
    const status = String(
      medicine.identification_status || ""
    ).toLowerCase();

    if (
      status.includes("verified") ||
      status.includes("identified") ||
      status === "success"
    ) {
      return "Verified";
    }

    if (
      status.includes("unverified") ||
      status.includes("not_found") ||
      status.includes("failed")
    ) {
      return "Needs review";
    }

    return "Not confirmed";
  };

  const getConfidence = (medicine) => {
    const value = medicine.identification_confidence;

    if (value === undefined || value === null || value === "") {
      return "Not available";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) return String(value);

    return `${number <= 1
      ? (number * 100).toFixed(1)
      : number.toFixed(1)}%`;
  };

  return (
    <div className="analysis-page">
      <header className="analysis-header">
        <button
          className="analysis-back"
          onClick={() => navigate("/prescription-upload")}
        >
          <ArrowLeft size={18} />
          Back to Upload
        </button>

        <div className="analysis-brand">
          <Activity size={22} />
          <span>MedLense</span>
        </div>
      </header>

      <main className="analysis-container">
        <section className="analysis-heading">
          <div>
            <span className="analysis-eyebrow">
              PRESCRIPTION INTELLIGENCE
            </span>
            <h1>Prescription Analysis</h1>
            <p>
              Review the medicines and dosage information extracted
              from your prescription.
            </p>
          </div>

          <div className="analysis-heading-icon">
            <FileText size={30} />
          </div>
        </section>

        <section className="analysis-summary">
          <div className="summary-item">
            <span className="summary-icon">
              <Pill size={20} />
            </span>
            <div>
              <strong>{medicines.length}</strong>
              <span>Medicines extracted</span>
            </div>
          </div>

          <div className="summary-item">
            <span className="summary-icon">
              <FileText size={20} />
            </span>
            <div>
              <strong>
                {prescriptionId === "Not available"
                  ? "—"
                  : prescriptionId}
              </strong>
              <span>Prescription ID</span>
            </div>
          </div>
        </section>

        <section className="analysis-section">
          <div className="section-heading">
            <div>
              <h2>Extracted Medicines</h2>
              <p>Medicine information detected by the OCR pipeline.</p>
            </div>
            <span className="medicine-count">
              {medicines.length} found
            </span>
          </div>

          {medicines.length > 0 ? (
            <div className="medicine-list">
              {medicines.map((medicine, index) => {
                const status = getStatus(medicine);

                return (
                  <article
                    className="medicine-card"
                    key={medicine.id || index}
                  >
                    <div className="medicine-card-top">
                      <div className="medicine-number">
                        {String(index + 1).padStart(2, "0")}
                      </div>

                      <div className="medicine-title">
                        <h3>
                          {medicine.medicine_name ||
                            "Medicine name unavailable"}
                        </h3>
                        <span>
                          {medicine.active_ingredient ||
                            "Active ingredient not identified"}
                        </span>
                      </div>

                      <span
                        className={`medicine-status ${
                          status === "Verified"
                            ? "status-verified"
                            : "status-review"
                        }`}
                      >
                        {status === "Verified" ? (
                          <CheckCircle size={14} />
                        ) : (
                          <AlertTriangle size={14} />
                        )}
                        {status}
                      </span>
                    </div>

                    <div className="medicine-details">
                      <div>
                        <span>Strength</span>
                        <strong>{medicine.strength || "—"}</strong>
                      </div>

                      <div>
                        <span>Dosage</span>
                        <strong>{medicine.dose || "—"}</strong>
                      </div>

                      <div>
                        <span>Frequency</span>
                        <strong>{medicine.frequency || "—"}</strong>
                      </div>

                      <div>
                        <span>Duration</span>
                        <strong>{medicine.duration || "—"}</strong>
                      </div>

                      <div>
                        <span>Identification confidence</span>
                        <strong>
                          {getConfidence(medicine)}
                        </strong>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="analysis-empty">
              <Info size={28} />
              <h3>No analysis results available</h3>
              <p>
                Upload a prescription and complete the extraction
                process to view the results here.
              </p>
              <button
                onClick={() => navigate("/prescription-upload")}
              >
                Upload Prescription
              </button>
            </div>
          )}
        </section>

        {rawOcrText && (
          <section className="analysis-section ocr-section">
            <div className="section-heading">
              <div>
                <h2>Raw OCR Text</h2>
                <p>
                  Text detected from the uploaded prescription.
                </p>
              </div>
            </div>

            <pre className="ocr-content">{rawOcrText}</pre>
          </section>
        )}

        <div className="analysis-notice">
          <Info size={19} />
          <p>
            OCR and medicine identification results may require
            manual verification. Always confirm prescription details
            with a qualified healthcare professional before making
            medication decisions.
          </p>
        </div>

        <div className="analysis-actions">
          <button
            className="analysis-secondary-button"
            onClick={() => navigate("/prescription-upload")}
          >
            <RotateCcw size={17} />
            Analyse Another Prescription
          </button>
        </div>
      </main>
    </div>
  );
}

export default PrescriptionAnalysis;
