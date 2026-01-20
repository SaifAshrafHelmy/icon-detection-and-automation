# 🎯 Icon Detection App

A desktop automation tool that uses AI-powered icon detection to automate tasks on Windows.

## 📋 Overview

This application connects to a remote AI API to detect desktop icons and automate interactions with Windows applications. It can capture screenshots, locate specific app icons, and perform automated workflows like saving content to Notepad.

## ✨ Features

- **AI-Powered Icon Detection**: Uses UGround model through a remote API to detect and locate application icons on your desktop
- **Desktop Automation**: Automates mouse movements, clicks, and keyboard inputs
- **Screenshot Analysis**: Captures and analyzes desktop screenshots for icon detection
- **Safety Features**: 
  - Emergency stop hotkey (`Ctrl+Shift+Q`)
  - Confirmation mode for manual verification
  - Auto mode for unattended operation
- **Notepad Integration**: Automated content saving and file management

## 🧠 AI Model: UGround-V1

The core of the detection engine is **UGround-V1**, a state-of-the-art GUI visual grounding model developed by the **OSU NLP Group** and **Orby AI**.

### 📊 Key Information & Metrics

- **Architecture**: Based on the powerful `Qwen2-VL` vision-language model.
- **Training Data**: Trained on the largest GUI visual grounding dataset to date, featuring **10 Million GUI elements** across 1.3 million screenshots.
- **Capabilities**:
  - High-precision mapping of text and icon descriptions to (x, y) coordinates.
  - Native support for arbitrary resolutions and aspect ratios.
  - Advanced reasoning for ambiguous UI elements.

### 📈 Performance (ScreenSpot Benchmark)

| Category | Score (UGround-V1-7B) |
| :--- | :--- |
| **Average** | **86.3** |
| Web-Icon | 84.0 |
| Desktop-Icon | 76.4 |
| Mobile-Icon | 79.9 |
| Web-Text | 90.9 |
| Desktop-Text | 93.8 |
| Mobile-Text | 93.0 |

This project uses the **2B parameter version** (or **7B** depending on GPU availability) to ensure fast inference while maintaining high accuracy for desktop icon detection.

## 🚀 Getting Started

Follow these steps in order to set up and run the Icon Detection App:

### Step 1: Install Local Dependencies

1. Clone or download this repository to your local machine
2. Open a terminal in the project directory
3. Install and sync the required Python packages:
```bash
uv sync
```

**Dependencies include**: `pyautogui`, `pyperclip`, `requests`, `Pillow`, `keyboard`

### Step 2: Setup Google Colab API Server

The app requires a remote AI detection API running on Google Colab with T4 GPU.

#### 2.1 Upload and Configure Colab Notebook

1. **Upload the notebook**: Open `icon_detector_final.ipynb` in [Google Colab](https://colab.research.google.com)

2. **Enable T4 GPU Runtime** (Required):
   - Click `Runtime` → `Change runtime type`
   - Under **Hardware accelerator**, select `T4 GPU`
   - Click `Save`
   - ✓ This is essential for running the AI model efficiently

#### 2.2 Setup Ngrok Tunnel

1. **Get your ngrok authtoken**:
   - Visit [ngrok.com](https://ngrok.com) and sign up for a free account
   - Go to [Your Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
   - Copy your authtoken (you'll need it in the next step)

2. **Run the Colab notebook**:
   - Click `Runtime` → `Run all` (or execute cells one by one)
   - When prompted, **paste your ngrok authtoken** and press Enter
   - Wait for the setup to complete (this may take a few minutes)

3. **Copy the API URL**:
   - After setup completes, you'll see output like:
     ```
     ============================================================
     ✓ API URL: https://xxxx-xx-xxx-xxx-xx.ngrok-free.app
     ============================================================
     ```
   - **Copy this entire URL** - you'll need it in the next step

**What the notebook does**:
- Installs: `pyngrok`, `flask`, `transformers`, `accelerate`, `qwen-vl-utils`, `easyocr`
- Loads **UGround-V1** vision model (2B for T4 GPU, 7B for larger GPUs)
- Initializes OCR verification with EasyOCR
- Starts Flask API server on port `5001`
- Creates ngrok tunnel to expose the API publicly

### Step 3: Run the Automation Script

1. **Start the script**:
```bash
uv run python main.py
```

2. **Enter the ngrok URL**:
   - When prompted: `Enter ngrok URL:`
   - Paste the URL you copied from Colab (e.g., `https://xxxx-xx-xxx-xxx-xx.ngrok-free.app`)
   - Press Enter

3. **Enter the app name**:
   - When prompted: `Enter app name to detect (e.g., Notepad):`
   - Type the name of the application icon you want to detect (e.g., `Notepad`, `Chrome`)
   - Press Enter

4. **Wait for automation**:
   - The script will connect to the API
   - Capture your desktop screenshot
   - Detect the specified icon
   - Perform automated tasks (e.g., opening Notepad, saving files)

**Command-line options** (optional):
```bash
# Use a specific screenshot file instead of live capture
uv run python main.py --screenshot path/to/screenshot.png

# Run in auto mode without confirmation prompts
uv run python main.py --auto

# Specify app name directly
uv run python main.py --app Notepad --auto
```

### API Endpoints Reference

The Colab server exposes:

- **GET** `/health` - Check API status
- **POST** `/detect` - Detect icons (used by main.py)

**Request format**:
```json
{
  "image": "<base64_encoded_image>",
  "description": "Locate the Notepad Windows application icon",
  "context": "desktop",
  "iterations": 2
}
```

**Response format**:
```json
{
  "found": true,
  "x": 150,
  "y": 200,
  "confidence": 0.87,
  "method": "ReGround-v2",
  "ocr_verification": "match",
  "time_seconds": 3.2
}
```

### Important Notes

- ⚠️ **Keep Colab running** - The API only works while the notebook cell is active
- ⚠️ **Temporary URL** - The ngrok URL changes each time you restart Colab
- ⚠️ **Free tier limits** - Ngrok free tier has connection/bandwidth limits
- ✓ **T4 GPU required** - Necessary for acceptable performance

## 🛡️ Safety

- **Emergency Stop**: Press `Ctrl+Shift+Q` at any time to abort the automation
- **Failsafe**: Move mouse to screen corner to trigger PyAutoGUI failsafe
- **Confirmation Mode**: Review detection results before proceeding (default)

## 📁 Output

- Detection previews and saved files are stored in: `~/Desktop/tjm-project/`
- Preview images show detected icon locations with visual markers

## 🔧 Configuration

Edit the configuration section in `main.py`:
- `API_URL`: API endpoint for fetching posts
- `OUTPUT_DIR`: Directory for saved files
- `pyautogui.PAUSE`: Delay between PyAutoGUI actions

## 📝 Notes

- Ensure the remote AI API is running and accessible before starting
- The app requires active window focus for certain operations
- Works best with a clean desktop for accurate icon detection

## 🤝 Contributing

Feel free to submit issues or pull requests for improvements.

## 📄 License

This project is open source and available for personal and educational use.
