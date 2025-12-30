import os
import json
from datetime import datetime
from json_repair import repair_json
from openai import AsyncOpenAI
from pathlib import Path


class AIService:
    """Service for parsing tasks from user messages using AI."""

    def __init__(self) -> None:
        """Initialize AIService with AsyncOpenAI client."""
        api_key = os.getenv("AI_API_KEY")
        base_url = os.getenv("AI_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not api_key:
            raise ValueError("AI_API_KEY is not set in environment variables")
        
        # Client for chat (via OpenRouter or custom provider)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Client for Whisper (native OpenAI API only)
        # Check if we have a separate OpenAI key for Whisper
        openai_key = os.getenv("OPENAI_API_KEY", api_key)
        self.whisper_client = AsyncOpenAI(
            api_key=openai_key,
            base_url="https://api.openai.com/v1"
        )
        
        # Using DeepSeek V3 - fast and cheap model
        self.model = "deepseek/deepseek-chat"

    def _build_system_prompt(self, current_datetime: str) -> str:
        """
        Build system prompt with current datetime for task parsing.
        
        Args:
            current_datetime: Current date and time in format "YYYY-MM-DD HH:MM:SS"
            
        Returns:
            System prompt for AI
        """
        return f"""Ты — умный парсер задач для таск-менеджера. Твоя задача — извлекать из сообщения пользователя описание задачи и время напоминания.

ТЕКУЩЕЕ ВРЕМЯ: {current_datetime} (UTC+3)

ПРАВИЛА:
1. Извлеки суть задачи из сообщения пользователя
2. Если указано время/дата — рассчитай точную дату и время в формате "YYYY-MM-DD HH:MM:SS"
3. Понимай относительные времена: "завтра", "через час", "в следующий вторник", "послезавтра в 15:00" и т.д.
4. Если время НЕ указано — верни null в поле datetime
5. Возвращай ТОЛЬКО чистый JSON, БЕЗ markdown блоков (```json)

ФОРМАТ ОТВЕТА:
{{"task": "описание задачи", "datetime": "YYYY-MM-DD HH:MM:SS"}}

ИЛИ если времени нет:
{{"task": "описание задачи", "datetime": null}}

ПРИМЕРЫ:
Пользователь: "Напомни купить хлеба завтра в 9 утра"
Ответ: {{"task": "Купить хлеба", "datetime": "2025-12-30 09:00:00"}}

Пользователь: "Позвонить маме"
Ответ: {{"task": "Позвонить маме", "datetime": null}}

Пользователь: "Через 2 часа сходить в магазин"
Ответ: {{"task": "Сходить в магазин", "datetime": "2025-12-29 22:15:49"}}"""

    async def parse_task_message(self, user_message: str) -> dict[str, str | None]:
        """
        Parse user message to extract task and scheduled datetime.
        
        Args:
            user_message: User's input message
            
        Returns:
            Dictionary with keys 'task' (str) and 'datetime' (str | None)
            Format: {"task": "Task description", "datetime": "YYYY-MM-DD HH:MM:SS" or null}
            
        Raises:
            Exception: If API call fails or response parsing fails
        """
        try:
            # Get current datetime in UTC+3
            current_dt = datetime.now()
            current_datetime_str = current_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            system_prompt = self._build_system_prompt(current_datetime_str)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.3  # Lower temperature for more consistent parsing
            )
            
            # Extract the response content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from AI")
                
                # Clean up the response (remove markdown code blocks if present)
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                # Try to parse JSON, use json_repair if needed
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    # Try to repair the JSON
                    repaired = repair_json(content)
                    parsed = json.loads(repaired)
                
                # Validate structure
                if not isinstance(parsed, dict) or 'task' not in parsed or 'datetime' not in parsed:
                    raise ValueError(f"Invalid response structure: {parsed}")
                
                return {
                    "task": str(parsed["task"]),
                    "datetime": str(parsed["datetime"]) if parsed["datetime"] else None
                }
            else:
                raise ValueError("No response from AI")
                
        except Exception as e:
            # Log the error (in production, use proper logging)
            print(f"AI Task Parsing Error: {e}")
            raise

    async def transcribe_voice(self, audio_file_path: str) -> str:
        """
        Transcribe voice message using Whisper API.
        
        Args:
            audio_file_path: Path to audio file (ogg, mp3, etc.)
            
        Returns:
            Transcribed text from the audio
            
        Raises:
            Exception: If API call fails or file not found
        """
        try:
            # Check if file exists
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
            # Open and transcribe audio file
            with open(audio_file_path, "rb") as audio_file:
                transcript = await self.whisper_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"  # Russian language hint for better accuracy
                )
            
            return transcript.text.strip()
            
        except Exception as e:
            print(f"Voice Transcription Error: {e}")
            raise
