import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Keep location handling simple for the assignment.
LOCATION_COORDS = {
	"montreal": {"latitude": 45.5017, "longitude": -73.5673, "name": "Montreal"},
}


def _resolve_location(location: str) -> dict:
	"""Return known coordinates for supported locations, defaulting to Montreal."""
	if not location:
		return LOCATION_COORDS["montreal"]
	return LOCATION_COORDS.get(location.strip().lower(), LOCATION_COORDS["montreal"])


def _build_weather_summary(temperature: float, windspeed: float) -> str:
	"""Create a short human-friendly weather summary."""
	if temperature <= 0:
		temp_text = "cold"
	elif temperature < 15:
		temp_text = "cool"
	elif temperature < 25:
		temp_text = "mild"
	else:
		temp_text = "warm"

	if windspeed < 10:
		wind_text = "light wind"
	elif windspeed < 25:
		wind_text = "moderate wind"
	else:
		wind_text = "strong wind"

	return f"It feels {temp_text} outside with {wind_text}."


def _build_study_suggestion(temperature: float, windspeed: float) -> str:
	"""Turn weather info into a short study-focused suggestion."""
	if temperature < 5 or windspeed > 30:
		return "Great day for an indoor focus block: try a 45-minute review session, then a short break."
	if 5 <= temperature <= 22 and windspeed <= 25:
		return "Nice conditions for a reset. Do a 30-minute study sprint, then take a 10-minute walk break."
	return "Keep momentum with two 25-minute pomodoros and a quick stretch between topics."


def get_study_weather(location: str = "Montreal") -> dict:
	"""Fetch current weather and return a transformed study coaching response."""
	selected = _resolve_location(location)
	params = {
		"latitude": selected["latitude"],
		"longitude": selected["longitude"],
		"current_weather": "true",
	}

	response = requests.get(OPEN_METEO_URL, params=params, timeout=20)
	response.raise_for_status()
	payload = response.json()

	current = payload.get("current_weather", {})
	temperature = current.get("temperature")
	windspeed = current.get("windspeed")

	if temperature is None or windspeed is None:
		raise ValueError("Open-Meteo response is missing current weather fields.")

	weather_summary = _build_weather_summary(float(temperature), float(windspeed))
	study_suggestion = _build_study_suggestion(float(temperature), float(windspeed))

	return {
		"location": selected["name"],
		"temperature": float(temperature),
		"windspeed": float(windspeed),
		"weather_summary": weather_summary,
		"study_suggestion": study_suggestion,
	}


if __name__ == "__main__":
	result = get_study_weather("Montreal")
	print("Study Weather Check")
	print(f"Location: {result['location']}")
	print(f"Temperature: {result['temperature']} C")
	print(f"Windspeed: {result['windspeed']} km/h")
	print(f"Summary: {result['weather_summary']}")
	print(f"Suggestion: {result['study_suggestion']}")
