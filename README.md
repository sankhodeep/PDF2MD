# PDF to Markdown Converter GUI

This application provides a user-friendly graphical user interface (GUI) to convert specific pages from a PDF file into Markdown format using the power of Google's Gemini AI. It is designed to replace a command-line-based workflow, making the process more interactive and accessible.

## Key Features

- **Interactive File Selection**: Easily browse and select any PDF file from your computer.
- **Specific Page Range**: Convert only the pages you need by specifying a start and end page.
- **Real-Time Progress**: Monitor the conversion process with a live output that displays the current page being processed and the extracted text.
- **Flexible Output**: Choose the exact location and filename for your saved Markdown file.
- **Configuration Management**: Save your settings (input PDF and output file paths) as named configurations, so you can quickly load them for future use.
- **Responsive & Stable**: The core conversion process runs in a background thread, ensuring the application's UI remains responsive.
- **Robust Error Handling**: The application provides clear feedback for common issues like missing files, invalid page numbers, or corrupted PDFs.

## Prerequisites

- Python 3.6+
- `pip` (the Python package installer)

## Setup and Installation

Follow these steps to set up the application on your local machine.

### 1. Clone the Repository

First, clone this repository to your local machine or download the source code.

### 2. Set Up the Environment Variable

The application requires a Google Gemini API key to function. You must set this key as an environment variable.

- Create a new file named `.env` in the root directory of the project.
- Open the `.env` file and add the following line, replacing `YOUR_API_KEY_HERE` with your actual Gemini API key:

  ```
  GEMINI_API_KEY="YOUR_API_KEY_HERE"
  ```

- The application will automatically load this key when it starts.

### 3. Install Required Packages

Install all the necessary Python packages using the `requirements.txt` file. Open your terminal or command prompt in the project's root directory and run the following command:

```bash
pip install -r requirements.txt
```

## How to Run the Application

Once you have completed the setup steps, you can run the application with a single command.

Make sure you are in the root directory of the project and execute the following command in your terminal:

```bash
python app.py
```

The application window will open, and you can start converting your PDFs.

medical study note