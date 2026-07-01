from pydantic import BaseModel, Field
from typing import List, Optional

class ProjectSchema(BaseModel):
    title: Optional[str] = Field(default=None, description="Title of the project")
    description: Optional[str] = Field(default=None, description="Short summary of work done")
    technologies: List[str] = Field(default_factory=list, description="Technologies used in this project")

class ExperienceSchema(BaseModel):
    company: Optional[str] = Field(default=None, description="Company name")
    role: Optional[str] = Field(default=None, description="Job title / role")
    start_date: Optional[str] = Field(default=None, description="Start date of employment")
    end_date: Optional[str] = Field(default=None, description="End date of employment or Present")
    description: Optional[str] = Field(default=None, description="Responsibilities and impact")

class CandidateParsedProfile(BaseModel):
    name: Optional[str] = Field(default=None, description="Full name of candidate")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    education: List[str] = Field(default_factory=list, description="Schools, degrees, courses")
    skills: List[str] = Field(default_factory=list, description="Individual skill keywords")
    experience: List[ExperienceSchema] = Field(default_factory=list, description="List of employment history")
    companies: List[str] = Field(default_factory=list, description="Names of previous employers")
    projects: List[ProjectSchema] = Field(default_factory=list, description="List of projects built")
    certifications: List[str] = Field(default_factory=list, description="Certifications achieved")
    awards: List[str] = Field(default_factory=list, description="Awards or honors received")
    publications: List[str] = Field(default_factory=list, description="Published research or papers")
    technologies: List[str] = Field(default_factory=list, description="List of technologies / framework keys")
    languages: List[str] = Field(default_factory=list, description="Languages spoken")
    soft_skills: List[str] = Field(default_factory=list, description="Interpersonal soft skills")
    leadership: List[str] = Field(default_factory=list, description="Leadership indicators (e.g. mentor, lead)")
    responsibilities: List[str] = Field(default_factory=list, description="Key operational responsibilities list")
    years_of_experience: Optional[float] = Field(default=0.0, description="Total years of work experience")
    raw_resume_text: Optional[str] = Field(default=None, description="The original raw text extracted from the document")
    id: Optional[str] = Field(default=None, description="The unique database ID of the candidate")


