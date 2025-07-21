import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

# --- Provider SDKs ---
import google.generativeai as genai
from openai import OpenAI
from anthropic import Anthropic

# --- Prompt Templates ---
from prompts import (
    StoryConcept,
    create_gemini_prompt,
    create_openai_prompt,
    create_anthropic_prompt
)

# --- Constants ---
DATA_DIR = Path("../data")
DATA_DIR.mkdir(exist_ok=True)

# --- Provider Enum ---
class Provider(str, Enum):
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    BAIDU = "baidu"
    ALIBABA = "alibaba"

# --- Pydantic Models ---
class ProjectConcept(BaseModel):
    genre: str
    theme: str
    core_idea: str
    style: str

class ProjectCreate(BaseModel):
    title: str
    concept: ProjectConcept
    provider: Provider
    api_key: str = Body(..., description="API key for the selected provider, handled by the backend.")

class Project(BaseModel):
    id: str
    title: str
    created_at: datetime
    provider: Provider
    concept: ProjectConcept
    outline: dict = Field(default_factory=dict)

class ProjectMetadata(BaseModel):
    id: str
    title: str
    created_at: datetime

# --- FastAPI App ---
app = FastAPI(title="Story Architect AI API")

# --- Helper Functions (File I/O) ---
# ... (same as before) ...

# --- API Endpoints ---
@app.post("/api/projects", response_model=Project, status_code=201)
def create_project(project_data: ProjectCreate):
    """Creates a new story project by generating an outline from the selected provider."""
    concept = StoryConcept(**project_data.concept.model_dump())
    outline_json = {}

    try:
        # --- AI Provider Dispatcher ---
        if project_data.provider == Provider.GOOGLE:
            genai.configure(api_key=project_data.api_key)
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            prompt = create_gemini_prompt(concept)
            response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(response_mime_type="application/json"))
            outline_json = json.loads(response.text)

        elif project_data.provider == Provider.OPENAI:
            client = OpenAI(api_key=project_data.api_key)
            messages = create_openai_prompt(concept)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"}
            )
            outline_json = json.loads(response.choices[0].message.content)

        elif project_data.provider == Provider.ANTHROPIC:
            client = Anthropic(api_key=project_data.api_key)
            messages, system_prompt = create_anthropic_prompt(concept)
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            )
            # Extract JSON from the text content
            json_text = response.content[0].text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:-3].strip()
            outline_json = json.loads(json_text)
        
        # TODO: Add cases for Zhipu, Moonshot, Baidu, Alibaba
        else:
            raise HTTPException(status_code=400, detail=f"Provider '{project_data.provider}' not yet supported.")

        # --- Save Project ---
        new_project = Project(
            id=f"story_{uuid.uuid4()}",
            title=project_data.title,
            created_at=datetime.utcnow(),
            provider=project_data.provider,
            concept=project_data.concept,
            outline=outline_json
        )
        
        path = DATA_DIR / f"{new_project.id}.json"
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_project.model_dump_json(indent=4))
            
        return new_project

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON from model response: {e}")
    except Exception as e:
        # Catch-all for API errors, config errors, etc.
        raise HTTPException(status_code=500, detail=f"An error occurred with provider {project_data.provider}: {str(e)}")

# --- Existing Endpoints (Unchanged) ---
@app.get("/api/projects", response_model=list[ProjectMetadata])
def list_projects():
    # ... (implementation remains the same)
    projects = []
    for project_file in DATA_DIR.glob("*.json"):
        with open(project_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                projects.append(ProjectMetadata(**data))
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
    projects.sort(key=lambda p: p.created_at, reverse=True)
    return projects

@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(project_id: str):
    # ... (implementation remains the same)
    path = DATA_DIR / f"{project_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return Project(**data)

@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    # ... (implementation remains the same)
    path = DATA_DIR / f"{project_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    os.remove(path)
    return