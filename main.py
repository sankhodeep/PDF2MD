# -*- coding: utf-8 -*-
"""
AI-Powered Medical Question Generator
This script automates the creation of high-quality MCQs for medical exams.
"""

import os
import sys
import fitz  # PyMuPDF
from PIL import Image
import io
import json
import random
import csv
from google import genai
from google.genai import types
import config  # Our configuration file
from dotenv import load_dotenv # Import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_user_input(prompt_message, default_value=""):
    """
    Prompts the user for input and returns the default value if none is provided.
    """
    user_input = input(f"{prompt_message} (default: {default_value}): ")
    return user_input.strip() if user_input.strip() else default_value


def _format_pyq_list_to_text(question_list):
    """
    Formats a list of question objects into the required plain text format.
    """
    formatted_text = ""
    for question in question_list:
        # Find the correct option text
        correct_option_text = "N/A"
        for option in question.get("options", []):
            if option.get("is_correct_answer"):
                correct_option_text = option.get("text", "N/A")
                break
        
        # Build the question block
        formatted_text += f"Question {question.get('question_number', 'N/A')}:\n"
        formatted_text += f"{question.get('text', '')}\n"
        formatted_text += "Options:\n"
        for option in question.get("options", []):
            formatted_text += f"{option.get('text', '')}\n"
        
        image_path = question.get('question_media_path') or "None"
        formatted_text += f"Question Image: {image_path}\n"
        formatted_text += f"Correct Option: {correct_option_text}\n\n"
        
    return formatted_text.strip()


def _transform_question_format(question_list):
    """
    Transforms the source question format to the target JSON format for the style guide.
    """
    transformed_questions = []
    for q_source in question_list:
        # Find correct option and build options object
        options_obj = {}
        correct_option_letter = ""
        for opt in q_source.get("options", []):
            option_text = opt.get("text", "")
            # Extract letter like 'A', 'B' from 'A. Some text'
            letter = option_text.split('.')[0].strip()
            if letter in "ABCD":
                options_obj[letter] = option_text
                if opt.get("is_correct_answer"):
                    correct_option_letter = letter
        
        q_target = {
            "question": q_source.get("text", ""),
            "options": options_obj,
            "correct_option": correct_option_letter,
            "image_link": q_source.get("question_media_path"),
            "labels": q_source.get("labels", [])
        }
        transformed_questions.append(q_target)
    return transformed_questions


def get_style_guide_pyqs_json():
    """
    Asks for style guide modules, loads all questions, samples 25,
    transforms them, and returns a JSON string.
    """
    print("\n--- Loading Style Guide PYQs ---")
    module_numbers_str = get_user_input("Enter Style Guide PYQ module numbers (e.g., 1,3,8)")
    if not module_numbers_str:
        print("⚠️ No module numbers entered. Skipping Style Guide PYQs.")
        return "{}", "" # Return empty JSON object and empty string for modules

    try:
        module_numbers = [int(n.strip()) for n in module_numbers_str.split(',')]
    except ValueError:
        print("❌ ERROR: Invalid format for module numbers.")
        return "{}", ""

    all_questions = []
    for num in module_numbers:
        folder_name = f"output_{num}"
        file_path = os.path.join(config.STYLE_GUIDE_PYQ_SOURCE_PATH, folder_name, "questions.json")
        
        if not os.path.exists(file_path):
            print(f"⚠️ WARNING: File not found, skipping: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                questions_in_file = json.load(f)
                all_questions.extend(questions_in_file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ WARNING: Could not read or parse {file_path}: {e}")

    print(f"✅ Found {len(all_questions)} total style guide questions.")
    
    # Randomly sample 25 questions if more than 25 are available
    if len(all_questions) > 25:
        print("   -> Randomly selecting 25 to use as a style guide...")
        sampled_questions = random.sample(all_questions, 25)
    else:
        sampled_questions = all_questions

    # Transform the questions to the required JSON format
    transformed_questions = _transform_question_format(sampled_questions)
    
    # Convert the final list to a JSON string
    return json.dumps(transformed_questions, indent=2), module_numbers_str


def get_topic_specific_pyqs_text():
    """
    Asks for module numbers, loads questions from an external path,
    filters them, and returns a formatted plain text string.
    """
    print("\n--- Loading Topic-Specific PYQs ---")
    module_numbers_str = get_user_input("Enter Topic PYQ module numbers (e.g., 2,5,18)")
    if not module_numbers_str:
        print("⚠️ No module numbers entered. Skipping Topic PYQs.")
        return "", ""

    try:
        module_numbers = [int(n.strip()) for n in module_numbers_str.split(',')]
    except ValueError:
        print("❌ ERROR: Invalid format for module numbers. Please use comma-separated numbers.")
        return "", ""

    all_questions = []
    for num in module_numbers:
        folder_name = f"output_{num}"
        file_path = os.path.join(config.TOPIC_PYQ_SOURCE_PATH, folder_name, "questions.json")
        
        if not os.path.exists(file_path):
            print(f"⚠️ WARNING: File not found, skipping: {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                questions_in_file = json.load(f)
                all_questions.extend(questions_in_file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ WARNING: Could not read or parse {file_path}: {e}")

    # Filter for questions with the '#recentNEET' label
    filtered_questions = [
        q for q in all_questions if "#recentNEET" in q.get("labels", [])
    ]
    
    print(f"✅ Found {len(all_questions)} total questions, filtered down to {len(filtered_questions)} recent NEET questions.")
    
    # Format the filtered list into the required plain text
    return _format_pyq_list_to_text(filtered_questions), module_numbers_str


def get_markdown_from_scanned_pdf(pdf_path, page_range_str):
    """
    Extracts pages from a scanned PDF as images, sends them to a multimodal AI,
    and returns the content as a structured Markdown string.
    """
    print("🤖 Sending images to AI for Markdown conversion (one page at a time)...")
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model = "gemini-2.5-pro" # Changed from flash-lite to flash
        with open("ocr_prompt.txt", "r", encoding="utf-8") as f:
            system_prompt = f.read()

        final_markdown = ""
        
        # This part is copied from the corrected test.py
        page_images_data = []
        doc = fitz.open(pdf_path)
        page_numbers_to_process = []
        for part in page_range_str.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    if start > end:
                        print(f"❌ ERROR: Invalid range '{part}'. Start page must be less than or equal to end page.")
                        return None
                    page_numbers_to_process.extend(range(start - 1, end))
                except ValueError:
                    print(f"❌ ERROR: Invalid range format '{part}'.")
                    return None
            else:
                try:
                    page_numbers_to_process.append(int(part) - 1)
                except ValueError:
                    print(f"❌ ERROR: Invalid page number '{part}'.")
                    return None
        
        # Remove duplicates and sort
        page_numbers_to_process = sorted(list(set(page_numbers_to_process)))

        for page_num in page_numbers_to_process:
            if page_num < 0 or page_num >= doc.page_count:
                print(f"❌ ERROR: Page number {page_num + 1} is out of bounds. PDF has {doc.page_count} pages.")
                continue
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=200)
            page_images_data.append(pix.tobytes("png"))
        doc.close()
        print("✅ Images extracted successfully.")

        for i, img_data in enumerate(page_images_data):
            print(f"\n   -> Processing page {i + 1}/{len(page_images_data)}...")
            
            image_part = types.Part(inline_data=types.Blob(mime_type="image/png", data=img_data))
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=system_prompt), image_part])]
            
            generate_content_config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                response_mime_type="text/plain",
            )
            
            page_response = ""
            for chunk in client.models.generate_content_stream(
                model=model, contents=contents, config=generate_content_config
            ):
                print(chunk.text, end="", flush=True)
                if chunk.text:
                    page_response += chunk.text
            
            if page_response:
                final_markdown += page_response + "\n\n---\n\n"
            else:
                print(f"\n   -> WARNING: No content generated for page {i + 1}. Skipping.")

        print("\n✅ All pages processed. Markdown generated successfully.")
        return final_markdown.strip()
    except Exception as e:
        print(f"\n❌ An error occurred during AI generation: {e}")
        return None


def generate_final_questions(markdown_content, topic_pyqs_text, style_guide_json, model_choice, topic_name):
    """
    Assembles the final prompt, saves it for review, and calls the AI.
    """
    print(f"\n🤖 Assembling final prompt and generating questions using 'gemini-2.5-{model_choice}'...")
    try:
        with open("prompt_template.txt", "r", encoding='utf-8') as f:
            prompt_template = f.read()

        final_prompt = prompt_template.replace("{{INSERT_MARKDOWN_CONTENT_HERE}}", markdown_content)
        final_prompt = final_prompt.replace("{{INSERT_THE_4_TOPIC_SPECIFIC_PYQS_HERE}}", topic_pyqs_text)
        final_prompt = final_prompt.replace("{{INSERT_THE_25_RANDOM_COMM_MED_PYQS_HERE}}", style_guide_json)

        # Save the final prompt for review in a structured folder
        prompt_filename = f"{topic_name.replace(' ', '_')}.md"
        save_path = os.path.join("final_prompt", prompt_filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(final_prompt)
        print(f"✅ Final prompt saved for review to: {save_path}")

        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        model_name = f"gemini-2.5-{model_choice}"
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=final_prompt)])]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            response_mime_type="application/json",
        )
        response = client.models.generate_content(
            model=model_name, contents=contents, config=generate_content_config
        )
        generated_questions = json.loads(response.text)
        print(f"✅ Successfully generated {len(generated_questions)} questions.")
        return generated_questions
    except Exception as e:
        print(f"❌ An error occurred during final question generation: {e}")
        return None


def save_questions_to_file(questions, topic_name):
    """
    Saves the generated questions to a timestamped JSON file.
    """
    if not questions:
        print("No questions to save.")
        return None
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{topic_name.replace(' ', '_')}_{timestamp}.json"
    save_path = os.path.join("Generated_Questions", filename)
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding='utf-8') as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)
        print(f"✅ Questions successfully saved to: {save_path}")
        return filename, timestamp # Return filename and timestamp for CSV logging
    except Exception as e:
        print(f"❌ Failed to save questions to file: {e}")
        return None, None


def save_markdown_to_file(markdown_content, topic_name):
    """
    Saves the generated markdown content to a file in the 'processed_notes' directory.
    """
    if not markdown_content:
        print("No markdown content to save.")
        return
    
    # Use the user-provided name, replacing spaces with underscores
    filename = f"{topic_name.replace(' ', '_')}.md"
    save_path = os.path.join("processed_notes", filename)
    
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"✅ Markdown notes successfully saved to: {save_path}")
    except Exception as e:
        print(f"❌ Failed to save markdown to file: {e}")


def save_run_details_to_csv(details):
    """
    Saves the details of the run to a CSV file.
    """
    folder_name = "generated_CSV"
    
    # Create a unique filename for the CSV log entry
    csv_filename = f"{details['markdown_filename'].replace('.md', '')}_{details['timestamp']}.csv"
    save_path = os.path.join(folder_name, csv_filename)
    
    # Ensure the full directory path exists before trying to save the file
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    header = [
        "timestamp", "pdf_page_range", "markdown_filename",
        "topic_pyq_modules", "style_guide_pyq_modules", "generated_question_file"
    ]
    
    row = [
        details["timestamp"],
        details["pdf_page_range"],
        details["markdown_filename"],
        details["topic_pyq_modules"],
        details["style_guide_pyq_modules"],
        details["generated_question_file"]
    ]
    
    try:
        with open(save_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerow(row)
        print(f"✅ Run details successfully saved to: {save_path}")
    except Exception as e:
        print(f"❌ Failed to save run details to CSV: {e}")


def main():
    """
    Main function to run the question generation pipeline.
    """
    print("--- AI Medical Question Generator ---")
    page_range = get_user_input("Enter the PDF page range (e.g., 45-49)", config.DEFAULT_PAGE_RANGE)
    model_choice = get_user_input("Enter the AI model to use ('pro' or 'flash')", config.DEFAULT_MODEL)
    
    markdown_content = get_markdown_from_scanned_pdf(config.PDF_FILE_PATH, page_range)
    if not markdown_content:
        sys.exit(1)

    topic_name = get_user_input("Enter a name for this topic (e.g., Analytical_Epidemiology)", "Generated_Topic")
    
    save_markdown_to_file(markdown_content, topic_name)
    
    topic_pyqs_text, topic_modules_str = get_topic_specific_pyqs_text()
    style_guide_json, style_guide_modules_str = get_style_guide_pyqs_json()
    
    final_questions = generate_final_questions(
        markdown_content,
        topic_pyqs_text,
        style_guide_json,
        model_choice,
        topic_name
    )

    if final_questions:
        json_filename, timestamp = save_questions_to_file(final_questions, topic_name)
        if json_filename:
            run_details = {
                "timestamp": timestamp,
                "pdf_page_range": page_range,
                "markdown_filename": f"{topic_name.replace(' ', '_')}.md",
                "topic_pyq_modules": topic_modules_str,
                "style_guide_pyq_modules": style_guide_modules_str,
                "generated_question_file": json_filename
            }
            save_run_details_to_csv(run_details)
        
        print("\n🎉 Pipeline complete! Your questions are ready.")
    else:
        print("\n😔 Pipeline finished with errors. No questions were generated.")


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERROR: The 'GEMINI_API_KEY' environment variable is not set.")
        sys.exit(1)
    main()