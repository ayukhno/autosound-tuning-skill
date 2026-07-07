===============================================================================
  !!! READ ME FIRST !!!
===============================================================================

Welcome to the manual car audio tuning pipeline!
Before making your first measurement or opening a chat with the AI, please read
these three critical rules.

-------------------------------------------------------------------------------
1. HOW TO READ .MD (MARKDOWN) FILES FOR A CLEAN, READABLE EXPERIENCE?
-------------------------------------------------------------------------------
All step templates and instructions in this folder are written in Markdown (.md). 
They contain tables, lists, and diagrams. If you open them as plain text, they 
will look cluttered with #, *, and | symbols.

To read them in a clean, rendered view (like a nice web page):

* OPTION A (Recommended for PC): VS Code (Visual Studio Code)
  Open any .md file in VS Code and press the shortcut:
  - On macOS:  Cmd + Shift + V
  - On Windows: Ctrl + Shift + V
  This will open an interactive preview window (Markdown Preview).

* OPTION B (Free Powerful App): Obsidian
  Obsidian (obsidian.md) is a free note-taking app for Windows, macOS, iOS, and 
  Android. Simply drag and drop the "manual_step-by-step" folder into Obsidian 
  as a new vault. It will perfectly render all tables, links, and even 
  interactive mermaid diagrams.

* OPTION C (Quick & Offline): GitHub / GitLab
  Since this project is hosted on GitHub, you can simply open your repository page 
  in a browser. GitHub automatically renders .md files in a beautiful, easy-to-read style.

* OPTION D (Browser-based): Chrome/Firefox Extensions
  Install a free "Markdown Viewer" extension in your browser. After that, you can 
  simply drag and drop any .md file directly into your browser window to render it 
  as a clean, beautiful document.

-------------------------------------------------------------------------------
2. THE GOLDEN RULE: STRICT STATELESS MODE (PROTECTION AGAINST AI HALLUCINATIONS)
-------------------------------------------------------------------------------
WEB CHATS (ChatGPT, Claude, Gemini) HAVE A LIMITED MEMORY (Context Window).
When a conversation lasts more than 1-2 hours, the model begins to "drift": 
it confuses delays, forgets crossover frequencies, makes math errors, and provides 
contradictory advice.

* RULE: Every new tuning step MUST be a completely NEW, CLEAN chat session!
* Workflow:
  1. Update your "autosound_context.md" file on disk.
  2. Open a completely NEW chat with the AI.
  3. Copy the corresponding step prompt (e.g., step_2_tonal_balance_eq.md).
  4. Send it along with the contents of your updated "autosound_context.md".
  5. Get the calculations and apply them to your DSP.
  6. Close/delete that chat and open a new one for the next step.

This protects you 100% against mathematical errors made by the AI and saves 
you a massive amount of time!

-------------------------------------------------------------------------------
3. SAFETY INSTRUCTIONS: DON'T BURN YOUR SPEAKERS!
-------------------------------------------------------------------------------
* Tweeters (HF) and midranges (MF) are physically fragile.
* NEVER run a measurement Sweep in REW on tweeters or midranges without an active 
  protective high-pass filter (HPF) in your DSP!
* Safe starting filters for measurements:
  - For Tweeters: HPF not lower than 1000-2000 Hz (usually at least 1.1 Fs of the speaker), with a slope of 24 dB/oct (e.g., LR4).
  - For Midranges: HPF not lower than 100-300 Hz (usually at least 1.1 Fs of the speaker), with a slope of 24 dB/oct (e.g., LR4).
* Always make your first test measurement at a very low volume!

-------------------------------------------------------------------------------
4. YOUR LOCAL SYSTEM PASSPORT (autosound_context.md) — WHO FILLS IT OUT?
-------------------------------------------------------------------------------
The "autosound_context.md" file is the single source of truth about your system, 
which holds the entire pipeline together. The process of filling it out is simple:

A. HOW TO CREATE THIS FILE AT THE START? (Two paths):
   * PATH 1 (AI fills it out): Copy the prompt from "step_0_intake_and_setup.md" 
     into a new chat. The AI will conduct a brief interview (asking 2-3 questions 
     at a time about your car, speakers, and amplifiers). Answer in natural language, 
     and at the end, the AI will generate and output a fully structured text. 
     Copy and save it as "autosound_context.md".
   * PATH 2 (Manual Quick Start): If you do not want to go through the interview, 
     take our ready-made template "autosound_context_template.md", open it in 
     a text editor, replace the placeholders in brackets (e.g., [DSP Model]) 
     with your real data, and save it as "autosound_context.md".

B. HOW IS IT UPDATED DURING TUNING? (Copy-pasting results):
   When you complete Steps 1, 2, or 3, the AI will calculate new values for you 
   (delays, crossover slopes, EQ bands, or phase angles). 
   After entering these settings into your DSP (via your processor's software), 
   simply copy these final tables or values from the chat window and paste them 
   into the corresponding sections of your local "autosound_context.md" file.

This takes just 30 seconds, but your "game save" remains 100% up-to-date! When you 
proceed to the next step, the new clean chat gets the updated file and instantly 
understands your current system state without any repetitive questions.

Have a great tuning session and enjoy pure, transparent sound!
===============================================================================
