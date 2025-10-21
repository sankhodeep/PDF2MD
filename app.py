import sys
import os
import json
import time
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from PySide6.QtCore import QThread, Signal, QObject, QEventLoop
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QFileDialog, QStatusBar, QMessageBox,
    QComboBox, QInputDialog, QCheckBox
)

CONFIG_FILE = "config.json"

class PdfConverter(QObject):
    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)
    user_choice_required = Signal(int)

    def __init__(self, pdf_path, start_page, end_page, include_page_numbers):
        super().__init__()
        self.pdf_path = pdf_path
        self.start_page = start_page
        self.end_page = end_page
        self.include_page_numbers = include_page_numbers
        self.is_running = True
        self.user_choice = None

    def run(self):
        print("🤖 Starting PDF to Markdown conversion...")
        try:
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            model = "gemini-2.5-pro"
            with open("ocr_prompt.txt", "r", encoding="utf-8") as f: system_prompt = f.read()
            final_markdown = ""
            doc = fitz.open(self.pdf_path)
            page_numbers_to_process = range(self.start_page - 1, self.end_page)
            print(f"✅ Found {len(page_numbers_to_process)} pages to process.")

            i = 0
            while i < len(page_numbers_to_process):
                if not self.is_running: break
                page_num = page_numbers_to_process[i]
                print(f"\n   -> Processing page {i + 1}/{len(page_numbers_to_process)} (Absolute Page: {page_num + 1})...")

                retries = 0
                max_retries = 3
                success = False

                while retries < max_retries and not success:
                    try:
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap(dpi=200)
                        img_data = pix.tobytes("png")
                        print("   -> Image extracted successfully.")
                        image_part = types.Part(inline_data=types.Blob(mime_type="image/png", data=img_data))
                        contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt), image_part])]

                        print("   -> Sending to AI model...")
                        response = client.models.generate_content(model=model, contents=contents, stream=True)
                        page_response = ""
                        for chunk in response:
                            if not self.is_running:
                                break
                            self.progress.emit(i + 1, chunk.text)
                            page_response += chunk.text
                        print("   -> AI content received.")

                        if self.is_running:
                            if page_response:
                                if self.include_page_numbers:
                                    final_markdown += f"--- Page {i + 1} ---\n"
                                final_markdown += f"{page_response}\n\n"
                            else:
                                self.progress.emit(i + 1, "No content generated.")
                        success = True

                    except Exception as e:
                        retries += 1
                        print(f"   -> ERROR on page {i + 1}: {e}. Retrying ({retries}/{max_retries})...")
                        if retries < max_retries:
                            time.sleep(2)
                        else:
                            print(f"   -> All retries failed for page {i + 1}.")
                            self.user_choice_required.emit(i + 1)
                            self.loop = QEventLoop()
                            self.loop.exec()

                            if self.user_choice == 'retry':
                                print("   -> User chose to RETRY.")
                                retries = 0
                            elif self.user_choice == 'skip':
                                print("   -> User chose to SKIP.")
                                success = True
                            elif self.user_choice == 'end':
                                print("   -> User chose to END.")
                                self.is_running = False
                                self.error.emit("Conversion ended by user.")
                                return
                i += 1

            doc.close()
            if self.is_running:
                print("\n✅ All pages processed. Markdown generated successfully.")
                self.finished.emit(final_markdown.strip())
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
            self.error.emit(f"An unexpected error occurred: {e}")

    def stop(self):
        self.is_running = False

# (MainWindow and other classes remain the same as the previous version)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF2MD")
        self.setGeometry(100, 100, 800, 600)
        self.thread = None
        self.converter = None
        self.current_processing_page = 0
        self.setup_ui()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready")
        self.load_configs()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        config_layout = QHBoxLayout()
        self.config_combo = QComboBox()
        load_config_button, save_config_button, delete_config_button = QPushButton("Load"), QPushButton("Save"), QPushButton("Delete")
        load_config_button.clicked.connect(self.load_selected_config)
        save_config_button.clicked.connect(self.save_config)
        delete_config_button.clicked.connect(self.delete_config)
        config_layout.addWidget(QLabel("Configuration:"))
        config_layout.addWidget(self.config_combo, 1)
        config_layout.addWidget(load_config_button)
        config_layout.addWidget(save_config_button)
        config_layout.addWidget(delete_config_button)
        self.main_layout.addLayout(config_layout)
        pdf_layout = QHBoxLayout()
        self.pdf_path_edit = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_pdf)
        pdf_layout.addWidget(QLabel("PDF File:"))
        pdf_layout.addWidget(self.pdf_path_edit)
        pdf_layout.addWidget(browse_button)
        self.main_layout.addLayout(pdf_layout)
        page_range_layout = QHBoxLayout()
        self.start_page_edit, self.end_page_edit = QLineEdit(), QLineEdit()
        self.page_count_label = QLabel("")
        page_range_layout.addWidget(QLabel("Page Range:"))
        page_range_layout.addWidget(self.start_page_edit)
        page_range_layout.addWidget(QLabel("to"))
        page_range_layout.addWidget(self.end_page_edit)
        page_range_layout.addWidget(self.page_count_label)
        page_range_layout.addStretch()
        self.main_layout.addLayout(page_range_layout)
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        self.main_layout.addWidget(QLabel("Live Output:"))
        self.main_layout.addWidget(self.content_display)
        md_layout = QHBoxLayout()
        self.md_path_edit = QLineEdit()
        save_as_button = QPushButton("Save As")
        save_as_button.clicked.connect(self.save_as_md)
        md_layout.addWidget(QLabel("Output File:"))
        md_layout.addWidget(self.md_path_edit)
        md_layout.addWidget(save_as_button)
        self.main_layout.addLayout(md_layout)
        action_layout = QHBoxLayout()
        self.include_page_numbers_checkbox = QCheckBox("Include page numbers in output")
        self.include_page_numbers_checkbox.setChecked(True)
        self.start_button = QPushButton("Start Conversion")
        self.start_button.clicked.connect(self.start_conversion)
        action_layout.addStretch()
        action_layout.addWidget(self.include_page_numbers_checkbox)
        action_layout.addWidget(self.start_button)
        action_layout.addStretch()
        self.main_layout.addLayout(action_layout)

        self.pdf_path_edit.textChanged.connect(self._update_start_button_state)
        self.md_path_edit.textChanged.connect(self._update_start_button_state)
        self.start_page_edit.textChanged.connect(self._update_start_button_state)
        self.end_page_edit.textChanged.connect(self._update_start_button_state)
        self._update_start_button_state()

    def ask_user_choice(self, page_num):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Conversion Error")
        msg_box.setText(f"Failed to process page {page_num} after 3 attempts.")
        msg_box.setInformativeText("What would you like to do?")
        skip_button = msg_box.addButton("Skip Page", QMessageBox.AcceptRole)
        retry_button = msg_box.addButton("Retry", QMessageBox.ActionRole)
        end_button = msg_box.addButton("End Conversion", QMessageBox.RejectRole)
        msg_box.exec()

        if msg_box.clickedButton() == skip_button:
            self.converter.user_choice = 'skip'
        elif msg_box.clickedButton() == retry_button:
            self.converter.user_choice = 'retry'
        else:
            self.converter.user_choice = 'end'
        self.converter.loop.quit()

    def start_conversion(self):
        self.set_ui_enabled(False)
        self.content_display.clear()
        self.current_processing_page = 0
        self.statusBar().showMessage("Starting...")
        self.thread = QThread()
        self.converter = PdfConverter(
            self.pdf_path_edit.text(),
            int(self.start_page_edit.text()),
            int(self.end_page_edit.text()),
            self.include_page_numbers_checkbox.isChecked()
        )
        self.converter.moveToThread(self.thread)
        self.thread.started.connect(self.converter.run)
        self.converter.progress.connect(self.update_progress)
        self.converter.finished.connect(self.on_conversion_finished)
        self.converter.error.connect(self.on_conversion_error)
        self.converter.user_choice_required.connect(self.ask_user_choice)
        self.thread.finished.connect(self.thread.deleteLater)
        self.converter.finished.connect(self.thread.quit)
        self.converter.finished.connect(self.converter.deleteLater)
        self.thread.start()

    def _update_start_button_state(self):
        all_fields_filled = all([
            self.pdf_path_edit.text(),
            self.md_path_edit.text(),
            self.start_page_edit.text(),
            self.end_page_edit.text()
        ])
        self.start_button.setEnabled(all_fields_filled)

    def load_configs(self):
        self.config_combo.clear()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: configs = json.load(f)
                self.config_combo.addItems(configs.keys())
            except (json.JSONDecodeError, IOError): pass
    def save_config(self):
        config_name, ok = QInputDialog.getText(self, "Save Configuration", "Enter a name:")
        if ok and config_name:
            configs = {}
            try:
                with open(CONFIG_FILE, "r") as f: configs = json.load(f)
            except (json.JSONDecodeError, IOError): pass
            configs[config_name] = {"pdf_path": self.pdf_path_edit.text(), "md_path": self.md_path_edit.text()}
            with open(CONFIG_FILE, "w") as f: json.dump(configs, f, indent=4)
            self.load_configs()
    def load_selected_config(self):
        config_name = self.config_combo.currentText()
        if config_name:
            try:
                with open(CONFIG_FILE, "r") as f: configs = json.load(f)
                config_data = configs.get(config_name)
                if config_data:
                    pdf_path = config_data.get("pdf_path", "")
                    self.pdf_path_edit.setText(pdf_path)
                    self.md_path_edit.setText(config_data.get("md_path", ""))
                    if pdf_path:
                        try:
                            with fitz.open(pdf_path) as doc:
                                self.page_count_label.setText(f"  Total Pages: 1-{doc.page_count}")
                        except fitz.errors.FitzError:
                            self.page_count_label.setText("  Invalid PDF")
                    else:
                        self.page_count_label.setText("")
            except (json.JSONDecodeError, IOError): pass
    def delete_config(self):
        config_name = self.config_combo.currentText()
        if not config_name: return
        reply = QMessageBox.question(self, "Delete", f"Delete '{config_name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                with open(CONFIG_FILE, "r") as f: configs = json.load(f)
                if config_name in configs: del configs[config_name]
                with open(CONFIG_FILE, "w") as f: json.dump(configs, f, indent=4)
                self.load_configs()
            except (json.JSONDecodeError, IOError): pass
    def browse_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file_name:
            self.pdf_path_edit.setText(file_name)
            try:
                with fitz.open(file_name) as doc: self.page_count_label.setText(f"  Total Pages: 1-{doc.page_count}")
            except fitz.errors.FitzError: self.page_count_label.setText("  Invalid PDF")
    def save_as_md(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save MD", "", "Markdown (*.md)")
        if file_name: self.md_path_edit.setText(file_name)
    def update_progress(self, page_num, content):
        self.statusBar().showMessage(f"Processing page {page_num}...")
        if self.current_processing_page != page_num:
            self.current_processing_page = page_num
            if self.include_page_numbers_checkbox.isChecked():
                self.content_display.append(f"--- Page {page_num} ---\n")
        self.content_display.insertPlainText(content)
        self.content_display.ensureCursorVisible()
    def on_conversion_finished(self, markdown_content):
        self.statusBar().showMessage("Success! Saving file...")
        try:
            with open(self.md_path_edit.text(), "w", encoding="utf-8") as f: f.write(markdown_content)
            self.statusBar().showMessage("File saved successfully!")
        except IOError: self.statusBar().showMessage("Error saving file.")
        self.set_ui_enabled(True)
    def on_conversion_error(self, message):
        QMessageBox.critical(self, "Conversion Error", message)
        self.statusBar().showMessage("Conversion failed.")
        self.set_ui_enabled(True)
    def set_ui_enabled(self, enabled):
        for widget_type in [QLineEdit, QPushButton, QComboBox]:
            for widget in self.centralWidget().findChildren(widget_type): widget.setEnabled(enabled)
    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Close",
                "A conversion is currently in progress. Closing now will result in unsaved changes. Are you sure you want to close?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.converter.stop()
                self.thread.quit()
                self.thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "API Key Error", "GEMINI_API_KEY not set.")
        sys.exit(1)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
