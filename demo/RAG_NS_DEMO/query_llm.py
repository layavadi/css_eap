from config import Config
import os

def query_llm(query, context):
    # Example with OpenAI GPT API
    from openai import AzureOpenAI

    os.environ["AZURE_OPENAI_API_KEY"] = Config.CSS_OPENAI_KEY
    
    azure_openai_api_version = Config.CSS_OPENAI_VERSION
    azure_openai_endpoint = Config.CSS_OPENAI_ENDPOINT
    azure_openai_deployment = Config.CSS_OPENAI_MODEL

    client = AzureOpenAI(
        # https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
        api_version=azure_openai_api_version,
        # https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal#create-a-resource
        azure_endpoint=azure_openai_endpoint,
    )

    completion = client.chat.completions.create(
        model=azure_openai_deployment,  # e.g. gpt4-turbo
        messages=[
            {
                "role": "user",
                "content": "Generate the response for this question : `" + query + "` based on the provided content below : `" + context + "`",
            },
        ],
    )
    return (completion.choices[0].message.content)