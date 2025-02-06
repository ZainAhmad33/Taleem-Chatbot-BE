from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import chromadb
import ollama
import os
from groq import Groq


class ChatService:
  def __init__(self):
    self.chat_history = list()
    self.historical_questions = list()
    self.chroma_client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_db"))
    self.groq_client = Groq(
      api_key="",
    )
    self.EMBEDDINGS_LLM = "bge-large"
    self.LLAMA_LLM = 'llama-3.2-1b-preview'
    self.DEEPSEEK_LLM = 'deepseek-r1-distill-llama-70b'

  def print_chat_history(self):
    for obj in self.chat_history:
      print(obj)
      print()

  def add_document(self, filename):
    loader = PyPDFLoader(filename)
    # Load the document
    documents = loader.load()
    text_splits = self.split_documents(documents)
    self.add_to_db("EmbeddingsCollection", filename, text_splits)

  def split_documents(self, documents, chunk_size=200, chunk_overlap=50):
    # Split the documents into chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
      chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)

  def add_to_db(self, collection_name, document_name, document_splits):
    print("Saving documents to database for retrieval")
    collection = self.chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "A collection containing documents for RAG with Ollama"}
    )

    for i, doc in enumerate(document_splits):
      response = ollama.embeddings( prompt=doc.page_content, model=self.EMBEDDINGS_LLM )["embedding"]
      collection.add(
          documents=[doc.page_content],
          metadatas=[doc.metadata],
          ids=[f'"{document_name}_{i}"'],
          embeddings=[response]
      )
    print("Documents Saved")

  def send_llm_query(self, prompt, model):
    chat_completion = self.groq_client.chat.completions.create(
      messages=[{
        "role": "user",
        "content": prompt
      }],
      model=model,
    )
    return chat_completion.choices[0].message.role, chat_completion.choices[0].message.content

  def contextualize_question(self, question):
    if len(self.historical_questions) > 0:
      prompt = f"""
        Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is.
        History: {','.join(self.historical_questions)}
        Current Question: {question}
        """
      _, content = self.send_llm_query(prompt, self.LLAMA_LLM)
      return content
    else:
      return question

  def retrieve_documents(self, collection_name, question, n_results=2):
    query_embedding = ollama.embeddings( prompt=question, model=self.EMBEDDINGS_LLM )["embedding"]
    collection = self.chroma_client.get_or_create_collection(name=collection_name)
    results = collection.query(
      query_embeddings=[query_embedding],
      n_results=n_results
    )
    return results['documents'][0], results['metadatas'][0]

  def add_to_chat_history(self, role, content):
    self.chat_history.append({
        "role": role,
        "content": content
    })

  def add_to_historical_questions(self, question):
    if len(self.historical_questions) == 5:
      self.historical_questions.pop(0)
    self.historical_questions.append(question)

  def ask_question(self, question):
    contextualized_question = self.contextualize_question(question)
    self.add_to_historical_questions(question)
    self.add_to_chat_history("user", question)

    documents, metadata = self.retrieve_documents("EmbeddingsCollection", contextualized_question, 3)
    formatted_documents = "\\n".join(documents)
    prompt=f"""You are an assistant for question-answering tasks.
        If you don't know the answer, just say that you don't know.
        Give answers either in English aur in Urdu only based on questions language. Don't use Hindi.
        For any mathematical quesions, give step by step solution with explanations.
        Question: {contextualized_question}
        Cite your answer, in the format [1],[2],[3] ,using these references.
        Use the following documents to answer the question:
        Documents: {formatted_documents}
        Answer:
        """
    role, content = self.send_llm_query(prompt, self.DEEPSEEK_LLM)
    self.add_to_chat_history(role, content)

    return content, {data['page'] for data in metadata}

service = ChatService()

def get_chat_service():
  return service