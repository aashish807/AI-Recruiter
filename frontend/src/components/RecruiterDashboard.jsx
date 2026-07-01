import React, { useEffect, useMemo, useState } from 'react'
import * as pdfjsLib from 'pdfjs-dist'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

const DEMO_CANDIDATES = [
  {
    name: 'Priya Sharma',
    text: 'Priya Sharma\n6 years of backend engineering experience. Deep expertise in AWS (EC2, S3, RDS, Lambda), Docker, and microservices architecture. Led a team of 4 engineers to rebuild a legacy monolith into a serverless infrastructure. Strong skills in Python, Node.js, and PostgreSQL.',
  },
  {
    name: 'Rahul Gupta',
    text: 'Rahul Gupta\n4 years of experience in DevOps and software engineering. Kubernetes administrator and OpenShift container orchestration specialist. Active open-source contributor to Helm charts and developer tooling. Proficient in Go, Python, and bash scripting.',
  },
  {
    name: 'Ankit Verma',
    text: 'Ankit Verma\n10 years of legacy Java development experience. Expert in Spring Boot, Hibernate, and Oracle SQL databases. Worked primarily on-premises with bank transaction systems. No experience with modern cloud providers (AWS/GCP) or container orchestration tools (Docker/Kubernetes).',
  },
]

const API_BASE = 'http://localhost:8000'

async function postJson(path, payload) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  let data = null
  try {
    data = await response.json()
  } catch {
    data = null
  }

  return { response, data }
}

function scoreLocally(jdText, resumeText) {
  const jdTokens = new Set(
    jdText
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(Boolean),
  )

  const resumeTokens = resumeText
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(Boolean)

  const hits = [...new Set(resumeTokens)].filter((token) => jdTokens.has(token))
  const score = Math.min(98, 32 + hits.length * 11 + Math.min(20, resumeTokens.length / 4))
  const strengths = hits.slice(0, 5).map((hit) => `Matches JD keyword: ${hit}`)
  const risks = []

  if (!jdText.trim()) risks.push('No JD ingested yet; using local heuristic ranking')
  if (!resumeTokens.some((token) => ['aws', 'cloud', 'docker', 'kubernetes', 'leadership'].includes(token))) {
    risks.push('Limited evidence of cloud/container leadership')
  }
  if (strengths.length === 0) risks.push('Few direct overlap signals with JD requirements')

  return {
    score: Math.round(score),
    score_band: score >= 75 ? 'strong' : score >= 55 ? 'moderate' : 'needs review',
    strengths: strengths.length ? strengths : ['Resume parsed successfully'],
    risks,
    recommendation: score >= 78 ? 'Strong match' : score >= 60 ? 'Consider for interview' : 'Lower priority',
    profile: {
      summary: resumeText,
    },
    jd_requirements: {
      skills: [],
      seniority: '',
      traits: [],
      culture: '',
    },
    match_breakdown: {
      jd_skills: [],
      candidate_skills: [],
      overlap: hits,
      experience_years: null,
      project_count: 0,
    },
    match_factors: {
      matched_tokens: hits,
      jd_skill_count: jdTokens.size,
      candidate_skill_count: resumeTokens.length,
      skill_overlap_count: hits.length,
      skill_overlap_ratio: jdTokens.size ? Math.round((hits.length / jdTokens.size) * 100) / 100 : 0,
      structured_score: Math.round(score),
      experience_years: null,
      project_count: 0,
      contribution_weights: {
        skill_overlap: 40,
        experience: 25,
        projects: 10,
      },
    },
    summary: {
      jd_focus: '',
      candidate_focus: [],
    },
  }
}

const RadialScoreGauge = ({ score }) => {
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (score / 100) * circumference
  
  let strokeColor = 'var(--danger)'
  if (score >= 75) strokeColor = 'var(--emerald)'
  else if (score >= 55) strokeColor = 'var(--amber)'

  return (
    <div className="radial-gauge-container">
      <svg className="radial-gauge" width="90" height="90" viewBox="0 0 100 100">
        <circle
          className="radial-gauge-bg"
          cx="50"
          cy="50"
          r={radius}
          stroke="rgba(255, 255, 255, 0.05)"
          strokeWidth="8"
          fill="transparent"
        />
        <circle
          className="radial-gauge-value"
          cx="50"
          cy="50"
          r={radius}
          stroke={strokeColor}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.4, 0, 0.2, 1)' }}
        />
        <text
          x="50%"
          y="52%"
          dominantBaseline="central"
          textAnchor="middle"
          fill="var(--text)"
          className="radial-gauge-text"
          style={{ fontSize: '20px', fontWeight: '800' }}
        >
          {score}%
        </text>
      </svg>
    </div>
  )
}

export default function RecruiterDashboard() {
  const [jdText, setJdText] = useState('')
  const [isJdUploaded, setIsJdUploaded] = useState(false)
  const [isRanking, setIsRanking] = useState(false)
  const [isResumeParsing, setIsResumeParsing] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const [resumes, setResumes] = useState([])
  const [uploadedResumeFiles, setUploadedResumeFiles] = useState([])
  const [statusMessage, setStatusMessage] = useState('Upload a JD and add resumes to begin.')
  const [backendMode, setBackendMode] = useState('live')
  const [expandedCandidateIndex, setExpandedCandidateIndex] = useState(-1)
  const [isDragOver, setIsDragOver] = useState(false)
  
  // Manual candidate states
  const [isManualModalOpen, setIsManualModalOpen] = useState(false)
  const [newCandidateName, setNewCandidateName] = useState('')
  const [newCandidateText, setNewCandidateText] = useState('')

  // Report tabs
  const [activeTab, setActiveTab] = useState('overview')

  const selectedBreakdown = selectedCandidate?.match_breakdown ?? {}
  const selectedJDRequirements = selectedCandidate?.jd_requirements ?? {}
  const selectedFactors = selectedCandidate?.match_factors ?? {}

  const pipelineStats = useMemo(() => {
    const avgScore = candidates.length
      ? Math.round(candidates.reduce((sum, c) => sum + c.score, 0) / candidates.length)
      : 0
    return {
      total: resumes.length,
      ranked: candidates.length,
      avgScore,
    }
  }, [candidates, resumes.length])

  useEffect(() => {
    if (!candidates.length) {
      setExpandedCandidateIndex(-1)
      return
    }

    const selectedIndex = candidates.findIndex((c) => c.name === selectedCandidate?.name)
    if (selectedIndex >= 0) {
      setExpandedCandidateIndex(selectedIndex)
    }
  }, [candidates, selectedCandidate?.name])

  const handleJdSubmit = async (event) => {
    event.preventDefault()
    if (!jdText.trim()) return

    try {
      const { response, data } = await postJson('/upload-jd', { jd_text: jdText })

      if (response.ok) {
        setBackendMode('live')
        setIsJdUploaded(true)
        setStatusMessage(data?.message ?? 'Job Description ingested successfully.')
        return
      }

      setBackendMode('fallback')
      setIsJdUploaded(true)
      setStatusMessage(data?.detail ?? 'JD saved locally (Backend response issue).')
    } catch (error) {
      console.error('Error uploading JD:', error)
      setBackendMode('fallback')
      setIsJdUploaded(true)
      setStatusMessage('Backend unavailable; JD kept locally for offline matching.')
    }
  }

  const handleDownloadReport = async (candidate) => {
    if (!candidate || !candidate.id) {
      setStatusMessage("No candidate database reference found for report.")
      return
    }
    setStatusMessage(`Compiling report for ${candidate.name}...`)
    try {
      const response = await fetch(`${API_BASE}/candidates/${candidate.id}/report?query_text=${encodeURIComponent(jdText)}`)
      if (!response.ok) throw new Error("Report download failed")
      
      const blob = await response.blob()
      const downloadAnchor = document.createElement('a')
      downloadAnchor.href = window.URL.createObjectURL(blob)
      downloadAnchor.download = `recruiter_report_${candidate.name.replace(/\s+/g, '_').toLowerCase()}.md`

      document.body.appendChild(downloadAnchor)
      downloadAnchor.click()
      downloadAnchor.remove()
      setStatusMessage(`Report for ${candidate.name} downloaded.`)
    } catch (error) {
      console.error(error)
      setStatusMessage("Report compile failed.")
    }
  }

  const handleRankCandidates = async () => {
    if (resumes.length === 0) {
      setStatusMessage('Please add candidates first.')
      return
    }
    setIsRanking(true)
    setStatusMessage('Querying Hybrid Blended scoring systems...')
    
    try {
      const response = await fetch(`${API_BASE}/rank?query_text=${encodeURIComponent(jdText)}`)
      if (!response.ok) throw new Error("Ranking failed")
      const rankedData = await response.json()
      
      const nextCandidates = rankedData.map((item) => {
        const evalData = item.evaluation || {}
        return {
          id: item.id,
          name: item.name,
          score: item.score,
          score_band: item.score_band,
          strengths: evalData.strengths || [],
          risks: evalData.weaknesses || [],
          recommendation: evalData.why_selected || 'Review manually',
          profile: { summary: evalData.overall_summary || '' },
          jd_requirements: {
            skills: evalData.matched_skills || [],
            seniority: evalData.missing_skills || [],
            traits: evalData.behavioral_insights || [],
            culture: evalData.recruiter_explanation || ''
          },
          match_breakdown: item.aspect_breakdown || {},
          match_factors: {
            matched_tokens: evalData.matched_skills || [],
            jd_skill_count: (evalData.matched_skills?.length || 0) + (evalData.missing_skills?.length || 0),
            candidate_skill_count: evalData.matched_skills?.length || 0,
            skill_overlap_count: evalData.matched_skills?.length || 0,
            skill_overlap_ratio: 1.0,
            structured_score: item.score,
            experience_years: 0,
            project_count: 0
          },
          summary: {
            jd_focus: evalData.recruiter_explanation || '',
            candidate_focus: evalData.overall_summary || ''
          }
        }
      })
      
      setCandidates(nextCandidates)
      setSelectedCandidate(nextCandidates[0] || null)
      setStatusMessage('Ranking execution finished successfully.')
    } catch (error) {
      console.error(error)
      setStatusMessage('Semantic matching failed. Falling back to local heuristic checks.')
      setBackendMode('fallback')
      
      // Fallback local heuristic ranking
      const nextCandidates = resumes.map((resume) => ({
        name: resume.name,
        ...scoreLocally(jdText, resume.text)
      }))
      nextCandidates.sort((a, b) => b.score - a.score)
      setCandidates(nextCandidates)
      setSelectedCandidate(nextCandidates[0] || null)
    } finally {
      setIsRanking(false)
    }
  }

  const extractTextFromPdf = async (file) => {
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
    const pages = []

    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
      const page = await pdf.getPage(pageNumber)
      const content = await page.getTextContent()
      const pageText = content.items.map((item) => item.str).join(' ')
      pages.push(pageText)
    }

    return pages.join('\n')
  }

  const extractTextFromFile = async (file) => {
    if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
      return extractTextFromPdf(file)
    }
    return file.text()
  }

  const processFiles = async (files) => {
    if (files.length === 0) return

    setIsResumeParsing(true)
    setStatusMessage(`Uploading and analyzing ${files.length} resume file${files.length > 1 ? 's' : ''}...`)

    try {
      const parsedCandidates = []
      const uploadedFiles = []

      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        
        const response = await fetch(`${API_BASE}/upload_resume`, {
          method: 'POST',
          body: formData
        })
        
        if (response.ok) {
          const data = await response.json()
          uploadedFiles.push({ name: file.name, size: file.size })
          parsedCandidates.push({
            id: data.id,
            name: data.name || file.name.replace(/\.[^/.]+$/, ''),
            text: data.raw_resume_text || '',
          })
        } else {
          // Local fallback extraction if backend fails
          const text = await extractTextFromFile(file)
          const fallbackName = file.name.replace(/\.[^/.]+$/, '')
          uploadedFiles.push({ name: file.name, size: file.size })
          parsedCandidates.push({ name: fallbackName, text })
        }
      }

      setResumes((current) => [...current, ...parsedCandidates])
      setUploadedResumeFiles((current) => [...current, ...uploadedFiles])
      setStatusMessage(`Ingested ${parsedCandidates.length} resume${parsedCandidates.length > 1 ? 's' : ''} successfully.`)
    } catch (error) {
      console.error('Error parsing resume file:', error)
      setStatusMessage('Failed to upload one or more resume files.')
    } finally {
      setIsResumeParsing(false)
    }
  }

  const handleResumeUpload = (event) => {
    const files = Array.from(event.target.files ?? [])
    processFiles(files)
    event.target.value = ''
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragOver(false)
    const files = Array.from(e.dataTransfer.files ?? [])
    processFiles(files)
  }

  const handleManualAddSubmit = async (e) => {
    e.preventDefault()
    if (!newCandidateName.trim() || !newCandidateText.trim()) return

    const file = new File([newCandidateText.trim()], `${newCandidateName.trim()}.txt`, { type: 'text/plain' })
    const formData = new FormData()
    formData.append('file', file)
    
    setIsResumeParsing(true)
    setStatusMessage(`Ingesting candidate ${newCandidateName.trim()}...`)
    
    try {
      const response = await fetch(`${API_BASE}/upload_resume`, {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        const data = await response.json()
        const newCandidate = {
          id: data.id,
          name: data.name,
          text: data.raw_resume_text,
        }
        setResumes((current) => [...current, newCandidate])
        setUploadedResumeFiles((current) => [...current, { name: `${data.name}.txt`, size: data.raw_resume_text.length }])
        setStatusMessage(`Added candidate "${newCandidate.name}" manually and saved to database.`)
      } else {
        const newCandidate = { name: newCandidateName.trim(), text: newCandidateText.trim() }
        setResumes((current) => [...current, newCandidate])
        setUploadedResumeFiles((current) => [...current, { name: `${newCandidate.name}.txt`, size: newCandidate.text.length }])
        setStatusMessage(`Added candidate "${newCandidate.name}" manually (offline fallback active).`)
      }
    } catch (err) {
      console.error(err)
      setStatusMessage("Manual ingestion failed.")
    } finally {
      setIsResumeParsing(false)
      setNewCandidateName('')
      setNewCandidateText('')
      setIsManualModalOpen(false)
    }
  }

  const loadDemoData = async () => {
    setIsResumeParsing(true)
    setStatusMessage('Loading and ingesting 3 demo resumes...')
    const uploadedFiles = []
    const parsedCandidates = []
    
    for (const c of DEMO_CANDIDATES) {
      try {
        const file = new File([c.text], `${c.name}.txt`, { type: 'text/plain' })
        const formData = new FormData()
        formData.append('file', file)
        
        const response = await fetch(`${API_BASE}/upload_resume`, {
          method: 'POST',
          body: formData
        })
        
        if (response.ok) {
          const data = await response.json()
          uploadedFiles.push({ name: `${data.name}.txt`, size: data.raw_resume_text.length })
          parsedCandidates.push({
            id: data.id,
            name: data.name,
            text: data.raw_resume_text,
          })
        } else {
          uploadedFiles.push({ name: `${c.name}.txt`, size: c.text.length })
          parsedCandidates.push(c)
        }
      } catch (err) {
        console.error(`Failed to ingest demo resume: ${c.name}`, err)
        uploadedFiles.push({ name: `${c.name}.txt`, size: c.text.length })
        parsedCandidates.push(c)
      }
    }
    setResumes(parsedCandidates)
    setUploadedResumeFiles(uploadedFiles)
    setIsResumeParsing(false)
    setStatusMessage('Loaded 3 demo resumes. Click "Execute Evaluation Match" when ready.')
  }

  const handleReset = () => {
    setJdText('')
    setIsJdUploaded(false)
    setCandidates([])
    setSelectedCandidate(null)
    setResumes([])
    setUploadedResumeFiles([])
    setStatusMessage('Dashboard cleared. Enter a new Job Description to start.')
  }

  const handleExport = async (format = 'xlsx') => {
    if (candidates.length === 0) return
    setStatusMessage(`Compiling ranked candidates spreadsheet (${format.toUpperCase()})...`)
    try {
      const response = await fetch(`${API_BASE}/candidates/export?format=${format}&query_text=${encodeURIComponent(jdText)}`)
      if (!response.ok) throw new Error("Export failed")
      
      const blob = await response.blob()
      const downloadAnchor = document.createElement('a')
      downloadAnchor.href = window.URL.createObjectURL(blob)
      downloadAnchor.download = `candidate_rankings.${format}`
      document.body.appendChild(downloadAnchor)
      downloadAnchor.click()
      downloadAnchor.remove()
      setStatusMessage(`Ranked candidate spreadsheet downloaded successfully.`)
    } catch (error) {
      console.error(error)
      setStatusMessage("Export failed. JSON backup download active.")
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(candidates, null, 2))
      const downloadAnchor = document.createElement('a')
      downloadAnchor.setAttribute("href", dataStr)
      downloadAnchor.setAttribute("download", "recruiter_evaluation_report.json")
      document.body.appendChild(downloadAnchor)
      downloadAnchor.click()
      downloadAnchor.remove()
    }
  }

  const removeCandidate = (index) => {
    setResumes((current) => current.filter((_, i) => i !== index))
    setUploadedResumeFiles((current) => current.filter((_, i) => i !== index))
    setExpandedCandidateIndex((current) => {
      if (current === index) return -1
      if (current > index) return current - 1
      return current
    })
  }

  const updateCandidate = (index, field, value) => {
    setResumes((current) => current.map((c, i) => (i === index ? { ...c, [field]: value } : c)))
  }


  const getPreviewText = (text) => {
    const normalized = text.replace(/\s+/g, ' ').trim()
    if (normalized.length <= 110) return normalized
    return `${normalized.slice(0, 110).trim()}…`
  }

  return (
    <div className="dashboard">
      <div className="dashboard-shell">
        <header className="topbar">
          <div className="header-branding">
            <div className="brand-logo-container">
              <svg className="brand-logo" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <h1 className="title">RecruiterGPT</h1>
              <p className="subtitle">AI-assisted resume evaluator and explainable candidate match report cockpit.</p>
            </div>
          </div>
          <div className="topbar-actions">
            <div className="pill glow">Bias-aware parsing active</div>
            {(isJdUploaded || resumes.length > 0) && (
              <button className="btn btn-secondary flex-btn reset-btn" type="button" onClick={handleReset}>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                </svg>
                Reset
              </button>
            )}
          </div>
        </header>

        <div className="pipeline-summary-bar">
          <div className="metric-row">
            <div className="metric-card">
              <span className="metric-label">Resumes Queued</span>
              <span className="metric-val">{pipelineStats.total}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Ranked Candidates</span>
              <span className="metric-val">{pipelineStats.ranked}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Avg. Match Score</span>
              <span className="metric-val">{pipelineStats.avgScore}%</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">System Mode</span>
              <span className="metric-val mode-val">{backendMode === 'live' ? '⚡ Live Engine' : '🛰️ Fallback'}</span>
            </div>
          </div>
          <div className="status-toast">
            <span className="status-indicator"></span>
            <span className="status-text">{statusMessage}</span>
          </div>
        </div>

        <div className="dashboard-grid">
          {/* COLUMN 1: INGESTION STACK */}
          <div className="grid-column column-inputs">
            <section className="panel">
              <div className="panel-header">
                <span className="panel-step">01</span>
                <h2>Job Description</h2>
              </div>
              <form onSubmit={handleJdSubmit} className="stack">
                <div className="textarea-wrapper">
                  <label className="panel-label">Role requirements & tech stack</label>
                  <textarea
                    className="textarea"
                    value={jdText}
                    onChange={(event) => setJdText(event.target.value)}
                    placeholder="Paste the Job Description (requirements, technology stack, experience needed)..."
                  />
                </div>
                <button className={`btn ${isJdUploaded ? 'btn-success-gradient' : 'btn-primary'}`} type="submit" disabled={!jdText.trim()}>
                  {isJdUploaded ? '✓ JD Ingested' : 'Analyze Requirements'}
                </button>
              </form>
            </section>

            <section className="panel">
              <div className="panel-header">
                <span className="panel-step">02</span>
                <h2>Candidates Batch</h2>
              </div>
              <div className="stack">
                <div 
                  className={`upload-card ${isDragOver ? 'dragover' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <div className="upload-card-header">
                    <div>
                      <div className="upload-eyebrow">Document Intake</div>
                      <h3 className="upload-title">Drop Resumes</h3>
                      <p className="upload-copy">Supports PDF or plain TXT files.</p>
                    </div>
                    <div className="upload-badge">{isResumeParsing ? 'Extracting…' : 'Ready'}</div>
                  </div>

                  <div className="upload-dropzone">
                    <input
                      id="resume-upload"
                      className="hidden-file-input"
                      type="file"
                      accept=".pdf,.txt,application/pdf,text/plain"
                      multiple
                      onChange={handleResumeUpload}
                      disabled={isResumeParsing}
                    />
                    <label htmlFor="resume-upload" className="upload-dropzone-label">
                      <svg className="upload-icon" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                      </svg>
                      <span className="upload-dropzone-title">Upload Resumes</span>
                      <span className="upload-dropzone-subtitle">or drag files directly here</span>
                    </label>
                  </div>
                </div>

                <div className="batch-actions-row">
                  <button className="btn btn-secondary flex-grow" type="button" onClick={() => setIsManualModalOpen(true)}>
                    + Manual Candidate
                  </button>
                  {resumes.length === 0 && (
                    <button className="btn btn-secondary demo-btn" type="button" onClick={loadDemoData}>
                      ⚡ Load Demo
                    </button>
                  )}
                </div>

                {resumes.length > 0 && (
                  <div className="divider-glow" />
                )}

                <div className="candidate-list scrollable-list-small">
                  {resumes.map((candidate, index) => (
                    <div key={`${candidate.name}-${index}`} className="candidate-profile-card">
                      <div className="candidate-profile-header">
                        <div className="candidate-header-copy">
                          <div className="candidate-profile-eyebrow">Candidate #{index + 1}</div>
                          <div className="candidate-name-readonly">
                            {candidate.name}
                          </div>
                          <div className="candidate-header-subcopy">
                            {getPreviewText(candidate.text)}
                          </div>
                        </div>
                        <div className="candidate-header-actions">
                          <button
                            className="mini-action-btn"
                            type="button"
                            onClick={() => setExpandedCandidateIndex((current) => (current === index ? -1 : index))}
                            title="Edit candidate details"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                            </svg>
                          </button>
                          <button 
                            className="mini-action-btn remove" 
                            type="button" 
                            onClick={() => removeCandidate(index)}
                            title="Remove candidate"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                          </button>
                        </div>
                      </div>

                      {expandedCandidateIndex === index && (
                        <div className="candidate-profile-expanded">
                          <textarea
                            className="candidate-preview"
                            value={candidate.text}
                            onChange={(event) => updateCandidate(index, 'text', event.target.value)}
                            placeholder="Candidate resume details..."
                            aria-label={`Candidate ${index + 1} resume text`}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <button 
                  className="btn btn-primary-gradient evaluate-btn" 
                  type="button" 
                  onClick={handleRankCandidates} 
                  disabled={isRanking || !isJdUploaded || resumes.length === 0}
                >
                  {isRanking ? 'Semantic Evaluator Active...' : 'Execute Evaluation Match'}
                </button>
              </div>
            </section>
          </div>

          {/* COLUMN 2: EVALUATION PIPELINE */}
          <div className="grid-column column-pipeline">
            <section className="panel full-height">
              <div className="panel-header">
                <span className="panel-step">03</span>
                <h2>Evaluation Pipeline</h2>
                {candidates.length > 0 && (
                  <button className="mini-action-btn export-btn" onClick={() => handleExport('xlsx')} title="Download Results (Excel)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                    </svg>
                  </button>
                )}
              </div>
              
              {candidates.length === 0 ? (
                <div className="callout empty-pipeline-state">
                  <svg className="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                  </svg>
                  <strong>No ranked pipeline generated.</strong>
                  <p className="muted">Upload role JD, stack candidate files, then execute semantic matching above to score.</p>
                </div>
              ) : (
                <div className="results-list scroll">
                  {candidates.map((candidate, index) => {
                    const selected = selectedCandidate?.name === candidate.name
                    const band = candidate.score_band ?? 'moderate'

                    return (
                      <div
                        key={`${candidate.name}-${index}`}
                        className={`candidate-card-v2 ${selected ? 'selected' : ''} band-${band}`}
                        onClick={() => setSelectedCandidate(candidate)}
                      >
                        <div className="card-left">
                          <span className="rank-badge">Rank #{index + 1}</span>
                          <strong className="candidate-title-name">{candidate.name}</strong>
                          <span className="candidate-card-recommendation">{candidate.recommendation}</span>
                        </div>
                        <div className="card-right">
                          <div className={`score-badge ${band}`}>
                            {candidate.score}%
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>
          </div>

          {/* COLUMN 3: EXPLAINABILITY REPORT */}
          <div className="grid-column column-report">
            <section className="panel full-height">
              <div className="panel-header animate-fade-in">

                <span className="panel-step">04</span>
                <h2>Explainability Report</h2>
                {selectedCandidate && selectedCandidate.id && (
                  <button 
                    className="mini-action-btn download-report-btn" 
                    onClick={() => handleDownloadReport(selectedCandidate)} 
                    title="Download Recruiter MD Report"
                    style={{ marginLeft: 'auto' }}
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                    </svg>
                  </button>
                )}
              </div>

              
              {selectedCandidate ? (
                <div className="stack report-details">
                  
                  {/* Gauge & Main Info Row */}
                  <div className="report-main-hero">
                    <RadialScoreGauge score={selectedCandidate.score} />
                    <div className="hero-text-block">
                      <span className="hero-eyebrow">Match Status</span>
                      <h3 className="hero-match-band band-text">{selectedCandidate.score_band?.toUpperCase() ?? 'MODERATE'}</h3>
                      <p className="hero-recommendation">{selectedCandidate.recommendation}</p>
                    </div>
                  </div>

                  {/* Tabs Selector */}
                  <div className="report-tab-selector">
                    <button 
                      className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
                      type="button"
                      onClick={() => setActiveTab('overview')}
                    >
                      Fit Overview
                    </button>
                    <button 
                      className={`tab-btn ${activeTab === 'skills' ? 'active' : ''}`}
                      type="button"
                      onClick={() => setActiveTab('skills')}
                    >
                      Skill Breakdown
                    </button>
                    <button 
                      className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
                      type="button"
                      onClick={() => setActiveTab('profile')}
                    >
                      Bias-Free Profile
                    </button>
                  </div>

                  <div className="report-tab-content scroll">
                    
                    {/* TAB 1: OVERVIEW */}
                    {activeTab === 'overview' && (
                      <div className="tab-pane stack">
                        <div>
                          <div className="report-section-header">
                            <span className="indicator-dot green"></span>
                            <h4>Verified Fit Signals</h4>
                          </div>
                          <ul className="fit-signals-list positive">
                            {(selectedCandidate.strengths ?? []).map((item, index) => (
                              <li key={`${item}-${index}`}>
                                <svg className="bullet-icon check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                  <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        {selectedCandidate.risks?.length > 0 && (
                          <div>
                            <div className="report-section-header">
                              <span className="indicator-dot red"></span>
                              <h4>Gap / Risk Analysis</h4>
                            </div>
                            <ul className="fit-signals-list negative">
                              {(selectedCandidate.risks ?? []).map((item, index) => (
                                <li key={`${item}-${index}`}>
                                  <svg className="bullet-icon cross" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                  </svg>
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <div className="fit-summary-note">
                          <span className="note-eyebrow">JD Seniority & Alignment</span>
                          <div className="note-details">
                            <div className="detail-item"><strong>Seniority:</strong> {selectedJDRequirements.seniority || 'No specific requirements extracted'}</div>
                            <div className="detail-item"><strong>Traits Requested:</strong> {(selectedJDRequirements.traits ?? []).join(', ') || 'n/a'}</div>
                            <div className="detail-item"><strong>Cultural Focus:</strong> {selectedJDRequirements.culture || 'n/a'}</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* TAB 2: SKILL BREAKDOWN */}
                    {activeTab === 'skills' && (
                      <div className="tab-pane stack">
                        <div className="metrics-bars-container">
                          <h4>Match Factors</h4>
                          
                          <div className="match-factor-bar-item">
                            <div className="factor-labels">
                              <span className="factor-name">Skill Overlap Ratio</span>
                              <span className="factor-val">
                                {selectedFactors.skill_overlap_count ?? 0} / {selectedFactors.jd_skill_count ?? 0}
                              </span>
                            </div>
                            <div className="factor-progress-bg">
                              <div 
                                className="factor-progress-value teal" 
                                style={{ width: `${Math.round((selectedFactors.skill_overlap_ratio ?? 0) * 100)}%` }}
                              ></div>
                            </div>
                          </div>

                          <div className="match-factor-bar-item">
                            <div className="factor-labels">
                              <span className="factor-name">Experience Years fit</span>
                              <span className="factor-val">{selectedBreakdown.experience_years ?? 'N/A'} yrs</span>
                            </div>
                            <div className="factor-progress-bg">
                              <div 
                                className="factor-progress-value cyan" 
                                style={{ width: `${selectedBreakdown.experience_years ? Math.min(100, (selectedBreakdown.experience_years / 10) * 100) : 0}%` }}
                              ></div>
                            </div>
                          </div>

                          <div className="match-factor-bar-item">
                            <div className="factor-labels">
                              <span className="factor-name">Demonstrated Projects</span>
                              <span className="factor-val">{selectedBreakdown.project_count ?? 0} project(s)</span>
                            </div>
                            <div className="factor-progress-bg">
                              <div 
                                className="factor-progress-value emerald" 
                                style={{ width: `${Math.min(100, (selectedBreakdown.project_count ?? 0) * 20)}%` }}
                              ></div>
                            </div>
                          </div>
                        </div>

                        <div className="skills-compare-container">
                          <h4>Skill Overlap Matrix</h4>
                          <div className="comparison-box">
                            <span className="sub-title">Extracted JD Skills</span>
                            <div className="chip-row">
                              {(selectedBreakdown.jd_skills ?? []).length ? (
                                selectedBreakdown.jd_skills.map((item) => (
                                  <span key={item} className="chip chip-muted">{item}</span>
                                ))
                              ) : (
                                <span className="empty-text">None extracted from Job Description</span>
                              )}
                            </div>

                            <span className="sub-title margin-top">Candidate Resume Tech Stack</span>
                            <div className="chip-row">
                              {(selectedBreakdown.candidate_skills ?? []).length ? (
                                selectedBreakdown.candidate_skills.map((item) => (
                                  <span key={item} className="chip chip-cyan">{item}</span>
                                ))
                              ) : (
                                <span className="empty-text">None extracted from Resume</span>
                              )}
                            </div>

                            <span className="sub-title margin-top">Matched Skill Intersections</span>
                            <div className="chip-row">
                              {(selectedBreakdown.overlap ?? []).length ? (
                                selectedBreakdown.overlap.map((item) => (
                                  <span key={item} className="chip chip-teal">{item}</span>
                                ))
                              ) : (
                                <span className="empty-text">No direct keyword intersections matched</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* TAB 3: PROFILE */}
                    {activeTab === 'profile' && (
                      <div className="tab-pane stack">
                        <div className="bias-free-callout">
                          <strong>Anonymized Profile</strong>
                          <p className="muted">This format hides structural bias indicators like school names, candidate locations, gender markers, or age metrics, evaluating only skill competencies.</p>
                        </div>
                        <div className="code-block-wrapper">
                          <pre className="json-display">
                            {JSON.stringify(selectedCandidate.profile, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="callout empty-report-state">
                  <svg className="empty-state-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </svg>
                  <strong>No candidate selected.</strong>
                  <p className="muted">Evaluate the candidates queue, then select an individual candidate to populate the explainable reasoning audit trail.</p>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>

      {/* MANUAL INTENSION MODAL DIALOG */}
      {isManualModalOpen && (
        <div className="modal-overlay" onClick={() => setIsManualModalOpen(false)}>
          <div className="modal-drawer glass" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Candidate Manually</h3>
              <button className="close-btn" onClick={() => setIsManualModalOpen(false)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <form onSubmit={handleManualAddSubmit} className="modal-form stack">
              <div>
                <label className="panel-label">Candidate Name</label>
                <input
                  type="text"
                  required
                  className="input"
                  value={newCandidateName}
                  onChange={(e) => setNewCandidateName(e.target.value)}
                  placeholder="e.g. Sarah Jenkins"
                />
              </div>
              <div className="textarea-wrapper">
                <label className="panel-label">Resume Text Content</label>
                <textarea
                  required
                  className="textarea candidate-preview"
                  value={newCandidateText}
                  onChange={(e) => setNewCandidateText(e.target.value)}
                  placeholder="Paste or write the candidate's skills, qualifications, work experiences..."
                />
              </div>
              <div className="modal-actions-row">
                <button type="button" className="btn btn-secondary" onClick={() => setIsManualModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!newCandidateName.trim() || !newCandidateText.trim()}>
                  Add Candidate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
