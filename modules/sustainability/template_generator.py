"""
Auto Template Generator for Sustainability Documents

Uses LLM to automatically:
1. Analyze new document structures
2. Generate extraction templates
3. Define emission factors
4. Create validation rules

This makes the system SELF-LEARNING - it can handle ANY document type!
"""

import json
import os
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import re


@dataclass
class FieldDefinition:
    """Definition of a field to extract."""
    name: str
    description: str
    data_type: str  # string, number, date, boolean, array
    required: bool = False
    emission_factor_key: Optional[str] = None
    unit: Optional[str] = None
    validation_pattern: Optional[str] = None
    example: Optional[str] = None


@dataclass
class GeneratedTemplate:
    """Auto-generated extraction template."""
    template_id: str
    name: str
    description: str
    document_indicators: List[str]  # Keywords that identify this doc type
    category: str  # energy, travel, shipping, esg, other
    scope: str  # scope_1, scope_2, scope_3, multiple
    fields: List[FieldDefinition]
    extraction_prompt: str
    emission_calculation: Dict[str, Any]
    created_at: str
    created_by: str = "llm_auto"
    version: int = 1
    usage_count: int = 0
    accuracy_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "document_indicators": self.document_indicators,
            "category": self.category,
            "scope": self.scope,
            "fields": [asdict(f) for f in self.fields],
            "extraction_prompt": self.extraction_prompt,
            "emission_calculation": self.emission_calculation,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "version": self.version,
            "usage_count": self.usage_count,
            "accuracy_score": self.accuracy_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneratedTemplate":
        fields = [FieldDefinition(**f) for f in data.get("fields", [])]
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            document_indicators=data.get("document_indicators", []),
            category=data.get("category", "other"),
            scope=data.get("scope", "scope_3"),
            fields=fields,
            extraction_prompt=data["extraction_prompt"],
            emission_calculation=data.get("emission_calculation", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            created_by=data.get("created_by", "llm_auto"),
            version=data.get("version", 1),
            usage_count=data.get("usage_count", 0),
            accuracy_score=data.get("accuracy_score", 0.0)
        )


# Prompt to analyze document and generate template
TEMPLATE_GENERATION_PROMPT = """You are an expert at analyzing sustainability documents and creating data extraction templates.

Analyze this document and create a template for extracting sustainability-relevant data.

DOCUMENT TEXT:
{text}

Create a JSON template with:

1. **name**: Short name for this document type (e.g., "utility_bill_electric", "carbon_offset_certificate")

2. **description**: What this document is and what data it contains

3. **document_indicators**: List of 5-10 keywords that identify this document type

4. **category**: One of: energy, travel, shipping, fleet, waste, water, esg, carbon_offset, supply_chain, other

5. **scope**: Which GHG Protocol scope: scope_1, scope_2, scope_3, or multiple

6. **fields**: Array of fields to extract, each with:
   - name: field name (snake_case)
   - description: what this field contains
   - data_type: string, number, date, boolean, or array
   - required: true/false
   - emission_factor_key: if this field is used for CO2e calculation, what factor to use (e.g., "electricity_kwh", "flight_km", "fuel_liters")
   - unit: measurement unit if applicable (kWh, kg, km, liters, etc.)
   - example: example value from the document

7. **emission_calculation**: How to calculate CO2e from extracted fields:
   - formula: description of calculation
   - primary_field: main field for calculation
   - factor_type: what emission factor to apply
   - multiplier: any additional multiplier

Respond with ONLY valid JSON:

```json
{{
  "name": "document_type_name",
  "description": "Description of document",
  "document_indicators": ["keyword1", "keyword2", ...],
  "category": "category_name",
  "scope": "scope_x",
  "fields": [
    {{
      "name": "field_name",
      "description": "Field description",
      "data_type": "number",
      "required": true,
      "emission_factor_key": "factor_key_or_null",
      "unit": "unit_or_null",
      "example": "example_value"
    }}
  ],
  "emission_calculation": {{
    "formula": "field_name * emission_factor",
    "primary_field": "field_name",
    "factor_type": "electricity_kwh",
    "multiplier": 1.0
  }}
}}
```
"""


class TemplateGenerator:
    """
    Auto-generates extraction templates using LLM.
    
    Features:
    - Analyzes unknown document types
    - Creates structured extraction templates
    - Stores templates for reuse
    - Improves accuracy over time
    """
    
    # Standard emission factors for reference
    EMISSION_FACTORS = {
        "electricity_kwh": 0.417,      # kg CO2e per kWh (US avg)
        "electricity_kwh_uk": 0.207,
        "natural_gas_therm": 5.31,
        "natural_gas_m3": 2.02,
        "flight_economy_km": 0.156,
        "flight_business_km": 0.468,
        "car_petrol_km": 0.171,
        "car_diesel_km": 0.168,
        "fuel_petrol_liter": 2.31,
        "fuel_diesel_liter": 2.68,
        "shipping_road_tkm": 0.107,
        "shipping_sea_tkm": 0.016,
        "shipping_air_tkm": 0.602,
        "waste_landfill_kg": 0.587,
        "waste_recycled_kg": 0.021,
        "water_m3": 0.344,
        "paper_kg": 1.84,
        "server_kwh": 0.475,
    }
    
    def __init__(self, templates_dir: str = "data/templates"):
        self.templates_dir = templates_dir
        self.llm_router = None
        self.templates: Dict[str, GeneratedTemplate] = {}
        self._load_templates()
    
    def set_llm_router(self, llm_router):
        """Set LLM router for template generation."""
        self.llm_router = llm_router
    
    def _load_templates(self):
        """Load existing templates from disk."""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            return
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.templates_dir, filename), "r") as f:
                        data = json.load(f)
                        template = GeneratedTemplate.from_dict(data)
                        self.templates[template.template_id] = template
                except Exception as e:
                    print(f"Error loading template {filename}: {e}")
    
    def _save_template(self, template: GeneratedTemplate):
        """Save template to disk."""
        os.makedirs(self.templates_dir, exist_ok=True)
        filepath = os.path.join(self.templates_dir, f"{template.template_id}.json")
        with open(filepath, "w") as f:
            json.dump(template.to_dict(), f, indent=2)
    
    def _generate_template_id(self, name: str) -> str:
        """Generate unique template ID."""
        timestamp = datetime.now().strftime("%Y%m%d")
        hash_suffix = hashlib.md5(name.encode()).hexdigest()[:6]
        return f"{name}_{timestamp}_{hash_suffix}"
    
    async def generate_template(
        self, 
        document_text: str,
        hint_type: Optional[str] = None
    ) -> GeneratedTemplate:
        """
        Generate a new template from document text using LLM.
        
        Args:
            document_text: The document to analyze
            hint_type: Optional hint about document type
            
        Returns:
            GeneratedTemplate object
        """
        if not self.llm_router:
            raise ValueError("LLM Router not configured")
        
        prompt = TEMPLATE_GENERATION_PROMPT.format(text=document_text[:4000])
        
        if hint_type:
            prompt += f"\n\nHint: This appears to be a {hint_type} document."
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a sustainability data expert. Analyze documents and create extraction templates. Always respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            if response.get("status") != "success":
                raise ValueError(f"LLM error: {response.get('error')}")
            
            content = response["content"]
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("No JSON found in response")
            
            template_data = json.loads(json_str)
            
            # Create template object
            template_id = self._generate_template_id(template_data["name"])
            
            fields = []
            for f in template_data.get("fields", []):
                fields.append(FieldDefinition(
                    name=f["name"],
                    description=f.get("description", ""),
                    data_type=f.get("data_type", "string"),
                    required=f.get("required", False),
                    emission_factor_key=f.get("emission_factor_key"),
                    unit=f.get("unit"),
                    example=f.get("example")
                ))
            
            # Generate extraction prompt
            extraction_prompt = self._create_extraction_prompt(
                template_data["name"],
                template_data.get("description", ""),
                fields
            )
            
            template = GeneratedTemplate(
                template_id=template_id,
                name=template_data["name"],
                description=template_data.get("description", ""),
                document_indicators=template_data.get("document_indicators", []),
                category=template_data.get("category", "other"),
                scope=template_data.get("scope", "scope_3"),
                fields=fields,
                extraction_prompt=extraction_prompt,
                emission_calculation=template_data.get("emission_calculation", {}),
                created_at=datetime.now().isoformat()
            )
            
            # Save and cache
            self._save_template(template)
            self.templates[template_id] = template
            
            return template
            
        except Exception as e:
            raise ValueError(f"Failed to generate template: {str(e)}")
    
    def _create_extraction_prompt(
        self, 
        name: str, 
        description: str,
        fields: List[FieldDefinition]
    ) -> str:
        """Create an extraction prompt from field definitions."""
        fields_text = "\n".join([
            f"- {f.name}: {f.description} ({f.data_type}){' [REQUIRED]' if f.required else ''}"
            for f in fields
        ])
        
        return f"""Extract data from this {name} document.

{description}

DOCUMENT TEXT:
{{text}}

Extract these fields (use null if not found):
{fields_text}

Respond with JSON containing exactly these field names."""
    
    async def extract_with_template(
        self, 
        document_text: str,
        template: GeneratedTemplate
    ) -> Dict[str, Any]:
        """
        Extract data using a generated template.
        
        Args:
            document_text: Document to extract from
            template: Template to use
            
        Returns:
            Extracted data dictionary
        """
        if not self.llm_router:
            raise ValueError("LLM Router not configured")
        
        prompt = template.extraction_prompt.format(text=document_text[:4000])
        
        try:
            response = await self.llm_router.run(
                model_id="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Extract data precisely. Respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            if response.get("status") != "success":
                return {"error": response.get("error")}
            
            content = response["content"]
            json_match = re.search(r'[\[\{][\s\S]*[\]\}]', content)
            if json_match:
                return json.loads(json_match.group())
            
            return {"error": "No JSON in response"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def calculate_emissions(
        self, 
        data: Dict[str, Any],
        template: GeneratedTemplate
    ) -> Optional[float]:
        """
        Calculate emissions using template's emission calculation rules.
        
        Args:
            data: Extracted data
            template: Template with calculation rules
            
        Returns:
            CO2e in kg, or None if can't calculate
        """
        calc = template.emission_calculation
        if not calc:
            return None
        
        try:
            primary_field = calc.get("primary_field")
            factor_type = calc.get("factor_type")
            multiplier = calc.get("multiplier", 1.0)
            
            if not primary_field or not factor_type:
                return None
            
            value = data.get(primary_field, 0) or 0
            factor = self.EMISSION_FACTORS.get(factor_type, 0)
            
            return float(value) * factor * float(multiplier)
            
        except Exception:
            return None
    
    def find_matching_template(
        self, 
        document_text: str
    ) -> Optional[GeneratedTemplate]:
        """
        Find a matching template for a document.
        
        Args:
            document_text: Document to match
            
        Returns:
            Best matching template or None
        """
        text_lower = document_text.lower()
        best_match = None
        best_score = 0
        
        for template in self.templates.values():
            score = sum(
                1 for indicator in template.document_indicators 
                if indicator.lower() in text_lower
            )
            
            if score > best_score and score >= 2:  # Need at least 2 matches
                best_score = score
                best_match = template
        
        return best_match
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        return [
            {
                "template_id": t.template_id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "scope": t.scope,
                "fields_count": len(t.fields),
                "usage_count": t.usage_count,
                "created_at": t.created_at
            }
            for t in self.templates.values()
        ]
    
    def get_template(self, template_id: str) -> Optional[GeneratedTemplate]:
        """Get a specific template by ID."""
        return self.templates.get(template_id)
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self.templates:
            del self.templates[template_id]
            filepath = os.path.join(self.templates_dir, f"{template_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        return False


# Singleton instance
template_generator = TemplateGenerator()

