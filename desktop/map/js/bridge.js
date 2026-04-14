(function () {
  'use strict';

  new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge;
  });
})();

