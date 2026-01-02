//! Multi-city transit feed management with automatic downloads and ZIP extraction

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use zip::ZipArchive;

/// Configuration for a single transit agency feed
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeedConfig {
    pub city_code: String,
    pub name: String,
    pub gtfs_static_url: String,
    pub gtfs_rt_trip_updates: Option<String>,
    pub gtfs_rt_vehicle_positions: Option<String>,
    pub gtfs_rt_alerts: Option<String>,
    pub requires_api_key: bool,
    pub bounding_box: Option<BoundingBox>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundingBox {
    pub min_lat: f64,
    pub max_lat: f64,
    pub min_lon: f64,
    pub max_lon: f64,
}

/// Global registry of transit feeds
pub struct FeedRegistry {
    feeds: HashMap<String, FeedConfig>,
    base_path: PathBuf,
}

impl FeedRegistry {
    pub fn new(base_path: PathBuf) -> Self {
        let mut registry = Self {
            feeds: HashMap::new(),
            base_path,
        };
        
        registry.register_default_feeds();
        registry
    }

    /// Register pre-configured major US transit systems
    fn register_default_feeds(&mut self) {
        // Washington DC Metro (WMATA)
        self.feeds.insert("wmata".to_string(), FeedConfig {
            city_code: "wmata".to_string(),
            name: "Washington DC Metro".to_string(),
            gtfs_static_url: "https://transitfeeds.com/p/wmata/85/latest/download".to_string(),
            gtfs_rt_trip_updates: Some("https://api.wmata.com/gtfs/bus-gtfsrt-tripupdates.pb".to_string()),
            gtfs_rt_vehicle_positions: None,
            gtfs_rt_alerts: None,
            requires_api_key: true,
            bounding_box: Some(BoundingBox {
                min_lat: 38.79,
                max_lat: 39.12,
                min_lon: -77.47,
                max_lon: -76.91,
            }),
        });

        // New York City (MTA)
        self.feeds.insert("mta".to_string(), FeedConfig {
            city_code: "mta".to_string(),
            name: "New York City MTA".to_string(),
            gtfs_static_url: "http://web.mta.info/developers/data/nyct/subway/google_transit.zip".to_string(),
            gtfs_rt_trip_updates: Some("https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs".to_string()),
            gtfs_rt_vehicle_positions: None,
            gtfs_rt_alerts: Some("https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/camsys%2Fsubway-alerts".to_string()),
            requires_api_key: true,
            bounding_box: Some(BoundingBox {
                min_lat: 40.50,
                max_lat: 40.92,
                min_lon: -74.26,
                max_lon: -73.70,
            }),
        });

        // San Francisco (BART)
        self.feeds.insert("bart".to_string(), FeedConfig {
            city_code: "bart".to_string(),
            name: "San Francisco BART".to_string(),
            gtfs_static_url: "https://www.bart.gov/dev/schedules/google_transit.zip".to_string(),
            gtfs_rt_trip_updates: Some("https://api.bart.gov/gtfsrt/tripupdate.aspx".to_string()),
            gtfs_rt_vehicle_positions: None,
            gtfs_rt_alerts: Some("https://api.bart.gov/gtfsrt/alerts.aspx".to_string()),
            requires_api_key: false,
            bounding_box: Some(BoundingBox {
                min_lat: 37.48,
                max_lat: 38.02,
                min_lon: -122.52,
                max_lon: -121.90,
            }),
        });

        // Chicago (CTA)
        self.feeds.insert("cta".to_string(), FeedConfig {
            city_code: "cta".to_string(),
            name: "Chicago Transit Authority".to_string(),
            gtfs_static_url: "https://www.transitchicago.com/downloads/sch_data/google_transit.zip".to_string(),
            gtfs_rt_trip_updates: None,
            gtfs_rt_vehicle_positions: None,
            gtfs_rt_alerts: None,
            requires_api_key: false,
            bounding_box: Some(BoundingBox {
                min_lat: 41.64,
                max_lat: 42.07,
                min_lon: -87.94,
                max_lon: -87.52,
            }),
        });

        // Los Angeles (LA Metro)
        self.feeds.insert("lametro".to_string(), FeedConfig {
            city_code: "lametro".to_string(),
            name: "Los Angeles Metro".to_string(),
            gtfs_static_url: "https://gitlab.com/LACMTA/gtfs_rail/raw/master/gtfs_rail.zip".to_string(),
            gtfs_rt_trip_updates: Some("https://api.metro.net/gtfsrt/vehicles/all".to_string()),
            gtfs_rt_vehicle_positions: None,
            gtfs_rt_alerts: None,
            requires_api_key: false,
            bounding_box: Some(BoundingBox {
                min_lat: 33.70,
                max_lat: 34.34,
                min_lon: -118.67,
                max_lon: -117.92,
            }),
        });

        // Boston (MBTA)
        self.feeds.insert("mbta".to_string(), FeedConfig {
            city_code: "mbta".to_string(),
            name: "Boston MBTA".to_string(),
            gtfs_static_url: "https://cdn.mbta.com/MBTA_GTFS.zip".to_string(),
            gtfs_rt_trip_updates: Some("https://cdn.mbta.com/realtime/TripUpdates.pb".to_string()),
            gtfs_rt_vehicle_positions: Some("https://cdn.mbta.com/realtime/VehiclePositions.pb".to_string()),
            gtfs_rt_alerts: Some("https://cdn.mbta.com/realtime/Alerts.pb".to_string()),
            requires_api_key: false,
            bounding_box: Some(BoundingBox {
                min_lat: 42.23,
                max_lat: 42.52,
                min_lon: -71.19,
                max_lon: -70.92,
            }),
        });

        // Seattle (King County Metro)
        self.feeds.insert("kingcounty".to_string(), FeedConfig {
            city_code: "kingcounty".to_string(),
            name: "Seattle King County Metro".to_string(),
            gtfs_static_url: "https://metro.kingcounty.gov/gtfs/google_transit.zip".to_string(),
            gtfs_rt_trip_updates: Some("https://s3.amazonaws.com/kcm-alerts-realtime-prod/tripupdates.pb".to_string()),
            gtfs_rt_vehicle_positions: Some("https://s3.amazonaws.com/kcm-alerts-realtime-prod/vehiclepositions.pb".to_string()),
            gtfs_rt_alerts: Some("https://s3.amazonaws.com/kcm-alerts-realtime-prod/alerts.pb".to_string()),
            requires_api_key: false,
            bounding_box: Some(BoundingBox {
                min_lat: 47.24,
                max_lat: 47.78,
                min_lon: -122.44,
                max_lon: -122.22,
            }),
        });

        // Philadelphia (SEPTA)
        self.feeds.insert("septa".to_string(), FeedConfig {
            city_code: "septa".to_string(),
            name: "Philadelphia SEPTA".to_string(),
            gtfs_static_url: "http://www3.septa.org/gtfsrt/gtfs-public.zip".to_string(),
            gtfs_rt_trip_updates: Some("http://www3.septa.org/gtfsrt/septarail-pa-us/Trip/rtTripUpdates.pb".to_string()),
            gtfs_rt_vehicle_positions: None,
            gtfs_rt_alerts: Some("http://www3.septa.org/gtfsrt/septarail-pa-us/Alert/rtAlerts.pb".to_string()),
            requires_api_key: false,
            bounding_box: Some(BoundingBox {
                min_lat: 39.87,
                max_lat: 40.14,
                min_lon: -75.28,
                max_lon: -74.96,
            }),
        });
    }

    /// Download and extract a GTFS feed
    pub async fn download_and_extract_feed(&self, city_code: &str) -> Result<PathBuf, String> {
        let config = self.feeds.get(city_code)
            .ok_or(format!("Unknown city code: {}", city_code))?;

        log::info!("Downloading GTFS feed for {}", config.name);

        // Create directory for this feed
        let feed_dir = self.base_path.join(city_code);
        fs::create_dir_all(&feed_dir)
            .map_err(|e| format!("Failed to create directory: {}", e))?;

        // Download ZIP file
        let zip_path = feed_dir.join("gtfs.zip");
        let response = reqwest::get(&config.gtfs_static_url).await
            .map_err(|e| format!("Failed to download feed: {}", e))?;

        let content = response.bytes().await
            .map_err(|e| format!("Failed to read download: {}", e))?;

        fs::write(&zip_path, content)
            .map_err(|e| format!("Failed to save ZIP: {}", e))?;

        log::info!("Downloaded to {:?}, extracting...", zip_path);

        // Extract ZIP
        extract_zip(&zip_path, &feed_dir)?;

        log::info!("Extracted GTFS feed for {} to {:?}", config.name, feed_dir);

        Ok(feed_dir)
    }

    /// Select appropriate feed based on user location
    pub fn select_feed_by_location(&self, lat: f64, lon: f64) -> Option<String> {
        for (code, config) in &self.feeds {
            if let Some(bbox) = &config.bounding_box {
                if lat >= bbox.min_lat && lat <= bbox.max_lat &&
                   lon >= bbox.min_lon && lon <= bbox.max_lon {
                    return Some(code.clone());
                }
            }
        }
        None
    }

    /// Get feed configuration by city code
    pub fn get_feed(&self, city_code: &str) -> Option<&FeedConfig> {
        self.feeds.get(city_code)
    }

    /// List all available city codes and names
    pub fn list_cities(&self) -> Vec<(String, String)> {
        self.feeds.iter()
            .map(|(code, config)| (code.clone(), config.name.clone()))
            .collect()
    }

    /// Check if a feed is already downloaded and extracted
    pub fn is_feed_downloaded(&self, city_code: &str) -> bool {
        let feed_dir = self.base_path.join(city_code);
        feed_dir.join("stops.txt").exists() && feed_dir.join("routes.txt").exists()
    }
}

/// Extract a ZIP archive to a directory
pub fn extract_zip(zip_path: &Path, extract_to: &Path) -> Result<(), String> {
    let file = File::open(zip_path)
        .map_err(|e| format!("Failed to open ZIP: {}", e))?;

    let mut archive = ZipArchive::new(file)
        .map_err(|e| format!("Failed to read ZIP archive: {}", e))?;

    for i in 0..archive.len() {
        let mut file = archive.by_index(i)
            .map_err(|e| format!("Failed to read ZIP entry: {}", e))?;

        let outpath = match file.enclosed_name() {
            Some(path) => extract_to.join(path),
            None => continue,
        };

        if file.name().ends_with('/') {
            fs::create_dir_all(&outpath)
                .map_err(|e| format!("Failed to create directory: {}", e))?;
        } else {
            if let Some(parent) = outpath.parent() {
                fs::create_dir_all(parent)
                    .map_err(|e| format!("Failed to create parent directory: {}", e))?;
            }
            
            let mut outfile = File::create(&outpath)
                .map_err(|e| format!("Failed to create file: {}", e))?;
            
            io::copy(&mut file, &mut outfile)
                .map_err(|e| format!("Failed to write file: {}", e))?;
        }
    }

    log::info!("Extracted {} files from ZIP", archive.len());
    Ok(())
}

// Tauri commands

#[tauri::command]
pub async fn list_available_cities(state: tauri::State<'_, FeedRegistryState>) -> Result<Vec<CityInfo>, String> {
    let cities = state.0.list_cities().into_iter()
        .map(|(code, name)| CityInfo {
            code,
            name,
            downloaded: state.0.is_feed_downloaded(&code),
        })
        .collect();
    
    Ok(cities)
}

#[tauri::command]
pub async fn download_city_feed(city_code: String, state: tauri::State<'_, FeedRegistryState>) -> Result<String, String> {
    state.0.download_and_extract_feed(&city_code).await?;
    Ok(format!("Successfully downloaded and extracted feed for {}", city_code))
}

#[tauri::command]
pub fn get_city_by_location(lat: f64, lon: f64, state: tauri::State<'_, FeedRegistryState>) -> Result<Option<String>, String> {
    Ok(state.0.select_feed_by_location(lat, lon))
}

// State wrappers

pub struct FeedRegistryState(pub FeedRegistry);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CityInfo {
    pub code: String,
    pub name: String,
    pub downloaded: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feed_selection_dc() {
        let registry = FeedRegistry::new(PathBuf::from("./test_data"));
        
        // Test DC location
        let result = registry.select_feed_by_location(38.9072, -77.0369);
        assert_eq!(result, Some("wmata".to_string()));
    }

    #[test]
    fn test_feed_selection_nyc() {
        let registry = FeedRegistry::new(PathBuf::from("./test_data"));
        
        // Test NYC location (Times Square)
        let result = registry.select_feed_by_location(40.7580, -73.9855);
        assert_eq!(result, Some("mta".to_string()));
    }
}
