from flask import Flask, jsonify, send_from_directory
import requests

def fetch_weather_data():
    api_key = "${WEATHER_API_KEY}"
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Barcelona&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    return {
        "temperature": data["main"]["temp"],
        "description": data["weather"][0]["description"],
        "city": data["name"]
    }

app = Flask(__name__, static_url_path="/", static_folder="static")

@app.route(/)
def serve_index():
    return send_from_directory(app.static_folder, index.html)

@app.route(/api/weather)
def get_weather():
    weather_data = fetch_weather_data()
    return jsonify(weather_data)

if __name__ == "__main__":
    app.run(debug=True)
