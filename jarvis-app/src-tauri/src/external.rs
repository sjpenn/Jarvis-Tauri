//! External API clients for weather, transit, and other services
//!
//! These are triggered on-demand by the AI layer, NOT streamed continuously.

use serde::{Deserialize, Serialize};

/// Weather data from weather.gov API
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeatherData {
    pub temperature: f32,
    pub unit: String,
    pub conditions: String,
    pub humidity: Option<i32>,
    pub wind_speed: Option<String>,
    pub forecast: Vec<ForecastPeriod>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ForecastPeriod {
    pub name: String,
    pub temperature: i32,
    pub unit: String,
    pub short_forecast: String,
}

/// Train departure info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainDeparture {
    pub line: String,
    pub destination: String,
    pub minutes: String,
    pub car_count: Option<i32>,
}

/// Flight info
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlightInfo {
    pub callsign: String,
    pub origin: Option<String>,
    pub destination: Option<String>,
    pub altitude: Option<i32>,
    pub heading: Option<i32>,
    pub latitude: f64,
    pub longitude: f64,
}

/// Get weather data from weather.gov (free, no API key)
#[tauri::command]
pub async fn get_weather(latitude: f64, longitude: f64) -> Result<WeatherData, String> {
    // First, get the forecast office URL
    let points_url = format!(
        "https://api.weather.gov/points/{:.4},{:.4}",
        latitude, longitude
    );

    let client = reqwest::Client::new();
    
    let points_resp: serde_json::Value = client
        .get(&points_url)
        .header("User-Agent", "JARVIS-App/1.0")
        .send()
        .await
        .map_err(|e| format!("Failed to fetch weather points: {}", e))?
        .json()
        .await
        .map_err(|e| format!("Failed to parse points response: {}", e))?;

    let forecast_url = points_resp["properties"]["forecast"]
        .as_str()
        .ok_or("Could not find forecast URL")?;

    // Get the forecast
    let forecast_resp: serde_json::Value = client
        .get(forecast_url)
        .header("User-Agent", "JARVIS-App/1.0")
        .send()
        .await
        .map_err(|e| format!("Failed to fetch forecast: {}", e))?
        .json()
        .await
        .map_err(|e| format!("Failed to parse forecast: {}", e))?;

    let periods = forecast_resp["properties"]["periods"]
        .as_array()
        .ok_or("No forecast periods found")?;

    let current = periods.first().ok_or("No current weather data")?;

    let forecast: Vec<ForecastPeriod> = periods
        .iter()
        .take(6)
        .filter_map(|p| {
            Some(ForecastPeriod {
                name: p["name"].as_str()?.to_string(),
                temperature: p["temperature"].as_i64()? as i32,
                unit: p["temperatureUnit"].as_str()?.to_string(),
                short_forecast: p["shortForecast"].as_str()?.to_string(),
            })
        })
        .collect();

    Ok(WeatherData {
        temperature: current["temperature"].as_f64().unwrap_or(0.0) as f32,
        unit: current["temperatureUnit"].as_str().unwrap_or("F").to_string(),
        conditions: current["shortForecast"].as_str().unwrap_or("Unknown").to_string(),
        humidity: current["relativeHumidity"]["value"].as_i64().map(|h| h as i32),
        wind_speed: current["windSpeed"].as_str().map(|s| s.to_string()),
        forecast,
    })
}

/// Get Metro train times from WMATA API
#[tauri::command]
pub async fn get_train_times(station_code: String, api_key: String) -> Result<Vec<TrainDeparture>, String> {
    let url = format!(
        "https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{}",
        station_code
    );

    let client = reqwest::Client::new();
    
    let resp: serde_json::Value = client
        .get(&url)
        .header("api_key", &api_key)
        .send()
        .await
        .map_err(|e| format!("Failed to fetch train times: {}", e))?
        .json()
        .await
        .map_err(|e| format!("Failed to parse train response: {}", e))?;

    let trains = resp["Trains"]
        .as_array()
        .ok_or("No train data found")?
        .iter()
        .filter_map(|t| {
            Some(TrainDeparture {
                line: t["Line"].as_str()?.to_string(),
                destination: t["Destination"].as_str()?.to_string(),
                minutes: t["Min"].as_str()?.to_string(),
                car_count: t["Car"].as_str().and_then(|c| c.parse().ok()),
            })
        })
        .collect();

    Ok(trains)
}

/// Get nearby flights from OpenSky Network (free, no API key)
#[tauri::command]
pub async fn get_nearby_flights(
    latitude: f64,
    longitude: f64,
    radius_miles: f64,
) -> Result<Vec<FlightInfo>, String> {
    // Convert radius to lat/lon bounds (rough approximation)
    let lat_delta = radius_miles / 69.0; // ~69 miles per degree latitude
    let lon_delta = radius_miles / (69.0 * (latitude.to_radians().cos()));

    let url = format!(
        "https://opensky-network.org/api/states/all?lamin={}&lomin={}&lamax={}&lomax={}",
        latitude - lat_delta,
        longitude - lon_delta,
        latitude + lat_delta,
        longitude + lon_delta
    );

    let client = reqwest::Client::new();
    
    let resp: serde_json::Value = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to fetch flights: {}", e))?
        .json()
        .await
        .map_err(|e| format!("Failed to parse flight data: {}", e))?;

    let states = resp["states"]
        .as_array()
        .ok_or("No flight data found")?;

    let flights: Vec<FlightInfo> = states
        .iter()
        .filter_map(|state| {
            let arr = state.as_array()?;
            Some(FlightInfo {
                callsign: arr.get(1)?.as_str()?.trim().to_string(),
                origin: arr.get(2)?.as_str().map(|s| s.to_string()),
                destination: None,
                latitude: arr.get(6)?.as_f64()?,
                longitude: arr.get(5)?.as_f64()?,
                altitude: arr.get(7)?.as_f64().map(|a| (a * 3.281) as i32), // meters to feet
                heading: arr.get(10)?.as_f64().map(|h| h as i32),
            })
        })
        .take(20) // Limit to 20 flights
        .collect();

    Ok(flights)
}
