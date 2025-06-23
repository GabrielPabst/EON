# Matching configuration
DEFAULT_THRESHOLD = 0.6
SCALE_FACTORS = [0.95, 0.975, 1.0, 1.025, 1.05]

# Matching methods with their weights
MATCHING_METHODS = [
    ('TM_CCOEFF_NORMED', 1.0),  # Exact matching
    ('TM_CCORR_NORMED', 0.9),   # More tolerant to intensity changes
]

# Visualization settings
MATCH_COLOR = (0, 255, 0)  # Green in BGR
FONT_SCALE = 0.7
FONT_THICKNESS = 2
TEXT_COLOR = (0, 255, 0)  # Green in BGR
RECT_THICKNESS = 2

# Minimum dimensions for scaled templates
MIN_TEMPLATE_SIZE = 10
