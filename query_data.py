import argparse
import os
import re
# from langchain_community.vectorstores.chroma import Chroma
from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_community.llms.ollama import Ollama
from openai import AzureOpenAI
import httpx

from get_embedding_function import get_embedding_function
from check_sr import create_sr,check_sr

# Disable SSL verification (not recommended for production)
http_client = httpx.Client(verify=False)
CHROMA_PATH = "chroma"

def load_template(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read()
    return ""

def combine_templates(services, forms, other):
    service_template_path = f"Prompt_Templates/Services/{services}/template.txt"
    forms_template_path = f"Prompt_Templates/Forms/{forms}/template.txt"
    other_template_path = f"Prompt_Templates/Other/{other}/template.txt"

    service_template = load_template(service_template_path)
    forms_template = load_template(forms_template_path)
    other_template = load_template(other_template_path)

    combined_template = service_template + "\n" + forms_template + "\n" + other_template + "\n" + PROMPT_TEMPLATE

    return combined_template

PROMPT_TEMPLATE = """
  You are an AI assistant reading a current user query and chat_history.
  Given the chat_history, and current user's query, infer the user's intent expressed in the current user query.
  Once you infer the intent, respond with a search query that can be used to retrieve relevant documents for the current user's query based on the intent.
  Be specific in what the user is asking about, but disregard parts of the chat history that are not relevant to the user's intent.

  Your main focus is to **only retrieve information related to Service Request (SR) creation** for the specific service the user is asking about.
  If the query is related to SR creation or open SR, ensure that your search focuses on the following:
  - Information required to raise a sr or service request in servicenow to onboard the account on I-AIOPS
  - Information required to raise a sr or service request in servicenow to enable extension services
  - Information required to raise a sr or service request in servicenow to enable Automation services

  Ignore any requests or parts of the chat history that are not directly related to SR creation for the service in question.
{context}

---

Answer the question based on the above context: {question}
"""

def main():
    sr_queries = ["create","sr","check","update"]
    match_count = 0

    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    parser.add_argument("--services", type=str, required=True, help="Services for the query.")
    parser.add_argument("--forms", type=str, required=True, help="Forms for the query.")
    parser.add_argument("--other", type=str, required=True, help="Other query.")
    args = parser.parse_args()

    query_text = args.query_text
    services = args.services
    forms = args.forms
    other = args.other

    for query in sr_queries:
        if query in query_text.lower():
            match_count += 1

    if (match_count <= 1 ):
        query_rag(query_text, services, forms, other)
    else:
        if 'create' in query_text.lower():
            pattern = r'(create an sr to|open an sr for|create an sr for|open an sr to) (.*)'
            matches = re.findall(pattern,query_text.lower())
            query_text = create_sr(matches[0][1])
            # print("########## Query text - Create [WILL BE REMOVED] ##########")
            # print(query_text)
            query_rag(query_text, services, forms, other)
        elif 'check' in query_text.lower():
            pattern = r'(sr\d+|ritm\d+|\d+)'
            matched_sr_pattern = re.findall(pattern, query_text.lower())
            query_text = check_sr(matched_sr_pattern[0])
            # print("########## Query text - Check [WILL BE REMOVED] ##########")
            # print(query_text)
            query_rag(query_text, services, forms, other)

def build_query(user_query, services, forms):
    # Combine services and forms with the user query
    #query = f"Role: {role}, Account: {account}, Query: {user_query}"
    query = f"Forms: {forms}, Services: {services}, Query: {user_query}"
    # print("************* Buid Query Out *************")
    # print (query)
    return query

def query_rag(query_text: str, services: str, forms: str, other: str):
    # print("Original Query:", query_text)

    # Build the final query with forms and services
    final_query = build_query(query_text, forms, services)
    # print("Final Query:", final_query)

    embedding_function = get_embedding_function()
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)
    # Perform the search without a specific role filter
    results = db.similarity_search_with_score(final_query, k=5)
    # print("Raw Results Retrieved:", results)

    # if not results:
    #     print("No results found with the current query.")
    #     return "No valid documents available."

    # # Manually filter results by role in the document metadata
    # filtered_results = [
    #     (doc, score) for doc, score in results if (doc.metadata.get("service") == services or doc.metadata.get("form") == forms)
    # ]
    # print("Filtered Results:", filtered_results)

    # if not filtered_results:
    #     print("No results found after filtering by Services.")
    #     return "No valid documents available."

    # try:
    #     context_texts = [doc.page_content for doc, _score in filtered_results]
    #     context_text = "\n\n---\n\n".join(context_texts)
    #     print("Context Text:", context_text)

    # except:
    #     print("############## Error ##############")

    if not results:
        print("No results found with the current query.")
        return "No valid documents available."

    # try:
    #     context_texts = [results]
    #     context_text = "\n\n---\n\n".join(context_texts)
    #     print("Context Text:", context_text)

    # except:
    #     print("############## Error ##############")

    # Combine templates for prompt engineering
    prompt_template = combine_templates(services, forms, other)
    prompt = ChatPromptTemplate.from_template(prompt_template)
    final_prompt = prompt.format(context=results, question=query_text)
    # print("Final Prompt Sent to LLM:", final_prompt)

    # # Call the model with the constructed prompt
    # model = Ollama(model="mistral")
    # # response_text = model.invoke(final_prompt)
    # response_text = model.invoke(final_prompt, request_timeout=500)

    llm = AzureOpenAI(
    api_key="87469c792e614835a87e891ef9d8bedb",
    base_url="https://asopeanai.openai.azure.com/openai/deployments/completionaideployment/chat/completions?api-version=2023-03-15-preview",
    api_version="2024-02-15-preview",
    http_client=http_client
)

    def generate_response(prompt):
      response = llm.chat.completions.create(
          model="gpt-4o-mini",  # Use the deployment name
          messages=[
              {"role": "user", "content": prompt}
          ],
          max_tokens=1024,
          n=1,
          stop=None,
          temperature=0.7
      )
      return response.choices[0].message.content


    final_prompt = f"{results}\n\nUser Query: {query_text}"

    response_text = generate_response(final_prompt)

    sources = [doc.metadata.get("id", None) for doc, _score in results]
    formatted_response = f"Response: {response_text}"
    # formatted_response = f"Response: {response_text}\nSources: {sources}"
    print(formatted_response)
    # print("Formatted Response:", formatted_response)
    return formatted_response

if __name__ == "__main__":
    main()
