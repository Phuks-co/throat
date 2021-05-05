// Post page-related code.
import u from './Util';
import _ from './utils/I18n';


u.addEventForChild(document, 'click', '.close-report', function (e, qelem) {
  const errorbox = document.querySelector('.error');
  let action = qelem.getAttribute('data-action');
  let id = qelem.getAttribute('data-id');
  let type = qelem.getAttribute('data-type');

  if (type == "comment") {
    let uri = '/do/report/close_comment_report/' + id + '/' + action;
    u.post(uri, {},
      function (data) {
        if (data.status != "ok") {
          errorbox.style.display = 'block';
          errorbox.innerHTML = _('Error: %1', data.error);
        } else {
          window.location.reload();
        }
      }, function () {
        errorbox.style.display = 'block';
        errorbox.innerHTML = _('Could not contact the server');
      });
  }
  else {
    let uri = '/do/report/close_post_report/' + id + '/' + action;
    u.post(uri, {},
      function (data) {
        if (data.status != "ok") {
          errorbox.style.display = 'block';
          errorbox.innerHTML = _('Error: %1', data.error);
        } else {
          window.location.reload();
        }
      }, function () {
        errorbox.style.display = 'block';
        errorbox.innerHTML = _('Could not contact the server');
      });
  }
});

u.addEventForChild(document, 'click', '.banuserbutton', function (e, qelem) {
  let form = document.getElementById('report-ban-user-form');
  form.style.display = 'block';
});


u.addEventForChild(document, 'click', '.close-related-reports', function (e, qelem) {
  const errorbox = document.querySelector('.error');
  let reports = qelem.getAttribute('data-reports');
  let original_report = qelem.getAttribute('data-original')
  let type = qelem.getAttribute('data-type');

  if (type == "comment") {
    let uri = '/do/report/close_comment_related_reports/' + reports + '/' + original_report;
    u.post(uri, {},
      function (data) {
        if (data.status != "ok") {
          errorbox.style.display = 'block';
          errorbox.innerHTML = _('Error: %1', data.error);
        } else {
          window.location.reload();
        }
      }, function () {
        errorbox.style.display = 'block';
        errorbox.innerHTML = _('Could not contact the server');
      });
  }
  else {
    let uri = '/do/report/close_post_related_reports/' + reports + '/' + original_report;
    u.post(uri, {},
      function (data) {
        if (data.status != "ok") {
          errorbox.style.display = 'block';
          errorbox.innerHTML = _('Error: %1', data.error);
        } else {
          window.location.reload();
        }
      }, function () {
        errorbox.style.display = 'block';
        errorbox.innerHTML = _('Could not contact the server');
      });
  }
});


u.addEventForChild(document, 'change', '#flair_id', function (e, qelem) {
  if(qelem.value == '-1') {
    document.querySelector('#assign_flair_form #text').classList.remove('hide')
  } else {
    document.querySelector('#assign_flair_form #text').classList.add('hide')
  }
});


// Admin site configuration page

u.addEventForChild(document, 'click', '.admin-config-doc-toggle', function (e, qelem) {
    let docElem = document.getElementById(qelem.id + "-doc");
    if (docElem.classList.contains('hide')) {
        docElem.classList.remove('hide');
        qelem.innerHTML = "▿";
    } else {
        docElem.classList.add('hide')
        qelem.innerHTML = "▹";
    }
});

u.addEventForChild(document, 'click', '.admin-config-edit', function (e, qelem) {
  let name = qelem.getAttribute('data-setting');
  let valueElem = document.getElementById(name + '-value');
  let value = valueElem.innerText;

  const changeForm = document.querySelector('.admin-config-edit-form');
  let parent = changeForm.parentElement;
  let valueField = document.getElementById('value');
  let changeButton = document.getElementById('admin-config-edit-submit');
  const label = document.getElementById('bool-label');

  document.querySelector('.error').classList.add('hide');
  changeForm.querySelector('.div-error').style.display = 'none';

  if (valueElem != parent) {
    let oldValue = parent.getAttribute('data-old-value');
    let type = qelem.getAttribute('data-type');
    document.getElementById('setting').value = name;

    if (type == 'bool') {
      let isSet = value == _('Enabled');
      changeButton.innerHTML = isSet ? _('Disable') : _('Enable');
      valueField.value = isSet ? 'False' : 'True';
      valueField.classList.add('hide');
      label.classList.remove('hide');
      label.innerHTML = value;
    } else {
      changeButton.innerHTML = _('Change');
      valueField.value = value;
      valueField.classList.remove('hide');
      label.classList.add('hide');
    }
    valueElem.setAttribute('data-old-value', value);
    changeForm.classList.remove('hide');
    valueElem.innerHTML = "";
    valueElem.appendChild(changeForm);
    if (oldValue) {
      parent.innerHTML = oldValue;
    }
  }
});

u.addEventForChild(document, 'click', '#admin-config-edit-cancel', function (e, qelem) {
  const changeForm = document.querySelector('.admin-config-edit-form');
  let parent = changeForm.parentElement;
  let formContainer = document.getElementById('form-container');

  if (formContainer != parent) {
    let oldValue = parent.getAttribute('data-old-value');
    formContainer.appendChild(changeForm);
    changeForm.classList.add('hide')
    if (oldValue) {
      parent.innerHTML = oldValue;
    }
  }
});
