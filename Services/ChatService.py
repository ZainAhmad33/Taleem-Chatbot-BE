from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import chromadb
import ollama
import os
from groq import Groq

from Models.Request.ChatRequestModel import ChatRequestModel
from Models.Response.MessageResponseModel import MessageResponseModel

import Helpers


class ChatService:
  def __init__(self):
    self.chat_history = list()
    self.historical_questions = ''
    self.chroma_client = chromadb.PersistentClient(path=os.path.join(os.getcwd(), "chroma_db"))
    self.groq_client = Groq(
      api_key="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",
    )
    self.EMBEDDINGS_LLM = "bge-large"
    self.LLAMA_LLM = 'gemma2-9b-it'
    self.DEEPSEEK_LLM = 'deepseek-r1-distill-llama-70b'

  async def print_chat_history(self):
    for obj in self.chat_history:
      print(obj)
      print()

  async def add_document(self, filename):
    loader = PyPDFLoader(filename)
    # Load the document
    documents = loader.load()
    text_splits = await self.split_documents(documents)
    return self.add_to_db("EmbeddingsCollection", filename, text_splits)

  async def split_documents(self, documents, chunk_size=200, chunk_overlap=50):
    # Split the documents into chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
      chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)

  async def add_to_db(self, collection_name, document_name, document_splits):
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
    query_embedding = ollama.embeddings( prompt=question, model=self.EMBEDDINGS_LLM )["embedding"]
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

  async def ask_question(self, chat_data: ChatRequestModel):
    question = chat_data.chat.pop().content
    historical_question = chat_data.historical_question
    grade = chat_data.grade
    course = chat_data.course
    
    contextualized_question = await self.contextualize_question(historical_question, question)
    print('Question: ', contextualized_question)
    #self.add_to_historical_questions(contextualized_question)
    #self.add_to_chat_history("user", question)

    documents, metadata = await self.retrieve_documents("EmbeddingsCollection", contextualized_question, 3)
    formatted_documents = "\\n".join(documents)
    prompt=f"""You are an assistant for question-answering tasks.
        If you don't know the answer, just say that you don't know.
        Give answers either in English aur in Urdu only based on questions language. Don't use Hindi.
        For any mathematical quesions, give step by step solution with explanations.
        Question: {contextualized_question}
        Use the following documents to answer the question. Also use in-text citations in the format [1],[2],[3]:
        Documents: {formatted_documents}
        Answer:
        """
    role, content = await self.send_llm_query(prompt, self.DEEPSEEK_LLM)
    #self.add_to_chat_history(role, content)
    reasoning, content = Helpers.split_content(content)
    response = MessageResponseModel.create(role, content, {data['page'] for data in metadata}, documents, contextualized_question, reasoning)

    return response

service = ChatService()

def get_chat_service():
  return service