
import { useState } from "react";
import {
  Upload, Camera, FileText, Image, X, Plus,
  Trash2, ArrowRight, ShieldCheck, ClipboardList
} from "lucide-react";
import "./PrescriptionUpload.css";

export default function PrescriptionUpload() {
  const [file, setFile] = useState(null);
  const [manualMode, setManualMode] = useState(false);
  const [medicine, setMedicine] = useState({
    name: "",
    dosage: "",
    frequency: "",
    duration: ""
  });
  const [medicines, setMedicines] = useState([]);
  const [message, setMessage] = useState("");

  function handleFile(selectedFile) {
    if (!selectedFile) return;

    const allowed = [
      "image/jpeg",
      "image/png",
      "image/webp",
      "application/pdf"
    ];

    if (!allowed.includes(selectedFile.type)) {
      setMessage("Please select a JPG, PNG, WEBP or PDF file.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setMessage("File size must be below 10 MB.");
      return;
    }

    setFile(selectedFile);
    setMessage("");
  }

  function addMedicine(e) {
    e.preventDefault();

    if (!medicine.name.trim()) {
      setMessage("Please enter a medicine name.");
      return;
    }

    setMedicines((previous) => [
      ...previous,
      { ...medicine, id: Date.now() }
    ]);

    setMedicine({
      name: "",
      dosage: "",
      frequency: "",
      duration: ""
    });

    setMessage("");
  }

  function removeMedicine(id) {
    setMedicines((previous) =>
      previous.filter((item) => item.id !== id)
    );
  }

  function handleContinue() {
    if (!file && medicines.length === 0) {
      setMessage("Please upload a prescription or add medicine details.");
      return;
    }

    setMessage(
      "Your prescription details are ready. Backend OCR and medication analysis integration is the next step."
    );
  }

  return (
    <div className="prescription-page">

      <div className="prescription-heading">
        <div>
          <span className="prescription-eyebrow">MEDICAL DOCUMENTS</span>
          <h1>Prescription Upload</h1>
          <p>Upload a prescription or enter your medicine details manually.</p>
        </div>

        <div className="privacy-indicator">
          <ShieldCheck size={17} />
          Secure document handling
        </div>
      </div>

      <div className="prescription-content">

        <section className="upload-card">
          <div className="section-heading">
            <div>
              <h2>Upload prescription</h2>
              <p>Choose an image or PDF of your prescription.</p>
            </div>
            <div className="section-icon"><Upload /></div>
          </div>

          <label className="upload-zone">
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.pdf"
              onChange={(e) => handleFile(e.target.files[0])}
              hidden
            />

            <div className="upload-icon">
              <Upload size={28} />
            </div>

            <strong>Click to upload your prescription</strong>
            <span>or select a file from your device</span>
            <small>JPG, PNG, WEBP or PDF · Maximum 10 MB</small>
          </label>

          <div className="capture-options">
            <label className="capture-button">
              <Camera size={19} />
              <span>Capture with camera</span>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={(e) => handleFile(e.target.files[0])}
                hidden
              />
            </label>

            <button
              className={`capture-button ${manualMode ? "selected" : ""}`}
              onClick={() => {
                setManualMode(!manualMode);
                setMessage("");
              }}
            >
              <ClipboardList size={19} />
              <span>Manual entry</span>
            </button>
          </div>

          {file && (
            <div className="selected-file">
              <div className="file-icon">
                {file.type === "application/pdf" ? (
                  <FileText />
                ) : (
                  <Image />
                )}
              </div>

              <div className="file-details">
                <strong>{file.name}</strong>
                <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              </div>

              <button
                className="remove-file"
                onClick={() => setFile(null)}
                aria-label="Remove file"
              >
                <X size={19} />
              </button>
            </div>
          )}

          <div className="upload-note">
            <ShieldCheck size={17} />
            <span>
              Only upload medical documents you are authorized to share.
            </span>
          </div>
        </section>

        {manualMode && (
          <section className="upload-card manual-card">
            <div className="section-heading">
              <div>
                <h2>Enter medicine details</h2>
                <p>Enter information exactly as written on the prescription.</p>
              </div>
              <div className="section-icon"><ClipboardList /></div>
            </div>

            <form onSubmit={addMedicine} className="medicine-form">
              <label>Medicine name *</label>
              <input
                placeholder="Enter medicine name"
                value={medicine.name}
                onChange={(e) =>
                  setMedicine({ ...medicine, name: e.target.value })
                }
                required
              />

              <label>Dosage</label>
              <input
                placeholder="e.g. 500 mg"
                value={medicine.dosage}
                onChange={(e) =>
                  setMedicine({ ...medicine, dosage: e.target.value })
                }
              />

              <label>Frequency</label>
              <input
                placeholder="e.g. Twice daily"
                value={medicine.frequency}
                onChange={(e) =>
                  setMedicine({ ...medicine, frequency: e.target.value })
                }
              />

              <label>Duration</label>
              <input
                placeholder="e.g. 5 days"
                value={medicine.duration}
                onChange={(e) =>
                  setMedicine({ ...medicine, duration: e.target.value })
                }
              />

              <button type="submit" className="add-medicine-button">
                <Plus size={18} /> Add medicine
              </button>
            </form>

            {medicines.length > 0 && (
              <div className="medicine-list">
                <h3>Added medicines ({medicines.length})</h3>

                {medicines.map((item) => (
                  <div className="medicine-item" key={item.id}>
                    <div>
                      <strong>{item.name}</strong>
                      <span>
                        {[item.dosage, item.frequency, item.duration]
                          .filter(Boolean)
                          .join(" · ") || "Details not provided"}
                      </span>
                    </div>

                    <button
                      onClick={() => removeMedicine(item.id)}
                      aria-label={`Remove ${item.name}`}
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        <section className="analysis-next-card">
          <div className="analysis-next-icon"><ShieldCheck size={27} /></div>
          <div>
            <h3>Ready for medication safety analysis?</h3>
            <p>
              Your uploaded prescription or manually entered medicines
              can be submitted for processing once backend integration is connected.
            </p>
          </div>
          <button onClick={handleContinue}>
            Continue <ArrowRight size={17} />
          </button>
        </section>

        {message && (
          <div className="prescription-message" role="status">
            {message}
          </div>
        )}

      </div>
    </div>
  );
}
