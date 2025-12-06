"""Prompt engineering templates for Visual Tutor App."""

from typing import Optional


def get_analysis_prompt(annotations: list[dict], student_question: Optional[str] = None) -> str:
    """
    Generate a prompt for analyzing an annotated image.
    
    Args:
        annotations: List of annotation dictionaries
        student_question: Optional explicit question from student
        
    Returns:
        Formatted prompt string
    """
    annotations_text = ""
    if annotations:
        annotations_text = "The student has made the following annotations:\n"
        for i, ann in enumerate(annotations, 1):
            ann_type = ann.get("type", "unknown")
            x = ann.get("x", 0)
            y = ann.get("y", 0)
            
            position = _get_position_description(x, y)
            
            if ann_type == "text":
                annotations_text += f"{i}. Text \"{ann.get('text', '')}\" at {position}\n"
            elif ann_type == "circle":
                annotations_text += f"{i}. Circle highlighting area at {position}\n"
            elif ann_type == "arrow":
                end_pos = _get_position_description(ann.get("end_x", 0), ann.get("end_y", 0))
                annotations_text += f"{i}. Arrow from {position} pointing to {end_pos}\n"
            elif ann_type == "highlight":
                annotations_text += f"{i}. Highlighted area at {position}\n"
            else:
                annotations_text += f"{i}. {ann_type.capitalize()} annotation at {position}\n"
    
    question_text = ""
    if student_question:
        question_text = f'\nThe student asked: "{student_question}"\n'
    
    return f"""
Analyze this educational image that a student is studying.

{annotations_text}
{question_text}

Based on the image content and annotations, identify:

1. What specific concept or element the student is confused about
2. The difficulty level (beginner, intermediate, or advanced)
3. What type of visual explanation would help most (schematic, cartoon, realistic, minimalist, gamified)
4. The subject area (math, physics, chemistry, biology, history, etc.)
5. The specific subtopic within that subject

Respond with a JSON object containing:
{{
    "confusion_concept": "specific concept the student is struggling with",
    "difficulty_level": "beginner|intermediate|advanced",
    "suggested_explanation_type": "schematic|cartoon|realistic|minimalist|gamified",
    "subject": "subject area",
    "subtopic": "specific subtopic",
    "key_elements": ["list", "of", "key", "elements", "to", "explain"],
    "reasoning": "brief explanation of why you identified this confusion point"
}}
"""


def get_nanobananapro_prompt_template(
    concept: str,
    subject: str,
    style: str,
    difficulty: str
) -> str:
    """
    Generate a base template for Nano Banana Pro image generation.
    
    Args:
        concept: The concept to explain
        subject: Subject area
        style: Visual style
        difficulty: Difficulty level
        
    Returns:
        Prompt template string
    """
    style_instructions = _get_style_instructions(style)
    subject_instructions = _get_subject_instructions(subject)
    difficulty_adjustments = _get_difficulty_adjustments(difficulty)
    
    return f"""
Create an educational diagram explaining: {concept}

STYLE: {style_instructions}

SUBJECT CONTEXT: {subject_instructions}

DIFFICULTY ADAPTATION: {difficulty_adjustments}

REQUIRED ELEMENTS:
- Clear title at the top: "{concept}"
- Well-organized layout with logical flow
- All text labels must be legible and properly positioned
- Color coding to distinguish different elements
- Arrows or lines showing relationships

VISUAL REQUIREMENTS:
- High contrast for readability
- Clean, professional appearance
- No cluttered or overlapping elements
- Consistent visual hierarchy
"""


def get_explanation_prompt(analysis: dict) -> str:
    """
    Generate a prompt for explaining a generated diagram.
    
    Args:
        analysis: The confusion analysis result
        
    Returns:
        Formatted prompt string
    """
    concept = analysis.get("confusion_concept", "the concept")
    subject = analysis.get("subject", "this subject")
    difficulty = analysis.get("difficulty_level", "intermediate")
    
    persona = _get_tutor_persona(difficulty)
    
    return f"""
You are a friendly, encouraging tutor helping a student understand {concept} in {subject}.

{persona}

Look at both images:
1. The ORIGINAL image shows what the student was studying when they got confused
2. The GENERATED diagram is the visual explanation you created

Now explain the generated diagram to the student:

GUIDELINES:
- Start with an encouraging statement
- Reference specific elements in your generated diagram ("Look at the red arrow...")
- Explain step by step, building understanding gradually
- Use analogies that relate to everyday experiences
- Check for understanding with questions like "Does that make sense?"
- End with a summary of the key takeaway

Keep your explanation:
- Conversational and friendly (use "you" and "I")
- Focused on the visual elements you created
- Appropriate for a {difficulty} level student
- Under 300 words

Begin your explanation now:
"""


def _get_position_description(x: float, y: float) -> str:
    """Convert relative coordinates to human-readable position."""
    horizontal = "left" if x < 0.33 else "center" if x < 0.67 else "right"
    vertical = "top" if y < 0.33 else "middle" if y < 0.67 else "bottom"
    return f"{vertical}-{horizontal}"


def _get_style_instructions(style: str) -> str:
    """Get style-specific instructions."""
    styles = {
        "schematic": """
Technical diagram style with:
- Clean lines and geometric shapes
- Professional, blueprint-like appearance
- Precise labeling with technical terminology
- Grid or guideline structure
- Minimal decorative elements
""",
        "cartoon": """
Friendly cartoon style with:
- Rounded shapes and soft edges
- Colorful, engaging appearance
- Simplified representations
- Optional: friendly characters or mascots
- Fun, approachable aesthetic
""",
        "realistic": """
Realistic illustration style with:
- Accurate proportions and details
- Naturalistic colors and shading
- Photo-like representations where appropriate
- Depth and dimension
- Professional educational textbook quality
""",
        "minimalist": """
Clean minimalist style with:
- Essential elements only
- Plenty of whitespace
- Simple shapes and icons
- Limited color palette (2-3 colors)
- Focus on clarity over decoration
""",
        "gamified": """
Game-inspired visual style with:
- Pixel art or game UI elements
- Achievement/progress indicators
- Familiar gaming metaphors (levels, power-ups)
- Bright, engaging colors
- Interactive-looking elements
"""
    }
    return styles.get(style, styles["schematic"])


def _get_subject_instructions(subject: str) -> str:
    """Get subject-specific instructions."""
    subjects = {
        "math": """
For mathematics:
- Use standard mathematical notation
- Show step-by-step processes
- Include number lines or coordinate systems when relevant
- Use geometric shapes accurately
- Show formulas clearly formatted
""",
        "physics": """
For physics:
- Use standard physics diagram conventions
- Show force vectors with arrows
- Include units and measurements
- Use free body diagrams when appropriate
- Show before/after states for dynamic processes
""",
        "chemistry": """
For chemistry:
- Use standard chemical notation
- Show molecular structures accurately
- Include electron configurations when relevant
- Use color coding for different elements
- Show reaction arrows and conditions
""",
        "biology": """
For biology:
- Show anatomical structures accurately
- Use magnified views for cellular details
- Include scale indicators
- Show processes with flow diagrams
- Use cross-sections where helpful
""",
        "history": """
For history:
- Use timeline formats when appropriate
- Show geographical context with maps
- Include dates and periods clearly
- Use cause-and-effect diagrams
- Show relationships between events/people
""",
        "general": """
For general education:
- Use clear, universal visual language
- Focus on relationships and connections
- Include helpful icons and symbols
- Show processes with flowcharts
- Use comparison layouts when helpful
"""
    }
    return subjects.get(subject, subjects["general"])


def _get_difficulty_adjustments(difficulty: str) -> str:
    """Get difficulty-level adjustments."""
    adjustments = {
        "beginner": """
For beginner level:
- Use very simple terminology
- Include more visual cues and fewer words
- Break down into smallest possible steps
- Use everyday analogies and examples
- Add encouraging elements
""",
        "intermediate": """
For intermediate level:
- Use standard terminology with brief explanations
- Balance visuals and text
- Show connections to prior knowledge
- Include moderate detail
- Challenge slightly with extensions
""",
        "advanced": """
For advanced level:
- Use technical/academic terminology
- Show complex relationships and nuances
- Include edge cases or exceptions
- Connect to broader concepts
- Add depth and sophisticated analysis
"""
    }
    return adjustments.get(difficulty, adjustments["intermediate"])


def _get_tutor_persona(difficulty: str) -> str:
    """Get appropriate tutor persona for difficulty level."""
    personas = {
        "beginner": """
PERSONA: You are a patient, encouraging elementary school tutor.
- Use simple words and short sentences
- Be very enthusiastic and supportive
- Celebrate small wins
- Use lots of relatable examples (toys, games, food)
""",
        "intermediate": """
PERSONA: You are a helpful, engaging middle/high school tutor.
- Balance friendliness with substance
- Encourage curiosity and questions
- Connect to real-world applications
- Build confidence while challenging growth
""",
        "advanced": """
PERSONA: You are a knowledgeable, collegial advanced tutor.
- Treat the student as intellectually capable
- Use precise, academic language
- Encourage deeper exploration
- Connect to broader academic context
"""
    }
    return personas.get(difficulty, personas["intermediate"])


# Template library for specific concepts
CONCEPT_TEMPLATES = {
    "quadratic_formula": """
Create a visual breakdown of the quadratic formula: x = (-b ± √(b²-4ac)) / 2a

Layout:
- TOP: The complete formula in large, clear text
- MIDDLE LEFT: Each variable (a, b, c) with color coding
- MIDDLE RIGHT: The discriminant (b²-4ac) highlighted with explanation
- BOTTOM: Visual graph showing how roots relate to x-intercepts

Color scheme: Use blue for 'a', green for 'b', red for 'c'
""",
    "photosynthesis": """
Create a diagram of photosynthesis process.

Layout:
- CENTER: A plant/leaf cross-section
- LEFT: Inputs (sunlight, water, CO₂) with arrows pointing in
- RIGHT: Outputs (glucose, oxygen) with arrows pointing out
- BOTTOM: Chemical equation simplified

Use green for plant elements, yellow for sunlight, blue for water
""",
    "pulley_system": """
Create a mechanical advantage diagram for a pulley system.

Layout:
- MAIN: Show the pulley configuration clearly
- Label each pulley and rope segment
- Show force vectors with RED arrows
- Show displacement with BLUE arrows
- Include the mechanical advantage calculation

Add a side-by-side: "Without pulley" vs "With pulley" comparison
""",
}


def get_concept_template(concept_key: str) -> Optional[str]:
    """Get a pre-made template for common concepts."""
    return CONCEPT_TEMPLATES.get(concept_key.lower().replace(" ", "_"))
