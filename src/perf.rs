use std::io::Cursor;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};
use rocket::{Request, Data, Response};
use rocket::fairing::{Fairing, Info, Kind};

pub struct Perf {
    tscache: AtomicU64 // TODO: Query counter
}

fn curr_time_millis() -> u64 {
    let start = SystemTime::now();
    let since_the_epoch = start
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards");

    since_the_epoch.as_secs() * 1000 +
        since_the_epoch.subsec_nanos() as u64 / 1_000_000
}


#[rocket::async_trait]
impl Fairing for Perf {
    // This is a request and response fairing named "GET/POST Counter".
    fn info(&self) -> Info {
        Info {
            name: "Performance measurer >:D",
            kind: Kind::Request | Kind::Response
        }
    }

    // Increment the counter for `GET` and `POST` requests.
    async fn on_request(&self, _request: &mut Request<'_>, _: &mut Data<'_>) {
        self.tscache.store(curr_time_millis(), Ordering::Relaxed);
    }

    async fn on_response<'r>(&self, _request: &'r Request<'_>, response: &mut Response<'r>) {
        let rbody = response.body_mut();
        if rbody.preset_size().is_some() {
            let tsi = curr_time_millis() - self.tscache.load(Ordering::Relaxed);
            let bcont = rbody.to_string().await.unwrap().replace("__EXECUTION_TIME__", tsi.to_string().as_str());
            response.set_sized_body(bcont.len(), Cursor::new(bcont));
        }
    }
}

pub fn init_perf() -> Perf {
    Perf { tscache: AtomicU64::new(0) }
}