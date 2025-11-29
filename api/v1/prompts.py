"""
Prompt Library API - Save and reuse prompt templates.

Features:
- Create, read, update, delete prompts
- Template variables {{variable}}
- Categories and tags
- Usage tracking
- Sharing and favorites
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
import secrets


router = APIRouter()


class PromptTemplate(BaseModel):
    """A saved prompt template."""
    id: str
    name: str
    description: Optional[str] = None
    template: str
    variables: List[str] = []
    category: str = "general"
    tags: List[str] = []
    is_public: bool = False
    is_favorite: bool = False
    usage_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    author: Optional[str] = None


class PromptCreate(BaseModel):
    """Create a new prompt template."""
    name: str
    description: Optional[str] = None
    template: str
    category: str = "general"
    tags: List[str] = []
    is_public: bool = False


class PromptUpdate(BaseModel):
    """Update a prompt template."""
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    is_favorite: Optional[bool] = None


class PromptExecute(BaseModel):
    """Execute a prompt with variables."""
    prompt_id: Optional[str] = None
    template: Optional[str] = None
    variables: Dict[str, str] = {}
    model: Optional[str] = "gpt-4o-mini"


# In-memory storage (replace with database in production)
prompts_db: Dict[str, PromptTemplate] = {}

# Seed with example prompts
EXAMPLE_PROMPTS = [
    {
        "name": "Summarize Text",
        "description": "Summarize any text into key points",
        "template": "Please summarize the following text into {{num_points}} key points:\n\n{{text}}",
        "category": "writing",
        "tags": ["summary", "writing", "analysis"]
    },
    {
        "name": "Code Review",
        "description": "Review code for bugs and improvements",
        "template": "Please review this {{language}} code and identify:\n1. Potential bugs\n2. Performance issues\n3. Best practice violations\n4. Suggestions for improvement\n\n```{{language}}\n{{code}}\n```",
        "category": "coding",
        "tags": ["code", "review", "debugging"]
    },
    {
        "name": "Explain Like I'm 5",
        "description": "Explain complex topics simply",
        "template": "Explain {{topic}} in simple terms that a 5-year-old would understand. Use analogies and examples.",
        "category": "education",
        "tags": ["explanation", "simple", "education"]
    },
    {
        "name": "Email Writer",
        "description": "Write professional emails",
        "template": "Write a {{tone}} email about {{subject}}.\n\nKey points to include:\n{{key_points}}\n\nRecipient: {{recipient}}",
        "category": "writing",
        "tags": ["email", "professional", "communication"]
    },
    {
        "name": "SQL Query Generator",
        "description": "Generate SQL from natural language",
        "template": "Generate a SQL query for the following request:\n\n{{request}}\n\nDatabase schema:\n{{schema}}\n\nProvide the SQL query with explanations.",
        "category": "coding",
        "tags": ["sql", "database", "query"]
    },
    {
        "name": "Meeting Notes",
        "description": "Structure meeting notes",
        "template": "Please organize these meeting notes into a structured format:\n\n{{raw_notes}}\n\nInclude:\n- Key decisions\n- Action items (with owners)\n- Next steps\n- Open questions",
        "category": "productivity",
        "tags": ["meetings", "notes", "organization"]
    },
    {
        "name": "Pros and Cons Analysis",
        "description": "Analyze pros and cons of a decision",
        "template": "Analyze the pros and cons of {{decision}}.\n\nContext: {{context}}\n\nProvide a balanced analysis with a recommendation.",
        "category": "analysis",
        "tags": ["decision", "analysis", "comparison"]
    },
    {
        "name": "Translation",
        "description": "Translate text between languages",
        "template": "Translate the following text from {{source_language}} to {{target_language}}:\n\n{{text}}\n\nMaintain the original tone and style.",
        "category": "writing",
        "tags": ["translation", "language", "international"]
    }
]


def _seed_prompts():
    """Seed example prompts."""
    for prompt_data in EXAMPLE_PROMPTS:
        prompt_id = f"prompt_{secrets.token_hex(4)}"
        variables = _extract_variables(prompt_data["template"])
        
        prompts_db[prompt_id] = PromptTemplate(
            id=prompt_id,
            name=prompt_data["name"],
            description=prompt_data.get("description"),
            template=prompt_data["template"],
            variables=variables,
            category=prompt_data.get("category", "general"),
            tags=prompt_data.get("tags", []),
            is_public=True,
            author="system"
        )

def _extract_variables(template: str) -> List[str]:
    """Extract {{variable}} placeholders from template."""
    pattern = r'\{\{(\w+)\}\}'
    return list(set(re.findall(pattern, template)))


def _fill_template(template: str, variables: Dict[str, str]) -> str:
    """Fill template with variable values."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


# Seed example prompts
_seed_prompts()


@router.get("")
async def list_prompts(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False
):
    """
    List all prompt templates.
    
    Filter by category, tag, or search term.
    """
    results = list(prompts_db.values())
    
    if category:
        results = [p for p in results if p.category == category]
    
    if tag:
        results = [p for p in results if tag in p.tags]
    
    if search:
        search_lower = search.lower()
        results = [
            p for p in results
            if search_lower in p.name.lower() or 
               (p.description and search_lower in p.description.lower())
        ]
    
    if favorites_only:
        results = [p for p in results if p.is_favorite]
    
    # Sort by usage count (most used first)
    results.sort(key=lambda x: x.usage_count, reverse=True)
    
    return {
        "prompts": [p.dict() for p in results],
        "total": len(results)
    }


@router.get("/categories")
async def list_categories():
    """Get all available categories."""
    categories = set()
    for p in prompts_db.values():
        categories.add(p.category)
    
    return {"categories": sorted(list(categories))}


@router.get("/tags")
async def list_tags():
    """Get all available tags with counts."""
    tag_counts = {}
    for p in prompts_db.values():
        for tag in p.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    return {
        "tags": [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])
        ]
    }


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get a specific prompt template."""
    if prompt_id not in prompts_db:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    return prompts_db[prompt_id].dict()


@router.post("")
async def create_prompt(prompt_data: PromptCreate):
    """
    Create a new prompt template.
    
    Use {{variable}} syntax for template variables.
    
    Example:
    ```
    {
        "name": "My Prompt",
        "template": "Write about {{topic}} in {{style}} style",
        "category": "writing"
    }
    ```
    """
    prompt_id = f"prompt_{secrets.token_hex(6)}"
    variables = _extract_variables(prompt_data.template)
    
    prompt = PromptTemplate(
        id=prompt_id,
        name=prompt_data.name,
        description=prompt_data.description,
        template=prompt_data.template,
        variables=variables,
        category=prompt_data.category,
        tags=prompt_data.tags,
        is_public=prompt_data.is_public
    )
    
    prompts_db[prompt_id] = prompt
    
    return prompt.dict()


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, prompt_data: PromptUpdate):
    """Update a prompt template."""
    if prompt_id not in prompts_db:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    prompt = prompts_db[prompt_id]
    
    if prompt_data.name is not None:
        prompt.name = prompt_data.name
    if prompt_data.description is not None:
        prompt.description = prompt_data.description
    if prompt_data.template is not None:
        prompt.template = prompt_data.template
        prompt.variables = _extract_variables(prompt_data.template)
    if prompt_data.category is not None:
        prompt.category = prompt_data.category
    if prompt_data.tags is not None:
        prompt.tags = prompt_data.tags
    if prompt_data.is_public is not None:
        prompt.is_public = prompt_data.is_public
    if prompt_data.is_favorite is not None:
        prompt.is_favorite = prompt_data.is_favorite
    
    prompt.updated_at = datetime.now()
    
    return prompt.dict()


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt template."""
    if prompt_id not in prompts_db:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    del prompts_db[prompt_id]
    
    return {"message": "Prompt deleted"}


@router.post("/{prompt_id}/favorite")
async def toggle_favorite(prompt_id: str):
    """Toggle favorite status."""
    if prompt_id not in prompts_db:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    prompt = prompts_db[prompt_id]
    prompt.is_favorite = not prompt.is_favorite
    
    return {"is_favorite": prompt.is_favorite}


@router.post("/execute")
async def execute_prompt(request: PromptExecute):
    """
    Execute a prompt template with variables.
    
    Provide either prompt_id or template directly.
    
    Example:
    ```
    {
        "prompt_id": "prompt_abc123",
        "variables": {
            "topic": "artificial intelligence",
            "style": "academic"
        }
    }
    ```
    """
    from core.llm import llm_router
    
    # Get template
    if request.prompt_id:
        if request.prompt_id not in prompts_db:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        prompt = prompts_db[request.prompt_id]
        template = prompt.template
        
        # Increment usage count
        prompt.usage_count += 1
    elif request.template:
        template = request.template
    else:
        raise HTTPException(status_code=400, detail="Provide prompt_id or template")
    
    # Check required variables
    required_vars = _extract_variables(template)
    missing_vars = [v for v in required_vars if v not in request.variables]
    
    if missing_vars:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required variables: {', '.join(missing_vars)}"
        )
    
    # Fill template
    filled_prompt = _fill_template(template, request.variables)
    
    # Execute with LLM
    response = await llm_router.run(
        model_id=request.model,
        messages=[{"role": "user", "content": filled_prompt}]
    )
    
    return {
        "prompt": filled_prompt,
        "response": response.get("content", ""),
        "model": response.get("model", request.model),
        "usage": response.get("usage", {})
    }


@router.post("/preview")
async def preview_prompt(template: str, variables: Dict[str, str] = {}):
    """Preview a filled template without executing."""
    filled = _fill_template(template, variables)
    extracted_vars = _extract_variables(template)
    
    return {
        "template": template,
        "variables": extracted_vars,
        "provided": list(variables.keys()),
        "missing": [v for v in extracted_vars if v not in variables],
        "preview": filled
    }

