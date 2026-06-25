import os
from pathlib import Path
from src.utils.config import config
from src.utils.logger import logger
from src.storage.storage_manager import StorageManager
from src.engine.metrics_engine import MetricsEngine
from src.engine.rag_engine import rag_engine

def deduplicate_all_data():
    """Scans all contact markdown logs, removes duplicate messages,
    rebuilds the SQLite metrics database, and re-indexes ChromaDB.
    """
    logger.info("Starting global self-healing data deduplication process...")
    
    chats_dir = Path(config.CHATS_DIR)
    if not chats_dir.exists():
        logger.warning(f"Chats directory {chats_dir} does not exist. Nothing to deduplicate.")
        return
        
    contacts = [d.name for d in chats_dir.iterdir() if d.is_dir()]
    metrics_engine = MetricsEngine()
    storage_manager = StorageManager(chats_dir)
    
    modified_contacts = set()
    
    # Step 1: Markdown Deduplication
    for contact in contacts:
        paths = storage_manager.get_chat_paths(contact)
        contact_chats_dir = Path(paths["chats_dir"])
        
        if not contact_chats_dir.exists():
            continue
            
        seen_signatures = set()
        contact_modified = False
        
        # Sort files to process them chronologically
        md_files = sorted([f for f in contact_chats_dir.iterdir() if f.is_file() and f.suffix == ".md"])
        
        for file_path in md_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                blocks = content.split("---")
                unique_blocks = []
                file_modified = False
                
                for block in blocks:
                    block_strip = block.strip()
                    if not block_strip:
                        continue
                        
                    lines = block_strip.split("\n")
                    header = lines[0].strip()
                    
                    if header.startswith("### ["):
                        closing_bracket_idx = header.find("]")
                        if closing_bracket_idx != -1:
                            time_str = header[5:closing_bracket_idx]
                            sender = header[closing_bracket_idx + 2:].strip()
                            
                            sig = (sender, time_str)
                            if sig in seen_signatures:
                                # Found a duplicate block! Discard it.
                                file_modified = True
                                contact_modified = True
                                continue
                            else:
                                seen_signatures.add(sig)
                                
                    unique_blocks.append(block)
                
                if file_modified:
                    # Reconstruct file with only unique blocks
                    # Join by "---" and append a trailing "---" if unique_blocks is not empty
                    if unique_blocks:
                        new_content = "---".join(unique_blocks)
                        if not new_content.endswith("\n---\n"):
                            new_content += "\n---\n"
                    else:
                        new_content = ""
                        
                    # Write cleaned logs back thread-safely
                    lock = StorageManager.get_lock(str(file_path))
                    with lock:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                    logger.info(f"Deduplicated monthly log: {file_path}")
                    
            except Exception as e:
                logger.error(f"Failed to deduplicate file {file_path}: {e}")
                
        if contact_modified:
            modified_contacts.add(contact)
            
    logger.info(f"Markdown deduplication complete. Modified contacts: {list(modified_contacts)}")
    
    # Step 2: SQLite Metrics & RAG Re-indexing Repair
    if not modified_contacts:
        logger.info("No duplicates found. Database and RAG indices are clean.")
        return
        
    for contact in modified_contacts:
        logger.info(f"Repairing database metrics and RAG index for contact: {contact}")
        
        # 1. Clear SQLite metrics for this contact
        try:
            with metrics_engine._write_lock:
                cur = metrics_engine.conn.cursor()
                cur.execute("DELETE FROM connection_metrics WHERE chat_name = ?;", (contact,))
                metrics_engine.conn.commit()
            logger.info(f"Cleared SQLite metrics for {contact}.")
        except Exception as e:
            logger.error(f"Failed to clear SQLite metrics for {contact}: {e}")
            
        # 2. Clear RAG index in ChromaDB for this contact
        try:
            with rag_engine._lock:
                rag_engine.collection.delete(where={"chat_name": contact})
            logger.info(f"Cleared RAG index in ChromaDB for {contact}.")
        except Exception as e:
            logger.error(f"Failed to clear RAG index for {contact}: {e}")
            
        # 3. Parse cleaned markdown logs and repopulate both SQLite metrics and RAG index
        paths = storage_manager.get_chat_paths(contact)
        contact_chats_dir = Path(paths["chats_dir"])
        
        md_files = sorted([f for f in contact_chats_dir.iterdir() if f.is_file() and f.suffix == ".md"])
        rag_batch = []
        BATCH_SIZE = 50
        
        for file_path in md_files:
            month_id = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                blocks = content.split("---")
                for block in blocks:
                    block_strip = block.strip()
                    if not block_strip:
                        continue
                        
                    lines = block_strip.split("\n")
                    header = lines[0].strip()
                    
                    if header.startswith("### ["):
                        closing_bracket_idx = header.find("]")
                        if closing_bracket_idx != -1:
                            time_str = header[5:closing_bracket_idx]
                            date_str = time_str.split()[0]  # YYYY-MM-DD
                            
                            # Re-increment message count
                            metrics_engine.increment_message(contact, date_str)
                            
                    # Accumulate RAG chunks
                    rag_batch.append((contact, month_id, block))
                    if len(rag_batch) >= BATCH_SIZE:
                        rag_engine.add_messages_batch(rag_batch)
                        rag_batch = []
                        
            except Exception as e:
                logger.error(f"Failed to parse cleaned logs for re-indexing {file_path}: {e}")
                
        if rag_batch:
            rag_engine.add_messages_batch(rag_batch)
            
        logger.info(f"Successfully repaired metrics and RAG index for {contact}.")
        
    logger.info("Global self-healing data deduplication process finished successfully.")

if __name__ == "__main__":
    # Execute deduplication directly if run as a script
    import sys
    # Add project root to path if needed
    sys.path.append(str(Path(__file__).parent.parent.parent))
    deduplicate_all_data()
