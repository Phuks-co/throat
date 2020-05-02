from app import misc

def on_report(post, user, reason):
    text = "[\002Report\002] {0} (by {1}) | Reason: {2} | Reporter: https://cekni.to/u/{3} | https://cekni.to/p/{4}".format(post['title'], post['user'], reason, user.name, post['pid'])
    misc.sendMail('glob4list@gmail.com', 'Post reported on cekni.to', text)

def on_report_comment(comm, user, reason):
    text = "[\002Comment report\002] Reason: {1} | Reporter: https://cekni.to/u/{2} | https://cekni.to/c/{3}".format(comm.uid.name, reason, user.name, comm.cid)
    misc.sendMail('glob4list@gmail.com', 'Comment reported on cekni.to', text)

ON_POST_REPORT = on_report
ON_COMMENT_REPORT = on_report_comment