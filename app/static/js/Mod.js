// Post page-related code.
import u from './Util';
import _ from './utils/I18n';


u.addEventForChild(document, 'click', '.close-report', function (e, qelem) {
  let id = qelem.getAttribute('data-id');
  let type = qelem.getAttribute('data-type');
  let uri = '/do/report/close_post_report/' + id;

  if (type == "comment") {
    console.log("COMMENT REPORT")
    return;
  }
  u.post(uri, {},
      function (data) {
          if (data.status == "ok") {
            console.log("CLOSED REPORT");
          } else {
            console.log("FAILED");
          }}
      // }, function () {
      //     errorbox.style.display = 'block';
      //     errorbox.innerHTML = _('Could not contact the server');
      // }
    );
});
