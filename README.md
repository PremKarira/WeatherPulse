# Weather Monitoring Application

## Overview

This application is designed to monitor weather data, utilizing the OpenWeatherMap API to retrieve weather information and store it in a MongoDB database. It provides a RESTful API to interact with the data and a simple user interface to display weather information.

## Features

- Fetch current weather data from the OpenWeatherMap API.
- Store weather data in a MongoDB database.
- Calculate daily weather summaries.
- Trigger alerts based on user-defined thresholds.
- User-friendly interface for viewing weather data.

## Technologies Used

- **Python**: The primary programming language.
- **Flask**: Web framework for building the API.
- **MongoDB**: NoSQL database for storing weather data.
- **Requests**: For making API calls to OpenWeatherMap.

## Getting Started

### Prerequisites

- **Python**: Ensure Python is installed on your machine. You can download it from [Python's official website](https://www.python.org/downloads/).
- **MongoDB**: Make sure you have a MongoDB instance running. You can download MongoDB from [MongoDB's official website](https://www.mongodb.com/try/download/community).

### Setup

1. Create a `.env` file in the root directory of your project with the following content:
    ```
    OPENWEATHER_API_KEY=your_api_key_here
    MONGODB_URI=mongodb://localhost:27017/weatherdb
    ```
   Replace `your_api_key_here` with your actual OpenWeatherMap API key.

2. Install the required Python packages:

   pip install -r requirements.txt

3. Run the application:

   python app.py

4. Access the application at `http://localhost:5000`.

### Dependencies

To set up and run the application, the following dependencies are required:

- **Flask**: For building the web server and API.
- **Requests**: For making API calls to OpenWeatherMap.
- **PyMongo**: For interacting with the MongoDB database.

These dependencies are listed in the `requirements.txt` file.

## Running Tests

To run the tests, use the following command:
```bash
    pytest test_app.py
```
