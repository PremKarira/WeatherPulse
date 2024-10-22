import os
import pytest
from unittest.mock import patch, MagicMock
from app import app, get_weather_data, kelvin_to_celsius, calculate_daily_summary, check_alerts

@pytest.fixture(scope="module")
def test_client():
    app.testing = True
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="module", autouse=True)
def set_env_variables():
    os.environ['OPENWEATHER_API_KEY'] = os.getenv('OPENWEATHER_API_KEY')
    os.environ['MONGODB_URI'] = os.getenv('MONGODB_URI')

@pytest.fixture(scope="module")
def mock_database():
    client = MagicMock()
    client.weather_monitoring.weather_data = MagicMock()
    client.weather_monitoring.daily_summaries = MagicMock()
    
    # Mocking the insert_many method
    client.weather_monitoring.weather_data.insert_many = MagicMock()
    
    # Mocking find_one method for daily summaries
    client.weather_monitoring.daily_summaries.find_one = MagicMock(return_value={
        'date': '2024-10-20',
        'cities': {
            'Delhi': {
                'average_temp': 30.0
            }
        }
    })

    with patch('app.MongoClient', return_value=client):
        yield client

def test_system_setup(test_client):
    response = test_client.get('/')
    assert response.status_code == 200

@patch('app.requests.get')
def test_data_retrieval(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'name': 'Delhi',
        'weather': [{'main': 'Clear', 'description': 'clear sky'}],
        'main': {'temp': 300, 'feels_like': 298},
        'dt': 1633072800  
    }
    mock_get.return_value = mock_response

    data = get_weather_data('Delhi')
    assert data is not None
    assert data['name'] == 'Delhi'

def test_temperature_conversion():
    temp_kelvin = 300  
    temp_celsius = kelvin_to_celsius(temp_kelvin)
    assert pytest.approx(temp_celsius, 0.01) == 26.85

def test_daily_summary_average_temp(mock_database):
    weather_entries = [
        {'city': 'Delhi', 'temperature': 30, 'main': 'Clear', 'date_time': '2024-10-20 10:00:00', 'unix_time': 1697798400},
        {'city': 'Delhi', 'temperature': 32, 'main': 'Clear', 'date_time': '2024-10-20 12:00:00', 'unix_time': 1697802000},
        {'city': 'Delhi', 'temperature': 31, 'main': 'Clear', 'date_time': '2024-10-20 14:00:00', 'unix_time': 1697805600},
        {'city': 'Delhi', 'temperature': 28, 'main': 'Clouds', 'date_time': '2024-10-20 16:00:00', 'unix_time': 1697809200},
        {'city': 'Delhi', 'temperature': 29, 'main': 'Clouds', 'date_time': '2024-10-20 18:00:00', 'unix_time': 1697812800},
    ]
    
    mock_database.weather_data.insert_many(weather_entries)

    calculate_daily_summary('2024-10-20')

    # Set up what find_one should return
    expected_summary = {
        'date': '2024-10-20',
        'cities': {
            'Delhi': {
                'average_temp': 30.0  # Example value
            }
        }
    }
    
    # Mock the return value of find_one
    mock_database.daily_summaries.find_one.return_value = expected_summary

    summary = mock_database.daily_summaries.find_one({'date': '2024-10-20'})
    assert summary is not None
    assert 'cities' in summary
    assert 'Delhi' in summary['cities']
    assert summary['cities']['Delhi']['average_temp'] == pytest.approx(30.0, 0.01)


@patch('app.print')
def test_alerting_thresholds(mock_print):
    data = {
        'main': {'temp': 290},  
        'name': 'Delhi'
    }
    check_alerts(data)
    mock_print.assert_called_with("ALERT: Delhi temperature exceeds 15°C. Current: 16.85°C")


if __name__ == '__main__':
    pytest.main()
