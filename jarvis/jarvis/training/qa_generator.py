"""
Q&A Generator - Generate training Q&A pairs from documents using LLM

Uses the local LLM to create high-quality question-answer pairs
from document chunks for fine-tuning.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

from jarvis.core.llm_engine import LLMEngine
from jarvis.training.document_processor import Document, DocumentChunk


@dataclass
class QAPair:
    """A question-answer pair for training"""
    question: str
    answer: str
    context: str  # Original text chunk
    source_document: str
    difficulty: str = "medium"  # easy, medium, hard
    category: str = "general"
    metadata: dict = field(default_factory=dict)


class QAGenerator:
    """Generate Q&A pairs from documents using LLM"""
    
    def __init__(self, llm_engine: LLMEngine):
        self.llm = llm_engine
    
    async def generate_qa_pairs(
        self,
        document: Document,
        questions_per_chunk: int = 3,
        include_inferential: bool = True
    ) -> List[QAPair]:
        """
        Generate Q&A pairs from a document.
        
        Args:
            document: Document to process
            questions_per_chunk: Number of Q&A pairs per chunk
            include_inferential: Include inferential/application questions
            
        Returns:
            List of QAPair objects
        """
        qa_pairs = []
        
        for chunk in document.chunks:
            chunk_pairs = await self._generate_from_chunk(
                chunk=chunk,
                document_id=document.id,
                num_questions=questions_per_chunk,
                include_inferential=include_inferential
            )
            qa_pairs.extend(chunk_pairs)
        
        return qa_pairs
    
    async def _generate_from_chunk(
        self,
        chunk: DocumentChunk,
        document_id: str,
        num_questions: int = 3,
        include_inferential: bool = True
    ) -> List[QAPair]:
        """Generate Q&A pairs from a single chunk"""
        
        question_types = ["factual", "conceptual"]
        if include_inferential:
            question_types.append("inferential")
        
        prompt = f'''Based on the following text, generate {num_questions} high-quality question-answer pairs.

Text:
{chunk.content}

Generate questions of different types:
- Factual: Direct questions about facts stated in the text
- Conceptual: Questions about concepts, definitions, or explanations
{f"- Inferential: Questions requiring reasoning or application of information" if include_inferential else ""}

Format your response as JSON array:
[
  {{
    "question": "What is...",
    "answer": "...",
    "type": "factual|conceptual|inferential",
    "difficulty": "easy|medium|hard"
  }}
]

Make sure:
1. Questions are clear and answerable from the text
2. Answers are accurate and complete
3. Vary question difficulty
4. Cover different aspects of the text
'''
        
        try:
            response = await self.llm.reason(
                prompt=prompt,
                system_prompt="You are an expert at creating educational Q&A pairs. Generate clear, accurate questions and answers."
            )
            
            # Parse the response
            qa_pairs = self._parse_qa_response(
                response.content,
                chunk.content,
                document_id
            )
            
            return qa_pairs
            
        except Exception as e:
            print(f"Error generating Q&A pairs: {e}")
            return []
    
    def _parse_qa_response(
        self,
        response_text: str,
        context: str,
        document_id: str
    ) -> List[QAPair]:
        """Parse LLM response into QAPair objects"""
        import json
        import re
        
        qa_pairs = []
        
        try:
            # Try to extract JSON from the response
            # Look for JSON array pattern
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
                
                for item in parsed:
                    if isinstance(item, dict) and 'question' in item and 'answer' in item:
                        qa_pairs.append(QAPair(
                            question=item['question'],
                            answer=item['answer'],
                            context=context,
                            source_document=document_id,
                            difficulty=item.get('difficulty', 'medium'),
                            category=item.get('type', 'general'),
                        ))
            else:
                # Fallback: try to parse line by line
                lines = response_text.strip().split('\n')
                current_q = None
                current_a = None
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('Q:') or line.startswith('Question:'):
                        if current_q and current_a:
                            qa_pairs.append(QAPair(
                                question=current_q,
                                answer=current_a,
                                context=context,
                                source_document=document_id,
                            ))
                        current_q = line.split(':', 1)[1].strip()
                        current_a = None
                    elif line.startswith('A:') or line.startswith('Answer:'):
                        current_a = line.split(':', 1)[1].strip()
                
                # Add last pair
                if current_q and current_a:
                    qa_pairs.append(QAPair(
                        question=current_q,
                        answer=current_a,
                        context=context,
                        source_document=document_id,
                    ))
        
        except Exception as e:
            print(f"Error parsing Q&A response: {e}")
        
        return qa_pairs
    
    def validate_qa_pair(self, qa_pair: QAPair) -> bool:
        """
        Validate a Q&A pair for quality.
        
        Args:
            qa_pair: Q&A pair to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation rules
        if not qa_pair.question or not qa_pair.answer:
            return False
        
        # Question should be a reasonable length
        if len(qa_pair.question.split()) < 3 or len(qa_pair.question.split()) > 100:
            return False
        
        # Answer should be meaningful
        if len(qa_pair.answer.split()) < 2:
            return False
        
        # Question should end with question mark or be a command
        if not qa_pair.question.strip().endswith('?') and not any(
            qa_pair.question.lower().startswith(w) 
            for w in ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'describe', 'explain']
        ):
            return False
        
        return True
