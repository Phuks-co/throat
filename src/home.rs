use rocket::fairing::{AdHoc};
use rocket::{request, Request};
use rocket::outcome::Outcome::Success;
use rocket::request::FromRequest;
use rocket::serde::{Serialize, Deserialize};

use rocket_db_pools::{Connection};
use rocket_dyn_templates::{context, Template};
use sqlx::types::chrono::{DateTime, TimeZone, Utc};
use crate::db::Db;
use crate::jinja::RequestVars;
use crate::session::CurrentUser;


#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct Post {
    #[serde(skip_deserializing, skip_serializing_if = "Option::is_none")]
    pid: Option<i64>,
    ptype: Option<i64>,
    title: String,
    flair: Option<String>,
    link: Option<String>,
    content: Option<String>,
    thumbnail: Option<String>,
    score: i64,
    comments: i64,
    nsfw: Option<bool>,
    pub posted: DateTime<Utc>,
    posted_days_ago: i64,  // convenience
    userstatus: i64,
    user: String,
    uid: String,
    sub: String,
    distinguish: Option<i32>,
    user_flair: Option<String>,
}

// Data to be shown at the home sidebar, etc.
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct HomeData {
    sub_of_the_day: String,
    top_posts: Vec<String>,
    recent_activity: Vec<String>
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for HomeData {
    type Error = std::convert::Infallible;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<HomeData, Self::Error> {
        let mut db = request.guard::<Connection<Db>>().await.expect("db");
        // let default_subs = sqlx::query!("SELECT sub.name FROM site_metadata INNER JOIN sub ON sub.sid = site_metadata.value WHERE key='default'")
        //     .fetch_all(&mut **db).await.unwrap().into_iter().map(|x| x.name).collect(); // TODO: Cache?

        Success(HomeData {
            sub_of_the_day: "".into(),
            top_posts: vec![],
            recent_activity: vec![]
        })
    }
}


#[get("/")]
async fn home<'r>(mut db: Connection<Db>, current_user: CurrentUser, rv: RequestVars) -> Template {
    let posts: Vec<Post> = sqlx::query!("
        SELECT
            post.pid,
            post.ptype,
            post.title,
            post.flair,
            post.link,
            post.thumbnail,
            post.content,
            post.posted,
            post.score,
            post.comments,
            post.nsfw,
            post.uid,
            post.distinguish,
            u.status userstatus,
            u.name \"user\",
            sub.name \"sub\",
            sub_user_flair.flair \"user_flair?\"
        FROM sub_post AS post
        LEFT OUTER JOIN \"user\" u ON u.uid = post.uid
        LEFT OUTER JOIN sub on sub.sid = post.sid
        LEFT OUTER JOIN sub_user_flair ON sub_user_flair.sid = post.sid AND sub_user_flair.uid = post.uid
        WHERE
            post.deleted = 0 AND
            sub.status = 0 AND
            sub.sid IN (SELECT value FROM site_metadata WHERE key='default')
        ORDER BY HOT(post.score, EXTRACT(EPOCH FROM post.posted)) DESC
        LIMIT 25
        ")
        .fetch_all(&mut **db).await.unwrap().into_iter()
        .map(|r| Post {
            pid: Some(r.pid),
            ptype: r.ptype,
            title: r.title,
            flair: r.flair,
            link: r.link,
            content: r.content,
            thumbnail: r.thumbnail,
            score: r.score,
            comments: r.comments,
            nsfw: r.nsfw,
            posted: Utc.from_utc_datetime(&r.posted),
            posted_days_ago: (Utc::now() - Utc.from_utc_datetime(&r.posted)).num_days(),
            userstatus: r.userstatus,
            user: r.user.expect("Haunted!"),
            uid: r.uid,
            sub: r.sub,
            distinguish: r.distinguish,
            user_flair: r.user_flair,
        }).collect();

    Template::render(
        "index",
        context! {
            title: "Hello",
            sort: "hot",
            page_name: "home",
            page: 0,
            posts: posts,
            current_user: current_user,
            request: rv
        },
    )
}

pub fn stage() -> AdHoc {
    AdHoc::on_ignite("SQLx Stage", |rocket| async {
            rocket.mount("/", routes![home])
    })
}