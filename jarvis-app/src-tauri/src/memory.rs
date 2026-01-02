//! SQLite-based memory store for user preferences and semantic memory
//!
//! This module handles:
//! - User profile storage
//! - Preference management
//! - Long-term memory/facts
//!
//! Note: For full vector similarity search (SQLite-VSS), additional setup is required.
//! This version provides keyword-based search as a foundation.

use rusqlite::{Connection, Result as SqlResult, params};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Mutex;

/// User profile information
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct UserProfile {
    pub name: Option<String>,
    pub facts: Vec<String>,
    pub created_at: Option<String>,
    pub updated_at: Option<String>,
}

/// A stored preference
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Preference {
    pub category: String,
    pub key: String,
    pub value: String,
    pub created_at: Option<String>,
}

/// A memory entry
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Memory {
    pub id: i64,
    pub content: String,
    pub category: String,
    pub importance: i32,
    pub created_at: Option<String>,
    pub last_accessed: Option<String>,
}

/// Memory store manager
pub struct MemoryStore {
    conn: Mutex<Connection>,
}

impl MemoryStore {
    /// Create a new memory store
    pub fn new(db_path: Option<PathBuf>) -> SqlResult<Self> {
        let path = db_path.unwrap_or_else(|| {
            let mut home = dirs::home_dir().expect("Could not find home directory");
            home.push(".jarvis");
            std::fs::create_dir_all(&home).ok();
            home.push("memory.db");
            home
        });

        let conn = Connection::open(&path)?;
        let store = Self { conn: Mutex::new(conn) };
        store.init_db()?;
        Ok(store)
    }

    /// Initialize database schema
    fn init_db(&self) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();

        conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                name TEXT,
                facts TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_accessed TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);

            -- Ensure we have a default profile row
            INSERT OR IGNORE INTO user_profile (id, name) VALUES (1, NULL);
            ",
        )?;

        Ok(())
    }

    /// Get the user profile
    pub fn get_user_profile(&self) -> SqlResult<UserProfile> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT name, facts, created_at, updated_at FROM user_profile WHERE id = 1"
        )?;

        let profile = stmt.query_row([], |row| {
            let facts_json: String = row.get(1)?;
            let facts: Vec<String> = serde_json::from_str(&facts_json).unwrap_or_default();

            Ok(UserProfile {
                name: row.get(0)?,
                facts,
                created_at: row.get(2)?,
                updated_at: row.get(3)?,
            })
        })?;

        Ok(profile)
    }

    /// Set the user's name
    pub fn set_user_name(&self, name: &str) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "UPDATE user_profile SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            params![name],
        )?;
        Ok(())
    }

    /// Add a fact about the user
    pub fn add_user_fact(&self, fact: &str) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();
        let mut profile = {
            let mut stmt = conn.prepare("SELECT facts FROM user_profile WHERE id = 1")?;
            let facts_json: String = stmt.query_row([], |row| row.get(0))?;
            serde_json::from_str::<Vec<String>>(&facts_json).unwrap_or_default()
        };

        if !profile.contains(&fact.to_string()) {
            profile.push(fact.to_string());
            let facts_json = serde_json::to_string(&profile).unwrap();
            conn.execute(
                "UPDATE user_profile SET facts = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
                params![facts_json],
            )?;
        }
        Ok(())
    }

    /// Set or update a preference
    pub fn set_preference(&self, category: &str, key: &str, value: &str) -> SqlResult<()> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO preferences (category, key, value) VALUES (?, ?, ?)
             ON CONFLICT(category, key) DO UPDATE SET value = excluded.value",
            params![category, key, value],
        )?;
        Ok(())
    }

    /// Get a specific preference
    pub fn get_preference(&self, category: &str, key: &str) -> SqlResult<Option<String>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT value FROM preferences WHERE category = ? AND key = ?"
        )?;

        match stmt.query_row(params![category, key], |row| row.get(0)) {
            Ok(value) => Ok(Some(value)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e),
        }
    }

    /// Get all preferences
    pub fn get_all_preferences(&self) -> SqlResult<Vec<Preference>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT category, key, value, created_at FROM preferences ORDER BY category, key"
        )?;

        let prefs = stmt.query_map([], |row| {
            Ok(Preference {
                category: row.get(0)?,
                key: row.get(1)?,
                value: row.get(2)?,
                created_at: row.get(3)?,
            })
        })?
        .filter_map(|r| r.ok())
        .collect();

        Ok(prefs)
    }

    /// Add a memory
    pub fn add_memory(&self, content: &str, category: &str, importance: i32) -> SqlResult<i64> {
        let conn = self.conn.lock().unwrap();
        conn.execute(
            "INSERT INTO memories (content, category, importance) VALUES (?, ?, ?)",
            params![content, category, importance],
        )?;
        Ok(conn.last_insert_rowid())
    }

    /// Search memories by keyword
    pub fn search_memories(&self, query: &str, limit: usize) -> SqlResult<Vec<Memory>> {
        let conn = self.conn.lock().unwrap();
        let search_pattern = format!("%{}%", query);
        let mut stmt = conn.prepare(
            "SELECT id, content, category, importance, created_at, last_accessed 
             FROM memories 
             WHERE content LIKE ?
             ORDER BY importance DESC, created_at DESC
             LIMIT ?"
        )?;

        let memories = stmt.query_map(params![search_pattern, limit as i64], |row| {
            Ok(Memory {
                id: row.get(0)?,
                content: row.get(1)?,
                category: row.get(2)?,
                importance: row.get(3)?,
                created_at: row.get(4)?,
                last_accessed: row.get(5)?,
            })
        })?
        .filter_map(|r| r.ok())
        .collect();

        Ok(memories)
    }

    /// Get recent memories
    pub fn get_recent_memories(&self, limit: usize) -> SqlResult<Vec<Memory>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare(
            "SELECT id, content, category, importance, created_at, last_accessed 
             FROM memories 
             ORDER BY created_at DESC
             LIMIT ?"
        )?;

        let memories = stmt.query_map(params![limit as i64], |row| {
            Ok(Memory {
                id: row.get(0)?,
                content: row.get(1)?,
                category: row.get(2)?,
                importance: row.get(3)?,
                created_at: row.get(4)?,
                last_accessed: row.get(5)?,
            })
        })?
        .filter_map(|r| r.ok())
        .collect();

        Ok(memories)
    }

    /// Get context summary for LLM system prompt
    pub fn get_context_summary(&self) -> SqlResult<String> {
        let profile = self.get_user_profile()?;
        let prefs = self.get_all_preferences()?;
        let memories = self.get_recent_memories(10)?;

        let mut summary = String::new();

        // User profile
        if let Some(name) = &profile.name {
            summary.push_str(&format!("User's name is {}.\n", name));
        }
        if !profile.facts.is_empty() {
            summary.push_str("User facts:\n");
            for fact in &profile.facts {
                summary.push_str(&format!("- {}\n", fact));
            }
        }

        // Preferences & System Context
        let mut system_prefs = Vec::new();
        let mut user_prefs = Vec::new();
        
        for pref in &prefs {
            if pref.category == "system" {
                system_prefs.push(pref);
            } else {
                user_prefs.push(pref);
            }
        }

        // Add explicit location context if available
        let city = system_prefs.iter().find(|p| p.key == "city").map(|p| p.value.as_str());
        let region = system_prefs.iter().find(|p| p.key == "region").map(|p| p.value.as_str());
        
        if let (Some(c), Some(r)) = (city, region) {
            summary.push_str(&format!("Current Location: {}, {}.\n", c, r));
        }

        if !user_prefs.is_empty() {
            summary.push_str("\nUser preferences:\n");
            for pref in user_prefs {
                summary.push_str(&format!("- {}/{}: {}\n", pref.category, pref.key, pref.value));
            }
        }

        // Key memories
        if !memories.is_empty() {
            summary.push_str("\nRelevant memories:\n");
            for mem in &memories {
                summary.push_str(&format!("- {}\n", mem.content));
            }
        }

        Ok(summary)
    }
}

// Tauri commands

#[tauri::command]
pub fn get_user_profile(state: tauri::State<MemoryStore>) -> Result<UserProfile, String> {
    state.get_user_profile().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn set_user_name(name: String, state: tauri::State<MemoryStore>) -> Result<(), String> {
    state.set_user_name(&name).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn add_user_fact(fact: String, state: tauri::State<MemoryStore>) -> Result<(), String> {
    state.add_user_fact(&fact).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn set_preference(
    category: String,
    key: String,
    value: String,
    state: tauri::State<MemoryStore>,
) -> Result<(), String> {
    state.set_preference(&category, &key, &value).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_all_preferences(state: tauri::State<MemoryStore>) -> Result<Vec<Preference>, String> {
    state.get_all_preferences().map_err(|e| e.to_string())
}

#[tauri::command]
pub fn add_memory(
    content: String,
    category: String,
    importance: i32,
    state: tauri::State<MemoryStore>,
) -> Result<i64, String> {
    state.add_memory(&content, &category, importance).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn search_memories(
    query: String,
    limit: usize,
    state: tauri::State<MemoryStore>,
) -> Result<Vec<Memory>, String> {
    state.search_memories(&query, limit).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_memory_context(state: tauri::State<MemoryStore>) -> Result<String, String> {
    state.get_context_summary().map_err(|e| e.to_string())
}
