/* ========================================
   项目管理系统 - 共享 JavaScript
   ======================================== */

document.addEventListener('DOMContentLoaded', function () {
    // Active nav link highlighting
    highlightActiveNav();

    // Auto-dismiss alerts after 5 seconds
    autoCloseAlerts();

    // Animate stat numbers on dashboard
    animateStatNumbers();

    // Enhanced table interactions
    initEditableCells();
    initNumberFormatters();
    initButtonRipple();
    initSaveIndicators();
});

/**
 * Highlight the current page's nav link
 */
function highlightActiveNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href === currentPath) {
            link.classList.add('active');
        }
    });
}

/**
 * Auto-close Bootstrap alerts
 */
function autoCloseAlerts() {
    setTimeout(function () {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function (alert) {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {
                // Alert already closed or not a Bootstrap alert
            }
        });
    }, 5000);
}

/**
 * Animate stat numbers counting up from 0
 */
function animateStatNumbers() {
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(el => {
        const target = parseInt(el.textContent) || 0;
        if (target === 0) return;

        const duration = 800;
        const start = performance.now();
        el.textContent = '0';

        function step(timestamp) {
            const progress = Math.min((timestamp - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            el.textContent = Math.floor(eased * target);
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                el.textContent = target;
            }
        }

        requestAnimationFrame(step);
    });
}

/**
 * Enhanced editable cells initialization
 */
function initEditableCells() {
    const editableCells = document.querySelectorAll('.editable-cell[contenteditable="true"]');

    editableCells.forEach(cell => {
        // Save on blur
        cell.addEventListener('blur', function() {
            const value = this.textContent.trim();
            const field = this.dataset.field;
            const rowId = this.closest('tr')?.dataset.id;

            if (field && rowId) {
                saveEditableCell(this, field, value, rowId);
            }
        });

        // Enter key to save and move to next
        cell.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.blur();
                
                // Move to next editable cell
                const nextCell = this.closest('td')?.nextElementSibling?.querySelector('.editable-cell');
                if (nextCell) {
                    nextCell.focus();
                }
            }
        });

        // Visual feedback on focus
        cell.addEventListener('focus', function() {
            this.classList.add('editing');
        });

        cell.addEventListener('blur', function() {
            this.classList.remove('editing');
        });
    });
}

/**
 * Save editable cell data
 */
function saveEditableCell(cell, field, value, rowId) {
    const indicator = cell.closest('tr')?.querySelector('.save-indicator');
    
    if (indicator) {
        indicator.className = 'save-indicator saving';
        indicator.textContent = '保存中...';
    }

    // Simulate save (replace with actual API call)
    setTimeout(() => {
        if (indicator) {
            indicator.className = 'save-indicator saved';
            indicator.textContent = '已保存';
            
            // Reset after 2 seconds
            setTimeout(() => {
                indicator.className = 'save-indicator';
                indicator.textContent = '';
            }, 2000);
        }
    }, 500);
}

/**
 * Format numbers with thousand separators
 */
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || num === '') return '';
    
    const value = parseFloat(num);
    if (isNaN(value)) return num;

    return value.toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Initialize number formatters for table cells
 */
function initNumberFormatters() {
    const numericCells = document.querySelectorAll('.numeric-cell');
    numericCells.forEach(cell => {
        const originalValue = cell.textContent.trim();
        const formattedValue = formatNumber(originalValue);
        if (formattedValue !== originalValue) {
            cell.textContent = formattedValue;
        }
    });
}

/**
 * Button ripple effect
 */
function initButtonRipple() {
    const buttons = document.querySelectorAll('.btn');

    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Remove existing ripple
            const existingRipple = this.querySelector('.ripple');
            if (existingRipple) existingRipple.remove();

            // Create ripple
            const ripple = document.createElement('span');
            ripple.className = 'ripple';
            ripple.style.left = e.offsetX + 'px';
            ripple.style.top = e.offsetY + 'px';

            this.appendChild(ripple);

            // Remove after animation
            setTimeout(() => ripple.remove(), 600);
        });
    });
}

/**
 * Initialize save indicators
 */
function initSaveIndicators() {
    const indicators = document.querySelectorAll('.save-indicator');
    indicators.forEach(indicator => {
        // Hide initially
        if (!indicator.textContent.trim()) {
            indicator.style.display = 'none';
        }
    });
}

/**
 * Show enhanced toast notification
 */
function showToast(message, type = 'success', duration = 3000) {
    const existingToast = document.querySelector('.custom-toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = `custom-toast toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="bi ${getToastIcon(type)} me-2"></i>
            <span>${message}</span>
        </div>
        <div class="toast-progress"></div>
    `;

    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Auto dismiss
    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Get icon for toast type
 */
function getToastIcon(type) {
    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        info: 'bi-info-circle-fill'
    };
    return icons[type] || icons.success;
}

/**
 * Format file size from bytes
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Debounce function for performance
 */
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

/**
 * Table row hover effects
 */
document.querySelectorAll('.table tbody tr').forEach(row => {
    row.addEventListener('mouseenter', function() {
        this.classList.add('hover');
    });
    row.addEventListener('mouseleave', function() {
        this.classList.remove('hover');
    });
});

/**
 * Form input focus effects
 */
document.querySelectorAll('.form-control, .form-select').forEach(input => {
    input.addEventListener('focus', function() {
        this.closest('.mb-3, .form-group')?.classList.add('focused');
    });
    input.addEventListener('blur', function() {
        this.closest('.mb-3, .form-group')?.classList.remove('focused');
    });
});
