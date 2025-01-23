use rocket::outcome::Outcome::{Success};
use rocket::request::{self, Request, FromRequest};
use rocket::serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize, Clone)]
#[serde(crate = "rocket::serde")]
pub struct CurrentUser {
    pub logged_in: bool,
    pub uid: Option<String>,
    pub is_admin: bool,
    pub can_admin: bool,
    pub likes_scroll: bool,  // Todo: move to a prefs object
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for CurrentUser {
    type Error = std::convert::Infallible;

    async fn from_request(request: &'r Request<'_>) -> request::Outcome<CurrentUser, Self::Error> {
        let user_id = request.cookies()
            .get_private("user_id")
            .and_then(|cookie| cookie.value().parse::<String>().ok());

        Success(CurrentUser {
            logged_in: user_id.is_some(),
            uid: user_id, // todo validate
            is_admin: false,  // todo
            can_admin: false,  // todo
            likes_scroll: true,
        })
    }
}
