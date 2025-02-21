from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import chromadb
from groq import Groq

import base64
import os
import tempfile
import requests

from Models.Request.ChatRequestModel import ChatRequestModel
from Models.Request.UploadBookRequestModel import UploadBookRequestModel

from Models.Response.MessageResponseModel import MessageResponseModel

from Config import settings
import Helpers
from Constants import Constants

from fastapi import HTTPException


class ChatService:
  def __init__(self):
    self.chat_history = list()
    self.historical_questions = ''
    self.chroma_client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_db"))
    self.groq_client = Groq(
      api_key=settings.groq_api,
    )
    self.LLAMA_LLM = settings.contextualize_llm
    self.DEEPSEEK_LLM = settings.chat_llm

  async def print_chat_history(self):
    for obj in self.chat_history:
      print(obj)
      print()

  async def add_document(self, book_data: UploadBookRequestModel):
    pdf_data = base64.b64decode(book_data.filedata)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(pdf_data)
        tmp_file_path = tmp_file.name 
    
    loader = PyPDFLoader(tmp_file_path)
    # Load the document
    documents = loader.load()
    text_splits = await self.split_documents(documents)
    return await self.add_to_db(book_data.filename, text_splits)

  async def split_documents(self, documents, chunk_size=200, chunk_overlap=50):
    # Split the documents into chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
      chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)

  async def add_to_db(self, collection_name, document_splits):
    print("Saving documents to database for retrieval")
    collection = self.chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "A collection containing documents for RAG with Ollama"}
    )

    for i, doc in enumerate(document_splits):
      response = await self.get_embeddings(doc.page_content)
      collection.add(
          documents=[doc.page_content],
          metadatas=[doc.metadata],
          ids=[f'"{collection_name}_{i}"'],
          embeddings=[response]
      )
    print("Documents Saved")
    return "Document Saved"

  async def send_llm_query(self, prompt, model):
    chat_completion = self.groq_client.chat.completions.create(
      messages=[{
        "role": "user",
        "content": prompt
      }],
      model=model,
    )
    return chat_completion.choices[0].message.role, chat_completion.choices[0].message.content

  async def contextualize_question(self, historical_question, question):
    if historical_question != '':
      prompt = f"""
        Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just return the question. If the question asked is not relevant to chat history, return it without chaning anything.
        History: {historical_question}
        Current Question: {question}
        """
      _, content = await self.send_llm_query(prompt, self.LLAMA_LLM)
      return content
    else:
      return question

  async def retrieve_documents(self, collection_name, question, n_results=2):
    query_embedding = await self.get_embeddings(question)
    collection = self.chroma_client.get_or_create_collection(name=collection_name)
    results = collection.query(
      query_embeddings=[query_embedding],
      n_results=n_results
    )
    docs = []
    metadatas = []
    for idx, dist in enumerate(results['distances'][0]):
      if dist <= 250:
        docs.append(results['documents'][0][idx])
        metadatas.append(results['metadatas'][0][idx])
    return docs, metadatas

  async def add_to_chat_history(self, role, content):
    self.chat_history.append({
        "role": role,
        "content": content
    })

  async def add_to_historical_questions(self, question):
    self.historical_questions = question
    
  async def get_embedding_collection_name(self, grade, course):
    if grade == Constants.grade_9th:
      if course == Constants.course_physics:
        return settings.physics_9th_collection
      elif course == Constants.course_biology:
        return settings.biology_9th_collection
    return None

  async def ask_question(self, chat_data: ChatRequestModel):
    question = chat_data.chat.pop().content
    historical_question = chat_data.historical_question
    
    grade = chat_data.grade
    course = chat_data.course
    collection_name = await self.get_embedding_collection_name(grade, course)
    if collection_name is None:
      raise HTTPException(status_code=400, detail="Invalid grade or course")
    
    contextualized_question = await self.contextualize_question(historical_question, question)
    print('Question: ', contextualized_question)
    #self.add_to_historical_questions(contextualized_question)
    #self.add_to_chat_history("user", question)

    documents, metadata = await self.retrieve_documents(collection_name, contextualized_question, 3)
    formatted_documents = "\\n".join(documents)
    prompt=f"""You are an assistant for question-answering tasks.
        If you don't know the answer, just say that you don't know.
        Give answers either in English aur in Urdu only based on questions language. Don't use Hindi.
        For any mathematical quesions, give step by step solution with explanations.
        Question: {contextualized_question}
        Use the following documents to answer the question. Also use in-text citations in the format [1],[2],[3]. Do not create a bibliography.:
        Documents: {formatted_documents}
        Answer:
        """
    role, content = await self.send_llm_query(prompt, self.DEEPSEEK_LLM)
    #self.add_to_chat_history(role, content)
    reasoning, content = Helpers.split_content(content)
    response = MessageResponseModel.create(role, content, {data['page'] for data in metadata}, documents, contextualized_question, reasoning)

    return response

  async def get_embeddings(self, text:str):
    url = 'https://api-atlas.nomic.ai/v1/embedding/text'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {settings.nomic_key}'
    }
    data = {
        "texts": [text],
        "task_type": "search_document",
        "max_tokens_per_text": 8192,
        "dimensionality": 768
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Raise an exception for HTTP errors
    output = response.json()
    return output['embeddings'][0]

service = ChatService()

def get_chat_service():
  return service