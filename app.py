import os
import time
import requests
import schedule
import threading
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
from flask import request

load_dotenv()

app = Flask(__name__)

MONGODB_URI = os.getenv('MONGODB_URI')
client = MongoClient(MONGODB_URI)
db = client['weather_monitoring']
weather_collection = db['weather_data']
summaries_collection = db['daily_summaries']

try:
    client.admin.command('ping')
    print("MongoDB connection successful.")
except Exception as e:
    print(f"MongoDB connection error: {e}")

API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITIES = ["Delhi", "Mumbai", "Chennai", "Bengaluru", "Kolkata", "Hyderabad"]
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
ALERT_THRESHOLD_TEMP = 15

def unix_to_readable(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def kelvin_to_celsius(temp_kelvin):
    return temp_kelvin - 273.15

def get_weather_data(city):
    url = f"{BASE_URL}?q={city}&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data for {city}, Response Code: {response.status_code}")
        return None

def process_weather_data(data):
    city = data['name']
    main = data['weather'][0]['main']
    description = data['weather'][0]['description']
    temp_celsius = kelvin_to_celsius(data['main']['temp'])
    feels_like = kelvin_to_celsius(data['main']['feels_like'])
    dt = unix_to_readable(data['dt'])

    weather_entry = {
        'city': city,
        'temperature': temp_celsius,
        'feels_like': feels_like,
        'main': main,
        'description': description,
        'date_time': dt,
        'unix_time': data['dt'] 
    }

    weather_collection.insert_one(weather_entry)

def check_alerts(data):
    temp_celsius = kelvin_to_celsius(data['main']['temp'])
    city = data['name']

    if temp_celsius > ALERT_THRESHOLD_TEMP:
        print(f"ALERT: {city} temperature exceeds {ALERT_THRESHOLD_TEMP}°C. Current: {round(temp_celsius, 2)}°C")

def calculate_daily_summary(date=None):
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    if date is None:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    else:
        try:
            today = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    daily_summary = {
        'date': today,
        'cities': {}
    }
    
    for city in CITIES:
        regex_pattern = f"^{today}"
        weather_data = list(weather_collection.find({"date_time": {"$regex": regex_pattern, "$options": 'i'}, "city": city}))
        record_count = len(weather_data)

        if record_count > 0:
            temp_values = [entry['temperature'] for entry in weather_data]
            main_weather_conditions = [entry['main'] for entry in weather_data]

            average_temp = round(sum(temp_values) / len(temp_values), 2)
            max_temp = round(max(temp_values), 2)
            min_temp = round(min(temp_values), 2)
            dominant_weather = max(set(main_weather_conditions), key=main_weather_conditions.count)

            daily_summary['cities'][city] = {
                'average_temp': average_temp,
                'max_temp': max_temp,
                'min_temp': min_temp,
                'dominant_weather': dominant_weather,
                'record_count': record_count
            }
        else:
            daily_summary['cities'][city] = {
                'record_count': record_count,
                'message': "No records found"
            }

    summaries_collection.update_one(
        {'date': today},
        {"$set": daily_summary},
        upsert=True
    )

def monitor_weather():
    for city in CITIES:
        weather_data = get_weather_data(city)
        if weather_data:
            process_weather_data(weather_data)
            check_alerts(weather_data)

def time_until_next_run():
    now = datetime.now()
    next_monitor_run = now.replace(second=0, microsecond=0)
    if next_monitor_run.minute % 5 != 0:
        next_monitor_run += timedelta(minutes=(5 - (next_monitor_run.minute % 5)))

    next_monitor_run += timedelta(minutes=5)
    next_summary_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    time_left_monitor = (next_monitor_run - now).total_seconds()
    time_left_summary = (next_summary_run - now).total_seconds()

    return time_left_monitor, time_left_summary

@app.route('/')
def index():
    try:
        summaries = list(summaries_collection.find().sort("date", -1).limit(30))
        time_left_monitor, time_left_summary = time_until_next_run()
        if summaries:
            latest_summary = summaries[0]

            if 'date' in latest_summary and latest_summary.keys() != {'_id', 'date'}:
                return render_template('index.html', summary=latest_summary, time_left_monitor=time_left_monitor, time_left_summary=time_left_summary)
            else:
                return render_template('index.html', error="No valid city data found.")
        else:
            return render_template('index.html', error="No summaries available.")
    except Exception as e:
        print(f"Error encountered: {e}")
        return render_template('index.html', error="An error occurred while processing your request.")

@app.route('/run_weather_monitor', methods=['POST'])
def run_weather_monitor():
    monitor_weather()
    return redirect(url_for('index'))

@app.route('/run_daily_summary', methods=['POST'])
def run_daily_summary():
    calculate_daily_summary()
    return redirect(url_for('index'))

@app.route('/get_summary', methods=['POST'])
def get_summary():
    selected_date = request.form.get('date')
    if selected_date:
        calculate_daily_summary(selected_date)
    
    summary = summaries_collection.find_one({'date': selected_date})
    time_left_monitor, time_left_summary = time_until_next_run()

    if summary:
        return render_template('index.html', summary=summary, time_left_monitor=time_left_monitor, time_left_summary=time_left_summary)
    else:
        return render_template('index.html', error="No data found for the selected date.", time_left_monitor=time_left_monitor, time_left_summary=time_left_summary)

# Relative scheduling
# schedule.every(5).minutes.do(monitor_weather)
# schedule.every(24).hours.do(calculate_daily_summary)

# def run_schedule():
#     while True:
#         schedule.run_pending()
#         time.sleep(1)

# absolute scheduling
def schedule_monitor_weather():
    now = datetime.now()
    next_run = now.replace(second=0, microsecond=0)

    if next_run.minute % 5 != 0:
        next_run += timedelta(minutes=(5 - (next_run.minute % 5)))
    
    next_run += timedelta(minutes=5)
    time_to_wait = (next_run - now).total_seconds()
    
    threading.Timer(time_to_wait, schedule_monitor_weather).start()
    monitor_weather()

def schedule_daily_summary():
    now = datetime.now()
    next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    time_to_wait = (next_run - now).total_seconds()
    threading.Timer(time_to_wait, schedule_daily_summary).start()
    calculate_daily_summary()

if __name__ == '__main__':
    threading.Thread(target=schedule_monitor_weather).start()
    threading.Thread(target=schedule_daily_summary).start()
    app.run(debug=True)
