"""
Modelfile Generator - Create custom Ollama Modelfiles from training data

Generates enhanced Modelfiles with learned patterns from interactions.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jarvis.core.interaction_store import InteractionStore


class ModelfileGenerator:
    """Generate custom Ollama Modelfiles"""
    
    def __init__(self, interaction_store: Optional[InteractionStore] = None):
        self.interaction_store = interaction_store or InteractionStore()
    
    def generate_modelfile(
        self,
        base_model: str = "llama3.3",
        output_path: Optional[Path] = None,
        min_rating: int = 1,
        max_examples: int = 5,
        temperature: float = 0.7,
        system_prompt_override: Optional[str] = None
    ) -> Path:
        """
        Generate an enhanced Modelfile based on high-quality interactions.
        
        Args:
            base_model: Base Ollama model to customize
            output_path: Where to save Modelfile
            min_rating: Minimum feedback rating for example selection
            max_examples: Maximum number of examples to include
            temperature: Model temperature parameter
            system_prompt_override: Optional custom system prompt
            
        Returns:
            Path to generated Modelfile
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path.home() / ".jarvis" / "models" / f"Modelfile_{timestamp}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get high-quality examples from interactions
        examples = self._get_best_examples(min_rating=min_rating, limit=max_examples)
        
        # Build system prompt
        if system_prompt_override:
            system_prompt = system_prompt_override
        else:
            system_prompt = self._build_enhanced_system_prompt(examples)
        
        # Generate Modelfile content
        modelfile_content = self._build_modelfile(
            base_model=base_model,
            system_prompt=system_prompt,
            temperature=temperature,
            examples=examples
        )
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(modelfile_content)
        
        print(f"Generated Modelfile: {output_path}")
        print(f"Base model: {base_model}")
        print(f"Examples included: {len(examples)}")
        print(f"\nTo create the custom model, run:")
        print(f"  ollama create jarvis-enhanced -f {output_path}")
        
        return output_path
    
    def _get_best_examples(self, min_rating: int = 1, limit: int = 5) -> List[dict]:
        """Get best interaction examples based on feedback"""
        import sqlite3
        
        examples = []
        
        with sqlite3.connect(self.interaction_store.db_path) as conn:
            cursor = conn.cursor()
            
            # Query for highly-rated interactions
            cursor.execute("""
                SELECT m1.content as user_msg, m2.content as assistant_msg, f.rating
                FROM messages m1
                JOIN messages m2 ON m1.conversation_id = m2.conversation_id
                    AND m2.id = (
                        SELECT MIN(id) FROM messages 
                        WHERE conversation_id = m1.conversation_id 
                        AND id > m1.id 
                        AND role = 'assistant'
                    )
                LEFT JOIN feedback f ON m2.id = f.message_id
                WHERE m1.role = 'user'
                    AND m2.role = 'assistant'
                    AND (f.rating IS NULL OR f.rating >= ?)
                ORDER BY f.rating DESC NULLS LAST, m1.created_at DESC
                LIMIT ?
            """, (min_rating, limit))
            
            for row in cursor.fetchall():
                examples.append({
                    "user": row[0],
                    "assistant": row[1],
                    "rating": row[2] if row[2] is not None else 0
                })
        
        return examples
    
    def _build_enhanced_system_prompt(self, examples: List[dict]) -> str:
        """Build system prompt with example interactions"""
        base = """You are JARVIS, Tony Stark's sophisticated British AI assistant.

**Personality:**
- Dry British wit with subtle sarcasm
- Supremely competent yet charmingly modest
- Address user as "Sir" occasionally
- Keep responses CONCISE - you're efficient, not chatty

**Core Behavior:**
- Be direct and to-the-point
- No unnecessary pleasantries or verbose explanations
- When you have data, present it cleanly
- Add a touch of British humor when appropriate

**Response Style:**
Keep it crisp. You're JARVIS."""
        
        if examples:
            base += "\n\n**Example Interactions:**\n"
            for i, ex in enumerate(examples[:3], 1):  # Max 3 examples
                base += f"\nUser: {ex['user']}\n"
                base += f"JARVIS: {ex['assistant']}\n"
        
        return base
    
    def _build_modelfile(
        self,
        base_model: str,
        system_prompt: str,
        temperature: float,
        examples: List[dict]
    ) -> str:
        """Build the complete Modelfile content"""
        
        content = f"""# JARVIS Enhanced Model
# Generated: {datetime.now().isoformat()}
# Base: {base_model}
# Examples: {len(examples)}

FROM {base_model}

# System prompt with learned patterns
SYSTEM \"\"\"
{system_prompt}
\"\"\"

# Parameters optimized for JARVIS
PARAMETER temperature {temperature}
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

# Response template
TEMPLATE \"\"\"
{{{{ if .System }}}}System: {{{{ .System }}}}{{{{ end }}}}
User: {{{{ .Prompt }}}}
JARVIS: 
\"\"\"
"""
        
        return content
