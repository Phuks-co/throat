import u from "../Util";

import {
  Platform,
  Client,
  LoadStatus,
  createNavigation,
  createRouter,
  RoomViewModel,
  TimelineView,
  viewClassForTile, TemplateView, MessageComposer
} from "hydrogen-view-sdk";
import downloadSandboxPath from 'hydrogen-view-sdk/asset-build/assets/download-sandbox.html';
import workerPath from 'hydrogen-view-sdk/asset-build/assets/main.js';

import olmWasmPath from '@matrix-org/olm/olm.wasm';
import olmJsPath from '@matrix-org/olm/olm.js';
import olmLegacyJsPath from '@matrix-org/olm/olm_legacy.js';

const assetPaths = {
  downloadSandbox: downloadSandboxPath,
  worker: workerPath,
  olm: {
    wasm: olmWasmPath,
    legacyBundle: olmLegacyJsPath,
    wasmBundle: olmJsPath
  }
};
import "hydrogen-view-sdk/asset-build/assets/theme-element-light.css";
import sdk from "matrix-js-sdk";

// import "hydrogen-view-sdk/asset-build/assets/theme-element-dark.css";


class CustomRoomView extends TemplateView {
  constructor(vm, viewClassForTile2) {
    super(vm);
    this._viewClassForTile = viewClassForTile2;
  }

  render(t, vm) {
    return t.main({className: "RoomView middle"}, [
      t.div({className: "RoomView_body"}, [
        t.div({className: "RoomView_error"}, (vm2) => vm2.error),
        t.mapView((vm2) => vm2.timelineViewModel, (timelineViewModel) => {
          return timelineViewModel ? new TimelineView(timelineViewModel, this._viewClassForTile) : new TimelineLoadingView(vm);
        }),
        t.mapView((vm2) => vm2.composerViewModel, (composerViewModel) => {
          switch (composerViewModel == null ? void 0 : composerViewModel.kind) {
            case "composer":
              return new MessageComposer(vm.composerViewModel, this._viewClassForTile);
            case "disabled":
              return new DisabledComposerView(vm.composerViewModel);
          }
        })
      ]),
    ]);
  }
}


async function main(homeServerUrl, roomId) {
  const app = document.querySelector('#chpop')

  // Fix buggy popup menus
  function fixMenu(menu, retry, force) {
    if (!menu) return
    let top = menu.style.top
    if (!top || force) {
      menu.style.display = "block";
      let menu_rect = menu.getBoundingClientRect();
      let menu_width = menu_rect.width;
      let menu_height = menu_rect.height
      menu.style.display = "none";

      console.log("Found topless element. Last Clickety:", window._lastClickety, retry)
      if (!window._lastClickety || window._lastClickety.getBoundingClientRect().left === 0) {
        // Shit's not populated. Wait a bit and retry
        if (retry < 10) {
          setTimeout(() => fixMenu(menu, retry + 1), 10)
        }
        return
      }

      // button bounding rect
      let button_rect = window._lastClickety.getBoundingClientRect();
      let dom_rect = document.documentElement.getBoundingClientRect();

      // Check if we should put this below or above the clicked button
      if ((button_rect.left + menu_width) > dom_rect.width) {
        menu.style.left = (button_rect.left - menu_width) + 'px'
      } else {
        menu.style.left = button_rect.left + 'px'
      }

      if ((button_rect.top + menu_height) > dom_rect.height) {
        menu.style.top = (button_rect.top - menu_height) + 'px'
      } else {
        menu.style.top = button_rect.top + 'px'
      }
      menu.style.display = "block";
    }
  }

  let x = new MutationObserver(function (e) {
    if (e[0].addedNodes) {
      if (e[0].addedNodes[0] && e[0].addedNodes[0].classList[0] === "popupContainer") {
        fixMenu(e[0].addedNodes[0].firstChild, 0)
        let x = new MutationObserver(function (e) {
          if (e[0].addedNodes) {
            fixMenu(e[0].addedNodes[0], 0)
          }
        });
        x.observe(e[0].addedNodes[0], {childList: true});
      }
    }
  });

  u.addEventForChild(app, 'click', 'button', function (e, qelem) {
    if (qelem.classList[0] === "Timeline_messageOptions") {
      window._lastClickety = qelem
    } else if (qelem.classList[0] === "sendFile") {
      window._lastClickety = qelem
      // remove the broken "icon" class....
      setTimeout(() => {
        u.each(".popupContainer .menu .icon", (e) => {
          e.classList.remove("icon")
        })
        fixMenu(document.querySelector(".popupContainer .menu"), 0, true)
      }, 20)
    }
  })
  // /buggy popup fix

  x.observe(document.getElementById("chpop"), {childList: true});

  const config = {};
  // XXX: Hack because we cannot load the wasm as a file :(
  await window.Olm.init()
  const platform = new Platform({container: app, assetPaths, config, options: {development: true}});
  platform._olmPromise = window.Olm
  const navigation = createNavigation();
  platform.setNavigation(navigation);
  const urlRouter = createRouter({
    navigation: navigation,
    history: platform.history
  });
  urlRouter.attach();
  const client = new Client(platform);

  let db = indexedDB.open("test");
  let can_use_indexeddb = true;
  db.onerror = () => {
    can_use_indexeddb = false;
  }
  await new Promise(r => setTimeout(r, 10));

  if(!can_use_indexeddb) {
    document.getElementById('chloading').innerHTML = '<p>Fatal error: Cannot use IndexedDB.</p>'
    document.getElementById('chloading').innerHTML += '<p>(this is a known bug on private mode in Firefox)</p>'
    document.getElementById('chloading').innerHTML += '<p>Cannot load chat client.</p>'
    return
  }

  // Check if we're already logged in.....
  const sessions = await client._platform.sessionInfoStorage.getAll();

  let session_id;

  if (sessions.length === 0) {
    const clock = client._platform.clock;
    document.getElementById('chloading').innerText = "Fetching token..."

    const authData = await fetch('/auth/matrix', {method: 'POST', credentials: 'include'})
    if(authData.status !== 200) {
      document.getElementById('chloading').innerText = `Could not fetch tokens (Status ${authData.status})`
      return;
    }
    const loginToken = await authData.json()
    document.getElementById('chloading').innerText = "Logging in...."

    const matrixClient = sdk.createClient({
      baseUrl: homeServerUrl
    });

    const matrixAccessToken = await matrixClient.loginWithToken(loginToken.token)
    document.getElementById('chloading').innerText = "Loading session..."

    let sessionInfo = {
      id: client.createNewSessionId(),
      deviceId: "throat chat",
      userId: matrixAccessToken.user_id,
      homeServer: homeServerUrl,
      homeserver: homeServerUrl,
      accessToken: matrixAccessToken.access_token,
      lastUsed: clock.now()
    };

    await client._platform.logger.run("login", async (log) => {
      await client._platform.sessionInfoStorage.add(sessionInfo);
      await client._loadSessionInfo(sessionInfo, null, log);
    })

    session_id = sessionInfo.id;
  } else {
    const sess = sessions[0]
    await client.startWithExistingSession(sess.id)
    session_id = sess.id;
  }

  await client.loadStatus.waitFor((status) => {
    return status === LoadStatus.Ready ||
      status === LoadStatus.Error ||
      status === LoadStatus.LoginFailed;
  }).promise;

  if (client.loginFailure) {
    document.getElementById('chloading').innerText = "Login Failed: " + client.loginFailure
  } else if (client.loadError) {
    document.getElementById('chloading').innerHTML = "Load Failed: " + client.loadError.message
    await client.startLogout(session_id)
    document.getElementById('chloading').innerHTML += "<p>The session has been purged. Reload the page and retry.</p>"
  } else {
    const {session} = client;
    // looks for room corresponding to #element-dev:matrix.org, assuming it is already joined
    const room = session.rooms.get(roomId);
    console.log("all good?")
    const vm = new RoomViewModel({
      room,
      ownUserId: session.userId,
      platform,
      urlCreator: urlRouter,
      navigation,
    });
    await vm.load();
    const view = new CustomRoomView(vm, viewClassForTile);
    app.appendChild(view.mount());
    document.getElementById("chloading").parentNode.removeChild(document.getElementById("chloading"))
    window.isChatLoaded = true;

  }
}

export function loadChat() {
  const homeServerUrl = document.getElementById('matrix-homeserver').getAttribute('data-value')
  const roomId = document.getElementById('matrix-roomId').getAttribute('data-value')
  document.getElementById('chloading').innerText = "Logging in..."
  main(homeServerUrl, roomId)
}
