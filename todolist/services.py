# todolist/services.py
import openai
from django.conf import settings

def get_gpt_response(user_message, conversation_history=None):
    openai.api_key = settings.OPENAI_API_KEY

    if conversation_history is None:
        conversation_history = []

    # Добавляем сообщение пользователя
    conversation_history.append({"role": "user", "content": user_message})

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # или "gpt-4", если у вас есть доступ
        messages=conversation_history,
        max_tokens=512,
        temperature=0.7,
    )
    # Получаем текст
    assistant_reply = response.choices[0].message["content"]
    return assistant_reply
