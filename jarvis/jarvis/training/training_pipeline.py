"""
Training Pipeline - Main orchestration for JARVIS training data preparation

Combines interaction logs and document Q&A pairs into training datasets.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jarvis.core.interaction_store import InteractionStore
from jarvis.core.llm_engine import LLMEngine
from jarvis.training.document_processor import Document, DocumentProcessor
from jarvis.training.qa_generator import QAGenerator, QAPair


class TrainingPipeline:
    """Main training data preparation pipeline"""
    
    def __init__(
        self,
        llm_engine: LLMEngine,
        interaction_store: Optional[InteractionStore] = None,
        output_dir: Optional[Path] = None
    ):
        self.llm = llm_engine
        self.interaction_store = interaction_store or InteractionStore()
        self.output_dir = output_dir or Path.home() / ".jarvis" / "training"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.doc_processor = DocumentProcessor()
        self.qa_generator = QAGenerator(llm_engine)
    
    async def ingest_document(
        self,
        document_path: Path,
        generate_qa: bool = True,
        questions_per_chunk: int = 3
    ) -> Document:
        """
        Ingest a document and optionally generate Q&A pairs.
        
        Args:
            document_path: Path to document
            generate_qa: Whether to generate Q&A pairs
            questions_per_chunk: Number of Q&A pairs per chunk
            
        Returns:
            Processed Document
        """
        # Process document
        doc = self.doc_processor.process_file(document_path)
        
        # Generate Q&A pairs if requested
        if generate_qa:
            qa_pairs = await self.qa_generator.generate_qa_pairs(
                document=doc,
                questions_per_chunk=questions_per_chunk
            )
            
            # Filter valid pairs
            valid_pairs = [
                qa for qa in qa_pairs 
                if self.qa_generator.validate_qa_pair(qa)
            ]
            
            # Save Q&A pairs
            self._save_qa_pairs(valid_pairs, doc.id)
            
            print(f"Generated {len(valid_pairs)} Q&A pairs from {document_path.name}")
        
        return doc
    
    async def ingest_directory(
        self,
        directory_path: Path,
        generate_qa: bool = True,
        recursive: bool = True
    ) -> List[Document]:
        """
        Ingest all documents in a directory.
        
        Args:
            directory_path: Path to directory
            generate_qa: Whether to generate Q&A pairs
            recursive: Whether to search subdirectories
            
        Returns:
            List of processed Documents
        """
        directory_path = Path(directory_path)
        documents = []
        
        # Supported extensions
        extensions = {'.pdf', '.txt', '.md', '.markdown', '.html', '.htm', '.docx', '.doc'}
        
        # Find files
        if recursive:
            files = [
                f for f in directory_path.rglob('*') 
                if f.suffix.lower() in extensions
            ]
        else:
            files = [
                f for f in directory_path.glob('*') 
                if f.suffix.lower() in extensions
            ]
        
        print(f"Found {len(files)} documents to process")
        
        # Process each file
        for file_path in files:
            try:
                doc = await self.ingest_document(file_path, generate_qa=generate_qa)
                documents.append(doc)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        return documents
    
    def prepare_training_dataset(
        self,
        min_rating: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_documents: bool = True,
        output_name: str = "training_dataset"
    ) -> Path:
        """
        Prepare a complete training dataset combining interactions and documents.
        
        Args:
            min_rating: Minimum feedback rating for interactions
            start_date: Only include interactions after this date
            end_date: Only include interactions before this date
            include_documents: Whether to include document Q&A pairs
            output_name: Name for output file
            
        Returns:
            Path to generated JSONL file
        """
        output_path = self.output_dir / f"{output_name}.jsonl"
        
        all_examples = []
        
        # Export interactions
        if min_rating is not None or start_date or end_date:
            print("Exporting filtered interactions...")
            temp_path = self.output_dir / "temp_interactions.jsonl"
            self.interaction_store.export_to_jsonl(
                output_path=temp_path,
                min_rating=min_rating,
                start_date=start_date,
                end_date=end_date,
                include_tool_calls=False  # Tools aren't needed for fine-tuning
            )
            
            # Read and convert to training format
            with open(temp_path, 'r') as f:
                for line in f:
                    conv_data = json.loads(line)
                    # Convert to Alpaca format
                    for i, msg in enumerate(conv_data['messages']):
                        if msg['role'] == 'user' and i + 1 < len(conv_data['messages']):
                            next_msg = conv_data['messages'][i + 1]
                            if next_msg['role'] == 'assistant':
                                all_examples.append({
                                    "instruction": msg['content'],
                                    "output": next_msg['content'],
                                    "source": "interaction"
                                })
            
            temp_path.unlink()  # Clean up
        
        # Include document Q&A pairs
        if include_documents:
            print("Including document Q&A pairs...")
            qa_files = list(self.output_dir.glob("qa_*.jsonl"))
            
            for qa_file in qa_files:
                with open(qa_file, 'r') as f:
                    for line in f:
                        qa_data = json.loads(line)
                        all_examples.append({
                            "instruction": qa_data['question'],
                            "output": qa_data['answer'],
                            "source": "document",
                            "context": qa_data.get('context', '')
                        })
        
        # Write combined dataset
        print(f"Writing {len(all_examples)} examples to {output_path}")
        with open(output_path, 'w') as f:
            for example in all_examples:
                f.write(json.dumps(example) + '\n')
        
        return output_path
    
    def _save_qa_pairs(self, qa_pairs: List[QAPair], document_id: str) -> None:
        """Save Q&A pairs to JSONL file"""
        output_path = self.output_dir / f"qa_{document_id}.jsonl"
        
        with open(output_path, 'w') as f:
            for qa in qa_pairs:
                data = {
                    "question": qa.question,
                    "answer": qa.answer,
                    "context": qa.context,
                    "source_document": qa.source_document,
                    "difficulty": qa.difficulty,
                    "category": qa.category,
                }
                f.write(json.dumps(data) + '\n')
    
    def get_stats(self) -> dict:
        """Get training pipeline statistics"""
        # Count Q&A files
        qa_files = list(self.output_dir.glob("qa_*.jsonl"))
        total_qa_pairs = 0
        
        for qa_file in qa_files:
            with open(qa_file, 'r') as f:
                total_qa_pairs += sum(1 for _ in f)
        
        # Get interaction stats
        interaction_stats = self.interaction_store.get_stats()
        
        return {
            "document_qa_files": len(qa_files),
            "total_qa_pairs": total_qa_pairs,
            "interaction_conversations": interaction_stats['conversation_count'],
            "interaction_messages": interaction_stats['message_count'],
            "training_output_dir": str(self.output_dir),
        }
