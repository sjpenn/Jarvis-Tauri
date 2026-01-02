//! LLM Chat module - Phi-3 Mini inference using llama-cpp-2

use serde::{Deserialize, Serialize};
use crate::memory::MemoryStore;
use std::sync::Mutex;
use std::path::PathBuf;
use std::num::NonZeroU32;

use llama_cpp_2::context::params::LlamaContextParams;
use llama_cpp_2::llama_backend::LlamaBackend;
use llama_cpp_2::llama_batch::LlamaBatch;
use llama_cpp_2::model::{LlamaModel, AddBos, Special};
use llama_cpp_2::model::params::LlamaModelParams;
use llama_cpp_2::sampling::LlamaSampler;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    pub message: String,
    pub memory_context_used: bool,
    pub memories_retrieved: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThoughtLog {
    pub step: String,
    pub detail: String,
    pub timestamp: i64,
}

pub struct LlmEngine {
    backend: Option<LlamaBackend>,
    model: Option<LlamaModel>,
    model_path: Option<PathBuf>,
}

unsafe impl Send for LlmEngine {}
unsafe impl Sync for LlmEngine {}

impl LlmEngine {
    pub fn new() -> Self {
        Self { backend: None, model: None, model_path: None }
    }

    pub fn init(&mut self, path: PathBuf) -> Result<(), String> {
        if !path.exists() {
            return Err(format!("Model not found: {:?}", path));
        }
        log::info!("Initializing LLM backend...");
        let backend = LlamaBackend::init()
            .map_err(|e| format!("Failed to init backend: {:?}", e))?;
        let model_params = LlamaModelParams::default();
        let model_params = std::pin::pin!(model_params);
        log::info!("Loading model from {:?}...", path);
        let model = LlamaModel::load_from_file(&backend, &path, &model_params)
            .map_err(|e| format!("Failed to load model: {:?}", e))?;
        self.backend = Some(backend);
        self.model = Some(model);
        self.model_path = Some(path);
        log::info!("Model loaded successfully!");
        Ok(())
    }

    pub fn is_ready(&self) -> bool {
        self.backend.is_some() && self.model.is_some()
    }

    pub fn generate(&self, prompt: &str, system: &str, context: &str) -> Result<String, String> {
        if !self.is_ready() {
            return Ok("JARVIS ready. Configure a model path in settings to enable AI.".into());
        }
        let backend = self.backend.as_ref().unwrap();
        let model = self.model.as_ref().unwrap();

        // Build prompt using Phi-3 Chat format
        // <|system|>\n...\n<|end|>\n<|user|>\n...\n<|end|>\n<|assistant|>
        let full_prompt = if context.is_empty() {
             format!("<|system|>\n{}<|end|>\n<|user|>\n{}<|end|>\n<|assistant|>", system, prompt)
        } else {
             format!("<|system|>\n{}<|end|>\n<|user|>\nI have already fetched this real-time data for you:\n---\n{}\n---\nUsing ONLY the above data, answer this: {}\nPlease present the data clearly. If tables are provided in the context, please retain them or present them in a similar structured format.<|end|>\n<|assistant|>", system, context, prompt)
        };

        // Tokenize
        let tokens = model.str_to_token(&full_prompt, AddBos::Always)
            .map_err(|e| format!("Tokenization failed: {:?}", e))?;

        // Create context
        let ctx_params = LlamaContextParams::default()
            .with_n_ctx(NonZeroU32::new(2048));
        let mut ctx = model.new_context(backend, ctx_params)
            .map_err(|e| format!("Context creation failed: {:?}", e))?;

        // Create batch and add tokens
        let mut batch = LlamaBatch::new(2048, 1);
        let last_idx = tokens.len() - 1;
        for (i, token) in tokens.iter().enumerate() {
            batch.add(*token, i as i32, &[0], i == last_idx)
                .map_err(|e| format!("Batch add failed: {:?}", e))?;
        }

        // Decode initial prompt
        ctx.decode(&mut batch)
            .map_err(|e| format!("Decode failed: {:?}", e))?;

        // Setup sampler
        // Setup sampler
        let mut sampler = LlamaSampler::chain_simple([
            LlamaSampler::temp(0.1),
            LlamaSampler::dist(1234),
        ]);

        // Generate tokens
        let mut response = String::new();
        let max_new_tokens = 512; // Increased to allow full tables
        let mut n_cur = tokens.len() as i32;
        let mut decoder = encoding_rs::UTF_8.new_decoder();
        
        let stop_sequences = ["<|end|>", "<|user|>", "<|system|>"];
        let mut new_tokens_count = 0;

        while new_tokens_count < max_new_tokens {
            let token = sampler.sample(&ctx, batch.n_tokens() - 1);
            sampler.accept(token);

            if model.is_eog_token(token) {
                break;
            }

            let output_bytes = model.token_to_bytes(token, Special::Tokenize)
                .map_err(|e| format!("Token decode failed: {:?}", e))?;
            let mut output_string = String::with_capacity(32);
            let _ = decoder.decode_to_string(&output_bytes, &mut output_string, false);
            response.push_str(&output_string);
            
            // Check for stop sequences
            let mut stopped = false;
            for stop in stop_sequences {
                if response.ends_with(stop) || response.contains(stop) {
                     response = response.replace(stop, "").trim().to_string();
                     stopped = true;
                     break;
                }
            }
            if stopped { break; }

            batch.clear();
            batch.add(token, n_cur, &[0], true)
                .map_err(|e| format!("Batch add failed: {:?}", e))?;
            ctx.decode(&mut batch)
                .map_err(|e| format!("Decode failed: {:?}", e))?;

            n_cur += 1;
            new_tokens_count += 1;
        }

        Ok(response.trim().to_string())
    }
}


fn get_system_prompt(state: &MemoryStore) -> String {
    state.get_preference("llm", "system_prompt")
        .ok()
        .flatten()
        .unwrap_or_else(|| "You are JARVIS, a helpful AI assistant.".to_string())
}

static LLM_ENGINE: Mutex<Option<LlmEngine>> = Mutex::new(None);

pub fn init_llm_engine(model_path: Option<PathBuf>) -> Result<(), String> {
    // Drop the global engine first to release the backend
    {
        let mut guard = LLM_ENGINE.lock().unwrap();
        *guard = None;
    }
     
    let mut engine = LlmEngine::new();
    if let Some(path) = model_path {
        engine.init(path)?;
    }
    *LLM_ENGINE.lock().unwrap() = Some(engine);
    Ok(())
}

#[tauri::command]
pub async fn chat(message: String, state: tauri::State<'_, MemoryStore>) -> Result<ChatResponse, String> {
    let memories = state.search_memories(&message, 5).map_err(|e| e.to_string())?;
    let context = state.get_context_summary().map_err(|e| e.to_string())?;
    
    let system_prompt = get_system_prompt(&state);
    
    let response = LLM_ENGINE.lock().unwrap().as_ref()
        .map(|e| e.generate(&message, &system_prompt, &context).unwrap_or_default())
        .unwrap_or_else(|| "Engine not initialized".into());

    Ok(ChatResponse { message: response, memory_context_used: !context.is_empty(), memories_retrieved: memories.len() })
}

#[tauri::command]
pub fn start_chat_stream(message: String, state: tauri::State<'_, MemoryStore>, app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Emitter;
    use tauri::Manager; // Import Manager trait for app.state()

    log::info!("start_chat_stream called with message: {}", message);

    let memories = state.search_memories(&message, 5).map_err(|e| e.to_string())?;
    
    // Retrieve context from memory store (UserProfile + Preferences)
    let base_context = state.get_context_summary().unwrap_or_default();

    let _ = app.emit("chat:thought", ThoughtLog { 
        step: "Search".into(), 
        detail: format!("{} memories", memories.len()), 
        timestamp: chrono::Utc::now().timestamp() 
    });
    
    let system_prompt = get_system_prompt(&state);
    let system_prompt = get_system_prompt(&state);
    
    // Improved Intent Detection
    let m_lower = message.to_lowercase();
    let direct_keywords = ["train", "metro", "rail", "subway", "wmata"];
    let routing_keywords = ["route", "trip", "get to", "go to", "travel to", "how do i get"];
    
    let mut contains_train = direct_keywords.iter().any(|k| m_lower.contains(k));
    
    // If not explicit, check for routing keywords + station name
    if !contains_train && routing_keywords.iter().any(|k| m_lower.contains(k)) {
        // Quick check against common station names to avoid false positives (e.g. "get to work")
        // We reuse the list from below or just do a quick check.
        // For efficiency, we'll let the thread handle the full check, but here we can be optimistic
        // if we see a routing keyword. Or better: define the list once constant or share it.
        // For now, let's assume if they ask "how do i get to...", it's likely transit if we are in this context.
        // But to be safe, let's just enable it and let the thread decide if it finds a station.
        contains_train = true; 
    }

    // Extract all data we need before spawning thread
    let api_key = if contains_train {
        let key = state.get_preference("transport", "wmata_api_key").ok().flatten();
        if key.is_none() {
            log::warn!("WMATA API Key not found in preferences");
        } else {
            log::info!("WMATA API Key found");
        }
        key
    } else {
        None
    };

    let user_lat = state.get_preference("system", "latitude").ok().flatten()
        .and_then(|l| l.parse::<f64>().ok());
    let user_lon = state.get_preference("system", "longitude").ok().flatten()
        .and_then(|l| l.parse::<f64>().ok());
    
    if contains_train && (user_lat.is_none() || user_lon.is_none()) {
        log::warn!("User location not found, defaulting to Metro Center");
    }

    let app_for_thread = app.clone();

    std::thread::spawn(move || {
        let mut context_addon = String::new();
        
        // Smart Transit Logic (moved into thread)
        if contains_train {
            log::info!("Transit intent detected in thread");
            let _ = app_for_thread.emit("chat:thought", ThoughtLog { 
                step: "Tool".into(), 
                detail: "Analyzing Transit Request...".into(), 
                timestamp: chrono::Utc::now().timestamp() 
            });

            if let Some(key) = api_key {
                let gtfs_state = app_for_thread.state::<crate::gtfs::GtfsState>();
                
                // Identify mentions
                let mut identified_stations = Vec::new();
                let possible_names = ["Silver Spring", "Metro Center", "Union Station", "Bethesda", "Rockville", "Shady Grove", "Glenmont", "Wheaton", "Forest Glen", "Takoma", "Fort Totten", "Brookland", "Rhode Island", "NoMa", "Gallery Place", "Judiciary Square", "Archives", "L'Enfant", "Smithsonian", "Federal Triangle", "Farragut", "Dupont", "Woodley", "Cleveland", "Van Ness", "Tenleytown", "Friendship", "Rosslyn", "Courthouse", "Clarendon", "Virginia Square", "Ballston", "East Falls Church", "West Falls Church", "Dunn Loring", "Vienna", "Arlington", "Pentagon", "Crystal City", "National Airport", "Braddock", "King St", "Eisenhower", "Huntington", "Capitol South", "Eastern Market", "Potomac Ave", "Stadium-Armory", "Benning", "Capitol Heights", "Addison", "Morgan", "Largo", "Navy Yard", "Anacostia", "Congress Heights", "Southern Ave", "Naylor", "Suitland", "Branch Ave", "Waterfront", "Columbia Heights", "Georgia Ave", "Petworth"];
                
                let message_lower = message.to_lowercase();
                
                 // Find all mentions (preserving order for "from X to Y")
                for name in possible_names.iter() {
                     let name_lower = name.to_lowercase();
                     if let Some(idx) = message_lower.find(&name_lower) {
                          if let Ok(Some(stop)) = gtfs_state.0.find_stop_by_name(name) {
                               identified_stations.push((idx, stop));
                               log::info!("Found station mention: {}", name);
                          }
                     }
                }
                identified_stations.sort_by_key(|k| k.0); // Sort by position in message
                let stations: Vec<_> = identified_stations.into_iter().map(|(_, s)| s).collect();

                // Determine Intent
                let is_trip_plan = message_lower.contains("route") || message_lower.contains("trip") || message_lower.contains("get to") || message_lower.contains("go to") || message_lower.contains("travel to");
                
                let (origin, dest) = if is_trip_plan {
                    if stations.len() >= 2 {
                        // "From X to Y"
                         (Some(stations[0].clone()), Some(stations[1].clone()))
                    } else if stations.len() == 1 {
                        // "To Y" (Origin = Location)
                         (None, Some(stations[0].clone()))
                    } else {
                        (None, None)
                    }
                } else {
                    // "Next train at X"
                    if let Some(s) = stations.first() {
                        (Some(s.clone()), None)
                    } else {
                        (None, None)
                    }
                };
                
                // Resolve Origin if missing (Current Location)
                let final_origin = if let Some(o) = origin {
                    Some(o)
                } else {
                    if let (Some(lat), Some(lon)) = (user_lat, user_lon) {
                        gtfs_state.0.find_closest_stop(lat, lon).ok().flatten()
                    } else {
                        None
                    }
                };

                let rt = tokio::runtime::Runtime::new().unwrap();
                let output = rt.block_on(async {
                    let mut out = String::new();
                    
                    // 1. Trip Plan Info (if Dest exists)
                    if let (Some(org), Some(dst)) = (&final_origin, &dest) {
                        let _ = app_for_thread.emit("chat:thought", ThoughtLog { 
                            step: "Tool".into(), 
                            detail: format!("Planning trip: {} -> {}", org.name, dst.name), 
                            timestamp: chrono::Utc::now().timestamp() 
                        });
                        
                        let org_code = org.id.replace("STN_", "");
                        let dst_code = dst.id.replace("STN_", "");
                        
                        match crate::external::get_route_info(&org_code, &dst_code, &key).await {
                            Ok(info) => {
                                // Construct Rich UI Data
                                let mut legs = Vec::new();
                                
                                // Mock Transfer/Walk to station (optional context)
                                // legs.push(crate::external::TransitLeg {
                                //    mode: "Transfer".to_string(),
                                //    description: Some("Walk to platform".to_string()),
                                //    duration: 2,
                                //    icon: Some("WALK".to_string()),
                                //    ..Default values..
                                // });

                                // Main Metro Leg
                                // We don't have the exact line from `get_route_info` (it just gives time/cost).
                                // But we can guess it or leave it generic.
                                // Let's try to get line from predictions below or just use a default color.
                                
                                legs.push(crate::external::TransitLeg {
                                    mode: "Metro".to_string(),
                                    line_name: Some("Metro Rail".to_string()), // Could be specific if we knew (e.g. "Red Line")
                                    stop_start: Some(org.name.clone()),
                                    stop_end: Some(dst.name.clone()),
                                    duration: info.travel_time_minutes as i64,
                                    color: Some("#00f3ff".to_string()), // Default Cyan
                                    description: None,
                                    icon: None,
                                });

                                let route_data = crate::external::TransitRoute {
                                    origin: org.name.clone(),
                                    destination: dst.name.clone(),
                                    departure_time: "Now".to_string(), // We don't have exact next train time in this block yet
                                    arrival_time: format!("+{} min", info.travel_time_minutes),
                                    duration_minutes: info.travel_time_minutes as i64,
                                    fare: format!("${:.2}", info.fare.peak),
                                    legs,
                                };

                                let _ = app_for_thread.emit("chat:transit", route_data);

                                out.push_str(&format!("\n### Trip Plan: {} → {}\n", org.name, dst.name));
                                out.push_str("| Metric | Value |\n|---|---|\n");
                                out.push_str(&format!("| **Travel Time** | {} min |\n", info.travel_time_minutes));
                                out.push_str(&format!("| **Distance** | {:.1} miles |\n", info.miles));
                                out.push_str(&format!("| **Peak Fare** | ${:.2} |\n", info.fare.peak));
                                out.push_str(&format!("| **Off-Peak Fare** | ${:.2} |\n", info.fare.off_peak));
                                out.push_str("\n");
                            },
                            Err(e) => out.push_str(&format!("> [!WARNING]\n> Could not fetch route info: {}\n", e)),
                        }
                    }

                    // 2. Real-time Departures at Origin
                    if let Some(org) = &final_origin {
                        let org_code = org.id.replace("STN_", "");
                         let _ = app_for_thread.emit("chat:thought", ThoughtLog { 
                            step: "Tool".into(), 
                            detail: format!("Checking trains at {}", org.name), 
                            timestamp: chrono::Utc::now().timestamp() 
                        });
                        
                        let url = format!("https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{}", org_code);
                        let client = reqwest::Client::new();
                        match client.get(&url).header("api_key", &key).send().await {
                             Ok(resp) => {
                                 if let Ok(json) = resp.json::<serde_json::Value>().await {
                                     if let Some(trains_arr) = json["Trains"].as_array() {
                                         if trains_arr.is_empty() {
                                             out.push_str(&format!("\n> No trains currently scheduled at **{}**.\n", org.name));
                                         } else {
                                             out.push_str(&format!("\n### Real-time Departures at {}\n", org.name));
                                             out.push_str("| Line | Dest | Min | Cars |\n|---|---|---|---|\n");
                                             for t in trains_arr.iter().take(6) { // Show top 6
                                                 let line = t["Line"].as_str().unwrap_or("??");
                                                 let dest_name = t["Destination"].as_str().unwrap_or("Unknown");
                                                 let min = t["Min"].as_str().unwrap_or("?");
                                                 let car = t["Car"].as_str().unwrap_or("-");
                                                 
                                                 out.push_str(&format!("| **{}** | {} | {} | {} |\n", line, dest_name, min, car));
                                             }
                                             out.push_str("\n");
                                         }
                                     } 
                                 }
                             },
                             Err(e) => out.push_str(&format!("\n> [!ERROR]\n> Failed to fetch predictions: {}\n", e)),
                        }
                    } else {
                        out.push_str("\n> [!NOTE]\n> Could not determine origin station. Please specify a station name (e.g., 'From Metro Center') or ensure location services are active.\n");
                    }
                    
                    out
                });
                
                context_addon.push_str(&output);

            } else {
                context_addon.push_str("\n[System Alert] WMATA API key not configured. I cannot fetch real-time train data. Please add your WMATA API key in settings.\n");
            }
        }

        let full_context = format!("{}\n{}", base_context, context_addon);
        log::info!("Final Context for LLM:\n{}", full_context);

        let response = {
             let guard = LLM_ENGINE.lock().unwrap();
             if let Some(engine) = guard.as_ref() {
                 match engine.generate(&message, &system_prompt, &full_context) {
                     Ok(r) => r,
                     Err(e) => {
                         log::error!("LLM Generation failed: {}", e);
                         format!("I encountered an error generating a response: {}", e)
                     }
                 }
             } else {
                 "LLM Engine not initialized".to_string()
             }
        };

        log::info!("LLM Raw Response: '{}'", response);

        for word in response.split_whitespace() {
            log::debug!("Emitting token: {}", word);
            let _ = app_for_thread.emit("chat:token", format!("{} ", word));
            std::thread::sleep(std::time::Duration::from_millis(30));
        }
        log::info!("Finished emitting tokens. Sending complete signal.");
        let _ = app_for_thread.emit("chat:complete", true);
    });
    Ok(())
}

#[tauri::command]
pub fn detect_intent(message: String) -> Result<Vec<String>, String> {
    let m = message.to_lowercase();
    let mut i = vec![];
    if m.contains("weather") { i.push("get_weather".into()); }
    if m.contains("train") { i.push("get_train_times".into()); }
    if m.contains("flight") { i.push("get_flights".into()); }
    Ok(i)
}

#[tauri::command]
pub fn set_model_path(path: String, state: tauri::State<MemoryStore>) -> Result<(), String> {
    state.set_preference("llm", "model_path", &path).map_err(|e| e.to_string())?;
    init_llm_engine(Some(PathBuf::from(path)))
}
