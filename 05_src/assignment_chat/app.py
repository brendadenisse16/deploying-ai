"""Deployment AI Study Buddy: A Gradio chat interface with integrated services."""

import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

# Import services
from services.semantic_service import search_course_notes
from services.api_service import get_study_weather
from services.function_service import handle_study_tool_request
from services.guardrails import check_user_message, sanitize_response
from services.memory import ConversationMemory


# Load environment from 05_src/.secrets and .env
SRC_DIR = Path(__file__).resolve().parents[1]
if (SRC_DIR / ".secrets").exists():
    load_dotenv(SRC_DIR / ".secrets")
if (SRC_DIR / ".env").exists():
    load_dotenv(SRC_DIR / ".env")


# Initialize global memory
memory = ConversationMemory(max_turns=10)

# System prompt for the study coach
SYSTEM_PROMPT = (
    "You are a friendly, concise Deployment AI study coach. "
    "Help students review and understand course concepts clearly and encouragingly. "
    "Keep responses short but informative. Use accessible language. "
    "When providing information, be accurate about the course material."
)


def process_user_message(user_message: str) -> str:
    """
    Route user message to appropriate service and return response.
    
    Routing logic:
    1. Check guardrails first.
    2. If weather-related keywords, call get_study_weather().
    3. If study tool keywords (plan, quiz), call handle_study_tool_request().
    4. Otherwise, search course notes with semantic_service.
    5. Sanitize before returning.
    """
    # Check guardrails
    allowed, blocked_response = check_user_message(user_message)
    if not allowed:
        return blocked_response

    # Add user message to memory
    memory.add_user_message(user_message)

    message_lower = user_message.lower()
    response = None

    # Route 1: Weather and study break suggestions
    weather_keywords = ["weather", "break", "outside", "temperature", "montreal"]
    if any(kw in message_lower for kw in weather_keywords):
        try:
            weather_data = get_study_weather("Montreal")
            response = (
                f"🌤️ **Study Break Check**\n\n"
                f"Temperature: {weather_data['temperature']}°C\n"
                f"Wind: {weather_data['windspeed']} km/h\n\n"
                f"**Summary:** {weather_data['weather_summary']}\n\n"
                f"**Suggestion:** {weather_data['study_suggestion']}"
            )
        except Exception as e:
            response = (
                "I couldn't fetch the weather right now. "
                "Try asking about a course topic instead!"
            )

    # Route 2: Study planning and quizzes
    elif any(kw in message_lower for kw in ["plan", "quiz", "schedule"]):
        try:
            response = handle_study_tool_request(user_message)
        except Exception as e:
            response = (
                "I had trouble with that request. "
                "Could you be more specific? Try: 'Make a 30-minute study plan for embeddings' "
                "or 'Create a 3-question quiz on vector databases.'"
            )

    # Route 3: Course semantic search (default)
    else:
        try:
            results = search_course_notes(user_message, top_k=3)
            if results and len(results) > 0:
                response = "**Based on the course material:**\n\n"
                for i, result in enumerate(results, 1):
                    topic = result.get("topic", "Unknown")
                    module = result.get("module", "")
                    content = result.get("content", "")
                    response += f"{i}. **{topic}** (Module {module})\n{content}\n\n"
            else:
                response = (
                    "I didn't find relevant course material on that topic. "
                    "Could you rephrase your question or ask about a specific course concept? "
                    "Try asking about function calling, embeddings, RAG, or ChromaDB."
                )
        except Exception as e:
            response = (
                "I'm having trouble searching the course materials right now. "
                f"Please try again. (Error: {str(e)[:30]}...)"
            )

    # Sanitize response to prevent system prompt leakage
    response = sanitize_response(response)

    # Add assistant message to memory
    memory.add_assistant_message(response)

    return response


def launch_app() -> None:
    """Launch the Gradio chat interface."""
    with gr.Blocks(title="Deployment AI Study Buddy") as app:
        gr.Markdown("# 📚 Deployment AI Study Buddy")
        gr.Markdown(
            "A friendly study coach for reviewing Deployment AI concepts. "
            "Ask me about course material, get study plans, or take a quiz!"
        )

        # Chat history
        chatbot = gr.Chatbot(
            label="Conversation",
            height=400,
        )

        # Input section
        with gr.Row():
            user_input = gr.Textbox(
                placeholder="Ask me about a course topic, study plan, quiz, or weather break...",
                label="Your question",
                scale=4,
            )
            submit_btn = gr.Button("Send", variant="primary", scale=1)

        # Example prompts
        gr.Examples(
            examples=[
                "What is RAG?",
                "Explain function calling.",
                "Make me a 30-minute beginner study plan for embeddings.",
                "Create a 3-question intermediate quiz on vector databases.",
                "Should I take a study break in Montreal?",
            ],
            inputs=user_input,
            label="Try these prompts:",
        )

        def respond(message: str, chat_history: list) -> tuple:
            """Process user message and update chat history."""
            if chat_history is None:
                chat_history = []

            # Get response from service routing
            bot_response = process_user_message(message)

            # Append to chat history
            #chat_history.append((message, bot_response))
            chat_history.append({"role": "user", "content": message})
            chat_history.append({"role": "assistant", "content": bot_response})

            return "", chat_history

        # Connect events
        submit_btn.click(
            respond,
            inputs=[user_input, chatbot],
            outputs=[user_input, chatbot],
        )

        user_input.submit(
            respond,
            inputs=[user_input, chatbot],
            outputs=[user_input, chatbot],
        )

    app.launch()


if __name__ == "__main__":
    launch_app()
