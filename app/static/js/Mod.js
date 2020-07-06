// Post page-related code.
import u from './Util';
import _ from './utils/I18n';


u.addEventForChild(document, 'click', '.close-report', function (e, qelem) {
  let pid = qelem.getAttribute('data-pid');
  let uri = '/do/report/close_post_report/' + pid;

  if (!pid) {
    console.log("COMMENT REPORT")
    return;
  }
  u.post(uri, {},
      function (data) {
          if (data.status != "ok") {
              errorbox.style.display = 'block';
              errorbox.innerHTML = _('Error: %s', data.error);
              qelem.removeAttribute('disabled');
          } else {
              qelem.parentNode.parentNode.parentNode.innerHTML = _('Your report has been sent and will be reviewed by the site administrators.');
          }
      }, function () {
          errorbox.style.display = 'block';
          errorbox.innerHTML = _('Could not contact the server');
          qelem.removeAttribute('disabled');
      });

  console.log("CLOSED REPORT");
});
