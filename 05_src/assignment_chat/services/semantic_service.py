import json
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv


ASSIGNMENT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = ASSIGNMENT_DIR / "data" / "course_notes.jsonl"
CHROMA_PATH = ASSIGNMENT_DIR / "chroma_db"
COLLECTION_NAME = "assignment_course_notes"
EMBEDDING_MODEL = "text-embedding-3-small"
GATEWAY_BASE_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"


def _load_environment():
	"""Load environment variables from 05_src/.secrets and 05_src/.env when present."""
	secrets_path = SRC_DIR / ".secrets"
	env_path = SRC_DIR / ".env"

	if secrets_path.exists():
		load_dotenv(secrets_path)
	if env_path.exists():
		load_dotenv(env_path)


_load_environment()


def _build_embedding_function() -> OpenAIEmbeddingFunction:
    gateway_key = os.getenv("API_GATEWAY_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gateway_key:
        return OpenAIEmbeddingFunction(
            api_key="any value",
            model_name=EMBEDDING_MODEL,
            api_base=GATEWAY_BASE_URL,
            default_headers={"x-api-key": gateway_key},
        )

    if openai_key and _is_valid_openai_key(openai_key):
        return OpenAIEmbeddingFunction(
            api_key=openai_key,
            model_name=EMBEDDING_MODEL,
        )

    raise ValueError(
        "No valid API key found. Set API_GATEWAY_KEY or a valid OPENAI_API_KEY."
    )


def _get_collection():
	"""Create or reuse a persistent ChromaDB collection for course notes."""
	client = chromadb.PersistentClient(path=str(CHROMA_PATH))
	embedding_fn = _build_embedding_function()
	return client.get_or_create_collection(
		name=COLLECTION_NAME,
		embedding_function=embedding_fn,
	)


def _load_notes_jsonl(data_path: Path = DATA_PATH):
	"""Load one JSON object per line from the course notes dataset."""
	records = []
	with data_path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			records.append(json.loads(line))
	return records


def _index_course_notes(data_path: Path = DATA_PATH):
	"""Index notes into ChromaDB. Safe to call repeatedly (upsert by id)."""
	collection = _get_collection()
	records = _load_notes_jsonl(data_path)

	if not records:
		return collection

	ids = []
	documents = []
	metadatas = []

	for item in records:
		note_id = str(item.get("id", "")).strip()
		content = str(item.get("content", "")).strip()
		module = str(item.get("module", "")).strip()
		topic = str(item.get("topic", "")).strip()

		if not note_id or not content:
			continue

		ids.append(note_id)
		documents.append(content)
		metadatas.append(
			{
				"id": note_id,
				"module": module,
				"topic": topic,
			}
		)

	if ids:
		collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

	return collection


def search_course_notes(query: str, top_k: int = 3):
	"""Run semantic search over course notes and return normalized result dicts."""
	collection = _index_course_notes()
	results = collection.query(
		query_texts=[query],
		n_results=top_k,
		include=["documents", "metadatas", "distances"],
	)

	output = []
	ids = results.get("ids", [[]])[0]
	documents = results.get("documents", [[]])[0]
	metadatas = results.get("metadatas", [[]])[0]
	distances = results.get("distances", [[]])[0]

	for idx, _ in enumerate(ids):
		metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
		row = {
			"topic": metadata.get("topic", ""),
			"module": metadata.get("module", ""),
			"content": documents[idx] if idx < len(documents) else "",
		}

		if idx < len(distances):
			row["distance"] = distances[idx]
			# Lower distance is better in Chroma for cosine/l2-style metrics.
			row["score"] = 1.0 / (1.0 + distances[idx]) if distances[idx] is not None else None

		output.append(row)

	return output


if __name__ == "__main__":
	print("Indexing course notes into persistent ChromaDB...")
	_index_course_notes()
	print("Index ready.")

	test_query = "What is function calling and how do tools work in this course?"
	print(f"\nTest query: {test_query}")
	matches = search_course_notes(test_query, top_k=3)

	if not matches:
		print("No results found.")
	else:
		for i, match in enumerate(matches, start=1):
			print(f"\nResult {i}")
			print(f"Module: {match.get('module', '')}")
			print(f"Topic: {match.get('topic', '')}")
			if "distance" in match:
				print(f"Distance: {match['distance']}")
			if "score" in match:
				print(f"Score: {match['score']}")
			print(f"Content: {match.get('content', '')}")
