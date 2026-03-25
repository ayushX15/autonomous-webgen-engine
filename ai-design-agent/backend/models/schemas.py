from pydantic import BaseModel, Field
from typing import List, Optional

class CapturedFeatures(BaseModel):
    ui_components: List[str] = Field(default=[])
    color_palette: List[str] = Field(default=[])
    font_style: str = Field(default="sans-serif")
    font_size_scale: str = Field(default="medium")
    layout_type: str = Field(default="centered")
    tone: str = Field(default="minimal")
    page_sections: List[str] = Field(default=[])
    animation_style: str = Field(default="subtle")

class GeneratedPage(BaseModel):
    page_name: str
    tsx_code: str
    is_landing: bool
    route_path: str = Field(default="/")

class IterationResult(BaseModel):
    iteration: int
    similarity_score: float = Field(ge=0.0, le=1.0)
    visual_diff_notes: str
    suggestions: List[str]
    passed: bool
    screenshot_path: Optional[str] = None

class UserInput(BaseModel):
    user_requirement: str
    reference_urls: List[str] = Field(default=[])
    reference_image_paths: List[str] = Field(default=[])
    pages_requested: List[str] = Field(default=["index", "about", "contact"])

class AgentState(BaseModel):
    user_input: Optional[UserInput] = None
    captured_features: Optional[CapturedFeatures] = None
    generated_pages: List[GeneratedPage] = Field(default=[])
    output_run_id: Optional[str] = None
    current_iteration: int = Field(default=0)
    max_iterations: int = Field(default=5)
    iteration_results: List[IterationResult] = Field(default=[])
    latest_feedback: List[str] = Field(default=[])
    is_complete: bool = Field(default=False)
    final_output_path: Optional[str] = None
    error_message: Optional[str] = None