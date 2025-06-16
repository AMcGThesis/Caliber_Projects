# -*- coding: utf-8 -*-
"""
Created on Fri Jun 13 13:53:31 2025
@author: AngusMcGregor SamColdicott
"""

import os
import csv
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import pdfplumber
import sys

# The Black Magicks
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS2
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Define bounding boxes for different sheet sizes (based on standard layouts)
DRAWING_TITLE_BBOXES = {
    'A3': (670, 727, 1000, 746),
    'A2': (1175, 913, 1600, 955),
    'A1': (1880, 1410, 2340, 1445)
}

def determine_sheet_size(page):
    width = page.width
    height = page.height
    if width >= 2300 and height >= 1600:
        return 'A1'
    elif width >= 1550 and height >= 1100:
        return 'A2'
    elif width >= 1100 and height >= 800:
        return 'A3'
    else:
        return 'Unknown'

def extract_title_from_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return "No Pages Found"
            page = pdf.pages[0]
            sheet_size = determine_sheet_size(page)
            if sheet_size not in DRAWING_TITLE_BBOXES:
                return f"Unsupported Sheet Size ({sheet_size})"
            bbox = DRAWING_TITLE_BBOXES[sheet_size]
            cropped = page.within_bbox(bbox)
            text = cropped.extract_text()
            if not text:
                return "No Text Found"
            return text.strip()
    except Exception as e:
        return f"Error: {e}"

def save_to_csv(data, folder_path):
    csv_path = os.path.join(folder_path, "Drawing_Register_Data.csv")
    headers = ["Filename", "Drawing Title", "Error Message"]
    all_rows = [headers] + data

    col_widths = [0] * len(headers)
    for row in all_rows:
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell else ""
            col_widths[i] = max(col_widths[i], len(cell_str))

    padded_rows = []
    for row in all_rows:
        padded_row = [str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)]
        padded_rows.append(padded_row)

    with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(padded_rows)

    return csv_path

class PDFTitleExtractorApp:
    def __init__(self, master):
        self.master = master
        master.title("PDF Drawing Title Extractor")

        self.folder_path = ""
        self.csv_path = None  # Stores the path to the last saved CSV

        self.label = tk.Label(master, text="Select a folder containing PDF files:")
        self.label.pack(pady=5)

        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        self.select_button = tk.Button(button_frame, text="Select Folder", command=self.select_folder)
        self.select_button.pack(side=tk.LEFT, padx=10)

        self.run_button = tk.Button(button_frame, text="Run Extraction", command=self.run_extraction, state=tk.DISABLED)
        self.run_button.pack(side=tk.LEFT, padx=10)

        self.open_csv_button = tk.Button(button_frame, text="Open CSV", command=self.open_csv, state=tk.DISABLED)
        self.open_csv_button.pack(side=tk.LEFT, padx=10)

        self.progress = ttk.Progressbar(master, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=5)

        self.log_area = scrolledtext.ScrolledText(master, height=20, width=80, state=tk.DISABLED)
        self.log_area.pack(pady=10)

    def select_folder(self):
        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            self.log("Selected folder:\n" + self.folder_path + "\n")
            self.run_button.config(state=tk.NORMAL)
            self.open_csv_button.config(state=tk.DISABLED)
            self.csv_path = None

    def run_extraction(self):
        if not self.folder_path:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        self.run_button.config(state=tk.DISABLED)
        self.select_button.config(state=tk.DISABLED)
        self.progress["value"] = 0
        self.log("Starting extraction...\n")

        thread = threading.Thread(target=self.process_pdfs)
        thread.start()

    def process_pdfs(self):
        try:
            pdf_files = [f for f in os.listdir(self.folder_path) if f.lower().endswith('.pdf')]
            total = len(pdf_files)
            data = []

            if total == 0:
                self.finish_ui("No PDF files found in the selected folder.")
                return

            for i, filename in enumerate(pdf_files):
                base_name = os.path.splitext(filename)[0]
                file_path = os.path.join(self.folder_path, filename)
                title = extract_title_from_pdf(file_path)
                if title.lower().startswith("error") or "no " in title.lower():
                    data.append((base_name, "-", title))
                else:
                    data.append((base_name, title, ""))
                self.append_log(f"{base_name} --> {title}")
                self.update_progress((i + 1) / total * 100)

            self.csv_path = save_to_csv(data, self.folder_path)
            self.finish_ui(f"\n✅ CSV saved to: {self.csv_path}")
        except Exception as e:
            self.finish_ui(f"\n❌ Error: {e}")

    def update_progress(self, value):
        self.master.after(0, lambda: self.progress.config(value=value))

    def append_log(self, message):
        self.master.after(0, lambda: self.log(message))

    def finish_ui(self, message):
        self.master.after(0, lambda: self.log(message))
        self.master.after(0, lambda: self.run_button.config(state=tk.NORMAL))
        self.master.after(0, lambda: self.select_button.config(state=tk.NORMAL))
        self.master.after(0, lambda: self.open_csv_button.config(state=tk.NORMAL if self.csv_path else tk.DISABLED))

    def open_csv(self):
        if self.csv_path and os.path.isfile(self.csv_path):
            try:
                if sys.platform.startswith("darwin"):
                    os.system(f'open "{self.csv_path}"')
                elif os.name == "nt":
                    os.startfile(self.csv_path)
                elif os.name == "posix":
                    os.system(f'xdg-open "{self.csv_path}"')
            except Exception as e:
                messagebox.showerror("Error Opening File", f"Could not open CSV file:\n{e}")
        else:
            messagebox.showwarning("File Not Found", "CSV file not found or not generated yet.")

    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.yview(tk.END)
        self.log_area.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFTitleExtractorApp(root)
    root.mainloop()
