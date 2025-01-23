#[macro_use] extern crate rocket;
use dotenv::dotenv;
use rocket::fairing::AdHoc;
use rocket::figment::{Figment, Profile};
use rocket::figment::providers::{Env, Format, Serialized, Toml};
use rocket::fs::FileServer;
use rocket_db_pools::Database;
use rocket_dyn_templates::Template;
use crate::config::Config;
use crate::db::{run_migrations, Db, Redis};
use crate::perf::{init_perf};

mod home;
mod db;
mod jinja;
mod session;
mod perf;
mod config;

#[launch]
fn rocket() -> _ {
    dotenv().ok();

    let figment = Figment::from(rocket::Config::default())
        .merge(Serialized::defaults(Config::default()))
        .merge(Toml::file("App.toml").nested())
        .merge(Env::prefixed("THROAT_").global())
        .select(Profile::from_env_or("APP_PROFILE", "default"));

    rocket::custom(&figment)
        .attach(init_perf())
        .attach(AdHoc::config::<Config>())
        .attach(Db::init())
        .attach(Redis::init())
        .attach(AdHoc::try_on_ignite("SQLx Migrations", run_migrations))
        .attach(Template::custom(move |engines| {
            jinja::customize(&mut engines.minijinja, figment.extract().expect("couldn't fudge the hodge"));
        }))
        .mount("/static", FileServer::from("app/static"))
        .attach(home::stage())
}