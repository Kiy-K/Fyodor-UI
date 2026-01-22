import re
import json
import os
import streamlit as st

def get_secret(key, default=None):
    """
    Retrieves a secret from Streamlit secrets (priority) or environment variables.

    Args:
        key (str): The name of the secret/environment variable.
        default (any): The default value if not found.

    Returns:
        str or None: The secret value.
    """
    try:
        # st.secrets acts like a dictionary
        if key in st.secrets:
            return st.secrets[key]
    except (FileNotFoundError, AttributeError):
        # st.secrets might fail if not running in Streamlit or no secrets.toml
        pass

    return os.getenv(key, default)

def parse_dashboard_response(text):
    """
    Parses the model's markdown-based dashboard response into a dictionary.

    Args:
        text (str): The raw model response, expected to contain specific headings.

    Returns:
        dict: A dictionary with keys 'summary', 'reasoning', and 'sources'.
    """
    if not text:
        return {"summary": "", "reasoning": "", "sources": ""}

    # Clean the text by removing any thinking blocks first
    cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Define the sections based on the headings
    sections = {
        "summary": "### Executive Summary",
        "reasoning": "### Detailed Reasoning",
        "sources": "### Sources & Search Data"
    }

    parsed_content = {}

    # Use regex to find content between headings
    for key, heading in sections.items():
        pattern = re.escape(heading) + r"\s*---\s*(.*?)(?=\n### |\Z)"
        match = re.search(cleaned_text, pattern, re.DOTALL | re.IGNORECASE)
        if match:
            parsed_content[key] = match.group(1).strip()
        else:
            parsed_content[key] = f"Could not find section: '{heading}'"

    # Fallback if no sections are found
    if not any(match for match in parsed_content.values() if "Could not find section" not in match):
        return {"summary": cleaned_text, "reasoning": "No specific reasoning section found.", "sources": "No specific sources section found."}

    return parsed_content

def process_uploaded_files(uploaded_files):
    """
    Extracts text from uploaded PDF and DOCX files.
    Images are returned as is.
    """
    import docx
    from PyPDF2 import PdfReader
    import io

    extracted_texts = []
    image_files = []

    for file in uploaded_files:
        if file.type == "application/pdf":
            try:
                pdf_reader = PdfReader(io.BytesIO(file.getvalue()))
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                extracted_texts.append(f"--- Document: {file.name} ---\n{text}\n--- End Document ---")
            except Exception as e:
                extracted_texts.append(f"--- Document: {file.name} ---\nError reading PDF: {e}\n--- End Document ---")

        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                doc = docx.Document(io.BytesIO(file.getvalue()))
                text = "\n".join([para.text for para in doc.paragraphs])
                extracted_texts.append(f"--- Document: {file.name} ---\n{text}\n--- End Document ---")
            except Exception as e:
                extracted_texts.append(f"--- Document: {file.name} ---\nError reading DOCX: {e}\n--- End Document ---")

        elif file.type.startswith("image/"):
            image_files.append(file)

    return "\n\n".join(extracted_texts), image_files
