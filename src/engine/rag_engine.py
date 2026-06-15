import os
import chromadb
import hashlib
import google.generativeai as genai
from src.utils.config import config
from src.utils.logger import logger

class RAGEngine:
    def __init__(self):
        self.db_path = "chroma_db"
        self.client = chromadb.PersistentClient(path=self.db_path)

        if config.GOOGLE_API_KEY:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

        self.collection = self.client.get_or_create_collection(
            name="instagram_messages",
            metadata={"hnsw:space": "cosine"}
        )

    def add_messages_to_index(self, chat_name, quarter, messages_text):
        # Split by separator
        chunks = [c.strip() for c in messages_text.split("---") if c.strip()]
        if not chunks:
            return

        ids = [f"{chat_name}_{quarter}_{i}_{hashlib.md5(c.encode('utf-8')).hexdigest()}"[:100] for i, c in enumerate(chunks)]
        metadatas = [{"chat_name": chat_name, "quarter": quarter} for _ in range(len(chunks))]

        # We use the default embedding function provided by Chroma or could use Gemini embeddings
        self.collection.upsert(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def add_messages_batch(self, messages):
        """
        Batches multiple messages for a single upsert to ChromaDB.
        messages: list of (chat_name, quarter, messages_text) tuples.
        """
        all_chunks = []
        all_ids = []
        all_metadatas = []

        for chat_name, quarter, messages_text in messages:
            chunks = [c.strip() for c in messages_text.split("---") if c.strip()]
            for i, c in enumerate(chunks):
                all_chunks.append(c)
                # Stable ID across restarts
                msg_hash = hashlib.md5(c.encode('utf-8')).hexdigest()
                all_ids.append(f"{chat_name}_{quarter}_{i}_{msg_hash}"[:100])
                all_metadatas.append({"chat_name": chat_name, "quarter": quarter})

        if all_chunks:
            self.collection.upsert(
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids
            )

    def query(self, prompt, chat_filter=None):
        if not self.model:
            raise RuntimeError(
                "Gemini model not configured – set GOOGLE_API_KEY in .env. "
                "The RAG query will be skipped."
            )
        where = {"chat_name": chat_filter} if chat_filter else None
        results = self.collection.query(
            query_texts=[prompt],
            n_results=10,
            where=where
        )
        if not results['documents'] or not results['documents'][0]:
            return "No relevant chat history found for this query."
        context = "\n".join(results['documents'][0])
        full_prompt = f"""
        You are an AI assistant analyzing Instagram DMs.
        Use the following chat history context to answer the user's question accurately.

        CONTEXT:
        {context}

        USER QUESTION:
        {prompt}

        ANSWER:
        """
        response = self.model.generate_content(full_prompt)
        return response.text

    def analyze_profile(self, chat_name):
        if not self.model:
            return "Gemini model not configured."

        results = self.collection.get(where={"chat_name": chat_name})
        if not results['documents']:
            return f"No messages found for {chat_name} in the index."

        context = "\n".join(results['documents'])

        prompt = f"""
        Analyze the following chat history for the person named '{chat_name}'.
        Provide a detailed psychological profile including:
        1. General behavioral patterns.
        2. Strengths and weaknesses observed.
        3. Sentiments towards the user.
        4. Overall psychology.

        CHAT HISTORY:
        {context[:15000]}
        """

        response = self.model.generate_content(prompt)
        return response.text

rag_engine = RAGEngine()
