# ReceiptOCR-AI

## AI-Powered Receipt & Bill Analyzer

ReceiptOCR-AI is a Python-based OCR application that extracts useful information from receipt and bill images. It uses **Tesseract OCR** to recognize text and **OpenCV** to preprocess and analyze the receipt image.

The application can identify important receipt details such as merchant name, date, invoice number, GSTIN, line items, taxes, subtotal, and total amount. It also performs mathematical verification to check whether the detected amounts are consistent with the printed total.

---

## Features

* Upload receipt or bill images
* Extract text using Tesseract OCR
* Detect merchant name
* Extract receipt date and time
* Detect invoice/receipt number
* Detect GSTIN
* Extract individual line items
* Detect item quantities and prices
* Calculate subtotal and tax
* Identify the final/printed total
* Verify receipt calculations
* Analyze image sharpness
* Check brightness and contrast
* Estimate receipt skew
* Detect separator lines
* Identify barcode/QR-like regions
* Download detected items as a CSV file
* Display OCR results through an interactive Streamlit interface

---

## How It Works

The application follows a simple OCR and computer-vision pipeline:

```text
Receipt Image
      ↓
Image Preprocessing
      ↓
Tesseract OCR
      ↓
Text Line Detection
      ↓
Receipt Information Extraction
      ↓
Line Item & Amount Detection
      ↓
Tax & Total Calculation
      ↓
Mathematical Verification
      ↓
Image Quality & Layout Analysis
      ↓
Results Dashboard
```

---

## Technologies Used

| Technology          | Purpose                              |
| ------------------- | ------------------------------------ |
| Python              | Core programming language            |
| Streamlit           | Web application interface            |
| Tesseract OCR       | Text recognition                     |
| Pytesseract         | Python interface for Tesseract       |
| OpenCV              | Image processing and computer vision |
| NumPy               | Numerical and image operations       |
| Pandas              | Tabular data processing              |
| Pillow              | Image loading and processing         |
| Regular Expressions | Receipt information extraction       |

---

## Project Architecture

### 1. Image Upload

Users can upload receipt images in:

* PNG
* JPG
* JPEG

The uploaded image is displayed in the application before analysis.

### 2. Image Preprocessing

The receipt image is converted to grayscale and enhanced before OCR.

The preprocessing pipeline includes:

* Grayscale conversion
* Image enlargement
* Noise reduction
* CLAHE contrast enhancement
* Otsu thresholding
* Adaptive thresholding

Multiple processed versions of the image are generated to improve OCR reliability.

### 3. OCR Processing

Tesseract OCR is used to detect text from the processed receipt images.

The application tries multiple OCR configurations and selects the result with the highest confidence-based score.

### 4. Receipt Information Extraction

Regular expressions are used to identify important fields from the OCR output.

The application attempts to extract:

```text
Merchant
Date
Time
Invoice Number
GSTIN
```

The receipt header extraction logic is implemented using predefined date, invoice, GSTIN, and time patterns.

### 5. Line Item Extraction

The system identifies receipt items by searching for price-like values and extracting the text before the detected amount.

It also attempts to identify quantities such as:

```text
2 x Item
Item x 2
Item * 2
```

The extracted information is stored as:

```text
Item | Qty | Amount
```

and displayed as a Pandas DataFrame.

### 6. Tax and Total Extraction

The application identifies:

* Subtotal
* GST
* CGST
* SGST
* IGST
* VAT
* Total
* Grand Total
* Amount Due
* Net Payable

The extracted tax values are combined to calculate the detected tax amount.

### 7. Mathematical Verification

One of the main features of ReceiptOCR-AI is receipt calculation verification.

The application compares:

```text
Detected Item Sum
        +
Detected Tax
        =
Expected Total
```

with the printed total on the receipt.

If the difference is within a small rounding tolerance, the receipt is considered mathematically consistent.

If there is a mismatch, the application warns that OCR may have missed an item or incorrectly recognized a number.

### 8. Computer Vision Analysis

OpenCV is used to analyze the visual quality and layout of the receipt.

The application calculates:

* Sharpness
* Brightness
* Contrast
* Skew angle
* Separator lines
* Barcode/QR-like regions

This helps identify whether the uploaded image is suitable for reliable OCR processing.

---

## Application Output

After uploading a receipt, the application provides several sections:

### OCR Result

Displays the text detected from the receipt.

### Receipt Details

Displays:

* Merchant
* Date
* Time
* Invoice Number
* GSTIN

### Line Items

Displays detected items, quantities, and amounts in a table.

The detected line items can also be downloaded as:

```text
receipt_items.csv
```

### Totals & Tax

Displays:

* Subtotal
* Tax
* Total
* Individual tax values

### Math Verification

Checks whether the detected receipt values add up correctly.

### Image Quality & Layout

Displays:

* Sharpness
* Brightness
* Skew
* Separator lines

### Observations

The application provides additional observations such as GSTIN detection and the most expensive detected item.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hasinithrinadh/ReceiptOCR-AI.git
cd ReceiptOCR-AI
```

### 2. Install Python Dependencies

```bash
pip install streamlit opencv-python numpy pandas pytesseract pillow
```

### 3. Install Tesseract OCR

ReceiptOCR-AI requires **Tesseract OCR** to perform text recognition.

For Windows, install Tesseract OCR and make sure the executable is available through PATH.

The application also checks common Windows installation locations automatically:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
C:\Program Files (x86)\Tesseract-OCR\tesseract.exe
```

The application stops with an installation message if Tesseract cannot be found.

---

## Running the Application

Run the Streamlit application using:

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

Upload a receipt image and allow the application to process it.

---

## Example Workflow

```text
1. Upload Receipt
       ↓
2. Preprocess Image
       ↓
3. Run OCR
       ↓
4. Extract Receipt Details
       ↓
5. Detect Line Items
       ↓
6. Extract Tax & Total
       ↓
7. Verify Calculations
       ↓
8. Analyze Image Quality
       ↓
9. Display Results
```

---

## Project Structure

```text
ReceiptOCR-AI/
│
├── app.py
├── README.md
├── requirements.txt
│
└── sample_receipts/
    └── receipt.jpg
```

---

## Requirements

Example `requirements.txt`:

```text
streamlit
opencv-python
numpy
pandas
pytesseract
Pillow
```

Tesseract OCR is a separate system dependency and should be installed on the machine.

---

## Limitations

ReceiptOCR-AI depends on OCR quality, so results may vary depending on the receipt image.

Possible issues include:

* Blurry images
* Poor lighting
* Glare
* Tilted receipts
* Unusual receipt layouts
* Handwritten text
* Low-resolution images
* OCR misreading numbers
* Missing or incorrectly detected line items

The application itself warns users when image quality may affect OCR accuracy.

Important financial figures should always be verified against the original receipt.

---

## Future Improvements

Possible future enhancements include:

* Automatic receipt rotation
* Better table/column detection
* Support for PDF receipts
* Multi-language OCR
* Better product-name extraction
* Improved quantity detection
* Duplicate receipt detection
* Expense categorization
* Monthly expense analytics
* Database storage
* User authentication
* Cloud deployment
* AI-based receipt understanding
* Export complete receipt reports as PDF or Excel

---

## Learning Outcomes

This project demonstrates practical implementation of:

* Optical Character Recognition
* Image preprocessing
* Computer vision
* Regular expression-based information extraction
* Data processing with Pandas
* Streamlit application development
* OCR confidence handling
* Receipt data extraction
* Mathematical validation
* Image-quality analysis

---

## Conclusion

ReceiptOCR-AI combines **OCR, image processing, pattern matching, and data analysis** into a practical receipt-processing application.

Instead of simply converting an image into text, the project attempts to transform an unstructured receipt into structured information and then verify the extracted financial values.

It demonstrates how computer vision and OCR can be applied to a real-world document-processing problem.

---

## Author

**D. Hasini**

B.Sc. Computer Science with AI

GitHub:
https://github.com/hasinithrinadh/ReceiptOCR-AI

---

## Disclaimer

ReceiptOCR-AI is an OCR-based analysis tool. Extracted information may contain errors due to image quality or OCR limitations. Always verify important financial information using the original receipt.

