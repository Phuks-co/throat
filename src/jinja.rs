use std::collections::HashMap;
use std::fs::File;
use std::io::Read;
use std::string::ToString;
use std::sync::{LazyLock, Mutex};
use rocket::{request, Request};
use rocket::outcome::Outcome::Success;
use rocket::request::FromRequest;
use rocket::serde::{Deserialize, Serialize};
use rocket_db_pools::Connection;
use rocket_dyn_templates::minijinja::{Environment, Value};
use rocket_dyn_templates::minijinja::value::{Kwargs};
use url::Url;
use crate::config::Config as AppConfig;
use crate::db::Db;
use crate::session::CurrentUser;

static STATIC_ASSETS: LazyLock<Mutex<HashMap<String, String>>> = LazyLock::new(|| Mutex::new(HashMap::new()));

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct RequestVars {
    current_user: CurrentUser,
    theme_mode: String,
    subscriptions: Vec<String>
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for RequestVars {
    type Error = std::convert::Infallible;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<RequestVars, Self::Error> {
        let cookiejar = request.cookies();
        let current_user = CurrentUser::from_request(request).await.expect("wow so broken");

        let mut db = request.guard::<Connection<Db>>().await.expect("db");
        let default_subs = sqlx::query!("SELECT sub.name FROM site_metadata INNER JOIN sub ON sub.sid = site_metadata.value WHERE key='default'")
            .fetch_all(&mut **db).await.unwrap().into_iter().map(|x| x.name).collect(); // TODO: Cache?

        Success(RequestVars {
            current_user,
            theme_mode: cookiejar.get("dayNight")
                .and_then(|cookie| cookie.value().parse::<String>().ok())
                .unwrap_or("day".to_string()),
            subscriptions: default_subs,  // todo: when user's logged in load subs
        })
    }
}

fn asset_url_for(asset_name: String) -> Value {
    // TODO: Read statics dir from manifest
    Value::from_safe_string(format!("/static/gen/{}", STATIC_ASSETS.lock().unwrap().get(&asset_name).unwrap().clone()))
}

fn get_domain(url: String) -> String {
    Url::parse(&url).unwrap().host_str().unwrap().to_string()
}

// TODO: Implement gettext!
fn dummy_i18n(text: String) -> String { text }
fn dummy_i18n_parm(text: String, ctx: Kwargs) -> Value {
    // Not the most optimal solution, should prolly make a better parser
    let mut env = Environment::new();
    env.add_template("hello", text.as_str()).unwrap();
    let tmpl = env.get_template("hello").unwrap();
    Value::from_safe_string(tmpl.render(Value::from(ctx)).unwrap())
}

pub fn customize(env: &mut Environment, cfg: AppConfig) {
    // TODO: This may or may not be called on all request, we should offload all the file reading to
    // another place!

    // Read json manifest
    let file = File::open("manifest.json").unwrap();
    let json: HashMap<String, serde_json::Value> = serde_json::from_reader(file)
        .expect("file should be proper JSON");
    // so much borrowing we gone bankrupt
    let assetlist: &serde_json::Map<String, serde_json::Value> = json.get(&"assets".to_string()).unwrap().as_object().unwrap();
    for (key, val) in assetlist {
        STATIC_ASSETS.lock().unwrap().insert(key.clone(), val.as_str().unwrap().to_string());
    }

    env.add_function("asset_url_for", asset_url_for);
    env.add_function("get_domain", get_domain);
    env.add_function("_", dummy_i18n);
    env.add_function("_p", dummy_i18n_parm);
    // Load logo
    let mut file = File::open(cfg.site_logo.clone()).unwrap();
    let logo_str = &mut "".to_string();
    file.read_to_string(logo_str).expect("Logo file");
    env.add_global("THROAT_LOGO", Value::from_safe_string(logo_str.clone()));

    env.add_global("config", Value::from_serialize(cfg));
}
