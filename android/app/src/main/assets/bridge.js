(function () {
  if (window.pywebview) return;
  const pending = new Map();
  let seq = 0;
  window.__bridgeResolve = (id, json) => {
    const resolve = pending.get(id);
    pending.delete(id);
    if (resolve) resolve(JSON.parse(json));
  };
  const api = new Proxy({}, {
    get: (_, method) => (...args) => new Promise((resolve) => {
      const id = ++seq;
      pending.set(id, resolve);
      AndroidBridge.call(id, String(method), JSON.stringify(args));
    })
  });
  window.pywebview = { api };
  window.dispatchEvent(new Event('pywebviewready'));
})();
