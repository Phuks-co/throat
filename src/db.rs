use rocket::{fairing, Build, Rocket};
use rocket_db_pools::{Database, sqlx, deadpool_redis};

#[derive(Database)]
#[database("throat")]
pub struct Db(sqlx::PgPool);

#[derive(Database)]
#[database("redis")]
pub struct Redis(deadpool_redis::Pool);


pub async fn run_migrations(rocket: Rocket<Build>) -> fairing::Result {
    match Db::fetch(&rocket) {
        Some(db) => match sqlx::migrate!().run(&**db).await {
            Ok(_) => Ok(rocket),
            Err(e) => {
                error!("Failed to initialize SQLx database: {}", e);
                Err(rocket)
            }
        }
        None => Err(rocket),
    }
}