
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
    create_anthropic_prompt,
    create_chapter_analysis_prompt
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

class ChapterAnalysisRequest(BaseModel):
    chapter_text: str
    provider: Provider
    api_key: str

class ChapterAnalysisResponse(BaseModel):
    summary: str
    characters: list[str]

# --- FastAPI App ---
app = FastAPI(title="Story Architect AI API")

# --- Helper Functions (File I/O) ---
def get_project_path(project_id: str) -> Path:
    return DATA_DIR / f"{project_id}.json"

def save_project(project: Project):
    path = get_project_path(project.id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=4))

def load_project(project_id: str) -> Project:
    path = get_project_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return Project(**data)

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
            json_text = response.content[0].text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:-3].strip()
            outline_json = json.loads(json_text)
        
        else:
            raise HTTPException(status_code=400, detail=f"Provider '{project_data.provider}' not yet supported.")

        new_project = Project(
            id=f"story_{uuid.uuid4()}",
            title=project_data.title,
            created_at=datetime.utcnow(),
            provider=project_data.provider,
            concept=project_data.concept,
            outline=outline_json
        )
        
        save_project(new_project)
        return new_project

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON from model response: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred with provider {project_data.provider}: {str(e)}")

@app.post("/api/analyze-chapter", response_model=ChapterAnalysisResponse)
async def analyze_chapter(request: ChapterAnalysisRequest):
    """Analyzes a chapter's text to extract summary and characters."""
    try:
        prompt = create_chapter_analysis_prompt(request.chapter_text)
        analysis_json = {}

        if request.provider == Provider.GOOGLE:
            genai.configure(api_key=request.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(response_mime_type="application/json"))
            analysis_json = json.loads(response.text)

        elif request.provider == Provider.OPENAI:
            client = OpenAI(api_key=request.api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            analysis_json = json.loads(response.choices[0].message.content)

        elif request.provider == Provider.ANTHROPIC:
            client = Anthropic(api_key=request.api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            json_text = response.content[0].text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:-3].strip()
            analysis_json = json.loads(json_text)
        
        else:
            raise HTTPException(status_code=400, detail=f"Provider '{request.provider}' not yet supported for analysis.")

        return ChapterAnalysisResponse(**analysis_json)

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON from model response: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred with provider {request.provider}: {str(e)}")

@app.get("/api/projects", response_model=list[ProjectMetadata])
def list_projects():
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
    return load_project(project_id)

@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str):
    path = get_project_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    os.remove(path)
    return
