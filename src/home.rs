use chrono::TimeDelta;
use rocket::fairing::{AdHoc};
use rocket::{request, Request, State};
use rocket::futures::{TryFutureExt};
use rocket::outcome::Outcome::Success;
use rocket::request::FromRequest;
use rocket::serde::{Serialize, Deserialize};

use rocket_db_pools::{Connection};
use rocket_db_pools::deadpool_redis::redis::{AsyncCommands};
use rocket_dyn_templates::{context, Template};
use sqlx::types::chrono::{DateTime, TimeZone, Utc};
use crate::config::Config;
use crate::db::{Db, Redis};
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

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct HomeSubOfTheDay {
    pub sid: String,
    name: String,
    title: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct HomePostComment {
    obj_type: String, // "post" or "comment" todo: make enum?
    sub: String,
    title: Option<String>,
    user_name: String,
    posted: DateTime<Utc>,
    score: i64,
    nsfw: Option<bool>,
    sub_nsfw: bool,
}

// Data to be shown at the home sidebar, etc.
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct HomeData {
    sub_of_the_day: HomeSubOfTheDay,
    top_posts: Vec<HomePostComment>,
    recent_activity: Vec<HomePostComment>
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for HomeData {
    type Error = std::convert::Infallible;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<HomeData, Self::Error> {
        let mut db = request.guard::<Connection<Db>>().await.expect("db");
        let mut redis = request.guard::<Connection<Redis>>().await.expect("redis");
        let config = request.guard::<&State<Config>>().await.expect("config");

        // Sub of the day
        let daysub_r: Option<String> = redis.get("daysub").await.unwrap();
        let sub_of_the_day: HomeSubOfTheDay;
        if daysub_r.is_none() {
            sub_of_the_day = sqlx::query!("SELECT sid, name, title FROM sub ORDER BY RANDOM() LIMIT 1")
                .fetch_one(&mut **db)
                .map_ok(|r| HomeSubOfTheDay { sid: r.sid, name: r.name, title: r.title }).await.ok().expect("sub not found?");
            // TODO: make expiration the time to midnight
            let _: () = redis.set_ex("daysub", sub_of_the_day.sid.as_str(), 86400).await.expect("redis exploded");
        } else {
            sub_of_the_day = sqlx::query!("SELECT sid, name, title FROM sub WHERE sid = $1", daysub_r.unwrap())
                .fetch_one(&mut **db)
                .map_ok(|r| HomeSubOfTheDay { sid: r.sid, name: r.name, title: r.title }).await.ok().expect("sub not found?");
        }

        // Today's top posts
        let today_td = Utc::now() - TimeDelta::days(1);
        let day_top_posts: Vec<HomePostComment> = sqlx::query!("
            SELECT
                sub_post.title,
                sub_post.score,
                sub_post.nsfw,
                sub_post.posted,
                sub.name \"sub\",
                sub.nsfw \"sub_nsfw\",
                u.name \"user_name!\"
            FROM sub_post
            INNER JOIN sub ON sub.sid = sub_post.sid
            INNER JOIN \"user\" AS u ON u.uid = sub_post.uid
            WHERE sub_post.posted > $1 AND sub_post.nsfw = FALSE AND sub_post.deleted = 0
            ORDER BY score DESC
            LIMIT 5
        ", today_td.naive_utc()).fetch_all(&mut **db).await.unwrap().into_iter()  // todo: allow nsfw if in user prefs
            .map(|r| HomePostComment {
                obj_type: "post".to_string(),
                sub: r.sub,
                title: Some(r.title),
                user_name: r.user_name,
                score: r.score,
                posted: Utc.from_utc_datetime(&r.posted),
                nsfw: r.nsfw,
                sub_nsfw: r.sub_nsfw,
            }).collect();

        // recent activity tab
        let mut recent_activity_posts: Vec<HomePostComment> = vec![];
        if config.site_recent_activity_enabled {
            println!("got in!");
            recent_activity_posts.extend(sqlx::query!("
                SELECT
                    obj_type \"obj_type!\",
                    title \"title!\",
                    score \"score!\",
                    nsfw,
                    posted \"posted!\",
                    sub \"sub!\",
                    sub_nsfw \"sub_nsfw!\",
                    user_name \"user_name!\"
                FROM ((
                    SELECT
                        'post' \"obj_type\",
                        sub_post.title,
                        sub_post.score,
                        sub_post.nsfw,
                        sub_post.posted,
                        sub.name \"sub\",
                        sub.nsfw \"sub_nsfw\",
                        u.name \"user_name\"
                    FROM sub_post
                    INNER JOIN sub ON sub.sid = sub_post.sid
                    INNER JOIN \"user\" AS u ON u.uid = sub_post.uid
                    WHERE sub_post.nsfw = FALSE AND sub_post.deleted = 0
                    ORDER BY sub_post.pid DESC
                    LIMIT 50
                )
                UNION (
                    SELECT
                        'comment' \"obj_type\",
                        sub_post_comment.content \"title\",
                        sub_post_comment.score,
                        sub_post.nsfw,
                        sub_post_comment.time \"posted\",
                        sub.name \"sub\",
                        sub.nsfw \"sub_nsfw\",
                        u.name \"user_name\"
                    FROM sub_post_comment
                    INNER JOIN sub_post ON sub_post.pid = sub_post_comment.pid
                    INNER JOIN sub ON sub.sid = sub_post.sid
                    INNER JOIN \"user\" AS u ON u.uid = sub_post_comment.uid
                    WHERE sub_post_comment.status IS NULL AND sub_post.nsfw = FALSE
                    ORDER BY sub_post_comment.time DESC
                    LIMIT 50
                )) ORDER BY \"posted\" DESC
            ").fetch_all(&mut **db).await.unwrap().into_iter()  // todo: allow nsfw if in user prefs
                    .map(|r| HomePostComment {
                        obj_type: r.obj_type,
                        sub: r.sub,
                        title: Some(r.title),
                        user_name: r.user_name,
                        score: r.score,
                        posted: Utc.from_utc_datetime(&r.posted),
                        nsfw: r.nsfw,
                        sub_nsfw: r.sub_nsfw,
                    }).collect::<Vec<_>>());
        }


        Success(HomeData {
            sub_of_the_day,
            top_posts: day_top_posts,
            recent_activity: recent_activity_posts
        })
    }
}


#[get("/")]
async fn home<'r>(mut db: Connection<Db>, current_user: CurrentUser, rv: RequestVars, home_data: HomeData) -> Template {
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
            request: rv,
            home_data
        },
    )
}

pub fn stage() -> AdHoc {
    AdHoc::on_ignite("SQLx Stage", |rocket| async {
            rocket.mount("/", routes![home])
    })
}