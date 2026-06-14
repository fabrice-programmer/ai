/* ===================================================================
   HumanWriteAI — Complete Frontend Application Logic
   =================================================================== */

// ===================================================================
// Configuration
// ===================================================================
const API_BASE = 'http://127.0.0.1:5000/api';

// ===================================================================
// State
// ===================================================================
let currentUser = null;
let selectedFile = null;

// Load session from localStorage on page load
(function initSession() {
    const stored = localStorage.getItem('humanwriteai_user');
    if (stored) {
        try {
            currentUser = JSON.parse(stored);
            updateUIForAuth();
        } catch {
            localStorage.removeItem('humanwriteai_user');
        }
    }
})();

// ===================================================================
// Utility Functions
// ===================================================================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    const size = (bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1);
    return `${size} ${units[i]}`;
}

function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function apiUrl(path) {
    return `${API_BASE}${path}`;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ===================================================================
// Toast Notification System
// ===================================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 250);
    }, 4000);
}

// ===================================================================
// Navigation & Page System
// ===================================================================

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active-page'));
    const target = document.getElementById(`page-${pageId}`);
    if (target) target.classList.add('active-page');

    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.page === pageId);
    });

    document.getElementById('navLinks').classList.remove('mobile-open');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (pageId === 'dashboard' && currentUser) loadDashboard();
}

function toggleMobileMenu() {
    document.getElementById('navLinks').classList.toggle('mobile-open');
}

document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        const page = link.dataset.page;
        if (page) showPage(page);
    });
});

document.getElementById('logoLink').addEventListener('click', e => {
    e.preventDefault();
    showPage('home');
});

// ===================================================================
// Auth State UI Updates
// ===================================================================

function updateUIForAuth() {
    const isLoggedIn = !!currentUser;
    document.getElementById('btnLogin').style.display = isLoggedIn ? 'none' : 'inline-flex';
    document.getElementById('btnRegister').style.display = isLoggedIn ? 'none' : 'inline-flex';
    document.getElementById('btnLogout').style.display = isLoggedIn ? 'inline-flex' : 'none';
    document.getElementById('navDashboard').style.display = isLoggedIn ? '' : 'none';
    document.getElementById('navAnalyze').style.display = isLoggedIn ? '' : 'none';
    document.getElementById('navUpload').style.display = isLoggedIn ? '' : 'none';

    if (!isLoggedIn) {
        const activePage = document.querySelector('.page.active-page');
        if (activePage) {
            const id = activePage.id.replace('page-', '');
            if (['dashboard'].includes(id)) showPage('home');
        }
    }
}

// ===================================================================
// Authentication
// ===================================================================

async function handleRegister(e) {
    e.preventDefault();
    clearErrors('register');

    const username = document.getElementById('regUsername').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('regConfirm').value;

    if (password !== confirm) {
        showError('register', 'Passwords do not match.');
        return;
    }

    const btn = document.getElementById('registerBtn');
    setLoading(btn, true);

    try {
        const res = await fetch(apiUrl('/auth/register'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
        });

        const data = await res.json();

        if (!res.ok) {
            const msg = data.details
                ? Object.values(data.details).flat().join('. ')
                : data.error || 'Registration failed.';
            showError('register', msg);
            return;
        }

        currentUser = data.user;
        localStorage.setItem('humanwriteai_user', JSON.stringify(currentUser));
        updateUIForAuth();
        showPage('home');
        showToast('Account created successfully! Welcome aboard.', 'success');
    } catch (err) {
        showError('register', 'Could not connect to the server. Is the backend running?');
    } finally {
        setLoading(btn, false);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    clearErrors('login');

    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    const btn = document.getElementById('loginBtn');
    setLoading(btn, true);

    try {
        const res = await fetch(apiUrl('/auth/login'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        const data = await res.json();

        if (!res.ok) {
            showError('login', data.error || 'Invalid credentials.');
            return;
        }

        currentUser = data.user;
        localStorage.setItem('humanwriteai_user', JSON.stringify(currentUser));
        updateUIForAuth();
        showPage('home');
        showToast('Signed in successfully!', 'success');
    } catch (err) {
        showError('login', 'Could not connect to the server. Is the backend running?');
    } finally {
        setLoading(btn, false);
    }
}

function logout() {
    currentUser = null;
    selectedFile = null;
    localStorage.removeItem('humanwriteai_user');
    updateUIForAuth();
    showPage('home');
    showToast('Signed out.', 'info');
}

// ===================================================================
// Form Helpers
// ===================================================================

function showError(formName, message) {
    const el = document.getElementById(`${formName}Error`);
    if (el) {
        el.textContent = message;
        el.classList.add('visible');
    }
}

function clearErrors(formName) {
    const el = document.getElementById(`${formName}Error`);
    if (el) {
        el.textContent = '';
        el.classList.remove('visible');
    }
}

function setLoading(btn, isLoading) {
    const text = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.btn-spinner');
    if (text) text.style.display = isLoading ? 'none' : '';
    if (spinner) spinner.style.display = isLoading ? '' : 'none';
    btn.disabled = isLoading;
}

// ===================================================================
// Text Analysis
// ===================================================================

document.getElementById('inputText').addEventListener('input', function () {
    document.getElementById('charCount').textContent = `${this.value.length} characters`;
});

async function handleTextAnalysis(e) {
    e.preventDefault();
    clearErrors('analyze');

    const text = document.getElementById('inputText').value.trim();
    if (!text) {
        showError('analyze', 'Please enter some text to analyze.');
        return;
    }

    const btn = document.getElementById('analyzeBtn');
    setLoading(btn, true);

    try {
        const res = await fetch(apiUrl('/predict'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        const data = await res.json();

        if (!res.ok) {
            showError('analyze', data.error || 'Analysis failed.');
            return;
        }

        displayTextResults(data);
    } catch (err) {
        showError('analyze', 'Could not connect to the server. Is the backend running?');
    } finally {
        setLoading(btn, false);
    }
}

function displayTextResults(data) {
    const aiScore = data.ai_score != null ? data.ai_score : 0;
    const humanScore = data.human_score != null ? data.human_score : 0;
    const confidence = data.confidence != null ? data.confidence : 0;

    const aiPct = Math.round(aiScore * 100);
    const humanPct = Math.round(humanScore * 100);
    const confPct = Math.round(confidence * 100);

    setTimeout(() => {
        document.getElementById('textHumanBar').style.width = `${humanPct}%`;
        document.getElementById('textHumanVal').textContent = `${humanPct}%`;
        document.getElementById('textAiBar').style.width = `${aiPct}%`;
        document.getElementById('textAiVal').textContent = `${aiPct}%`;
    }, 100);

    let confLabel = 'Low';
    if (confidence >= 0.8) confLabel = 'High';
    else if (confidence >= 0.5) confLabel = 'Medium';

    document.getElementById('textConfidence').querySelector('strong').textContent = confLabel;

    const verdict = document.getElementById('textVerdict');
    if (aiScore > 0.7) {
        verdict.textContent = '⚠️ Likely AI Generated';
        verdict.className = 'result-verdict ai';
    } else if (humanScore > 0.7) {
        verdict.textContent = '✅ Likely Human Written';
        verdict.className = 'result-verdict human';
    } else {
        verdict.textContent = '⚖️ Uncertain — mixed signals';
        verdict.className = 'result-verdict uncertain';
    }

    document.getElementById('textResults').style.display = 'block';
}

function clearTextResults() {
    document.getElementById('textResults').style.display = 'none';
    document.getElementById('textHumanBar').style.width = '0%';
    document.getElementById('textAiBar').style.width = '0%';
    document.getElementById('inputText').value = '';
    document.getElementById('charCount').textContent = '0 characters';
}

// ===================================================================
// Document Upload
// ===================================================================

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) processFile(files[0]);
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) processFile(files[0]);
}

document.getElementById('dropzone').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

function processFile(file) {
    const allowed = ['.pdf', '.docx', '.txt'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!allowed.includes(ext)) {
        showError('upload', 'Unsupported file format. Please upload PDF, DOCX, or TXT files.');
        return;
    }

    clearErrors('upload');
    selectedFile = file;

    document.getElementById('dropzoneContent').style.display = 'none';
    document.getElementById('fileInfo').style.display = 'flex';
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
    document.getElementById('uploadBtn').disabled = false;
}

function clearFile() {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('dropzoneContent').style.display = '';
    document.getElementById('fileInfo').style.display = 'none';
    document.getElementById('uploadBtn').disabled = true;
}

async function handleUpload() {
    if (!selectedFile) return;
    if (!currentUser) {
        showToast('Please sign in to upload documents.', 'error');
        showPage('login');
        return;
    }

    clearErrors('upload');
    const btn = document.getElementById('uploadBtn');
    setLoading(btn, true);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('user_id', currentUser.id);

    try {
        const uploadRes = await fetch(apiUrl('/documents/upload'), {
            method: 'POST',
            body: formData,
        });

        const uploadData = await uploadRes.json();

        if (!uploadRes.ok) {
            showError('upload', uploadData.error || 'Upload failed.');
            return;
        }

        showToast('Document uploaded successfully!', 'success');
        const docId = uploadData.document.id;

        const analyseRes = await fetch(apiUrl(`/documents/${docId}/analyse`), {
            method: 'POST',
        });

        const analyseData = await analyseRes.json();

        if (!analyseRes.ok) {
            showError('upload', analyseData.error || 'Analysis failed.');
            return;
        }

        showToast('Analysis complete!', 'success');
        displayUploadResults(analyseData.analysis);
        clearFile();
    } catch (err) {
        showError('upload', 'Could not connect to the server. Is the backend running?');
    } finally {
        setLoading(btn, false);
    }
}

function displayUploadResults(analysis) {
    const aiScore = analysis.ai_score != null ? analysis.ai_score : 0;
    const humanScore = analysis.human_score != null ? analysis.human_score : 0;
    const confidence = analysis.confidence != null ? analysis.confidence : 0;

    const aiPct = Math.round(aiScore * 100);
    const humanPct = Math.round(humanScore * 100);

    setTimeout(() => {
        document.getElementById('uploadHumanBar').style.width = `${humanPct}%`;
        document.getElementById('uploadHumanVal').textContent = `${humanPct}%`;
        document.getElementById('uploadAiBar').style.width = `${aiPct}%`;
        document.getElementById('uploadAiVal').textContent = `${aiPct}%`;
    }, 100);

    let confLabel = 'Low';
    if (confidence >= 0.8) confLabel = 'High';
    else if (confidence >= 0.5) confLabel = 'Medium';

    document.getElementById('uploadConfidence').querySelector('strong').textContent = confLabel;

    const verdict = document.getElementById('uploadVerdict');
    if (aiScore > 0.7) {
        verdict.textContent = '⚠️ Likely AI Generated';
        verdict.className = 'result-verdict ai';
    } else if (humanScore > 0.7) {
        verdict.textContent = '✅ Likely Human Written';
        verdict.className = 'result-verdict human';
    } else {
        verdict.textContent = '⚖️ Uncertain — mixed signals';
        verdict.className = 'result-verdict uncertain';
    }

    document.getElementById('uploadResults').style.display = 'block';
}

function clearUploadResults() {
    document.getElementById('uploadResults').style.display = 'none';
    document.getElementById('uploadHumanBar').style.width = '0%';
    document.getElementById('uploadAiBar').style.width = '0%';
    clearFile();
}

// ===================================================================
// Dashboard
// ===================================================================

async function loadDashboard() {
    if (!currentUser) return;

    document.getElementById('dashboardGreeting').textContent =
        `Welcome back, ${escapeHtml(currentUser.username)}!`;

    try {
        const docRes = await fetch(apiUrl(`/documents/user/${currentUser.id}`));
        const docData = await docRes.json();
        const documents = docData.documents || [];

        document.getElementById('statDocuments').textContent = documents.length;
        renderDocumentsTable(documents);

        let allAnalyses = [];
        for (const doc of documents) {
            try {
                const aRes = await fetch(apiUrl(`/documents/${doc.id}/analyses`));
                const aData = await aRes.json();
                const analyses = aData.analyses || [];
                analyses.forEach(a => { a._filename = doc.filename; });
                allAnalyses = allAnalyses.concat(analyses);
            } catch { /* skip */ }
        }

        document.getElementById('statAnalyses').textContent = allAnalyses.length;
        renderAnalysesTable(allAnalyses);
    } catch (err) {
        showToast('Failed to load dashboard data.', 'error');
    }
}

function renderDocumentsTable(documents) {
    const tbody = document.getElementById('documentsBody');

    if (!documents || documents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No documents yet. <a href="#" onclick="showPage('upload')">Upload your first document</a></td></tr>`;
        return;
    }

    tbody.innerHTML = documents.map(doc => {
        const status = doc.status || 'processed';
        const statusClass = status === 'processed' ? 'completed' : status === 'pending' ? 'pending' : 'processing';
        const sizeStr = doc.text_length ? formatFileSize(doc.text_length) : '—';

        return `<tr>
            <td><strong>${escapeHtml(doc.filename)}</strong></td>
            <td>${sizeStr}</td>
            <td><span class="status-badge ${statusClass}">${status}</span></td>
            <td>${doc.upload_date ? formatDate(doc.upload_date) : '—'}</td>
            <td><button class="btn btn-sm btn-outline" onclick="analyseDocument(${doc.id})">Analyze</button></td>
        </tr>`;
    }).join('');
}

async function analyseDocument(docId) {
    if (!currentUser) return;

    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Analysing...';

    try {
        const res = await fetch(apiUrl(`/documents/${docId}/analyse`), {
            method: 'POST',
        });

        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || 'Analysis failed.', 'error');
            return;
        }

        showToast('Analysis complete!', 'success');
        loadDashboard();
    } catch {
        showToast('Could not connect to the server.', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze';
    }
}

function renderAnalysesTable(analyses) {
    const tbody = document.getElementById('analysesBody');

    if (!analyses || analyses.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No analyses yet. <a href="#" onclick="showPage('analyze')">Analyze some text</a></td></tr>`;
        return;
    }

    tbody.innerHTML = analyses.map(a => {
        const aiPct = Math.round((a.ai_score || 0) * 100);
        const humanPct = Math.round((a.human_score || 0) * 100);
        const confidence = a.confidence || 0;

        let scoreClass = 'mixed';
        if (aiPct > 70) scoreClass = 'ai';
        else if (humanPct > 70) scoreClass = 'human';

        let confLabel = 'Low';
        if (confidence >= 0.8) confLabel = 'High';
        else if (confidence >= 0.5) confLabel = 'Medium';

        return `<tr>
            <td>${escapeHtml(a._filename || `Analysis #${a.id}`)}</td>
            <td><span class="score-badge human">${humanPct}%</span></td>
            <td><span class="score-badge ai">${aiPct}%</span></td>
            <td><span class="conf-value ${confLabel.toLowerCase()}">${confLabel}</span></td>
            <td>${a.created_at ? formatDate(a.created_at) : '—'}</td>
        </tr>`;
    }).join('');
}

function switchDashboardTab(tab, btn) {
    document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('dashboardDocuments').style.display = tab === 'documents' ? '' : 'none';
    document.getElementById('dashboardAnalyses').style.display = tab === 'analyses' ? '' : 'none';
}