// app/static/js/admin.js

// Global variables
let authToken = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    initializeApp();
});

function initializeApp() {
    // Get auth token from cookie
    authToken = getAuthToken();

    // Initialize tooltips
    initializeTooltips();

    // Initialize auto-refresh for processing videos
    initializeAutoRefresh();

    // Initialize clipboard functionality
    initializeClipboard();
}

// Authentication utilities
function getAuthToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('access_token='));
    return cookie ? cookie.split('=')[1] : null;
}

// Toast notification system
function showToast(message, type = 'info', duration = 5000) {
    const toastElement = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    const toastHeader = toastElement.querySelector('.toast-header');

    // Set icon and color based on type
    let icon, headerClass;
    switch (type) {
        case 'success':
            icon = 'bi-check-circle';
            headerClass = 'text-success';
            break;
        case 'error':
        case 'danger':
            icon = 'bi-exclamation-circle';
            headerClass = 'text-danger';
            break;
        case 'warning':
            icon = 'bi-exclamation-triangle';
            headerClass = 'text-warning';
            break;
        default:
            icon = 'bi-info-circle';
            headerClass = 'text-info';
    }

    // Update toast content
    const iconElement = toastHeader.querySelector('i');
    iconElement.className = `bi ${icon} me-2`;
    iconElement.classList.add(headerClass);
    toastBody.textContent = message;

    // Show toast
    const toast = new bootstrap.Toast(toastElement, { delay: duration });
    toast.show();
}

// API utilities
async function makeAPIRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        }
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(url, mergedOptions);

        if (response.status === 401) {
            // Redirect to login if unauthorized
            window.location.href = '/admin/login';
            return null;
        }

        return response;
    } catch (error) {
        console.error('API Request failed:', error);
        showToast('Network error occurred', 'error');
        return null;
    }
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Auto-refresh for processing videos
function initializeAutoRefresh() {
    const processingElements = document.querySelectorAll('[data-video-status="processing"], [data-video-status="uploading"]');

    if (processingElements.length > 0) {
        // Refresh every 5 seconds if there are processing videos
        setInterval(refreshProcessingVideos, 5000);
    }
}

async function refreshProcessingVideos() {
    const processingElements = document.querySelectorAll('[data-video-status="processing"], [data-video-status="uploading"]');

    for (const element of processingElements) {
        const videoId = element.dataset.videoId;
        if (videoId) {
            await updateVideoProgress(videoId);
        }
    }
}

async function updateVideoProgress(videoId) {
    const response = await makeAPIRequest(`/api/v1/video/progress/${videoId}`);

    if (response && response.ok) {
        const data = await response.json();
        updateVideoProgressUI(videoId, data);
    }
}

function updateVideoProgressUI(videoId, progressData) {
    const statusElement = document.querySelector(`[data-video-id="${videoId}"] .badge`);
    const progressElement = document.querySelector(`[data-video-id="${videoId}"] .progress-bar`);

    if (statusElement) {
        // Update status badge
        statusElement.className = 'badge';
        if (progressData.status === 'completed') {
            statusElement.classList.add('bg-success');
            statusElement.innerHTML = '<i class="bi bi-check-circle"></i> Completed';

            // Reload page to show completed video
            setTimeout(() => window.location.reload(), 1000);
        } else if (progressData.status === 'failed') {
            statusElement.classList.add('bg-danger');
            statusElement.innerHTML = '<i class="bi bi-x-circle"></i> Failed';
        } else if (progressData.status === 'processing') {
            statusElement.classList.add('bg-warning');
            statusElement.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing';
        }
    }

    if (progressElement && progressData.progress) {
        progressElement.style.width = `${progressData.progress}%`;
    }
}

// Clipboard functionality
function initializeClipboard() {
    // Add click handlers for copy buttons
    document.addEventListener('click', function (e) {
        if (e.target.matches('[data-clipboard-text]') || e.target.closest('[data-clipboard-text]')) {
            const button = e.target.matches('[data-clipboard-text]') ? e.target : e.target.closest('[data-clipboard-text]');
            const text = button.dataset.clipboardText;
            copyToClipboard(text);
        }
    });
}

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch (error) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showToast('Copied to clipboard!', 'success');
        } catch (fallbackError) {
            showToast('Failed to copy to clipboard', 'error');
        }
        document.body.removeChild(textArea);
    }
}

// Video management functions
async function generateStreamingLink(videoId) {
    const response = await makeAPIRequest(`/api/v1/video/${videoId}/generate-token`, {
        method: 'POST'
    });

    if (response && response.ok) {
        const data = await response.json();
        await copyToClipboard(data.streaming_url);
        showToast('Streaming link copied to clipboard!', 'success');
        return data.streaming_url;
    } else {
        showToast('Failed to generate streaming link', 'error');
        return null;
    }
}

async function deleteVideo(videoId, videoTitle) {
    if (!confirm(`Are you sure you want to delete "${videoTitle}"? This action cannot be undone.`)) {
        return;
    }

    const response = await makeAPIRequest(`/api/v1/video/${videoId}`, {
        method: 'DELETE'
    });

    if (response && response.ok) {
        showToast('Video deleted successfully', 'success');

        // Remove the video row from table or reload page
        const videoRow = document.querySelector(`[data-video-id="${videoId}"]`);
        if (videoRow) {
            videoRow.remove();
        } else {
            setTimeout(() => window.location.reload(), 1000);
        }
    } else {
        showToast('Failed to delete video', 'error');
    }
}

// File upload utilities
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function validateVideoFile(file, maxSize, allowedTypes) {
    // Check file size
    if (file.size > maxSize) {
        showToast(`File too large. Maximum size is ${formatFileSize(maxSize)}.`, 'error');
        return false;
    }

    // Check file type
    const fileExtension = file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExtension)) {
        showToast(`Invalid file type. Allowed types: ${allowedTypes.join(', ').toUpperCase()}`, 'error');
        return false;
    }

    return true;
}

// Form validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Loading states
function setLoadingState(element, isLoading = true) {
    if (isLoading) {
        element.disabled = true;
        element.classList.add('loading');

        // Store original content
        if (!element.dataset.originalContent) {
            element.dataset.originalContent = element.innerHTML;
        }

        // Show loading spinner
        element.innerHTML = '<i class="bi bi-hourglass-split"></i> Loading...';
    } else {
        element.disabled = false;
        element.classList.remove('loading');

        // Restore original content
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
        }
    }
}

// Video preview functionality
function previewVideo(uniqueId, token = null) {
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    const videoElement = document.getElementById('previewVideo');

    let streamUrl = `/api/v1/video/stream/${uniqueId}`;
    if (token) {
        streamUrl += `?token=${token}`;
    }

    videoElement.src = streamUrl;
    modal.show();

    // Clean up when modal is hidden
    document.getElementById('previewModal').addEventListener('hidden.bs.modal', function () {
        videoElement.src = '';
        videoElement.load();
    }, { once: true });
}

// Statistics animation
function animateCounters() {
    const counters = document.querySelectorAll('[data-counter]');

    counters.forEach(counter => {
        const target = parseInt(counter.dataset.counter);
        const duration = 2000; // 2 seconds
        const step = target / (duration / 16); // 60fps
        let current = 0;

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                counter.textContent = target;
                clearInterval(timer);
            } else {
                counter.textContent = Math.floor(current);
            }
        }, 16);
    });
}

// Search and filter functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;

        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });
    }
}

function performSearch(query) {
    const tableRows = document.querySelectorAll('tbody tr');

    tableRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matches = text.includes(query.toLowerCase());
        row.style.display = matches ? '' : 'none';
    });
}

// Progress tracking for uploads
class UploadProgress {
    constructor(element) {
        this.element = element;
        this.progressBar = element.querySelector('.progress-bar');
        this.progressText = element.querySelector('.progress-text');
        this.statusMessage = element.querySelector('.status-message');
    }

    update(progress, message = '') {
        if (this.progressBar) {
            this.progressBar.style.width = `${progress}%`;
            this.progressBar.setAttribute('aria-valuenow', progress);
        }

        if (this.progressText) {
            this.progressText.textContent = `${Math.round(progress)}%`;
        }

        if (this.statusMessage && message) {
            this.statusMessage.textContent = message;
        }
    }

    complete(message = 'Upload completed successfully!') {
        this.update(100, message);
        this.element.classList.add('upload-complete');
        showToast(message, 'success');
    }

    error(message = 'Upload failed') {
        this.element.classList.add('upload-error');
        this.statusMessage.textContent = message;
        showToast(message, 'error');
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', function (e) {
    // Ctrl/Cmd + Enter to submit forms
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const activeForm = document.querySelector('form:focus-within');
        if (activeForm) {
            activeForm.submit();
        }
    }

    // Escape key to close modals
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            bootstrap.Modal.getInstance(openModal).hide();
        }
    }
});

// Auto-save for forms (draft functionality)
function initializeAutoSave() {
    const forms = document.querySelectorAll('[data-auto-save]');

    forms.forEach(form => {
        const formId = form.dataset.autoSave;

        // Load saved data
        loadFormData(form, formId);

        // Save data on input
        form.addEventListener('input', debounce(() => {
            saveFormData(form, formId);
        }, 1000));
    });
}

function saveFormData(form, formId) {
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    localStorage.setItem(`form_${formId}`, JSON.stringify(data));
}

function loadFormData(form, formId) {
    const savedData = localStorage.getItem(`form_${formId}`);
    if (savedData) {
        const data = JSON.parse(savedData);
        Object.entries(data).forEach(([name, value]) => {
            const field = form.querySelector(`[name="${name}"]`);
            if (field) {
                field.value = value;
            }
        });
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function () {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export functions for global use
window.AdminJS = {
    showToast,
    makeAPIRequest,
    generateStreamingLink,
    deleteVideo,
    previewVideo,
    formatFileSize,
    validateVideoFile,
    validateForm,
    setLoadingState,
    UploadProgress,
    copyToClipboard
};


