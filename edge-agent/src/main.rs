use std::collections::HashMap;
use std::env;
use std::sync::Arc;
use std::time::Duration;

use axum::{
    extract::State,
    response::IntoResponse,
    routing::get,
    Json, Router,
};
use reqwest;
use serde::Deserialize;
use serde_json;
use tokio::sync::RwLock;
use tracing::{error, info};

#[derive(Debug, Deserialize, Clone)]
struct TagsResponse {
    asset: String,
    readings: Vec<TagReading>,
}

#[derive(Debug, Deserialize, Clone, serde::Serialize)]
struct TagReading {
    tag_id: String,
    value: f64,
    unit: String,
    timestamp: String,
}

type Store = Arc<RwLock<HashMap<String, Vec<TagReading>>>>;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let simulator_url = env::var("SIMULATOR_URL")
        .unwrap_or_else(|_| "http://localhost:8001".to_string());
    let signal_api_url = env::var("SIGNAL_API_URL")
        .unwrap_or_else(|_| "http://localhost:8003".to_string());

    info!(
        event = "edge_agent_startup",
        simulator_url = %simulator_url,
        signal_api_url = %signal_api_url,
        version = env!("CARGO_PKG_VERSION"),
        "AURA Edge Agent starting"
    );

    let store: Store = Arc::new(RwLock::new(HashMap::new()));
    let store_clone = store.clone();

    let poll_handle = tokio::spawn(async move {
        let client = reqwest::Client::new();
        let poll_url = format!("{}/tags", simulator_url);
        let ingest_url = format!("{}/ingest", signal_api_url);

        loop {
            match client.get(&poll_url).send().await {
                Ok(resp) => match resp.json::<TagsResponse>().await {
                    Ok(data) => {
                        // Store in ring buffer
                        let mut map = store_clone.write().await;
                        for reading in &data.readings {
                            let entry = map.entry(reading.tag_id.clone()).or_default();
                            entry.push(reading.clone());
                            if entry.len() > 1000 {
                                entry.remove(0);
                            }
                        }
                        let total: usize = map.values().map(|v| v.len()).sum();

                        // Forward to signal-api
                        let forward_body = serde_json::json!({
                            "asset": &data.asset,
                            "readings": &data.readings
                        });
                        match client.post(&ingest_url).json(&forward_body).send().await {
                            Ok(_) => {
                                info!(event = "poll_success", tags_ingested = total, asset = %data.asset, forwarded = true);
                            }
                            Err(e) => {
                                info!(event = "poll_success", tags_ingested = total, asset = %data.asset, forwarded = false, forward_error = %e);
                            }
                        }
                    }
                    Err(e) => {
                        error!(event = "deserialize_failed", error = %e);
                    }
                },
                Err(e) => {
                    error!(event = "poll_failed", error = %e);
                }
            }
            tokio::time::sleep(Duration::from_secs(1)).await;
        }
    });

    let app = Router::new()
        .route("/health", get(health))
        .with_state(store.clone());

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8002").await?;
    info!(event = "health_endpoint_ready", port = 8002);

    let server_handle = tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });

    tokio::try_join!(poll_handle, server_handle)?;

    Ok(())
}

async fn health(State(state): State<Store>) -> impl IntoResponse {
    let map = state.read().await;
    let total: usize = map.values().map(|v| v.len()).sum();
    Json(serde_json::json!({
        "status": "up",
        "tags_ingested": total
    }))
}