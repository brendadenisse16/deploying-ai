import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


SRC_DIR = Path(__file__).resolve().parents[2]
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GATEWAY_BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"


def _load_environment() -> None:
	"""Load course env files if present."""
	secrets_path = SRC_DIR / ".secrets"
	env_path = SRC_DIR / ".env"

	if secrets_path.exists():
		load_dotenv(secrets_path)
	if env_path.exists():
		load_dotenv(env_path)


_load_environment()


def _get_client() -> OpenAI:
	"""Create an OpenAI client with course key precedence: gateway first, then OpenAI key."""
	gateway_key = os.getenv("API_GATEWAY_KEY")
	openai_key = os.getenv("OPENAI_API_KEY")

	if gateway_key:
		return OpenAI(
			base_url=GATEWAY_BASE_URL,
			api_key="any value",
			default_headers={"x-api-key": gateway_key},
		)

	if openai_key:
		return OpenAI(api_key=openai_key)

	raise ValueError(
		"No API key found. Set API_GATEWAY_KEY or OPENAI_API_KEY in 05_src/.secrets or 05_src/.env."
	)


def create_study_plan(topic: str, available_minutes: int, difficulty: str) -> dict:
	"""Create a simple study plan with short focus blocks and quick breaks."""
	total = max(15, int(available_minutes))
	difficulty_label = (difficulty or "beginner").strip().lower()

	if difficulty_label == "advanced":
		block_size = 30
	elif difficulty_label == "intermediate":
		block_size = 25
	else:
		block_size = 20

	blocks = []
	remaining = total
	block_index = 1

	while remaining > 0:
		current_block = min(block_size, remaining)
		activity = "review notes and summarize key ideas"
		if block_index % 2 == 0:
			activity = "practice with one small coding example"

		blocks.append(
			{
				"block": block_index,
				"minutes": current_block,
				"activity": f"{topic}: {activity}",
			}
		)

		remaining -= current_block
		if remaining > 0:
			break_minutes = min(5, remaining)
			blocks.append(
				{
					"block": f"break-{block_index}",
					"minutes": break_minutes,
					"activity": "short break: stand up, hydrate, and reset",
				}
			)
			remaining -= break_minutes

		block_index += 1

	return {
		"topic": topic,
		"difficulty": difficulty_label,
		"available_minutes": total,
		"plan": blocks,
		"tip": "Keep each study block focused on one concept before moving on.",
	}


def generate_quiz(topic: str, num_questions: int, difficulty: str) -> dict:
	"""Generate simple topic-focused quiz questions with expected answers."""
	count = max(1, min(10, int(num_questions)))
	difficulty_label = (difficulty or "beginner").strip().lower()

	question_templates = [
		"Define this concept in one or two sentences.",
		"Why is this concept important in Deployment AI?",
		"Give one practical example related to the course labs.",
		"What is a common mistake students make with this topic?",
		"How would you explain this topic to a classmate quickly?",
	]

	answer_templates = {
		"beginner": "A clear basic explanation that names the concept and one simple use case.",
		"intermediate": "An explanation with one concrete workflow step and one trade-off.",
		"advanced": "A concise explanation including implementation details and evaluation considerations.",
	}
	expected_style = answer_templates.get(difficulty_label, answer_templates["beginner"])

	questions = []
	for i in range(count):
		prompt = question_templates[i % len(question_templates)]
		questions.append(
			{
				"question_number": i + 1,
				"question": f"[{topic}] {prompt}",
				"expected_answer": expected_style,
			}
		)

	return {
		"topic": topic,
		"difficulty": difficulty_label,
		"num_questions": count,
		"questions": questions,
	}


TOOLS = [
	{
		"type": "function",
		"name": "create_study_plan",
		"description": "Create a short study plan with focused blocks and breaks.",
		"strict": True,
		"parameters": {
			"type": "object",
			"properties": {
				"topic": {
					"type": "string",
					"description": "Course topic, e.g., function calling or vector databases.",
				},
				"available_minutes": {
					"type": "integer",
					"description": "Total time available for study.",
				},
				"difficulty": {
					"type": "string",
					"description": "beginner, intermediate, or advanced",
				},
			},
			"required": ["topic", "available_minutes", "difficulty"],
			"additionalProperties": False,
		},
	},
	{
		"type": "function",
		"name": "generate_quiz",
		"description": "Generate a short quiz with expected answers.",
		"strict": True,
		"parameters": {
			"type": "object",
			"properties": {
				"topic": {
					"type": "string",
					"description": "Course topic, e.g., embeddings or APIs.",
				},
				"num_questions": {
					"type": "integer",
					"description": "Number of questions requested.",
				},
				"difficulty": {
					"type": "string",
					"description": "beginner, intermediate, or advanced",
				},
			},
			"required": ["topic", "num_questions", "difficulty"],
			"additionalProperties": False,
		},
	},
]


def handle_study_tool_request(user_message: str) -> str:
	"""Use model tool-calling so the model decides whether to build a plan or quiz."""
	client = _get_client()
	instructions = (
		"You are a friendly, concise Deployment AI study coach. "
		"When helpful, call exactly one tool: create_study_plan or generate_quiz. "
		"If required details are missing, ask one short follow-up question."
	)

	conversation_input = [{"role": "user", "content": user_message}]

	response = client.responses.create(
		model=MODEL_NAME,
		instructions=instructions,
		tools=TOOLS,
		input=conversation_input,
	)

	conversation_input += response.output

	for item in response.output:
		if item.type != "function_call":
			continue

		args = json.loads(item.arguments)

		if item.name == "create_study_plan":
			result = create_study_plan(**args)
		elif item.name == "generate_quiz":
			result = generate_quiz(**args)
		else:
			continue

		conversation_input.append(
			{
				"type": "function_call_output",
				"call_id": item.call_id,
				"output": json.dumps(result),
			}
		)

		follow_up = client.responses.create(
			model=MODEL_NAME,
			instructions=instructions,
			tools=TOOLS,
			input=conversation_input,
		)
		return follow_up.output_text

	return response.output_text


if __name__ == "__main__":
	print("Function service test")

	message_1 = "Make me a 45-minute beginner study plan for vector databases."
	print("\nRequest 1:", message_1)
	print("Response 1:")
	print(handle_study_tool_request(message_1))

	message_2 = "Create a 3-question intermediate quiz on function calling."
	print("\nRequest 2:", message_2)
	print("Response 2:")
	print(handle_study_tool_request(message_2))
