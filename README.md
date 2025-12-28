# Orbit

**Your Executive AI Task Manager.**
Orbit transforms your simple to-do list into a strategic daily briefing. It uses Google's Gemini AI to analyze your deadlines, prioritize your focus, and act as your personal productivity assistant.

## Features
**The Executive Brain:** A Daily AI briefing that analyzes your tasks and tells you exactly what to do first.
**Smart Deadlines:** Visual countdowns that create urgency (e.g., "🔥 Due Today", "⏳ 2 days left").
**Focus Mode:** A built-in Pomodoro timer to help you execute tasks immediately.
**Multi-User Orbit:** Supports multiple profiles with persistent logins via URL parameters.


## Tech Stack
**Frontend:** Streamlit (Python)
**AI:** Google Gemini 2.5 Flash (Generative AI)
**Data:** Local JSON Storage


## How to Run Locally

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/da-b0s/orbit-task-manager.git](https://github.com/da-b0s/orbit-task-manager.git)
    ```

2.  **Install dependencies:**
    ```bash
    pip install streamlit google-generativeai
    ```

3.  **Set up Secrets:**
    Create a folder named `.streamlit` in the root directory. Inside it, create a file named `secrets.toml` and add your key:
    ```toml
    GEMINI_API_KEY = "your_google_gemini_key"
    ```

4.  **Run the app:**
    ```bash
    streamlit run dashboard.py
    ```

5.  The app will automatically open in your browser (usually at http://localhost:8501).

---
Made with ❤️ by b0s