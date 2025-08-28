<div align="center">
  <img src="src/gui/icons/app.png" width="150" height="150" alt="App Icon" />
  <h1>Novel Translator</h1>
  <p>
    <b>A comprehensive desktop application for managing, processing, and translating novels and text documents.</b>
  </p>
  <p>
    <i><a href="README_ES.md">README in Spanish</a>.</i>
  </p>
</div>

A complete desktop application to manage, process, and translate novels and text documents. Designed specifically to handle large literary projects with support for multiple AI providers, advanced chapter management, ebook creation, and EPUB importation.

## Motivations

I created this application because I have some novels that were translated to Spanish but with very poor quality. It's also useful for translating novels that don't yet have quality Spanish translations. I designed it to work alongside the LightNovel-Crawler tool (https://github.com/dipu-bd/lightnovel-crawler).

## Quick Start

### Requirements
- Python 3.8+
- UV (Python package manager)
- PyQt6>=6.0.0
- See [Installation](#installation) for full dependencies

### Installation
1. Clone the repository:
```bash
git clone https://github.com/mfloresz/novel-manager.git
cd novel-manager
```

2. Create virtual environment:
```bash
uv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Configure API keys (create `.env` file from `.env.example`)

5. Run the application:
```bash
uv run python main.py
```

## Key Features

### 📁 File Management
- Intuitive graphical interface for file navigation
- **EPUB Import**: Convert existing EPUBs to text files
- Automatic file synchronization and preview
- File status tracking with color indicators
- Recent folders history for quick access

### 🌐 Advanced Translation
![Translation](assets/translate.webp)

- **Multiple AI Providers**: Google Gemini, Chutes AI, Together AI, DeepInfra, OpenAI
- **Check and Refine**: Includes options to verify the quality of the translation against the original text and to improve it through an additional refinement process. Both options consume a significant amount of additional tokens.
- **Advanced Check and Refine Configuration**: Allows configuring a different provider and model for the check and refine steps. This can be configured globally in the settings or for a single session from the translation panel.

### 🧹 Text Cleaning
![Translation](assets/clean.webp)

- **5 Cleaning Modes**: Delete content after text, remove duplicates, delete specific lines, normalize spacing, find & replace
- **Range Control**: Process specific chapters or all files
- **Preview & Backup**: Preview changes before applying and automatic backup

### 📚 EPUB Creation
![Translation](assets/ebook.webp)

- **Professional Conversion**: TXT to EPUB with literary structure
- **Smart Metadata**: Automatic title, author, and description management
- **Cover Detection**: Automatic cover image detection (cover.jpg, portada.png, etc.)
- **Responsive Design**: Professional CSS styles optimized for e-readers

## Usage Guide

### Basic Workflow
1. **Setup**: Configure API keys and translation settings
2. **Import**: Load existing files or import from EPUB
3. **Process**: Clean text, translate chapters, or create EPUBs
4. **Export**: Generate professional ebooks

### Interface Overview
- **Main Panel**: File browser with status indicators
- **Translate Tab**: Configure and execute translations
- **Clean Tab**: Apply text cleaning operations
- **Ebook Tab**: Create EPUBs with metadata and covers

## Configuration

### API Setup
Create a `.env` file with your API keys:
```env
GOOGLE_GEMINI_API_KEY=your_key_here
CHUTES_API_KEY=your_key_here
# Add other provider keys as needed
```

### Application Settings
- **Location**: `src/config/config.json`
- **Customizable**: Default provider, model, languages, segmentation size
- **Persistence**: Settings saved automatically per project

## Advanced Features

### 🏗️ Architecture
- **Hybrid Database**: SQLite with automatic JSON backup
- **Asynchronous Processing**: Background translations without UI blocking
- **Smart State Management**: Real-time status tracking with persistence
- **Modular Design**: Easy to extend with new providers and features

### 🔧 Technical Details
- **Performance**: Optimized for large files (100+ chapters)
- **Error Handling**: Robust retry mechanisms and logging
- **Resource Management**: Automatic rate limit control and monitoring
- **Logging**: Detailed session logging with export capabilities

## Project Structure
```
novel-manager/
├── src/
│   ├── gui/           # User Interface
│   ├── logic/         # Business Logic
│   └── config/        # Configuration Files
├── main.py            # Entry Point
├── requirements.txt   # Dependencies
└── README.md          # This File
```

## Multilingual Support
- **Interface Languages**: English (US), Spanish (Mexico)
- **Translation Languages**: English, Spanish (Mexico), with automatic detection
- **Adding Languages**: Create JSON files in `src/config/i18n/`

## Disclaimer
While this project works, I cannot guarantee its functionality as it was created with the help of AI.
