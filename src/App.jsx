import React, { useEffect, useMemo, useRef, useState } from "react";

// Secondary contact preset. Empty by default so the project ships without
// personal data; users can fill this from the Identity panel.
const gmailPreset = {
  location: "",
  phone: "",
  email: "",
};

const emptyProfile = {
  name: "",
  contact: { location: "", phone: "", email: "" },
  certifications: [],
  projects: [],
};

function fetchJson(url, options = {}) {
  return fetch(url, options).then(async (response) => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || data.message || "Request failed");
      error.data = data;
      throw error;
    }
    return data;
  });
}

function applyBold(text) {
  return (text || "").split(/(\*\*.*?\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

function looksLikeJobDescription(text) {
  const value = (text || "").trim();
  if (!value) return false;

  const lower = value.toLowerCase();
  const jdSignals = [
    "about the job",
    "role description",
    "company description",
    "qualifications",
    "responsibilities",
    "preferred qualifications",
    "basic qualifications",
    "essential qualifications",
    "about the role",
    "what you'll do",
    "what you will do",
    "job description",
  ];

  if (value.length > 600) return true;
  return jdSignals.some((signal) => lower.includes(signal));
}

function ThreadCard({ entry }) {
  return (
    <div className={`thread-card ${entry.kind}`}>
      <div className="thread-card-header">{entry.kind === "user" ? "You" : "Resume Engine"}</div>
      {entry.title ? <div className="thread-card-title">{entry.title}</div> : null}
      <div className="thread-card-body">
        {entry.lines?.map((line, index) => (
          <p key={index}>{line}</p>
        ))}
        {entry.list?.length ? (
          <ul className="thread-card-list">
            {entry.list.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

function ParsedPreview({ preview, loadingExperience }) {
  if (!preview) {
    return <div className="blank-state">Generate content to see the parsed preview.</div>;
  }

  const contactLine = [preview.contact?.location, preview.contact?.phone, preview.contact?.email]
    .filter(Boolean)
    .join(" | ");

  return (
    <div className="preview-scroll">
      <section className="preview-section">
        <div className="preview-title">{preview.title || ""}</div>
        {contactLine ? <div className="preview-contact">{contactLine}</div> : null}
      </section>

      {preview.summary ? (
        <section className="preview-section">
          <h3 className="section-label">Summary</h3>
          <p className="preview-copy">{preview.summary || ""}</p>
        </section>
      ) : null}

      {preview.technical_skills?.length ? (
        <section className="preview-section">
          <h3 className="section-label">Technical Skills</h3>
          <div className="skill-list">
            {preview.technical_skills.map((skill) => (
              <div key={skill.category} className="skill-row editable-row">
                <strong>{skill.category}:</strong>
                <span className="skill-row-text">{skill.items || ""}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {loadingExperience ? (
        <section className="preview-section">
          <h3 className="section-label">Professional Experience</h3>
          <div className="preview-loading-state">Professional experience is still generating...</div>
        </section>
      ) : preview.experience?.length ? (
        <section className="preview-section">
          <h3 className="section-label">Professional Experience</h3>
          <div className="experience-list">
            {preview.experience.map((item) => (
              <article key={`${item.company}-${item.dates}`} className="experience-card">
                <div className="experience-company">{item.company} | {item.dates}</div>
                <div className="experience-title-text">{item.title || ""}</div>
                <div className="experience-bullets">
                  {(item.bullets || []).map((bullet, index) => (
                    <div key={index} className="experience-bullet editable-row">
                      <span>•</span>
                      <span className="experience-bullet-text">{bullet}</span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

// Shared dialog accessibility: close on Escape, trap Tab focus within the
// dialog, focus the first focusable element on open, and restore focus to the
// previously-focused trigger on close.
function useDialogA11y(open, onClose) {
  const containerRef = useRef(null);
  const previouslyFocused = useRef(null);
  // Keep the latest onClose without making it an effect dependency, so the
  // effect runs only on open/close transitions (not on every parent re-render,
  // which would steal focus out of inputs after a single keystroke).
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    previouslyFocused.current = document.activeElement;
    const container = containerRef.current;

    const getFocusable = () =>
      container
        ? Array.from(
            container.querySelectorAll(
              'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
            )
          ).filter((el) => el.offsetParent !== null || el === document.activeElement)
        : [];

    // Move focus into the dialog.
    const focusable = getFocusable();
    if (focusable.length) focusable[0].focus();

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current?.();
        return;
      }
      if (event.key !== "Tab") return;
      const items = getFocusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      const prev = previouslyFocused.current;
      if (prev && typeof prev.focus === "function") prev.focus();
    };
  }, [open]);

  return containerRef;
}

function Modal({ open, title, onClose, children, footer }) {
  const containerRef = useDialogA11y(open, onClose);
  if (!open) return null;
  return (
    <div className="modal-shell" role="dialog" aria-modal="true" aria-label={title}>
      <button className="modal-backdrop" onClick={onClose} aria-label="Close modal" tabIndex={-1} />
      <div className="modal-card" ref={containerRef}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}

function SideDrawer({ open, title, onClose, children }) {
  const containerRef = useDialogA11y(open, onClose);
  if (!open) return null;
  return (
    <div className="drawer-shell" role="dialog" aria-modal="true" aria-label={title}>
      <button className="drawer-backdrop" onClick={onClose} aria-label="Close drawer" tabIndex={-1} />
      <aside className="drawer-panel" ref={containerRef}>
        <div className="drawer-header">
          <h2>{title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  );
}

function formatProjects(projects) {
  return (projects || [])
    .map((project) => {
      const bullets = (project.bullets || []).map((bullet) => `- ${bullet}`).join("\n");
      return [project.name || "", bullets].filter(Boolean).join("\n");
    })
    .filter(Boolean)
    .join("\n\n");
}

function parseProjects(text) {
  return text
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
      const name = lines.shift() || "";
      const bullets = lines.map((line) => line.replace(/^[-•●]\s*/, "").trim()).filter(Boolean);
      return { name, bullets };
    })
    .filter((project) => project.name);
}

function formatExperience(experience) {
  return (experience || [])
    .map((job) => {
      const header = [job.company || "", job.title || "", job.dates || "", job.location || ""].join(" | ");
      const bullets = (job.bullets || []).map((bullet) => `- ${bullet}`).join("\n");
      return [header, bullets].filter(Boolean).join("\n");
    })
    .filter(Boolean)
    .join("\n\n");
}

function parseExperience(text) {
  return (text || "")
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block) => {
      const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
      const headerParts = (lines.shift() || "").split("|").map((part) => part.trim());
      const [company = "", title = "", dates = "", location = ""] = headerParts;
      const bullets = lines.map((line) => line.replace(/^[-•●]\s*/, "").trim()).filter(Boolean);
      return { company, title, dates, location, bullets };
    })
    .filter((job) => job.company || job.title || job.bullets.length);
}

function formatSkills(skills) {
  return (skills || [])
    .map((skill) => `${skill.category || ""}: ${skill.items || ""}`.trim())
    .filter((line) => line && line !== ":")
    .join("\n");
}

function parseSkills(text) {
  return (text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const idx = line.indexOf(":");
      if (idx === -1) return { category: "", items: line };
      return { category: line.slice(0, idx).trim(), items: line.slice(idx + 1).trim() };
    })
    .filter((skill) => skill.category || skill.items);
}

function formatEducation(education) {
  return (education || [])
    .map((edu) => [edu.degree || "", edu.institution || "", edu.dates || ""].join(" | "))
    .filter((line) => line.replace(/\|/g, "").trim())
    .join("\n");
}

function parseEducation(text) {
  return (text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [degree = "", institution = "", dates = ""] = line.split("|").map((part) => part.trim());
      return { degree, institution, dates };
    })
    .filter((edu) => edu.degree || edu.institution);
}

function combineCoreDraft(titleSummaryContent, skillsContent) {
  return [titleSummaryContent?.trim(), skillsContent?.trim(), "Professional Experience"]
    .filter(Boolean)
    .join("\n\n");
}

function formatDateShort(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function daysSince(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.max(0, Math.floor((Date.now() - date.getTime()) / 86400000));
}

function dateValueForCompare(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().slice(0, 10);
}

function TrackerBoard({ applications, statuses, onStatusChange, onView, onOpenPdf, onOpenFolder }) {
  return (
    <div className="tracker-board">
      {statuses.map((status) => {
        const items = applications.filter((item) => item.status === status);
        return (
          <section key={status} className="tracker-column" aria-label={`${status} (${items.length})`}>
            <div className="tracker-column-header">
              <h3 className="tracker-column-title">{status}</h3>
              <span className="badge">{items.length}</span>
            </div>
            <div className="tracker-card-list">
              {items.length ? items.map((item) => (
                <article key={item.id} className="tracker-card">
                  <div className="tracker-card-top">
                    <div>
                      <div className="tracker-card-company">{item.company_name}</div>
                      <div className="tracker-card-role">{item.role_title}</div>
                    </div>
                    {item.role_family ? <span className="badge">{item.role_family}</span> : null}
                  </div>
                  <div className="tracker-card-meta">
                    <span>Applied {formatDateShort(item.applied_date)}</span>
                    <span>Updated {formatDateShort(item.status_updated_date || item.last_updated_date)}</span>
                  </div>
                  {item.folder_group ? (
                    <div className="tracker-card-meta">
                      <span>Folder group: {item.folder_group}</span>
                    </div>
                  ) : null}
                  <div className="tracker-card-meta">
                    <span>{daysSince(item.applied_date) ?? 0}d since apply</span>
                    <span>{daysSince(item.status_updated_date || item.last_updated_date) ?? 0}d since update</span>
                  </div>
                  <div className="tracker-card-actions">
                    <select aria-label={`Status for ${item.company_name}`} value={item.status} onChange={(e) => onStatusChange(item.id, e.target.value)}>
                      {statuses.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </div>
                  <div className="tracker-card-links">
                    <button className="link-button" onClick={() => onView(item)} disabled={!item.job_description}>View JD</button>
                    <button className="link-button" onClick={() => onOpenPdf(item)} disabled={!item.pdf_path}>Open PDF</button>
                    <button className="link-button" onClick={() => onOpenFolder(item)} disabled={!item.output_dir}>Folder</button>
                  </div>
                </article>
              )) : (
                <div className="tracker-empty-column">No applications</div>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function TrackerTable({ applications, statuses, onStatusChange, onView, onOpenPdf, onOpenFolder }) {
  return (
    <div className="tracker-table-shell">
      <table className="tracker-table">
        <thead>
          <tr>
            <th scope="col">Company</th>
            <th scope="col">Role</th>
            <th scope="col">Status</th>
            <th scope="col">Applied</th>
            <th scope="col">Last Update</th>
            <th scope="col">Since Apply</th>
            <th scope="col">Since Update</th>
            <th scope="col">Resume</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {applications.length ? applications.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="tracker-table-company">{item.company_name}</div>
                {item.role_family ? <div className="tracker-table-subtle">{item.role_family}</div> : null}
                {item.folder_group ? <div className="tracker-table-subtle">Folder group: {item.folder_group}</div> : null}
              </td>
              <td>{item.role_title}</td>
              <td>
                <select value={item.status} onChange={(e) => onStatusChange(item.id, e.target.value)}>
                  {statuses.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </td>
              <td>{formatDateShort(item.applied_date)}</td>
              <td>{formatDateShort(item.status_updated_date || item.last_updated_date)}</td>
              <td>{daysSince(item.applied_date) ?? "—"}d</td>
              <td>{daysSince(item.status_updated_date || item.last_updated_date) ?? "—"}d</td>
              <td>{item.resume_snapshot?.title || item.target_role || "Locked"}</td>
              <td>
                <div className="tracker-table-actions">
                  <button className="link-button" onClick={() => onView(item)} disabled={!item.job_description}>JD</button>
                  <button className="link-button" onClick={() => onOpenPdf(item)} disabled={!item.pdf_path}>PDF</button>
                  <button className="link-button" onClick={() => onOpenFolder(item)} disabled={!item.output_dir}>Folder</button>
                </div>
              </td>
            </tr>
          )) : (
            <tr>
              <td colSpan={9} className="tracker-empty-row">No applications tracked yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [profile, setProfile] = useState(emptyProfile);
  const [profileDraft, setProfileDraft] = useState(emptyProfile);
  const [settings, setSettings] = useState({ output_directory: "" });
  const [settingsDraft, setSettingsDraft] = useState("");
  const [pdfStatus, setPdfStatus] = useState({ ready: false, message: "Checking..." });
  const [aiStatus, setAiStatus] = useState({ ready: false, message: "Checking...", model: "gpt-5-mini", memory_limit: 2 });
  const [identity, setIdentity] = useState("outlook");
  const [contact, setContact] = useState({ location: "", phone: "", email: "" });
  const [companyName, setCompanyName] = useState("");
  const [composerInput, setComposerInput] = useState("");
  const [profileList, setProfileList] = useState({ active: "", profiles: [] });
  const [generatedContent, setGeneratedContent] = useState("");
  const [preview, setPreview] = useState(null);
  const [validation, setValidation] = useState({ valid: false, errors: [] });
  const [tab, setTab] = useState("parsed");
  const [aiSessionId, setAiSessionId] = useState(null);
  const [lastGeneratedJd, setLastGeneratedJd] = useState("");
  const [memoryCount, setMemoryCount] = useState(0);
  const [aiThread, setAiThread] = useState([]);
  const [aiError, setAiError] = useState("");
  const [showGeneratedArea, setShowGeneratedArea] = useState(false);
  const [latestAnalysis, setLatestAnalysis] = useState(null);
  // Auto-fill the company name from the analysis so the user rarely retypes it.
  useEffect(() => {
    const detected = (latestAnalysis?.company_name || "").trim();
    if (detected) {
      setCompanyName((current) => (current.trim() ? current : detected));
    }
  }, [latestAnalysis]);
  const [generatingAi, setGeneratingAi] = useState(false);
  const [reachoutLoading, setReachoutLoading] = useState(false);
  const [aiStage, setAiStage] = useState("");
  const [previewEditMode, setPreviewEditMode] = useState(false);
  const [pdfState, setPdfState] = useState({
    mode: "idle",
    error: "",
    statusPath: "",
    pdfPath: "",
    outputDir: "",
    statusLabel: "",
  });
  const [modals, setModals] = useState({
    instructions: false,
    settings: false,
    profile: false,
    controls: false,
    tracker: false,
    trackApply: false,
  });
  const [trackerData, setTrackerData] = useState({ applications: [], summary: { counts: {}, total: 0 }, statuses: ["Applied", "Updated", "Converted", "Ghosted", "Rejected"] });
  const [trackerLoading, setTrackerLoading] = useState(false);
  const [trackerError, setTrackerError] = useState("");
  const [trackerView, setTrackerView] = useState("board");
  const [trackerFilters, setTrackerFilters] = useState({
    query: "",
    applied_from: "",
    applied_to: "",
    profile: "",
  });
  // Application whose stored JD / analysis is being viewed in a modal.
  const [trackerDetail, setTrackerDetail] = useState(null);
  const [trackApplyDraft, setTrackApplyDraft] = useState({
    applied_date: new Date().toISOString().slice(0, 10),
    source: "",
    job_url: "",
    notes: "",
    status: "Applied",
  });

  const mediaRecorderRef = useRef(null);
  const mediaChunksRef = useRef([]);
  const streamRef = useRef(null);
  const [recordingTarget, setRecordingTarget] = useState("");

  useEffect(() => {
    fetchJson("/api/settings")
      .then((data) => {
        setSettings(data);
        setSettingsDraft(data.output_directory || "");
        setPdfStatus({
          ready: !!data.pdf_conversion_ready,
          message: data.pdf_conversion_status || "Unknown",
        });
      })
      .catch(() => {});

    fetchJson("/api/profile")
      .then((data) => {
        setProfile(data);
        setProfileDraft({
          ...data,
          contact: { ...(data.contact || emptyProfile.contact) },
        });
        setContact(data.contact || emptyProfile.contact);
      })
      .catch(() => {});

    fetchJson("/api/profiles")
      .then((data) => setProfileList({ active: data.active || "", profiles: data.profiles || [] }))
      .catch(() => {});

    fetchJson("/api/ai/status")
      .then((data) => setAiStatus(data))
      .catch((error) => {
        setAiStatus((current) => ({ ...current, ready: false, message: error.message }));
      });

    loadTracker();
  }, []);

  useEffect(() => {
    if (!generatedContent.trim()) {
      setPreview(null);
      setValidation({ valid: false, errors: [] });
      return;
    }

    const timeoutId = window.setTimeout(() => {
      fetchJson("/api/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: generatedContent,
          contact_override: contact,
          identity,
        }),
      })
        .then((data) => {
          setPreview(data.preview);
          setValidation({ valid: !!data.valid, errors: data.errors || [] });
        })
        .catch((error) => {
          setValidation({ valid: false, errors: [error.message] });
        });
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [generatedContent, contact, identity]);

  useEffect(() => {
    if (pdfState.mode !== "polling" || !pdfState.statusPath) return undefined;

    const timer = window.setInterval(() => {
      const url = `/api/status?path=${encodeURIComponent(pdfState.statusPath)}`;
      fetchJson(url)
        .then((data) => {
          if (data.state === "completed" || data.state === "success") {
            setPdfState((current) => ({
              ...current,
              mode: "ready",
              pdfPath: data.pdf || current.pdfPath,
              statusLabel: "PDF ready",
            }));
          } else if (data.state === "failed" || data.state === "error") {
            setPdfState((current) => ({
              ...current,
              mode: "error",
              error: data.error || "PDF generation failed",
            }));
          } else {
            setPdfState((current) => ({
              ...current,
              statusLabel: data.message || "Generating PDF...",
            }));
          }
        })
        .catch((error) => {
          setPdfState((current) => ({
            ...current,
            mode: "error",
            error: error.message,
          }));
        });
    }, 1500);

    return () => window.clearInterval(timer);
  }, [pdfState.mode, pdfState.statusPath]);

  const charCount = generatedContent.length;
  const pdfPreviewUrl = pdfState.pdfPath
    ? `/api/download?path=${encodeURIComponent(pdfState.pdfPath)}&preview=true`
    : "";

  const canGeneratePdf = validation.valid && generatedContent.trim().length > 0;

  const contactForIdentity = useMemo(
    () => ({
      outlook: profile.contact || emptyProfile.contact,
      gmail: gmailPreset,
    }),
    [profile.contact],
  );

  const statusBadgeClass = aiStatus.ready ? "badge status-ok" : "badge status-error";
  const jdModeLabel = showGeneratedArea ? "Current JD active" : "Waiting for new JD";
  // Distinct profile/folder-group values present in the tracker, for the filter.
  const trackerProfiles = useMemo(() => {
    const set = new Set();
    (trackerData.applications || []).forEach((item) => {
      const group = String(item.folder_group || "").trim();
      if (group) set.add(group);
    });
    return Array.from(set).sort();
  }, [trackerData.applications]);

  const filteredTrackerApplications = useMemo(() => {
    const query = trackerFilters.query.trim().toLowerCase();
    const from = trackerFilters.applied_from;
    const to = trackerFilters.applied_to;
    const profile = trackerFilters.profile;
    return (trackerData.applications || []).filter((item) => {
      const company = String(item.company_name || "").toLowerCase();
      const role = String(item.role_title || "").toLowerCase();
      if (query && !company.includes(query) && !role.includes(query)) {
        return false;
      }
      if (profile && String(item.folder_group || "").trim() !== profile) {
        return false;
      }
      const applied = dateValueForCompare(item.applied_date);
      if (from && applied && applied < from) return false;
      if (to && applied && applied > to) return false;
      if ((from || to) && !applied) return false;
      return true;
    });
  }, [trackerData.applications, trackerFilters]);

  // Open the generated PDF for a tracked application in a new tab.
  const openTrackerPdf = (item) => {
    const path = item?.pdf_path || "";
    if (!path) return;
    window.open(`/api/download?path=${encodeURIComponent(path)}&preview=true`, "_blank", "noopener");
  };

  // Reveal the application's output folder in the OS file browser.
  const openTrackerFolder = (item) => {
    const folder = item?.output_dir || "";
    if (!folder) return;
    fetchJson("/api/open-folder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: folder }),
    }).catch(() => {});
  };

  function openModal(name) {
    if (name === "settings") {
      fetchJson("/api/settings").then((data) => {
        setSettings(data);
        setSettingsDraft(data.output_directory || "");
      }).catch(() => {});
    }
    if (name === "profile") {
      Promise.all([fetchJson("/api/profile"), fetchJson("/api/profiles")])
        .then(([data, list]) => {
          setProfileDraft({
            ...data,
            contact: { ...(data.contact || emptyProfile.contact) },
            certificationsText: (data.certifications || []).join("\n"),
            projectsText: formatProjects(data.projects || []),
            title: data.title || "",
            summary: data.summary || "",
            experience: Array.isArray(data.experience) ? data.experience : [],
            technical_skills: Array.isArray(data.technical_skills) ? data.technical_skills : [],
            education: Array.isArray(data.education) ? data.education : [],
          });
          setProfileList({ active: list.active || "", profiles: list.profiles || [] });
        }).catch(() => {});
    }
    if (name === "tracker") {
      loadTracker();
    }
    setModals((current) => ({ ...current, [name]: true }));
  }

  function closeModal(name) {
    setModals((current) => ({ ...current, [name]: false }));
  }

  function resetAiSession(clearJd = true) {
    const sessionId = aiSessionId;
    setAiSessionId(null);
    setLastGeneratedJd("");
    setMemoryCount(0);
    setAiThread([]);
    setAiError("");
    setShowGeneratedArea(false);
    setLatestAnalysis(null);
    setGeneratedContent("");
    setAiStage("");
    if (clearJd) setComposerInput("");

    if (sessionId) {
      fetchJson("/api/ai/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      }).catch(() => {});
    }
  }

  function loadTracker() {
    setTrackerLoading(true);
    setTrackerError("");
    fetchJson("/api/tracker")
      .then((data) => setTrackerData({
        applications: data.applications || [],
        summary: data.summary || { counts: {}, total: 0 },
        statuses: data.statuses || ["Applied", "Updated", "Converted", "Ghosted", "Rejected"],
      }))
      .catch((error) => setTrackerError(error.message))
      .finally(() => setTrackerLoading(false));
  }

  async function submitTrackApplication() {
    if (!generatedContent.trim()) {
      setAiError("Generate a resume first before tracking an application.");
      return;
    }
    if (!companyName.trim() && !(latestAnalysis?.company_name || "").trim()) {
      setAiError("Add the company name before tracking the application.");
      return;
    }

    try {
      const data = await fetchJson("/api/tracker/applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: companyName,
          job_description: lastGeneratedJd,
          resume_content: generatedContent,
          analysis: latestAnalysis || {},
          applied_date: trackApplyDraft.applied_date,
          status: trackApplyDraft.status,
          source: trackApplyDraft.source,
          job_url: trackApplyDraft.job_url,
          notes: trackApplyDraft.notes,
          pdf_path: pdfState.pdfPath,
          output_dir: pdfState.outputDir,
          contact_override: contact,
          identity,
        }),
      });
      setTrackerData((current) => ({
        applications: [data.application, ...(current.applications || [])],
        summary: data.summary || current.summary,
        statuses: current.statuses,
      }));
      closeModal("trackApply");
      setTrackApplyDraft((current) => ({ ...current, notes: "", source: "", job_url: "" }));
      openModal("tracker");
    } catch (error) {
      setAiError(error.message || "Failed to track the application.");
    }
  }

  async function updateTrackedStatus(applicationId, nextStatus) {
    try {
      const data = await fetchJson(`/api/tracker/applications/${applicationId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus, effective_date: new Date().toISOString().slice(0, 10) }),
      });
      setTrackerData((current) => ({
        applications: (current.applications || []).map((item) => item.id === applicationId ? data.application : item),
        summary: data.summary || current.summary,
        statuses: current.statuses,
      }));
    } catch (error) {
      setTrackerError(error.message || "Failed to update status.");
    }
  }

  async function stopRecorder() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }

  async function startVoiceInput(target, setter) {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setAiError("Voice recording isn't supported in this browser. Try a recent Chrome or Safari.");
      return;
    }
    if (!window.isSecureContext) {
      setAiError(`Microphone needs a secure context. Open the app at ${window.location.origin} (use localhost, not a raw IP address).`);
      return;
    }

    if (recordingTarget === target) {
      stopRecorder();
      return;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      mediaChunksRef.current = [];

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;
      setRecordingTarget(target);
      setAiError("");

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          mediaChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setAiError("Voice recording failed. Try again.");
        setRecordingTarget("");
      };

      recorder.onstop = async () => {
        const blob = new Blob(mediaChunksRef.current, { type: "audio/webm" });
        mediaRecorderRef.current = null;
        mediaChunksRef.current = [];
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
        setRecordingTarget("");

        if (!blob.size) {
          return;
        }

        const formData = new FormData();
        formData.append("audio", blob, "speech.webm");
        formData.append("target", target);

        try {
          const data = await fetchJson("/api/transcribe", {
            method: "POST",
            body: formData,
          });
          setter((current) => (current ? `${current} ${data.text}` : data.text));
        } catch (error) {
          setAiError(error.message || "Voice transcription failed.");
        }
      };

      recorder.start();
    } catch (error) {
      setRecordingTarget("");
      const name = error?.name || "";
      console.error("[mic]", name, error);
      if (name === "NotAllowedError" || name === "SecurityError") {
        setAiError(
          "Microphone permission denied. Click the lock icon in the address bar → Site settings → set Microphone to Allow. " +
          "On macOS also check System Settings → Privacy & Security → Microphone → Chrome."
        );
      } else if (name === "NotFoundError" || name === "OverconstrainedError") {
        setAiError("No microphone was found. Plug one in or pick one in System Settings → Sound → Input.");
      } else if (name === "NotReadableError") {
        setAiError("Your microphone is busy in another app. Close Zoom/Meet/Slack/etc., then try again.");
      } else {
        setAiError(`Microphone access failed${name ? ` (${name})` : ""}. Check browser permissions and try again.`);
      }
    }
  }

  function soulThreadEntry(analysis) {
    const keySignals = (analysis.skills_mentioned || []).slice(0, 6);
    const highlights = (analysis.responsibilities || []).slice(0, 3);
    return {
      kind: "assistant",
      title: analysis.target_role || "Role summary",
      lines: [
        `Role family: ${analysis.role_family || ""}`,
        `Soul of the role: ${analysis.core_problem || ""}`,
        `System focus: ${analysis.system_description || ""}`,
        `Key signals: ${keySignals.join(", ")}`,
      ],
      list: highlights,
    };
  }

  async function submitAiGeneration() {
    const promptText = composerInput.trim();
    if (!promptText) {
      setAiError(aiSessionId ? "Enter the changes you want." : "Paste a job description first.");
      return;
    }

    const autoDetectedNewJd = !!aiSessionId && looksLikeJobDescription(promptText);
    const isNewJd = !aiSessionId || autoDetectedNewJd;
    const jd = isNewJd ? promptText : lastGeneratedJd;
    const revisionRequest = isNewJd ? "" : promptText;
    const userEntry = isNewJd
      ? { kind: "user", title: "", lines: [promptText.slice(0, 1200)] }
      : { kind: "user", title: "Changes", lines: [promptText] };
    const baseThread = isNewJd
      ? (userEntry ? [userEntry] : [])
      : [...aiThread, ...(userEntry ? [userEntry] : [])];

    setComposerInput("");
    setAiThread(baseThread);

    setGeneratingAi(true);
    setAiError("");
    setAiStage("analyzing");
    if (isNewJd) {
      if (autoDetectedNewJd) {
        setAiSessionId(null);
        setMemoryCount(0);
        setGeneratedContent("");
        setPreview(null);
        setValidation({ valid: false, errors: [] });
      }
      setCompanyName("");
    }

    try {
      const analyzeData = await fetchJson("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jd,
          revision_request: revisionRequest,
          current_resume_content: generatedContent,
          session_id: aiSessionId,
          reset_memory: isNewJd,
        }),
      });

      const nextSessionId = analyzeData.session_id || aiSessionId || null;
      setAiSessionId(nextSessionId);
      setLastGeneratedJd(jd);
      setLatestAnalysis(analyzeData.analysis || null);
      setMemoryCount(analyzeData.memory_count || 0);
      if ((analyzeData.analysis?.company_name || "").trim()) {
        setCompanyName((current) => current.trim() || analyzeData.analysis.company_name.trim());
      }
      setAiThread([...baseThread, soulThreadEntry(analyzeData.analysis)]);
      setShowGeneratedArea(true);
      setPreviewEditMode(false);
      setTab("parsed");

      setAiStage("core");
      const [titleSummaryData, skillsData] = await Promise.all([
        fetchJson("/api/ai/generate-title-summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: nextSessionId }),
        }),
        fetchJson("/api/ai/generate-skills", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: nextSessionId }),
        }),
      ]);

      const sessionAfterCore = titleSummaryData.session_id || skillsData.session_id || nextSessionId;
      const coreContent = combineCoreDraft(titleSummaryData.content, skillsData.content);
      setAiSessionId(sessionAfterCore);
      setShowGeneratedArea(true);
      setGeneratedContent(coreContent);
      setAiThread((current) => [
        ...current,
        {
          kind: "assistant",
          title: "Core Draft Ready",
          lines: ["Title, summary, and technical skills are ready. Professional experience is generating now."],
        },
      ]);

      setAiStage("experience");
      const [recentExperienceData, olderExperienceData] = await Promise.all([
        fetchJson("/api/ai/generate-experience-recent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionAfterCore }),
        }),
        fetchJson("/api/ai/generate-experience-older", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionAfterCore }),
        }),
      ]);

      const finalExperienceData = recentExperienceData.complete ? recentExperienceData : olderExperienceData;
      const sessionAfterExperience = finalExperienceData.session_id || sessionAfterCore;
      const fullResumeContent = finalExperienceData.content || coreContent;
      setAiSessionId(sessionAfterExperience || null);
      setGeneratedContent(fullResumeContent);
      setShowGeneratedArea(true);

      setAiStage("refinement");
      const reviewedCoreData = await fetchJson("/api/ai/review-core", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionAfterExperience }),
      });

      const sessionAfterReview = reviewedCoreData.session_id || sessionAfterExperience;
      const reviewedContent = reviewedCoreData.content || fullResumeContent;
      setAiSessionId(sessionAfterReview || null);
      setGeneratedContent(reviewedContent);
      setShowGeneratedArea(true);
      setComposerInput("");
      setTab("parsed");
      setAiThread((current) => {
        const next = [
          ...current,
          {
            kind: "assistant",
            title: reviewedCoreData.revised ? "Resume Refined" : "Resume Complete",
            lines: [
              reviewedCoreData.revised
                ? "The full resume is ready, and the summary and technical skills were tightened after experience generation."
                : "Complete resume is generated. You can edit it directly in the parsed preview.",
            ],
          },
        ];
        if (reviewedCoreData.title_warnings?.length) {
          next.push({
            kind: "assistant",
            title: "Experience Titles Adjusted",
            lines: ["A few historical job titles were normalized to fit the detected role family."],
            list: reviewedCoreData.title_warnings,
          });
        }
        return next;
      });
    } catch (error) {
      const payload = error.data || {};
      if (payload.analysis) {
        setAiSessionId(payload.session_id || aiSessionId || null);
        setMemoryCount(payload.memory_count || 0);
        setAiThread([...baseThread, soulThreadEntry(payload.analysis)]);
        setShowGeneratedArea(true);
      }
      if (payload.content) {
        setGeneratedContent(payload.content);
        setShowGeneratedArea(true);
        setTab("parsed");
      }

      const stageNames = {
        analysis: "JD analysis failed",
        title_summary_generation: "Title and summary generation failed",
        skills_generation: "Skills generation failed",
        core_review: "Resume refinement failed",
        core_generation: "Core resume generation failed",
        experience_generation: "Experience generation failed",
        resume_generation: "Resume generation failed",
      };
      const stageLabel = stageNames[payload.stage] || "";
      const totalMs = payload.timing?.total_ms || payload.timing?.analysis_ms || payload.timing?.core_ms || payload.timing?.experience_ms;
      const timingLabel = totalMs ? ` (${Math.round(totalMs / 100) / 10}s)` : "";
      setAiError(stageLabel ? `${stageLabel}${timingLabel}: ${error.message}` : error.message);
    } finally {
      setGeneratingAi(false);
      setAiStage("");
    }
  }

  function submitPdfGeneration() {
    if (!canGeneratePdf) return;

    setPdfState({
      mode: "loading",
      error: "",
      statusPath: "",
      pdfPath: "",
      outputDir: "",
      statusLabel: "Submitting...",
    });
    setTab("pdf");

    fetchJson("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: generatedContent,
        company_name: companyName || latestAnalysis?.company_name || "",
        contact_override: contact,
        identity,
        // Auto-capture into the tracker without a manual step.
        job_description: lastGeneratedJd,
        analysis: latestAnalysis || {},
      }),
    })
      .then((data) => {
        setPdfState({
          mode: "polling",
          error: "",
          statusPath: data.status_path,
          pdfPath: data.pdf,
          outputDir: data.output_dir,
          statusLabel: "Generating PDF...",
        });
      })
      .catch((error) => {
        setPdfState({
          mode: "error",
          error: error.message,
          statusPath: "",
          pdfPath: "",
          outputDir: "",
          statusLabel: "",
        });
      });
  }

  function saveSettings() {
    fetchJson("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ output_directory: settingsDraft }),
    })
      .then((data) => {
        setSettings((current) => ({ ...current, output_directory: data.output_directory }));
        closeModal("settings");
      })
      .catch((error) => window.alert(error.message));
  }

  function saveProfile() {
    const certifications = Array.isArray(profileDraft.certifications)
      ? profileDraft.certifications.map((c) => String(c || "").trim()).filter(Boolean)
      : (profileDraft.certificationsText || "")
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean);
    const projects = Array.isArray(profileDraft.projects) && profileDraft.projects.length
      ? profileDraft.projects
      : parseProjects(profileDraft.projectsText || "");
    const payload = {
      name: profileDraft.name || "",
      contact: profileDraft.contact || emptyProfile.contact,
      certifications,
      projects,
      title: profileDraft.title || "",
      summary: profileDraft.summary || "",
      experience: profileDraft.experience || [],
      technical_skills: profileDraft.technical_skills || [],
      education: profileDraft.education || [],
    };

    fetchJson("/api/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((data) => {
        setProfile(data.profile);
        setContact(data.profile.contact || emptyProfile.contact);
        closeModal("profile");
      })
      .catch((error) => window.alert(error.message));
  }

  function refreshProfileFromServer() {
    return Promise.all([
      fetchJson("/api/profile"),
      fetchJson("/api/profiles"),
    ]).then(([p, list]) => {
      setProfile(p);
      setProfileDraft({ ...p, contact: { ...(p.contact || emptyProfile.contact) } });
      setContact(p.contact || emptyProfile.contact);
      setProfileList({ active: list.active || "", profiles: list.profiles || [] });
    });
  }

  function switchActiveProfile(name) {
    if (!name || name === profileList.active) return;
    fetchJson("/api/profiles/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    })
      .then(() => refreshProfileFromServer())
      .catch((error) => window.alert(error.message));
  }

  function createNewProfile() {
    const name = window.prompt("Name for the new profile:");
    if (!name || !name.trim()) return;
    const copyChoice = window.confirm("Copy from the current profile?\nOK = copy, Cancel = start blank");
    fetchJson("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim(), copy_from: copyChoice ? profileList.active : "" }),
    })
      .then(() => refreshProfileFromServer())
      .catch((error) => window.alert(error.message));
  }

  function renameActiveProfile() {
    const current = profileList.active;
    if (!current) return;
    const next = window.prompt("Rename profile to:", current);
    if (!next || !next.trim() || next.trim() === current) return;
    fetchJson(`/api/profiles/${encodeURIComponent(current)}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: next.trim() }),
    })
      .then(() => refreshProfileFromServer())
      .catch((error) => window.alert(error.message));
  }

  function deleteActiveProfile() {
    const current = profileList.active;
    if (!current) return;
    if (profileList.profiles.length <= 1) {
      window.alert("You can't delete the last profile.");
      return;
    }
    if (!window.confirm(`Delete profile "${current}"? This can't be undone.`)) return;
    fetchJson(`/api/profiles/${encodeURIComponent(current)}`, { method: "DELETE" })
      .then(() => refreshProfileFromServer())
      .catch((error) => window.alert(error.message));
  }

  function selectIdentity(nextIdentity) {
    setIdentity(nextIdentity);
    setContact(contactForIdentity[nextIdentity] || emptyProfile.contact);
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!generatingAi && !reachoutLoading) {
        submitAiGeneration();
      }
    }
  }

  async function submitReachoutMessage() {
    if (!lastGeneratedJd.trim() || !generatedContent.trim() || !aiSessionId) {
      setAiError("Generate a resume first before creating a reachout message.");
      return;
    }

    setReachoutLoading(true);
    setAiError("");

    try {
      const data = await fetchJson("/api/ai/generate-reachout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: lastGeneratedJd,
          current_resume_content: generatedContent,
          session_id: aiSessionId,
        }),
      });

      const reachout = data.reachout || {};
      const message = (reachout.message || "").trim();
      const charCount = Number.isFinite(reachout.char_count) ? reachout.char_count : message.length;

      setAiThread((current) => [
        ...current,
        {
          kind: "assistant",
          title: "LinkedIn Reachout",
          lines: [message, `${charCount} characters`],
        },
      ]);
    } catch (error) {
      setAiError(error.message || "Reachout generation failed.");
    } finally {
      setReachoutLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-wrap">
          <div className="brand-dot" aria-hidden="true" />
          <div className="brand">Resume Generator</div>
        </div>
        <div className="topbar-actions">
          <button className="icon-button" onClick={() => openModal("controls")}>ID</button>
          <button className="icon-button" onClick={() => openModal("profile")}>Profile</button>
          <button className="icon-button" onClick={() => openModal("tracker")}>Tracker</button>
          <button className="icon-button" onClick={() => openModal("instructions")}>?</button>
          <button className="icon-button" onClick={() => openModal("settings")}>⚙</button>
          <span className={pdfStatus.ready ? "badge status-ok" : "badge status-error"}>
            {pdfStatus.ready ? "Ready" : "PDF Error"}
          </span>
        </div>
      </header>

      <main className="workspace chatgpt-shell">
        <section className="chat-surface">
          <div className="chat-surface-header">
            <div>
              <div className="panel-eyebrow">Conversation</div>
              <div className="panel-title">JD to Resume</div>
            </div>
          </div>
          <div className="chat-scroll">
            {!showGeneratedArea ? (
              <div className="chat-intro">
                <div className="intro-card">
                  <h2>Paste a job description to start.</h2>
                  <p>We automatically treat the first message as a new JD. After the draft is created, the same input becomes your change box for that JD until you start a new one.</p>
                </div>
              </div>
            ) : null}

            {aiError ? <div className="error-banner">{aiError}</div> : null}

            {aiThread.map((entry, index) => (
              <ThreadCard key={`${entry.kind}-${index}`} entry={entry} />
            ))}

            {generatingAi ? (
              <div className="loading-card" aria-live="polite">
                <div className="loading-card-header">Resume Engine</div>
                <div className="loading-card-body">
                  <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                  <div className="loading-copy">
                    {aiStage === "analyzing"
                      ? "Analyzing the JD..."
                      : aiStage === "core"
                        ? "Building title, summary, and skills..."
                        : aiStage === "experience"
                          ? "Writing the experience section..."
                          : showGeneratedArea
                            ? "Updating the draft for this JD..."
                            : "Reading the JD and building the first draft..."}
                  </div>
                </div>
              </div>
            ) : null}

            {reachoutLoading ? (
              <div className="loading-card" aria-live="polite">
                <div className="loading-card-header">Resume Engine</div>
                <div className="loading-card-body">
                  <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                  <div className="loading-copy">Writing a short LinkedIn reachout...</div>
                </div>
              </div>
            ) : null}

                {showGeneratedArea ? (
                  <div className="chat-block">
                    <div className="message-label">
                      {generatingAi && (aiStage === "core" || aiStage === "experience") ? "Core Resume Draft" : "Generated Resume"}
                      {generatingAi && aiStage === "experience" ? <span className="inline-status-pill">Experience still generating</span> : null}
                    </div>
                  </div>
                ) : null}
          </div>
          <div className="chat-composer-shell">
            <div className="composer-card">
              <textarea
                className="composer-textarea"
                value={composerInput}
                onChange={(e) => setComposerInput(e.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder={showGeneratedArea ? "Ask for changes for this JD only" : "Paste the full job description here"}
              />
              <div className="composer-toolbar">
                <div className="composer-toolbar-left">
                  {profileList.profiles.length > 0 && (
                    <label className="composer-profile-select" title="Resume profile used when generating">
                      <span className="composer-profile-label">Profile</span>
                      <select
                        aria-label="Resume profile used when generating"
                        value={profileList.active}
                        onChange={(e) => switchActiveProfile(e.target.value)}
                      >
                        {profileList.profiles.map((name) => (
                          <option key={name} value={name}>{name}</option>
                        ))}
                      </select>
                    </label>
                  )}
                  <button className="composer-pill" onClick={() => resetAiSession(true)}>New JD</button>
                  <button
                    className="composer-pill"
                    disabled={!showGeneratedArea || !generatedContent.trim() || generatingAi || reachoutLoading}
                    onClick={submitReachoutMessage}
                  >
                    {reachoutLoading ? "Writing..." : "Reachout"}
                  </button>
                </div>
                <div className="composer-toolbar-right">
                  <span className="composer-state">
                    {showGeneratedArea ? "Editing current JD" : "Ready for new JD"}
                  </span>
                  <button
                    className={`composer-icon-button ${recordingTarget === (showGeneratedArea ? "refinement" : "jd") ? "recording" : ""}`}
                    onClick={() => startVoiceInput(showGeneratedArea ? "refinement" : "jd", setComposerInput)}
                    aria-label={recordingTarget === (showGeneratedArea ? "refinement" : "jd") ? "Stop voice input" : "Start voice input"}
                  >
                    {recordingTarget === (showGeneratedArea ? "refinement" : "jd") ? "Stop" : "Mic"}
                  </button>
                  <button
                    className="composer-send-button"
                    disabled={generatingAi || reachoutLoading}
                    onClick={submitAiGeneration}
                    aria-label={showGeneratedArea ? "Update draft" : "Generate content"}
                  >
                    {generatingAi ? "..." : "Send"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="panel preview-surface">
          <div className="preview-toolbar">
            <div className="preview-toolbar-left">
              <div className="panel-eyebrow">Output</div>
              <div className="preview-toolbar-actions">
                <input
                  className="preview-company-input"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Company name (required)"
                />
                <button
                  className="primary-button"
                  disabled={!canGeneratePdf || !companyName.trim() || pdfState.mode === "loading" || pdfState.mode === "polling"}
                  onClick={submitPdfGeneration}
                >
                  Generate PDF
                </button>
                <button
                  className="secondary-button"
                  disabled={!generatedContent.trim()}
                  onClick={() => openModal("trackApply")}
                >
                  Add Tracker Details
                </button>
              </div>
            </div>
            <div className="preview-toolbar-right">
              {tab === "parsed" && preview ? (
                <button
                  className="secondary-button"
                  onClick={() => setPreviewEditMode((current) => !current)}
                >
                  {previewEditMode ? "Done" : "Edit"}
                </button>
              ) : null}
            </div>
          </div>
          <div className="tabs">
            <button className={`tab-button ${tab === "parsed" ? "active" : ""}`} onClick={() => setTab("parsed")}>Parsed Preview</button>
            <button className={`tab-button ${tab === "pdf" ? "active" : ""}`} onClick={() => setTab("pdf")}>PDF Preview</button>
          </div>
          <div className="panel-body preview-body">
            {tab === "parsed" ? (
              <>
                {validation.errors?.length ? (
                  <div className="error-list">
                    {validation.errors.map((error, index) => <div key={index}>{error}</div>)}
                  </div>
                ) : null}
                {previewEditMode ? (
                  <textarea
                    className="preview-editor"
                    value={generatedContent}
                    onChange={(e) => setGeneratedContent(e.target.value)}
                  />
                ) : (
                  <ParsedPreview
                    preview={preview}
                    loadingExperience={generatingAi && aiStage === "experience"}
                  />
                )}
              </>
            ) : (
              <div className="pdf-shell">
                {pdfState.mode === "idle" ? <div className="blank-state">Generate a resume to preview the PDF.</div> : null}
                {pdfState.mode === "loading" || pdfState.mode === "polling" ? (
                  <div className="blank-state">{pdfState.statusLabel || "Generating PDF..."}</div>
                ) : null}
                {pdfState.mode === "error" ? <div className="error-banner">{pdfState.error}</div> : null}
                {pdfState.mode === "ready" ? (
                  <>
                    <div className="pdf-actions">
                      <a className="primary-button link-button" href={`/api/download?path=${encodeURIComponent(pdfState.pdfPath)}`}>Download</a>
                      <button className="secondary-button" onClick={() => fetchJson("/api/open-folder", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ path: pdfState.outputDir }),
                      }).catch((error) => window.alert(error.message))}>Open Folder</button>
                    </div>
                    <iframe title="PDF Preview" className="pdf-frame" src={pdfPreviewUrl} />
                  </>
                ) : null}
              </div>
            )}
          </div>
        </section>
      </main>

      <Modal
        open={modals.instructions}
        title="Format Guide"
        onClose={() => closeModal("instructions")}
      >
        <div className="modal-copy">
          <p><strong>Updated Title</strong> followed by the target role.</p>
          <p><strong>Updated Summary</strong> with 3-4 production-focused lines.</p>
          <p><strong>Updated Skills</strong> as category-to-skill lists.</p>
          <p><strong>Professional Experience</strong> with the fixed company order and bullet rules.</p>
        </div>
      </Modal>

      <Modal
        open={modals.settings}
        title="Settings"
        onClose={() => closeModal("settings")}
        footer={(
          <>
            <button className="secondary-button" onClick={() => closeModal("settings")}>Cancel</button>
            <button className="primary-button" onClick={saveSettings}>Save</button>
          </>
        )}
      >
        <label className="field">
          Output Directory
          <input value={settingsDraft} onChange={(e) => setSettingsDraft(e.target.value)} />
        </label>
      </Modal>

      <Modal
        open={modals.profile}
        title="Profile"
        onClose={() => closeModal("profile")}
        footer={(
          <>
            <button className="secondary-button" onClick={() => closeModal("profile")}>Cancel</button>
            <button className="primary-button" onClick={saveProfile}>Save Profile</button>
          </>
        )}
      >
        <div className="profile-toolbar">
          <div className="profile-toolbar-row">
            <label className="composer-profile-select">
              <span className="composer-profile-label">Active Profile</span>
              <select
                value={profileList.active}
                onChange={(e) => switchActiveProfile(e.target.value)}
              >
                {profileList.profiles.map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </label>
            <div className="profile-toolbar-actions">
              <button className="secondary-button" onClick={createNewProfile}>+ New</button>
              <button className="secondary-button" onClick={renameActiveProfile}>Rename</button>
              <button className="secondary-button danger" onClick={deleteActiveProfile}>Delete</button>
            </div>
          </div>
          <small className="field-hint">Profiles let you keep separate résumés (e.g. one per role family). Edits below apply to the active profile.</small>
        </div>
        <div className="profile-grid">
          <label className="field">
            Name
            <input value={profileDraft.name || ""} onChange={(e) => setProfileDraft((current) => ({ ...current, name: e.target.value }))} />
          </label>
          <label className="field">
            Location
            <input value={profileDraft.contact?.location || ""} onChange={(e) => setProfileDraft((current) => ({ ...current, contact: { ...(current.contact || {}), location: e.target.value } }))} />
          </label>
          <label className="field">
            Phone
            <input value={profileDraft.contact?.phone || ""} onChange={(e) => setProfileDraft((current) => ({ ...current, contact: { ...(current.contact || {}), phone: e.target.value } }))} />
          </label>
          <label className="field">
            Email
            <input value={profileDraft.contact?.email || ""} onChange={(e) => setProfileDraft((current) => ({ ...current, contact: { ...(current.contact || {}), email: e.target.value } }))} />
          </label>
        </div>
        <label className="field">
          Professional Title
          <input value={profileDraft.title || ""} onChange={(e) => setProfileDraft((current) => ({ ...current, title: e.target.value }))} />
        </label>
        <label className="field">
          Summary
          <textarea value={profileDraft.summary || ""} onChange={(e) => setProfileDraft((current) => ({ ...current, summary: e.target.value }))} />
        </label>
        <div className="field">
          <div className="field-header">
            <span>Work Experience</span>
            <button className="add-link" type="button" onClick={() => setProfileDraft((c) => ({ ...c, experience: [...(c.experience || []), { company: "", title: "", dates: "", location: "", bullets: [""] }] }))}>+ Add Job</button>
          </div>
          <small className="field-hint">Fill the form fields. Each job has its own card; bullets can be added or removed individually.</small>
          <div className="entry-list">
            {(profileDraft.experience || []).map((job, jobIdx) => (
              <div key={jobIdx} className="entry-card">
                <div className="entry-card-grid">
                  <input placeholder="Company" value={job.company || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, company: e.target.value } : j) }))} />
                  <input placeholder="Job Title" value={job.title || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, title: e.target.value } : j) }))} />
                  <input placeholder="Dates (e.g. May 2024 – Present)" value={job.dates || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, dates: e.target.value } : j) }))} />
                  <input placeholder="Location" value={job.location || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, location: e.target.value } : j) }))} />
                </div>
                <div className="entry-bullets">
                  {(job.bullets || []).map((bullet, bIdx) => (
                    <div key={bIdx} className="bullet-row">
                      <textarea
                        rows={2}
                        placeholder={`Bullet ${bIdx + 1}`}
                        value={bullet || ""}
                        onChange={(e) => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, bullets: j.bullets.map((b, bi) => bi === bIdx ? e.target.value : b) } : j) }))}
                      />
                      <button className="icon-remove" type="button" title="Remove bullet" onClick={() => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, bullets: j.bullets.filter((_, bi) => bi !== bIdx) } : j) }))}>×</button>
                    </div>
                  ))}
                  <button className="add-link" type="button" onClick={() => setProfileDraft((c) => ({ ...c, experience: c.experience.map((j, i) => i === jobIdx ? { ...j, bullets: [...(j.bullets || []), ""] } : j) }))}>+ Add bullet</button>
                </div>
                <button className="secondary-button danger entry-remove" type="button" onClick={() => setProfileDraft((c) => ({ ...c, experience: c.experience.filter((_, i) => i !== jobIdx) }))}>Remove job</button>
              </div>
            ))}
            {(profileDraft.experience || []).length === 0 && (
              <div className="empty-hint">No jobs yet. Click <b>+ Add Job</b> to start.</div>
            )}
          </div>
        </div>

        <div className="field">
          <div className="field-header">
            <span>Technical Skills</span>
            <button className="add-link" type="button" onClick={() => setProfileDraft((c) => ({ ...c, technical_skills: [...(c.technical_skills || []), { category: "", items: "" }] }))}>+ Add Category</button>
          </div>
          <small className="field-hint">One row per category (e.g. <code>Backend Engineering</code>: <code>Node.js, FastAPI, Spring Boot</code>).</small>
          <div className="entry-list">
            {(profileDraft.technical_skills || []).map((skill, idx) => (
              <div key={idx} className="entry-card compact">
                <div className="entry-card-grid two">
                  <input placeholder="Category" value={skill.category || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, technical_skills: c.technical_skills.map((s, i) => i === idx ? { ...s, category: e.target.value } : s) }))} />
                  <input placeholder="Items (comma-separated)" value={skill.items || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, technical_skills: c.technical_skills.map((s, i) => i === idx ? { ...s, items: e.target.value } : s) }))} />
                </div>
                <button className="icon-remove" type="button" title="Remove" onClick={() => setProfileDraft((c) => ({ ...c, technical_skills: c.technical_skills.filter((_, i) => i !== idx) }))}>×</button>
              </div>
            ))}
          </div>
        </div>

        <div className="field">
          <div className="field-header">
            <span>Education</span>
            <button className="add-link" type="button" onClick={() => setProfileDraft((c) => ({ ...c, education: [...(c.education || []), { degree: "", institution: "", dates: "" }] }))}>+ Add Education</button>
          </div>
          <div className="entry-list">
            {(profileDraft.education || []).map((edu, idx) => (
              <div key={idx} className="entry-card compact">
                <div className="entry-card-grid three">
                  <input placeholder="Degree" value={edu.degree || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, education: c.education.map((x, i) => i === idx ? { ...x, degree: e.target.value } : x) }))} />
                  <input placeholder="Institution" value={edu.institution || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, education: c.education.map((x, i) => i === idx ? { ...x, institution: e.target.value } : x) }))} />
                  <input placeholder="Dates" value={edu.dates || ""} onChange={(e) => setProfileDraft((c) => ({ ...c, education: c.education.map((x, i) => i === idx ? { ...x, dates: e.target.value } : x) }))} />
                </div>
                <button className="icon-remove" type="button" title="Remove" onClick={() => setProfileDraft((c) => ({ ...c, education: c.education.filter((_, i) => i !== idx) }))}>×</button>
              </div>
            ))}
          </div>
        </div>
        <label className="field">
          Certifications
          <small className="field-hint">One certification per line.</small>
          <textarea value={profileDraft.certificationsText || (profileDraft.certifications || []).join("\n")} onChange={(e) => setProfileDraft((current) => ({ ...current, certificationsText: e.target.value }))} />
        </label>
        <label className="field">
          Projects
          <small className="field-hint">One project per block (blank line between). First line: project name. Then one bullet per line starting with “-”.</small>
          <textarea value={profileDraft.projectsText || formatProjects(profileDraft.projects || [])} onChange={(e) => setProfileDraft((current) => ({ ...current, projectsText: e.target.value }))} />
        </label>
      </Modal>

      <SideDrawer
        open={modals.controls}
        title="Resume Controls"
        onClose={() => closeModal("controls")}
      >
        <div className="drawer-section">
          <div className="sidebar-label">Identity</div>
          <div className="identity-group">
            <button className={`toggle-button ${identity === "outlook" ? "active" : ""}`} onClick={() => selectIdentity("outlook")}>Outlook</button>
            <button className={`toggle-button ${identity === "gmail" ? "active" : ""}`} onClick={() => selectIdentity("gmail")}>Gmail</button>
          </div>
        </div>

        <div className="drawer-section">
          <div className="sidebar-label" id="contact-fields-label">Contact</div>
          <div className="sidebar-fields" role="group" aria-labelledby="contact-fields-label">
            <label className="field-label" htmlFor="contact-location">Location</label>
            <input id="contact-location" value={contact.location} onChange={(e) => setContact((current) => ({ ...current, location: e.target.value }))} placeholder="City, ST" />
            <label className="field-label" htmlFor="contact-phone">Phone</label>
            <input id="contact-phone" value={contact.phone} onChange={(e) => setContact((current) => ({ ...current, phone: e.target.value }))} placeholder="(000) 000-0000" />
            <label className="field-label" htmlFor="contact-email">Email</label>
            <input id="contact-email" type="email" value={contact.email} onChange={(e) => setContact((current) => ({ ...current, email: e.target.value }))} placeholder="you@example.com" />
          </div>
        </div>

        <div className="drawer-section">
          <div className="sidebar-label">Output</div>
          <span className="badge">PDF controls moved to preview</span>
        </div>

        <div className="drawer-section drawer-meta">
          <span className={statusBadgeClass}>{aiStatus.ready ? "AI Ready" : "AI Error"}</span>
          <span className="badge">{charCount} chars</span>
          <span className="badge">{jdModeLabel}</span>
          {memoryCount > 0 ? <span className="badge">Memory {memoryCount}/{aiStatus.memory_limit || 2}</span> : null}
        </div>
      </SideDrawer>

      <Modal
        open={modals.trackApply}
        title="Tracker Details"
        onClose={() => closeModal("trackApply")}
        footer={(
          <>
            <button className="secondary-button" onClick={() => closeModal("trackApply")}>Cancel</button>
            <button className="primary-button" onClick={submitTrackApplication}>Save</button>
          </>
        )}
      >
        <div className="tracker-form-grid">
          <label className="field">
            Company
            <input value={companyName || latestAnalysis?.company_name || ""} onChange={(e) => setCompanyName(e.target.value)} />
          </label>
          <label className="field">
            Applied Date
            <input type="date" value={trackApplyDraft.applied_date} onChange={(e) => setTrackApplyDraft((current) => ({ ...current, applied_date: e.target.value }))} />
          </label>
          <label className="field">
            Status
            <select value={trackApplyDraft.status} onChange={(e) => setTrackApplyDraft((current) => ({ ...current, status: e.target.value }))}>
              {trackerData.statuses.map((status) => <option key={status} value={status}>{status}</option>)}
            </select>
          </label>
          <label className="field">
            Source
            <input placeholder="LinkedIn, company site, referral..." value={trackApplyDraft.source} onChange={(e) => setTrackApplyDraft((current) => ({ ...current, source: e.target.value }))} />
          </label>
        </div>
        <label className="field">
          Job URL
          <input placeholder="Optional job link" value={trackApplyDraft.job_url} onChange={(e) => setTrackApplyDraft((current) => ({ ...current, job_url: e.target.value }))} />
        </label>
        <label className="field">
          Notes
          <textarea placeholder="Optional notes" value={trackApplyDraft.notes} onChange={(e) => setTrackApplyDraft((current) => ({ ...current, notes: e.target.value }))} />
        </label>
        <div className="tracker-lock-note">
          Saved resume folders are tracked automatically. Use this to attach details like source, link, notes, or a manual status to the current saved application.
        </div>
      </Modal>

      <Modal
        open={modals.tracker}
        title="Application Tracker"
        onClose={() => closeModal("tracker")}
      >
        <div className="tracker-summary-row">
          <span className="badge">Total {trackerData.summary?.total || 0}</span>
          {trackerData.statuses.map((status) => (
            <span key={status} className="badge">{status} {trackerData.summary?.counts?.[status] || 0}</span>
          ))}
        </div>
        <div className="tracker-filters">
          <input
            className="tracker-search"
            placeholder="Search company or role"
            value={trackerFilters.query}
            onChange={(e) => setTrackerFilters((current) => ({ ...current, query: e.target.value }))}
          />
          <div className="tracker-date-filters">
            <label className="field">
              Applied From
              <input
                type="date"
                value={trackerFilters.applied_from}
                onChange={(e) => setTrackerFilters((current) => ({ ...current, applied_from: e.target.value }))}
              />
            </label>
            <label className="field">
              Applied To
              <input
                type="date"
                value={trackerFilters.applied_to}
                onChange={(e) => setTrackerFilters((current) => ({ ...current, applied_to: e.target.value }))}
              />
            </label>
            {trackerProfiles.length ? (
              <label className="field">
                Profile
                <select
                  value={trackerFilters.profile}
                  onChange={(e) => setTrackerFilters((current) => ({ ...current, profile: e.target.value }))}
                >
                  <option value="">All profiles</option>
                  {trackerProfiles.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
        </div>
        <div className="tracker-toolbar">
          <div className="identity-group tracker-view-toggle">
            <button className={`toggle-button ${trackerView === "board" ? "active" : ""}`} onClick={() => setTrackerView("board")}>Board</button>
            <button className={`toggle-button ${trackerView === "table" ? "active" : ""}`} onClick={() => setTrackerView("table")}>Table</button>
          </div>
          <button className="secondary-button" onClick={loadTracker}>Refresh</button>
        </div>
        {trackerError ? <div className="error-banner">{trackerError}</div> : null}
        {trackerLoading ? (
          <div className="blank-state">Loading tracker…</div>
        ) : trackerView === "board" ? (
          <TrackerBoard
            applications={filteredTrackerApplications}
            statuses={trackerData.statuses}
            onStatusChange={updateTrackedStatus}
            onView={setTrackerDetail}
            onOpenPdf={openTrackerPdf}
            onOpenFolder={openTrackerFolder}
          />
        ) : (
          <TrackerTable
            applications={filteredTrackerApplications}
            statuses={trackerData.statuses}
            onStatusChange={updateTrackedStatus}
            onView={setTrackerDetail}
            onOpenPdf={openTrackerPdf}
            onOpenFolder={openTrackerFolder}
          />
        )}
      </Modal>

      <Modal
        open={!!trackerDetail}
        title={trackerDetail ? `${trackerDetail.company_name} — ${trackerDetail.role_title}` : "Application"}
        onClose={() => setTrackerDetail(null)}
        footer={
          <div className="modal-actions">
            <button className="secondary-button" onClick={() => openTrackerPdf(trackerDetail)} disabled={!trackerDetail?.pdf_path}>Open PDF</button>
            <button className="secondary-button" onClick={() => openTrackerFolder(trackerDetail)} disabled={!trackerDetail?.output_dir}>Open Folder</button>
            <button className="primary-button" onClick={() => setTrackerDetail(null)}>Close</button>
          </div>
        }
      >
        {trackerDetail ? (
          <div className="jd-detail">
            <div className="jd-detail-meta">
              {trackerDetail.folder_group ? <span className="badge">Profile: {trackerDetail.folder_group}</span> : null}
              {trackerDetail.role_family ? <span className="badge">{trackerDetail.role_family}</span> : null}
              <span className="badge">Applied {formatDateShort(trackerDetail.applied_date)}</span>
              <span className="badge">{trackerDetail.status}</span>
            </div>
            <h3 className="jd-detail-heading">Job Description</h3>
            <pre className="jd-detail-text">{trackerDetail.job_description || "No job description stored for this application."}</pre>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
