"""
This file contains all the prompt templates for various AI providers.
Each provider may have a different required format for their API calls.
"""

# --- Base Concept (used by all) ---
class StoryConcept:
    def __init__(self, genre: str, theme: str, core_idea: str, style: str):
        self.genre = genre
        self.theme = theme
        self.core_idea = core_idea
        self.style = style

# --- 1. Google Gemini ---
def create_gemini_prompt(concept: StoryConcept) -> str:
    """
    Generates a prompt for Google Gemini, which requires a specific JSON output format.
    """
    # This is the original prompt, which works well with Gemini's JSON mode.
    return f"""You are a world-class Story Architect. Your task is to generate a complete, coherent, and compelling story outline based on the user's initial concepts.

**Instructions:**
1.  **Analyze the Core Concepts:** Carefully consider the provided Genre, Theme, Core Idea, and Style.
2.  **Structure the Outline:** Create a three-act structure (Act I, Act II, Act III).
3.  **Output Format:** You MUST return the outline as a valid JSON object. Do not include any explanatory text before or after the JSON. The JSON object should have a single root key "outline" which contains the three acts. Each act should be an object with a "title" and a list of "chapters". Each chapter should be an object with a "title" and a "summary".

**Core Concepts:**
*   **Genre:** {concept.genre}
*   **Theme:** {concept.theme}
*   **Core Idea:** {concept.core_idea}
*   **Style:** {concept.style}

**Example JSON Output Structure:**
{{
  "outline": {{
    "act_1": {{...}},
    "act_2": {{...}},
    "act_3": {{...}}
  }}
}}

Now, generate the JSON for the story described above.
"""

# --- 2. OpenAI (GPT series) ---
def create_openai_prompt(concept: StoryConcept) -> list[dict]:
    """
    Generates a prompt for OpenAI's Chat Completions API (GPT-4, etc.).
    It uses a system message and a user message for better results.
    """
    system_message = (
        "You are a world-class Story Architect. Your task is to generate a complete, coherent, and compelling story outline based on the user's initial concepts. "
        "You MUST return the outline as a valid JSON object. Do not include any explanatory text before or after the JSON. "
        "The JSON object should have a single root key \"outline\" which contains the three acts. Each act should be an object with a \"title\" and a list of \"chapters\". "
        "Each chapter should be an object with a \"title\" and a \"summary\" in a three-act structure."
    )
    user_message = (
        f"Please generate a story outline with the following concepts:\n"
        f"- **Genre:** {concept.genre}\n"
        f"- **Theme:** {concept.theme}\n"
        f"- **Core Idea:** {concept.core_idea}\n"
        f"- **Style:** {concept.style}"
    )
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

# --- 3. Anthropic (Claude series) ---
def create_anthropic_prompt(concept: StoryConcept) -> list[dict]:
    """
    Generates a prompt for Anthropic's Claude models.
    Claude also uses a system prompt and a user message structure.
    """
    system_message = (
        "You are a world-class Story Architect. Your task is to generate a complete, coherent, and compelling story outline based on the user's initial concepts. "
        "Please return the outline as a valid JSON object inside a single top-level `json` code block. Do not include any other text. "
        "The JSON object should have a single root key \"outline\" which contains the three acts. Each act should be an object with a \"title\" and a list of \"chapters\". "
        "Each chapter should be an object with a \"title\" and a \"summary\" in a three-act structure."
    )
    user_message = (
        f"Please generate a story outline with the following concepts:\n"
        f"- **Genre:** {concept.genre}\n"
        f"- **Theme:** {concept.theme}\n"
        f"- **Core Idea:** {concept.core_idea}\n"
        f"- **Style:** {concept.style}"
    )
    return [
        {"role": "user", "content": user_message}
    ], system_message # Anthropic separates the system prompt

# --- Add other providers as needed (Zhipu, Baidu, etc.) ---
# For now, we will focus on these three to establish the pattern.
# Each would have its own function `create_zhipu_prompt`, etc.