from app.config import get_settings
from groq import Groq


settings = get_settings()

api_key = settings.groq_api_key.get_secret_value()

print(
    "API key loaded by Settings:",
    bool(api_key),
)

print(
    "API key length:",
    len(api_key),
)


client = Groq(
    api_key=api_key,
    max_retries=0,
)


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_overall_sales",
            "description": (
                "Get overall CPG sales performance "
                "including revenue."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            }
                        },
                        "additionalProperties": False,
                    }
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    }
]


response = client.chat.completions.create(
    model=settings.groq_model,
    messages=[
        {
            "role": "user",
            "content": "What is our total revenue?",
        }
    ],
    tools=tools,
    tool_choice="auto",
    max_tokens=300,
    temperature=0,
)


print(response)