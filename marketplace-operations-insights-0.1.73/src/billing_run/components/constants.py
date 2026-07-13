# Default status configurations
DEFAULT_STATUS_TYPES = ['new', 'error', 'reviewed', 'finished', 'excluded']
DEFAULT_STATUS_COLORS = {
    'new': '#007bff',      # Blue
    'error': '#dc3545',     # Red
    'reviewed': '#0d4119',  # Deep Forest Green
    'finished': '#28a745',  # Green
    'excluded': '#6c757d'   # Gray
}

# Category-specific configurations
CATEGORY_CONFIGS = {
    'arrears_tasks': {
        'display_name': 'Billable Usage',
        'status_colors': DEFAULT_STATUS_COLORS
    },
    'invoice_generation': {
        'display_name': 'Invoice Generation',
        'status_colors': DEFAULT_STATUS_COLORS
    },
    'invoice_release': {
        'display_name': 'Invoice Release',
        'status_colors': DEFAULT_STATUS_COLORS
    },
    'tax_calculation': {
        'display_name': 'Tax Calculations',
        'status_colors': DEFAULT_STATUS_COLORS
    }
} 