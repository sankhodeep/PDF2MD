# -*- coding: utf-8 -*-
"""
Configuration file for the AI Question Generator.

Please fill in your details below.
"""

# --- API Configuration ---
# The script now uses an environment variable for the API key for better security.
# Please set the 'GEMINI_API_KEY' environment variable in your system.
# The API_KEY variable below is for reference and is not used by the script directly.
API_KEY = "SET_AS_ENVIRONMENT_VARIABLE"


# --- File & Folder Paths ---
# The path to your main Marrow PDF file.
PDF_FILE_PATH = "Marrow_edition_8.pdf"

# The absolute path to the external folder containing your TOPIC-SPECIFIC PYQ modules (e.g., output_1, output_2).
# IMPORTANT: Please update this to the correct path on your system.
TOPIC_PYQ_SOURCE_PATH = "C:/marrow/Medicine"

# The absolute path to the external folder containing your STYLE GUIDE PYQ modules.
STYLE_GUIDE_PYQ_SOURCE_PATH = "C:/marrow/PYQ"


# --- Default Generation Settings ---
# These values will be used if you don't provide an input when the script asks.

# Default page range to extract from the PDF (e.g., "45-49").
DEFAULT_PAGE_RANGE = "45-49"

# Default folder name inside "/PYQs/Topic_Specific/" for topic-specific questions.
DEFAULT_TOPIC_PYQ_FOLDER = "Descriptive_Studies"

# Default folder name inside "/PYQs/Style_Guide/" for style guide questions.
DEFAULT_STYLE_GUIDE_FOLDER = "Community_Medicine_NEET_2021"

# Default AI model to use ('pro' or 'flash').
DEFAULT_MODEL = "pro"