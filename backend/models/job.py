from pydantic import BaseModel, Field
from typing import List, Optional

class JobParsedProfile(BaseModel):
    must_have_skills: List[str] = Field(default_factory=list, description="Core requirements that candidate must satisfy")
    preferred_skills: List[str] = Field(default_factory=list, description="Desirable but not strictly required skills")
    experience_level: Optional[str] = Field(default=None, description="Experience level expected (e.g. Junior, Mid, Senior, Lead)")
    responsibilities: List[str] = Field(default_factory=list, description="Key work items and responsibilities")
    technology_stack: List[str] = Field(default_factory=list, description="Technologies, programming languages, and framework tokens")
    industry: Optional[str] = Field(default=None, description="The general industry classification (e.g. Fintech, SaaS, Healthtech)")
    domain: Optional[str] = Field(default=None, description="The technical or functional domain (e.g. Cloud Architecture, frontend Development)")
    soft_skills: List[str] = Field(default_factory=list, description="Behavioral or interpersonal soft skills")
    leadership_expectations: List[str] = Field(default_factory=list, description="Any mentoring, coaching, or team management expectation")
    education: Optional[str] = Field(default=None, description="Minimum or preferred educational degrees")
    nice_to_have_skills: List[str] = Field(default_factory=list, description="Optional skills that add extra value")
    certifications: List[str] = Field(default_factory=list, description="Required or preferred certifications")
