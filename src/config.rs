use std::collections::HashMap;
use rocket::serde::{Serialize, Deserialize};

#[derive(Deserialize, Serialize)]
#[serde(crate = "rocket::serde")]
pub struct Config {
    site_lema: String,
    site_enable_totp: bool,
    site_front_page_submit: bool,
    site_copyright: String,
    site_notifications_on_icon: bool,
    pub site_logo: String,
    pub site_default_subs: Vec<String>,
    pub site_footer_links: HashMap<String, String>,
    site_thumbnail_host: String,
    site_expando_sites: Vec<String>,

    auth_provider: String,  // TODO: Enum
}

impl Default for Config {
    fn default() -> Config {
        Config {
            site_lema: "Throat: Open discussion ;D".into(),
            site_enable_totp: false,
            site_front_page_submit: true,
            site_copyright: "Umbrella Corp".to_string(),
            site_notifications_on_icon: true,
            site_logo: "app/static/img/throat-logo.svg".to_string(),
            site_default_subs: vec![],
            site_footer_links: [
                ("ToS".to_string(), "/wiki/tos".to_string()),
                ("Privacy".to_string(), "/wiki/privacy".to_string())
            ].into(),
            site_thumbnail_host: "/static".to_string(),
            site_expando_sites: vec![
                "hooktube.com".into(),
                "www.hooktube.com".into(),
                "youtube.com".into(),
                "www.youtube.com".into(),
                "youtu.be".into(),
                "gfycat.com".into(),
                "streamja.com".into(),
                "streamable.com".into(),
                "vimeo.com".into(),
                "vine.co".into(),
                "instaud.io".into(),
                "player.vimeo.com".into(),
            ],

            auth_provider: "".into(),
        }
    }
}
